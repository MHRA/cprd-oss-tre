from typing import Optional
from pydantic import BaseModel

class DataMoveTransactionLog(BaseModel):
    transaction_id: Optional[str]
    protocol_id:Optional[str]
    user: dict = {}
    status: Optional[str]
    date_moved:Optional[float]
    data_volume:Optional[float]

    class config:
        schema_extra= {
            "example" :  {
                "transaction_id": "12345",
                "protocol_id": "prtclid",
                "protocol_name":"prtclname",
                "user":"user name",
                "status":["Complete", "Error", "Inprogress"],
                "date_moved":"when is the data moved",
                "data_volume": "1000 GB"
            }
        }

