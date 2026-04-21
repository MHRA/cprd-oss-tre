from typing import List
import uuid
import datetime

from pydantic import parse_obj_as
from azure.cosmos.aio import CosmosClient

from models.domain.data_move_transactions import DataMoveTransactions
from models.schemas.data_move_transactions import DataMoveTransactionRequest
from models.domain.authentication import User
from db.repositories.base import BaseRepository
from core import config


class DataMoveRepository(BaseRepository):

    @classmethod
    async def create(cls, client: CosmosClient):
        cls = DataMoveRepository()
        await super().create(client, config.STATE_STORE_DATA_MOVE_TRANSACTIONS)
        return cls

    @staticmethod
    def datamove_requests_query():
        return "SELECT * FROM c"

    async def get_datamove_requests(self, workspace_id: str) -> List[DataMoveTransactions]:
        query = "SELECT * FROM c WHERE c.workspaceId = @workspace_id"
        parameters = [
            {"name": "@workspace_id", "value": workspace_id}
        ]

        datamove_requests = await self.query(
            query=query,
            parameters=parameters
        )

        return parse_obj_as(List[DataMoveTransactions], datamove_requests)

    def create_datamove_request_item(
        self,
        datamove_request_input: DataMoveTransactionRequest,
        workspace_id: str,
        user: User
    ) -> DataMoveTransactions:

        full_datamove_request_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().timestamp()

        datamove_request = DataMoveTransactions(
            id=full_datamove_request_id,
            workspaceId=workspace_id,
            protocol_id=datamove_request_input.emasl_protocol_id,
            amsl_workspace_id=datamove_request_input.amsl_workspace_id,
            amsl_protocol_id=datamove_request_input.amsl_protocol_id,
            files_size=0.0,
            files=[],
            date_time=now,
            status="DRAFT",
            createdBy=user,
            createdWhen=now,
            updatedBy=user,
            updatedWhen=now,
        )

        return datamove_request
