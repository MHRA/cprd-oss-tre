from typing import List

from pydantic import BaseModel


class DataMoveTransactionRequest(BaseModel):
    emsl_workspace_id:str
    emasl_protocol_id:str
    amsl_workspace_id:str
    amsl_protocol_id:str


    class config:
        schema_extra= {
            "example" :  {

            }
        }

class DataMoveTransactionResponse(BaseModel):
    transaction_id:str
    workspace_id:str
    protocol_id:str
    file_size:float
    date_time:float
    status:str

    class config:
        schema_extra= {
            "example" :  {

            }
        }

class DataMoveTransactionResponseList(BaseModel):
    dataMoveTransactions: List[DataMoveTransactionResponse]
