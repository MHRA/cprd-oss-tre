from pydantic import Field
from models.domain.azuretremodel import AzureTREModel


class DataMoveTransactions(AzureTREModel):
    """
    DataMoveTransactions model
    """
    id: str = Field(title="Id", description="GUID identifying the resource")
    workspaceId: str = Field(title="Workspace Id", description="GUID identifying the workspace")
    protocol_id: str = Field(title="Protocol Id", description=" the protocol")
    file_size: float = Field(title="File Size", description="Size of the file being moved in bytes")
    date_time: float = Field(title="Date Time", description="POSIX Timestamp for when the data move transaction occurred")
    status: str = Field(title="Status", description="Status of the data move transaction")
    createdBy: dict = {}
    createdWhen: float = Field("", title="POSIX Timestamp for when the operation was submitted")
    updatedBy:dict = {}
    updatedWhen: float = Field("", title="POSIX Timestamp for When the operation was updated")

