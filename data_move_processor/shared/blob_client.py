import logging
import os

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, BlobLeaseClient
from api_app.core import credentials
from shared.config import STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS

def get_credential() -> DefaultAzureCredential:
    managed_identity = os.environ.get("MANAGED_IDENTITY_CLIENT_ID")
    if managed_identity:
        logging.info("using the data_move_processor's managed identity to get credentials.")
    return DefaultAzureCredential(managed_identity_client_id=os.environ.get("MANAGED_IDENTITY_CLIENT_ID"),
                                  exclude_shared_token_cache_credential=True) if managed_identity else DefaultAzureCredential()

def get_account_url(account_name: str) -> str:
    return f"https://{account_name}.blob.core.windows.net/"

def get_blob_service_client(workspace_id: str) -> BlobServiceClient:
    """Get BlobServiceClient for the given workspace ID."""
    account_name: str = STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS.format(workspace_id[-4:])
    blob_service_client = BlobServiceClient(
        account_url=get_account_url(account_name),
        credential=credentials.get_credential()
    )
    return blob_service_client

def list_blobs(workspace_id: str, container_name: str, prefix=None):
    blob_service_client = get_blob_service_client(workspace_id)
    container_client = blob_service_client.get_container_client(container_name)
    return [blob.name for blob in container_client.list_blobs(name_starts_with=prefix)]

def copy_blob(workspace_id: str, source_container: str, source_blob: str, dest_container: str, dest_blob: str):
    blob_service_client = get_blob_service_client(workspace_id)
    source_client = blob_service_client.get_blob_client(source_container, source_blob)
    dest_client = blob_service_client.get_blob_client(dest_container, dest_blob)
    dest_client.start_copy_from_url(source_client.url)
    return dest_client.get_blob_properties()

def delete_blob(workspace_id: str, container_name: str, blob_name: str):
    blob_service_client = get_blob_service_client(workspace_id)
    blob_client = blob_service_client.get_blob_client(container_name, blob_name)
    blob_client.delete_blob()

def get_blob_properties(workspace_id: str, container_name: str, blob_name: str):
    blob_service_client = get_blob_service_client(workspace_id)
    blob_client = blob_service_client.get_blob_client(container_name, blob_name)
    return blob_client.get_blob_properties()

def check_integrity(workspace_id: str, source_container: str, source_blob: str, dest_container: str, dest_blob: str):
    source_props = get_blob_properties(workspace_id, source_container, source_blob)
    dest_props = get_blob_properties(workspace_id, dest_container, dest_blob)
    return source_props.size == dest_props.size  # Simple size check, could add hash

def acquire_container_lease(workspace_id: str, container_name: str, lease_id=None):
    blob_service_client = get_blob_service_client(workspace_id)
    container_client = blob_service_client.get_container_client(container_name)
    lease_client = container_client.get_lease_client(lease_id)
    try:
        lease_client.acquire(lease_duration=60)  # 60 seconds, can be renewed
        return lease_client.id
    except Exception:
        return None

def release_container_lease(workspace_id: str, container_name: str, lease_id: str):
    blob_service_client = get_blob_service_client(workspace_id)
    container_client = blob_service_client.get_container_client(container_name)
    lease_client = container_client.get_lease_client(lease_id)
    lease_client.release()
