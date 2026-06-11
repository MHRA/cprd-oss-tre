from datetime import datetime, timedelta, date
from typing import List, Optional
from pydantic import BaseModel, Field

class StorageAccountLimitsInput(BaseModel):
    workspace_id: str = Field(title="Workspace id to be updated")
    storage_name: str = Field(title="Storage Account name to be updated")
    storage_limits: float = Field(title="New Storage Account storage limits")

    class Config:
        schema_extra = {
            "example": {
                "workspace_id": "6b2cb72e-7d1e-448f-a478-552973d12d46",
                "storage_name": "ssbsws2d46",
                "storage_limits": 5120.0
            }
        }

class MHRAStorageAccountLimitsItem(BaseModel):
    workspace_id: str
    storage_name: str
    storage_limits: float

class MHRAStorageAccountLimits(BaseModel):
    storage_account_limits_items: List[MHRAStorageAccountLimitsItem]

class MHRAContainerUsageItem(BaseModel):
    timestamp: Optional[datetime] = None
    workspace_name: Optional[str] = None
    workspace_id: Optional[str] = None
    storage_name: Optional[str] = None
    storage_usage: Optional[str] = None
    storage_limits: Optional[str] = None
    storage_remaining: Optional[str] = None
    storage_percentage: Optional[str] = None

class MHRAFileshareUsageItem(BaseModel):
    timestamp: Optional[datetime] = None
    workspace_name: Optional[str] = None
    workspace_id: Optional[str] = None
    storage_name: Optional[str] = None
    fileshare_usage:  Optional[str] = None
    fileshare_limits:  Optional[str] = None
    fileshare_remaining:  Optional[str] = None
    fileshare_percentage:  Optional[str] = None

class MHRAWorkspaceDataUsage(BaseModel):
    workspace_container_usage_items: List[MHRAContainerUsageItem]
    workspace_fileshare_usage_items: List[MHRAFileshareUsageItem]

class WorkspaceDataUsage(BaseModel):
    container_usage_item: Optional[MHRAContainerUsageItem] = None
    fileshare_usage_item: Optional[MHRAFileshareUsageItem] = None

class MHRAProtocolItem(BaseModel):
    timestamp: Optional[datetime] = None
    workspace_name: Optional[str] = None
    workspace_id: Optional[str] = None
    storage_name: Optional[str] = None
    storage_limits: Optional[str] = None
    protocol_id: Optional[str] = None
    protocol_data_usage: Optional[str] = None
    protocol_data_remaining: Optional[str] = None
    protocol_percentage_usage: Optional[str] = None
    status: Optional[str] = None
    filesSize: Optional[float] = None
    estimated_time: Optional[float] = None

class MHRAProtocolList(BaseModel):
    protocol_items: List[MHRAProtocolItem]
