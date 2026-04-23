from typing import List

from pydantic import BaseModel


class DataMoveTransactionRequest(BaseModel):
    workspace_id: str
    protocol_id: str


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

class DataMoveFile(BaseModel):
    workspance_name: str
    workspace_id: str
    source_container_name: str
    file_name: float
    file_size: float

    class config:
        schema_extra= {
            "example" : {
                "workspance_name": "rg-cprdtest-ws-f691",
                "workspace_id": "182106a0-bb87-49e1-a1fe-fb7cf168f691",
                "source_container_name": "26-092337e",
                "file_name": "sample_data_cut.txt",
                "file_size": 163.12
            }
        }

