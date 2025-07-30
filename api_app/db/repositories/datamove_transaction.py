from typing import List
import uuid
from db.repositories.base import BaseRepository

from datetime import datetime
from azure.cosmos.aio import CosmosClient
from models.domain.authentication import User
from models.domain.transaction import DataMoveTransaction
from models.schemas.transaction_response import DataMoveTransactionLog
from core import config
from pydantic import parse_obj_as

class DataMoveTransactionRepository(BaseRepository):
    @classmethod
    async def create(cls, client: CosmosClient):
        cls = DataMoveTransactionRepository()
        await super().create(client, config.STATE_STORE_DATA_MOVE_TRANSACTION)
        return cls

    async def set_transactions(self, transaction_data: DataMoveTransactionLog, user) -> DataMoveTransaction:

        transactions = DataMoveTransaction(
            id= str(uuid.uuid4()),
            transaction_id= transaction_data.transaction_id,
            protocol_id=transaction_data.protocol_id,
            status=transaction_data.status,
            user=user,
            data_volume=transaction_data.data_volume,
            date_moved=datetime.utcnow().timestamp()),

        await self.update_item(transactions)
        return transactions


    async def get_transactions(self) ->DataMoveTransaction:

        query = 'SELECT * FROM c'
        data = await self.query(query=query)
        if data and len(data) > 0:
            return parse_obj_as(List[DataMoveTransaction], data)
        else:
            return None





