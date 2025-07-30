

from http.client import HTTPException
import logging

from api_app.db.repositories.datamove_transaction import DataMoveTransactionRepository
from api_app.models.domain.authentication import User
from api_app.models.domain.transaction import DataMoveTransaction
from api_app.models.domain.workspace import Workspace
from api_app.models.schemas import status
from api_app.resources import strings


async def save_and_publish_event_datamove_request(datamove_request: DataMoveTransaction, airlock_request_repo: DataMoveTransactionRepository, user: User, workspace: Workspace):

    try:
        logging.debug(f"Saving data move request item: {datamove_request.id}")

    except Exception:
        logging.exception(f'Failed saving data move request {datamove_request}')
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

