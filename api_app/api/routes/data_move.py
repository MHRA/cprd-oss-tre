import json
import logging
from dateutil.relativedelta import relativedelta # type: ignore
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, status as status_code
from jsonschema import ValidationError # type: ignore

from api_app.api.dependencies.workspaces import get_deployed_workspace_by_id_from_path, get_workspace_by_id_from_path
from api_app.models.schemas.DataMove import DataMoveRequestCreate
from models.schemas.transaction_response import DataMoveTransactionLog
from db.repositories.datamove_transaction import DataMoveTransactionRepository
from api.dependencies.database import get_repository
from services.authentication import get_current_workspace_owner_or_researcher_user_or_airlock_manager_or_tre_admin,get_current_tre_user_or_tre_admin
from services.data_move import save_and_publish_event_datamove_request
from resources import strings


datmove_workspace_router = APIRouter(dependencies=[Depends(get_current_tre_user_or_tre_admin)])

@datmove_workspace_router.get("/datamove/get-transactions", status_code=status_code.HTTP_200_OK,
                              response_model=List[DataMoveTransactionLog],
                              name=strings.API_TO_GET_DATA_MOVE_TRANSACTION,
                              dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager_or_tre_admin)])
async def get_datamove_transactions(datamove_transaction_repo: DataMoveTransactionRepository = Depends(get_repository(DataMoveTransactionRepository))):
    try:
        datamovetransactions = await datamove_transaction_repo.get_transactions()
        if datamovetransactions is None:
            return []

        return [
            DataMoveTransactionLog(
                transaction_id=transaction.id,
                protocol_id=transaction.protocol_id,
                user=transaction.user,
                status=transaction.status,
                date_moved=transaction.date_moved,
                data_volume=transaction.data_volume
            ) for transaction in datamovetransactions
        ]
    except Exception as e:
        logging.exception("Error while retrieving data move transactions")
        raise HTTPException(status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieving data move transactions")


@datmove_workspace_router.post("/datamove/{workspace_id}/requests", status_code=status_code.HTTP_201_CREATED,
                               response_model=DataMoveTransactionLog, name=strings.API_CREATE_AIRLOCK_REQUEST,
                               dependencies=[Depends(get_current_tre_user_or_tre_admin), Depends(get_workspace_by_id_from_path)])
async def create_draft_request(datamove_request_input: DataMoveTransactionLog,user=Depends(get_current_tre_user_or_tre_admin),
                               datamove_transaction_repo=Depends(get_repository(DataMoveTransactionRepository)),
                               workspace=Depends(get_deployed_workspace_by_id_from_path)) -> DataMoveTransactionLog:

    try:
        datamove_request = await datamove_transaction_repo.set_transactions(datamove_request_input,user)
        await save_and_publish_event_datamove_request(datamove_request, datamove_transaction_repo, user, workspace)

        return DataMoveTransactionLog()
    except (ValidationError, ValueError) as e:
        logging.exception("Failed creating data move request model instance")
        raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail=str(e))
