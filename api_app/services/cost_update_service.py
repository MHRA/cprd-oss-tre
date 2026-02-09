from datetime import datetime, timedelta
import asyncio
import logging
import random
from uuid import uuid4

from azure.core.exceptions import HttpResponseError
from azure.data.tables import TableServiceClient, UpdateMode

from services.async_rate_limiter import AsyncRateLimiter
from services.cost_service import cost_service_factory
from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.workspaces import WorkspaceRepository
from api.dependencies.database import get_db_client
from models.domain.costs import GranularityEnum, WorkspaceCostReport
from core import config, credentials
from resources import constants


# ----------------------------
# Retry wrapper for Azure Cost API
# ----------------------------
async def query_cost_with_retry(
    fn,
    *,
    workspace_id: str,
    max_retries: int = 5
):
    delay = 10

    for attempt in range(1, max_retries + 1):
        try:
            return await fn()

        except HttpResponseError as e:
            if e.status_code != 429:
                raise

            retry_after = e.response.headers.get("Retry-After")
            wait_time = int(retry_after) if retry_after else delay
            wait_time += random.uniform(0, 2)

            logging.info(
                f"Azure Cost API throttled (429) for workspace {workspace_id}. "
                f"Retrying in {wait_time:.1f}s "
                f"(attempt {attempt}/{max_retries})"
            )

            await asyncio.sleep(wait_time)
            delay = min(delay * 2, 300)

    raise RuntimeError(
        f"Exceeded max retries for Azure Cost API (workspace {workspace_id})"
    )


# ----------------------------
# Main job
# ----------------------------
async def update_workspace_costs(app):
    cost_service = cost_service_factory()
    db_client = await get_db_client(app)

    user_resource_repo = await UserResourceRepository.create(db_client)
    workspace_repo = await WorkspaceRepository.create(db_client)
    workspace_services_repo = await WorkspaceServiceRepository.create(db_client)

    granularity = GranularityEnum.daily
    yesterday = datetime.utcnow() - timedelta(days=1)

    from_date = yesterday.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    to_date = yesterday.replace(
        hour=23, minute=59, second=59, microsecond=0
    )

    account_name = constants.STORAGE_ACCOUNT_NAME_CORE_RESOURCE_GROUP.format(
        config.TRE_ID
    )
    account_endpoint = f"https://{account_name}.table.core.windows.net"

    table_service_client = TableServiceClient(
        endpoint=account_endpoint,
        credential=credentials.get_credential(),
        headers={"ClientType": config.CLIENT_TYPE_CUSTOM_HEADER},
    )

    table_client = table_service_client.get_table_client(
        table_name=constants.WORKSPACE_COSTS_TABLE_NAME
    )

    workspaces = await workspace_repo.get_active_workspaces()

    # Azure Cost API–safe pacing
    rate_limiter = AsyncRateLimiter(interval_seconds=60)

    loop = asyncio.get_running_loop()

    for workspace in workspaces:
        logging.info(
            f"Updating workspace costs for workspace {workspace.id}"
        )

        # Enforce spacing BEFORE API call
        await rate_limiter.wait()

        try:
            report: WorkspaceCostReport = await query_cost_with_retry(
                lambda: cost_service.query_tre_workspace_costs(
                    workspace_id=workspace.id,
                    granularity=granularity,
                    from_date=from_date,
                    to_date=to_date,
                    workspace_repo=workspace_repo,
                    workspace_services_repo=workspace_services_repo,
                    user_resource_repo=user_resource_repo,
                ),
                workspace_id=workspace.id,
            )

            report_json = report.json()
            size_bytes = len(report_json.encode("utf-8"))

            # Azure Table Storage limit: 64KB per property
            if size_bytes > 64000:
                logging.error(
                    f"WorkspaceCosts too large for Table Storage "
                    f"(workspace={workspace.id}, size={size_bytes} bytes)"
                )
                continue

            entity = {
                "PartitionKey": "None",
                "RowKey": str(uuid4()),
                "Timestamp": datetime.utcnow().isoformat() + "Z",
                "FromDate": from_date,
                "ToDate": to_date,
                "WorkspaceCosts": report_json,
                "WorkspaceId": workspace.id,
            }

            # Table SDK is synchronous → offload to executor
            await loop.run_in_executor(
                None,
                table_client.upsert_entity,
                entity,
                UpdateMode.MERGE,
            )

            logging.info(
                f"Workspace costs stored successfully for workspace {workspace.id}"
            )

        except Exception:
            logging.exception(
                f"Failed to update workspace costs for workspace {workspace.id}"
            )
