import datetime
import logging

# from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient
from fastapi import APIRouter, HTTPException, status as status_code, Depends
from jsonschema import ValidationError
from starlette import status
from typing import Any, Dict, List

from api.dependencies.database import get_repository
from db.repositories.workspaces import WorkspaceRepository
from services import data_move
from core import credentials
from models.domain.authentication import User
from models.domain.data_move_transactions import DataMoveTransactions, DataMoveFile
from models.domain.workspace import Workspace
from db.repositories.data_move import DataMoveRepository
from models.schemas.data_move_transactions import (
    DataMoveFile,
    DataMoveTransactionRequest,
    DataMoveTransactionResponse,
    DataMoveTransactionResponseList,
)
from resources import strings
from core import config

from api.dependencies.workspaces import (
    get_workspace_by_id_from_path,
    get_deployed_workspace_by_id_from_path,
)
from services.authentication import (
    get_current_workspace_owner_or_researcher_user,
    get_current_tre_user_or_tre_admin,
)
from services.data_usage import DataUsageService, data_usage_service_factory

datamove_workspace_router = APIRouter(
    dependencies=[Depends(get_current_workspace_owner_or_researcher_user)]
)

datamove_core_router = APIRouter(
    dependencies=[Depends(get_current_tre_user_or_tre_admin)]
)


# -------------------------
# CREATE REQUEST
# -------------------------
@datamove_workspace_router.post(
    "/workspaces/{workspace_id}/data_move/requests",
    status_code=status_code.HTTP_201_CREATED,
    response_model=DataMoveTransactionResponse,
    name=strings.API_CREATE_DATA_MOVE_REQUEST,
    dependencies=[
        Depends(get_current_workspace_owner_or_researcher_user),
        Depends(get_workspace_by_id_from_path),
    ],
)
async def create_draft_request(
    datamove_request_input: DataMoveTransactionRequest,
    user=Depends(get_current_workspace_owner_or_researcher_user),
    datamove_request_repo=Depends(get_repository(DataMoveRepository)),
    workspaceRepo=Depends(get_repository(WorkspaceRepository)),
    workspace=Depends(get_deployed_workspace_by_id_from_path),
    data_usage_service: DataUsageService = Depends(data_usage_service_factory),
) -> DataMoveTransactionResponse:

    try:
        workspace_template_name = await workspaceRepo.get_workspace_type_by_id(workspace.id)
        if not workspace_template_name == strings.E_MSL_WORKSPACE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Data Move operations can only be initiated from Explore workspace. Workspace {workspace.id} is of type {workspace_template_name}."
            )


        emsl_protocol_id = datamove_request_input.protocol_id + "e"
        members: List[Dict[str, Any]] = await data_usage_service.get_group_members(emsl_protocol_id, workspace.id)

        # Extract and normalize member emails for consistent comparison
        members_emails_lower = {member.get("mail", "").lower() for member in (members or []) if member.get("mail")}

        workspace_owner_email = workspace.user.get("email") if isinstance(workspace.user, dict) else workspace.user.email
        workspace_owner_email = (workspace_owner_email or "").lower()

        if workspace_owner_email not in members_emails_lower:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User {workspace_owner_email} is not a member of the protocol {emsl_protocol_id} group. Data Move request cannot be created.",
            )

        workspace_asml = await workspaceRepo.get_asml_workspace(workspace.id)
        if not workspace_asml:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Associated AMSL workspace not found for workspace {workspace.id}. Data Move request cannot be created.",
            )

        datamove_request: DataMoveTransactions = datamove_request_repo.create_datamove_request_item(
                emsl_protocol_id=emsl_protocol_id,
                workspace_id=workspace.id,
                user=user,
            )

        logging.info(f"Created data move request with id {datamove_request.id} for workspace {workspace.id} and protocol {datamove_request.protocol_id}")

        files: List[DataMoveFile] = await data_move.get_files(workspace.id, emsl_protocol_id)
        logging.info(f"Retrieved {len(files)} files for data move request with id {datamove_request.id} for workspace {workspace.id} and protocol {datamove_request.protocol_id}")

        total_size: float = sum(file.file_size for file in files) if files else 0.0
        total_size_gb: float = total_size / (1024 * 1024 * 1024)
        datamove_request.files_size = total_size_gb
        datamove_request.files = files

        datamove_request.amsl_workspace_id = workspace_asml.id
        amsl_protocol_id: str = datamove_request_input.protocol_id + "a"
        datamove_request.amsl_protocol_id = amsl_protocol_id

        await save_and_publish_event_datamove_request(
            datamove_request=datamove_request,
            datamove_request_repo=datamove_request_repo,
            user=user,
            workspace=workspace,
        )

        return DataMoveTransactionResponse(
            transaction_id=datamove_request.id,
            workspace_id=datamove_request.workspaceId,
            protocol_id=datamove_request.protocol_id,
            file_size=datamove_request.files_size,
            date_time=datamove_request.date_time,
            status=datamove_request.status,
        )

    except (ValidationError, ValueError) as e:
        logging.exception("Failed creating data move request")
        raise HTTPException(
            status_code=status_code.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# -------------------------
# GET ALL REQUESTS
# -------------------------
@datamove_workspace_router.get(
    "/workspaces/{workspace_id}/data_move/history",
    status_code=status_code.HTTP_200_OK,
    response_model=DataMoveTransactionResponseList,
    name=strings.API_LIST_DATA_MOVE_REQUESTS,
    dependencies=[
        Depends(get_current_workspace_owner_or_researcher_user),
        Depends(get_workspace_by_id_from_path),
    ],
)
async def get_all_datamove_requests_by_workspace(
    datamove_request_repo=Depends(get_repository(DataMoveRepository)),
    workspace=Depends(get_deployed_workspace_by_id_from_path),
) -> DataMoveTransactionResponseList:

    try:
        datamove_requests = await datamove_request_repo.get_datamove_requests(
            workspace_id=workspace.id
        )

        return DataMoveTransactionResponseList(
            dataMoveTransactions=[
                DataMoveTransactionResponse(
                    transaction_id=req.id,
                    workspace_id=req.workspaceId,
                    protocol_id=req.protocol_id,
                    file_size=req.files_size,
                    date_time=req.date_time,
                    status=req.status,
                )
                for req in datamove_requests
            ]
        )

    except (ValidationError, ValueError) as e:
        logging.exception(
            "Failed retrieving all the data move requests for a workspace"
        )
        raise HTTPException(
            status_code=status_code.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# -------------------------
# SAVE + PUBLISH EVENT
# -------------------------
async def save_and_publish_event_datamove_request(
    datamove_request: DataMoveTransactions,
    datamove_request_repo: DataMoveRepository,
    user: User,
    workspace: Workspace,
):
    try:
        logging.debug(f"Saving data move request item: {datamove_request.id}")

        datamove_request.updatedBy = user
        datamove_request.updatedWhen = get_timestamp()

        await datamove_request_repo.save_item(datamove_request)

    except Exception:
        logging.exception(
            f"Failed saving data move request {datamove_request}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING,
        )

    try:
        logging.debug(
            f"Sending status changed event for data move request item: {datamove_request.id}"
        )

        await send_status_changed_event(datamove_request)

    except Exception:
        logging.exception("Failed sending status_changed message")

        # rollback (optional strategy — consider marking failed instead)
        await datamove_request_repo.delete_item(datamove_request.id)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=strings.EVENT_GRID_GENERAL_ERROR_MESSAGE,
        )


# -------------------------
# SERVICE BUS EVENT
# -------------------------
async def send_status_changed_event(datamove_request: DataMoveTransactions):
    message = ServiceBusMessage(
        body=datamove_request.json(),
        correlation_id=str(datamove_request.id),
        session_id=str(datamove_request.workspaceId),
    )

    async with credentials.get_credential_async() as credential:
        service_bus_client = ServiceBusClient(
            config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE,
            credential,
        )

        async with service_bus_client:
            sender = service_bus_client.get_queue_sender(
                queue_name=config.SERVICE_BUS_DATA_MOVE_QUEUE_NAME
            )

            async with sender:
                await sender.send_messages(message)



def get_timestamp() -> float:
    return datetime.datetime.utcnow().timestamp()
