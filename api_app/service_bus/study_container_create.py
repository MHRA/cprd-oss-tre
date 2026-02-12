import asyncio
import json
import uuid
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Callable, Awaitable
from datetime import datetime, timezone

from azure.servicebus.aio import ServiceBusClient, AutoLockRenewer
from azure.servicebus.exceptions import OperationTimeoutError, ServiceBusConnectionError
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets.aio import SecretClient
from azure.storage.blob.aio import BlobServiceClient
from azure.data.tables import TableServiceClient, UpdateMode
from azure.mgmt.authorization import AuthorizationManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.core.exceptions import ResourceExistsError, HttpResponseError
from azure.core.exceptions import ResourceNotFoundError
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from azure.servicebus import NEXT_AVAILABLE_SESSION

from msgraph import GraphServiceClient
from msgraph.generated.models.group import Group

from api.dependencies.database import get_db_client
from core import config, credentials
from resources import constants
from models.schemas.container_reation_request import ContainerCreateRequest, EntraGroup
from db.repositories.workspaces import WorkspaceRepository


# =========================================================
# Saga infrastructure
# =========================================================

@dataclass
class ProvisioningSagaContext:
    workspace_id: str
    protocol_id: str

    container_name: Optional[str] = None
    group_id: Optional[str] = None
    role_assignment_id: Optional[str] = None
    suffix: Optional[str] = None

    compensations: List[Callable[[], Awaitable[None]]] = field(default_factory=list)


class SagaFailed(Exception):
    pass


class ProvisioningSaga:
    def __init__(self, ctx: ProvisioningSagaContext):
        self.ctx = ctx

    async def run(self, steps: List[Callable[[], Awaitable[None]]]):
        try:
            for step in steps:
                await step()
        except Exception as exc:
            await self._rollback()
            raise SagaFailed("Provisioning saga failed") from exc

    async def _rollback(self):
        for compensate in reversed(self.ctx.compensations):
            try:
                await compensate()
            except Exception:
                logging.exception("Saga compensation failed")


# =========================================================
# Main service
# =========================================================

class StudyContainerProvisioningService:
    def __init__(self, app):
        self.app = app

    # ----------------------------
    # Entrypoint
    # ----------------------------
    def run(self, *args, **kwargs):
        asyncio.run(self.receive_messages())

    async def init_repos(self):
        db_client = await get_db_client(self.app)
        self.workspace_repo = await WorkspaceRepository.create(db_client)

        self.scope = f"/subscriptions/{config.SUBSCRIPTION_ID}"

        account_name = constants.STORAGE_ACCOUNT_NAME_CORE_RESOURCE_GROUP.format(
            config.TRE_ID
        )
        endpoint = f"https://{account_name}.table.core.windows.net"

        self.table_service = TableServiceClient(
            endpoint=endpoint,
            credential=credentials.get_credential(),
            headers={"ClientType": config.CLIENT_TYPE_CUSTOM_HEADER},
        )

        self.graph_client = await self._init_graph_client()

    # ----------------------------
    # Service Bus
    # ----------------------------
    async def receive_messages(self):
        queue_name = config.SERVICE_BUS_STUDY_CONTAINER_CREATE_QUEUE_NAME
        while True:
            try:
                async with credentials.get_credential_async() as credential:
                    service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)

                    logging.info(f"Looking for new session... {queue_name}")
                    # max_wait_time=1 -> don't hold the session open after processing of the message has finished
                    async with service_bus_client.get_queue_receiver(queue_name=queue_name, max_wait_time=1, session_id=NEXT_AVAILABLE_SESSION) as receiver:
                        logging.info(f"Got a session containing messages: {receiver.session.session_id}")
                        async with AutoLockRenewer() as renewer:
                            renewer.register(receiver, receiver.session, max_lock_renewal_duration=60)
                            async for msg in receiver:
                                complete_message = await self._handle_queue_message(msg)
                                if complete_message:
                                    await receiver.complete_message(msg)
                                else:
                                    # could have been any kind of transient issue, we'll abandon back to the queue, and retry
                                    await receiver.abandon_message(msg)
                        logging.info(f"Closing session: {receiver.session.session_id}")

            except OperationTimeoutError:
                # Timeout occurred whilst connecting to a session - this is expected and indicates no non-empty sessions are available
                logging.debug("No sessions for this process. Will look again...")

            except ServiceBusConnectionError:
                # Occasionally there will be a transient / network-level error in connecting to SB.
                logging.info("Unknown Service Bus connection error. Will retry...")

            except Exception as e:
                # Catch all other exceptions, log them via .exception to get the stack trace, and reconnect
                logging.exception(f"Unknown exception. Will retry - {e}")


    async def _handle_queue_message(self, message) -> bool:
        try:
            logging.info(f"Handle queue message for queue")
            body = b"".join(message.body)
            payload = json.loads(body.decode("utf-8"))
            request = ContainerCreateRequest(**payload)

            await self.provision_study_container(request)
            return True

        except Exception:
            logging.exception("Failed to process queue message")
            return False

    # =====================================================
    # Saga Orchestration
    # =====================================================
    async def provision_study_container(self, request: ContainerCreateRequest):
        workspace = await self.workspace_repo.get_workspace_by_id(
            request.workspaceId
        )

        ctx = ProvisioningSagaContext(
            workspace_id=request.workspaceId,
            protocol_id=request.protocolId,
        )

        saga = ProvisioningSaga(ctx)

        try:
            await self.set_perstudy_items(
                request.workspaceId,
                request.protocolId,
                status="In Progress",
            )
            await saga.run(
                [
                    lambda: self.saga_create_container(ctx, request, workspace),
                    lambda: self.saga_create_group(ctx, request),
                    lambda: self.saga_assign_role(ctx, request),
                    lambda: self.saga_update_table(ctx, request),  # success case
                ]
            )

        except Exception:
            logging.exception(
                "Provisioning failed for workspace=%s protocol=%s",
                request.workspaceId,
                request.protocolId,
            )

            #  Update table with failure status
            await self.set_perstudy_items(
                request.workspaceId,
                request.protocolId,
                status="Failed",
            )

            raise  # re-raise so Service Bus can abandon message


    # =====================================================
    # Saga Steps
    # =====================================================
    async def saga_create_container(self, ctx, request, workspace):
        logging.info(f"Creating container for protocol {request.protocolId}")
        result = await self._create_container(request, workspace)
        logging.info(f"Container created: {result['name']} with folders {result['folders']}")
        ctx.container_name = result["name"]
        suffix = result["name"][-1]
        ctx.suffix = suffix
        async def compensate():
            await self._delete_container(request.workspaceId, ctx.container_name)

        ctx.compensations.append(compensate)

    async def saga_create_group(self, ctx, request):
        logging.info(f"Creating Entra group for protocol {request.protocolId}")
        group = await self._create_group(request)
        logging.info(f"Entra group created: {group.display_name} (id={group.id})")
        ctx.group_id = group.id

        async def compensate():
            await self.graph_client.groups.by_group_id(group.id).delete()

        ctx.compensations.append(compensate)

    async def saga_assign_role(self, ctx, request):
        logging.info(f"Assigning RBAC role to group {ctx.group_id} for container {ctx.container_name}")
        max_retries = 3
        delay = 2  # seconds

        for attempt in range(1, max_retries + 1):
            try:
                # ------------------------------------
                # 1. Verify container exists
                # ------------------------------------
                await self._assert_container_exists(
                    workspace_id=request.workspaceId,
                    container_name=ctx.container_name,
                )

                # ------------------------------------
                # 2. Verify Entra group exists
                # ------------------------------------
                await self._assert_group_exists(ctx.group_id)

                # ------------------------------------
                # 3. Assign role
                # ------------------------------------
                await asyncio.sleep(20)
                assignment_id = await self._assign_role_to_group(
                    request.workspaceId,
                    ctx.group_id,
                    ctx.suffix,
                )

                ctx.role_assignment_id = assignment_id

                async def compensate():
                    client = AuthorizationManagementClient(
                        credentials.get_credential(),
                        config.SUBSCRIPTION_ID,
                    )
                    client.role_assignments.delete_by_id(assignment_id)

                ctx.compensations.append(compensate)
                return  # success → exit saga step

            except Exception as exc:
                logging.warning(
                    "RBAC assignment attempt %s/%s failed "
                    "(workspace=%s, container=%s, group=%s)",
                    attempt,
                    max_retries,
                    request.workspaceId,
                    ctx.container_name,
                    ctx.group_id,
                )

                if attempt == max_retries:
                    logging.error(
                        "RBAC assignment failed after %s attempts",
                        max_retries,
                    )
                    raise

                await asyncio.sleep(delay)
                delay *= 2  # exponential backoff


    async def saga_update_table(self, ctx, request):
        await self.set_perstudy_items(
            request.workspaceId,
            ctx.container_name,
            status="Success"
        )

    # =====================================================
    # Container
    # =====================================================
    async def _create_container(self, request, workspace):
        account_name = constants.STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS.format(
            request.workspaceId[-4:]
        )

        container_name = request.protocolId.lower()  # must be lowercase
        suffix = container_name[-1]

        service_client = BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net/",
            credential=credentials.get_credential(),
        )

        async with service_client:
            # Create container
            try:
                await service_client.create_container(container_name)
            except ResourceExistsError:
                pass

            # Get container client (THIS is what you were missing)
            container_client = service_client.get_container_client(container_name)

            # Retry until container is available
            max_retries = 5
            retry_delay = 2

            for attempt in range(max_retries):
                try:
                    await container_client.get_container_properties()
                    break
                except ResourceNotFoundError:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                    else:
                        logging.error(
                            f"Container was not found after creation: {container_name}"
                        )
                        raise

            # Create folder placeholders
            folders = [
                f"Type1{suffix}",
                f"Type2{suffix}",
                f"ReceiveFromExplore{suffix}"
                if suffix == "a"
                else f"SendToAnalyse{suffix}",
            ]

            for folder in folders:
                blob_name = f"{folder}/.emptyFile"
                await container_client.upload_blob(
                    name=blob_name,
                    data=b"",
                    overwrite=True,
                )

        return {"name": container_name, "folders": folders}

    async def _delete_container(self, workspace_id, container_name):
        account_name = constants.STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS.format(
            workspace_id[-4:]
        )

        client = BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net/",
            credential=credentials.get_credential(),
        )

        async with client:
            await client.delete_container(container_name)

    # =====================================================
    # Entra ID / Graph
    # =====================================================
    async def _init_graph_client(self):
        tenant_id = config.AAD_TENANT_ID
        vault = constants.CORE_KEYVAULT_NAME.format(config.TRE_ID)

        client_id, client_secret = await asyncio.gather(
            self._fetch_secret(
                "ssbs-management-app-registration-client-id", vault
            ),
            self._fetch_secret(
                "ssbs-management-app-registration-client-secret", vault
            ),
        )

        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

        return GraphServiceClient(credentials=credential)

    async def _create_group(self, request) -> EntraGroup:
        name = f"Researcher_Data_Access_{request.protocolId}"

        group = Group(
            display_name=name,
            mail_enabled=False,
            mail_nickname=name,
            security_enabled=True,
        )

        created = await self.graph_client.groups.post(group)

        return EntraGroup(
            id=created.id,
            display_name=created.display_name,
            mail_nickname=created.mail_nickname,
            security_enabled=created.security_enabled,
        )

    # =====================================================
    # RBAC
    # =====================================================
    async def _assign_role_to_group(self, workspace_id, group_id,suffix) -> str:
        credential = credentials.get_credential()
        subscription_id = config.SUBSCRIPTION_ID

        storage = await self._get_storage_account(credential, workspace_id)
        role_id = await self._get_role_definition_id(
            credential, subscription_id
        )

        client = AuthorizationManagementClient(
            credential, subscription_id
        )

        assignment_id = str(uuid.uuid4())

        client.role_assignments.create(
            scope=storage.id,
            role_assignment_name=assignment_id,
            parameters={
                "role_definition_id": (
                    f"/subscriptions/{subscription_id}"
                    f"/providers/Microsoft.Authorization/roleDefinitions/{role_id}"
                ),
                "principal_id": group_id,
                "condition": self._build_expression(suffix),
                "condition_version": "2.0",
            },
        )

        return assignment_id

    async def _get_storage_account(self, credential, workspace_id):
        client = StorageManagementClient(
            credential, config.SUBSCRIPTION_ID
        )

        rg = constants.WORKSPACE_RESOURCE_GROUP_NAME.format(
            config.TRE_ID, workspace_id[-4:]
        )
        name = constants.STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS.format(
            workspace_id[-4:]
        )

        return client.storage_accounts.get_properties(rg, name)

    async def _get_role_definition_id(self, credential, subscription_id):
        client = AuthorizationManagementClient(
            credential, subscription_id
        )

        role_name = "Workspace Researcher Blob Data Contributor"

        for rd in client.role_definitions.list(
            f"/subscriptions/{subscription_id}"
        ):
            if rd.role_name == role_name:
                return rd.id.split("/")[-1]

        raise RuntimeError(f"Role not found: {role_name}")

    def _build_expression(self,suffix):
        action = (
            "Microsoft.Storage/storageAccounts/"
            "blobServices/containers/blobs/delete"
        )

        paths = [f"SendToAnalyse{suffix}", f"Type1{suffix}", f"Type2{suffix}"]

        parts = [f"ActionMatches{{'{action}'}}"]
        parts += [
            (
                "NOT "
                "@Resource[Microsoft.Storage/"
                "storageAccounts/blobServices/containers/blobs:path] "
                f"StringLike '{p}/*'"
            )
            for p in paths
        ]

        return f"({' && '.join(parts)})"

    # =====================================================
    # Key Vault
    # =====================================================
    async def _fetch_secret(self, name, vault):
        client = SecretClient(
            vault_url=f"https://{vault}.vault.azure.net/",
            credential=credentials.get_credential(),
        )

        async with client:
            secret = await client.get_secret(name)
            return secret.value

    # =====================================================
    # Table Storage
    # =====================================================
    async def set_perstudy_items(self, workspaceId, protocolId,status="Success"):
        table = constants.WORKSPACE_PERSTUDY_USAGE_TABLE_NAME

        client = self.table_service.get_table_client(table)

        params = {
            "WorkspaceId": workspaceId,
            "ProtocolId": protocolId,
        }

        filter_expr = (
            "WorkspaceId eq @WorkspaceId and "
            "ProtocolId eq @ProtocolId"
        )

        try:
            entities = client.query_entities(
                query_filter=filter_expr,
                parameters=params,
            )

            for entity in entities:
                entity["Timestamp"] = datetime.now(
                    timezone.utc
                ).isoformat()
                entity["Latest"] = True
                entity["Status"] = status

                client.upsert_entity(
                    entity=entity,
                    mode=UpdateMode.MERGE,
                )

        except HttpResponseError:
            logging.exception(
                "Table update failed: workspace=%s protocol=%s",
                workspaceId,
                protocolId,
            )
            raise

    # =====================================================
    # Container existence check
    # =====================================================
    async def _assert_container_exists(self, workspace_id, container_name):
        account_name = constants.STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS.format(
            workspace_id[-4:]
        )

        client = BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net/",
            credential=credentials.get_credential(),
        )

        async with client:
            container = client.get_container_client(container_name)
            try:
                await container.get_container_properties()
            except ResourceNotFoundError:
                raise RuntimeError(
                    f"Container does not exist: {container_name}"
                )

    # =====================================================
    # Group existence check
    # =====================================================
    async def _assert_group_exists(self, group_id: str):
        try:
            await self.graph_client.groups.by_group_id(group_id).get()
        except ODataError:
            raise RuntimeError(
                f"Entra group does not exist: {group_id}"
            )
