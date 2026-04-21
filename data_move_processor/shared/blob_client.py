from datetime import timedelta
import datetime
import json
import logging
import os

from azure.identity import DefaultAzureCredential
from azure.storage.blob import ContainerSasPermissions, generate_container_sas, BlobServiceClient, BlobClient
from azure.storage.blob._container_client import ContainerClient
from azure.storage.blob._models import BlobProperties
from azure.storage.blob._shared.models import UserDelegationKey
from api_app.core import credentials
# from api_app.models.domain.data_move_transactions import DataMoveFile
from shared.cosmos_client import get_workspace_type
from shared.config import STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS, EMPTY_FILE_NAME, WORKSPACE_RESOURCE_GROUP_NAME, get_tre_id

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
    try:
        suffix = get_workspace_type(workspace_id)

    except Exception as e:
        logging.error("Exception error: %s", e)
        raise

    account_name: str = STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS.format(workspace_id[-4:],suffix)
    blob_service_client = BlobServiceClient(
        account_url=get_account_url(account_name),
        credential=credentials.get_credential()
    )
    return blob_service_client


def list_blobs(workspace_id: str, container_name: str, prefix=None):
    """List blobs to be moved. container_name must include the suffix."""
    blob_service_client: BlobServiceClient = get_blob_service_client(workspace_id)
    container_client: ContainerClient = blob_service_client.get_container_client(container_name)

    # We list the content only from the source directory.
    # This operation requires 'Storage Blob Data Reader' role.
    source_container_content = container_client.list_blobs(name_starts_with = prefix)
    source_files_data = []

    workspace_short_id = workspace_id[-4:]
    rg_workspace_name = WORKSPACE_RESOURCE_GROUP_NAME.format(get_tre_id(), workspace_short_id)

    # Iterate over returned blobs.
    for blob in source_container_content:
        blob_data_elem = {
                "WorkspaceName": rg_workspace_name,
                "WorkspaceId": workspace_id,
                "SourceContainerName": container_name,
                "FileName": blob['name'],
                "FileSize": blob['size']
            }

        if EMPTY_FILE_NAME not in blob['name']:
            source_files_data.append(blob_data_elem)

    return source_files_data

def copy_blob(
    workspace_id: str,
    source_container: str,
    source_blob: str,
    amsl_workspace_id: str,
):
    # Destination blob name is always same as source
    dest_blob: str = source_blob
    dest_container = (source_container[:-1]+"a")

    source_blob_service_client: BlobServiceClient = get_blob_service_client(workspace_id)
    source_blob_client: BlobClient = source_blob_service_client.get_blob_client(
        container=source_container,
        blob=source_blob,
    )

    start_time = datetime.utcnow() - timedelta(minutes=15)
    expiry_time = datetime.utcnow() + timedelta(hours=1)

    user_delegation_key: UserDelegationKey = source_blob_service_client.get_user_delegation_key(
        key_start_time=start_time,
        key_expiry_time=expiry_time,
    )

    sas_token: str = generate_container_sas(
        account_name=source_blob_service_client.account_name,
        container_name=source_container,
        user_delegation_key=user_delegation_key,
        permission=ContainerSasPermissions(read=True),
        start=start_time,
        expiry=expiry_time,
    )

    source_url_with_sas: str = f"{source_blob_client.url}?{sas_token}"

    # ------------------------------------------------------------------
    # Preserve and update metadata
    # ------------------------------------------------------------------
    properties: BlobProperties = source_blob_client.get_blob_properties()
    metadata = properties.metadata or {}

    copied_from = json.loads(metadata.get("copied_from", "[]"))
    copied_from.append(source_blob_client.url)
    metadata["copied_from"] = json.dumps(copied_from)

    # Destination client
    dest_blob_service_client: BlobServiceClient = get_blob_service_client(amsl_workspace_id)
    dest_blob_client: BlobClient = dest_blob_service_client.get_blob_client(
        container=dest_container,
        blob=dest_blob,
    )

    # Start copy
    copy_props = dest_blob_client.start_copy_from_url(
        source_url_with_sas,
        metadata=metadata,
    )

    logging.info(
        "Copy started: copy_id=%s, copy_status=%s",
        copy_props.get("copy_id"),
        copy_props.get("copy_status"),
    )

    return dest_blob_client.get_blob_properties()



def delete_blob(workspace_id: str, container_name: str, blob_name: str):
    blob_service_client: BlobServiceClient = get_blob_service_client(workspace_id)
    blob_client: BlobClient = blob_service_client.get_blob_client(container_name, blob_name)
    blob_client.delete_blob()

def get_blob_properties(workspace_id: str, container_name: str, blob_name: str):
    blob_service_client: BlobServiceClient = get_blob_service_client(workspace_id)
    blob_client: BlobClient = blob_service_client.get_blob_client(container_name, blob_name)
    return blob_client.get_blob_properties()

def check_integrity(workspace_id: str, source_container: str, source_blob: str, dest_container: str, dest_blob: str):
    source_props: BlobProperties = get_blob_properties(workspace_id, source_container, source_blob)
    dest_props: BlobProperties = get_blob_properties(workspace_id, dest_container, dest_blob)
    return source_props.size == dest_props.size  # Simple size check, could add hash

def acquire_container_lease(workspace_id: str, container_name: str, lease_id=None):
    blob_service_client: BlobServiceClient = get_blob_service_client(workspace_id)
    container_client: ContainerClient = blob_service_client.get_container_client(container_name)
    lease_client = container_client.get_lease_client(lease_id)
    try:
        lease_client.acquire(lease_duration=60)  # 60 seconds, can be renewed
        return lease_client.id
    except Exception:
        return None

def release_container_lease(workspace_id: str, container_name: str, lease_id: str):
    blob_service_client: BlobServiceClient = get_blob_service_client(workspace_id)
    container_client: ContainerClient = blob_service_client.get_container_client(container_name)
    lease_client = container_client.get_lease_client(lease_id)
    lease_client.release()
