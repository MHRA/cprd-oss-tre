
from pydantic import Field
from api_app.models.domain.azuretremodel import AzureTREModel


class DataMoveRequest(AzureTREModel):
    """
    Data Move request
    """
    id: str = Field(title="Id", description="GUID identifying the resource")
    resourceVersion: int = 0
    createdBy: dict = {}
    createdWhen: float = Field(None, title="Creation time of the request")
    updatedBy: dict = {}

