from pydantic import Field
from models.domain.azuretremodel import AzureTREModel


class DataMoveTransaction(AzureTREModel):
    """
    DataMoveTransaction model
    """
    id: str
    protocol_id:str
    user:dict = {}
    status: str = Field(None, title="Data Move Transaction status")
    date_moved:float
    data_volume:str



