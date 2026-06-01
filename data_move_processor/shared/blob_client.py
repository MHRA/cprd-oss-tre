from datetime import timedelta
import datetime
import json
import logging
import os
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobLeaseClient,
    ContainerSasPermissions,
    generate_container_sas,
    BlobServiceClient,
    BlobClient,
)
from azure.storage.blob._container_client import ContainerClient
from azure.storage.blob._models import BlobProperties
from azure.storage.blob._shared.models import UserDelegationKey

from shared.cosmos_client import get_workspace_type
from shared.config import (
    STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS,
    EMPTY_FILE_NAME,
    WORKSPACE_RESOURCE_GROUP_NAME,
    EXPLORE_WORKSPACE_SSBS_ORIGIN_FOLDER,
    ANALYSE_WORKSPACE_SSBS_DESTINATION,
    get_tre_id,
)

# ==========================================================
# Credentials (SELF-CONTAINED, SAFE)
# ==========================================================

def get_credential() -> DefaultAzureCredential:
    """
    Returns a credential for Azure SDKs.
    Uses managed identity if MANAGED_IDENTITY_CLIENT_ID is set.
    """
    managed_identity = os.getenv("MANAGED_IDENTITY_CLIENT_ID")

    if managed_identity:
        logging.info("Using managed identity for Blob access")
        return DefaultAzureCredential(
            managed_identity_client_id=managed_identity,
            exclude_shared_token_cache_credential=True,
        )

    return DefaultAzureCredential()


def get_account_url(account_name: str) -> str:
    return f"https://{account_name}.blob.core.windows.net/"


# ==========================================================
# Blob Service Client Factory
# ==========================================================

def get_blob_service_client(workspace_id: str) -> BlobServiceClient:
    """
    Create BlobServiceClient for a workspace.
    SAFE: No work done at import time.
    """
    suffix = get_workspace_type(workspace_id)

    account_name = STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS.format(
        workspace_id[-4:], suffix
    )

    return BlobServiceClient(
        account_url=get_account_url(account_name),
        credential=get_credential(),
    )


# ==========================================================
# Blob Listing
# ==========================================================

def list_blobs(workspace_id: str, container_name: str, prefix: Optional[str] = None):
    blob_service_client = get_blob_service_client(workspace_id)
    container_client: ContainerClient = blob_service_client.get_container_client(
        container_name
    )

    blobs = container_client.list_blobs(name_starts_with=prefix)
    results = []

    workspace_short_id = workspace_id[-4:]
    rg_workspace_name = WORKSPACE_RESOURCE_GROUP_NAME.format(
        get_tre_id(), workspace_short_id
    )

    for blob in blobs:
        if EMPTY_FILE_NAME in blob["name"]:
            continue

        results.append(
            {
                "WorkspaceName": rg_workspace_name,
                "WorkspaceId": workspace_id,
                "SourceContainerName": container_name,
                "FileName": blob["name"],
                "FileSize": blob["size"],
            }
        )

    return results


# ==========================================================
# Blob Copy
# ==========================================================

def copy_blob(
    workspace_id: str,
    source_container: str,
    source_blob: str,
    amsl_workspace_id: str,
):
    dest_container = source_container[:-1] + "a"

    # full_source_blob = f"SendToAnalyse/{source_blob}"
    # dest_blob = f"ReceiveFromExplore/{source_blob}"
    full_source_blob = f"{EXPLORE_WORKSPACE_SSBS_ORIGIN_FOLDER}/{source_blob}"
    dest_blob = f"{ANALYSE_WORKSPACE_SSBS_DESTINATION}/{source_blob}"

    source_bsc = get_blob_service_client(workspace_id)
    source_blob_client: BlobClient = source_bsc.get_blob_client(
        container=source_container,
        blob=full_source_blob,
    )

    start_time = datetime.datetime.utcnow() - timedelta(minutes=15)
    expiry_time = datetime.datetime.utcnow() + timedelta(hours=1)

    delegation_key: UserDelegationKey = source_bsc.get_user_delegation_key(
        key_start_time=start_time,
        key_expiry_time=expiry_time,
    )

    sas_token = generate_container_sas(
        account_name=source_bsc.account_name,
        container_name=source_container,
        user_delegation_key=delegation_key,
        permission=ContainerSasPermissions(read=True),
        start=start_time,
        expiry=expiry_time,
    )

    source_url_with_sas = f"{source_blob_client.url}?{sas_token}"

    props: BlobProperties = source_blob_client.get_blob_properties()
    metadata = props.metadata or {}

    copied_from = json.loads(metadata.get("copied_from", "[]"))
    copied_from.append(source_blob_client.url)
    metadata["copied_from"] = json.dumps(copied_from)

    dest_bsc = get_blob_service_client(amsl_workspace_id)
    dest_blob_client: BlobClient = dest_bsc.get_blob_client(
        container=dest_container,
        blob=dest_blob,
    )

    copy_props = dest_blob_client.start_copy_from_url(
        source_url_with_sas,
        metadata=metadata,
    )

    logging.info(
        "Copy started: %s -> %s (copy_id=%s status=%s)",
        full_source_blob,
        dest_blob,
        copy_props.get("copy_id"),
        copy_props.get("copy_status"),
    )

    return dest_blob_client.get_blob_properties()


# ==========================================================
# Blob Delete / Properties
# ==========================================================

def delete_blob(workspace_id: str, container_name: str, blob_name: str):
    blob_service_client = get_blob_service_client(workspace_id)
    full_blob_name = f"SendToAnalyse/{blob_name}"
    blob_client = blob_service_client.get_blob_client(container_name, full_blob_name)
    blob_client.delete_blob()


def get_blob_properties(workspace_id: str, container_name: str, blob_name: str):
    blob_service_client = get_blob_service_client(workspace_id)
    blob_client = blob_service_client.get_blob_client(container_name, blob_name)
    return blob_client.get_blob_properties()


# ==========================================================
# Integrity Check
# ==========================================================

def check_container_integrity(
    workspace_id: str,
    source_container: str,
    amsl_workspace_id: str,
) -> bool:

    dest_container = source_container[:-1] + "a"

    source_blobs = list_blobs(
        workspace_id,
        source_container,
        prefix="SendToAnalyse/"
    )

    dest_blobs = list_blobs(
        amsl_workspace_id,
        dest_container,
        prefix="ReceiveFromExplore/"
    )

    logging.info(
        f"Source blobs: {[b['FileName'] for b in source_blobs]}"
    )

    logging.info(
        f"Destination blobs: {[b['FileName'] for b in dest_blobs]}"
    )

    source_names = {
        b["FileName"].split("/")[-1]
        for b in source_blobs
    } if source_blobs else set()

    filtered_dest_blobs = [
        b for b in dest_blobs
        if b["FileName"].split("/")[-1] in source_names
    ] if dest_blobs else []

    logging.info(
        f"Filtered destination blobs (matching source): "
        f"{[b['FileName'] for b in filtered_dest_blobs]}"
    )

    source_size = (
        sum(b["FileSize"] for b in source_blobs)
        if source_blobs else 0
    )

    dest_size = (
        sum(b["FileSize"] for b in filtered_dest_blobs)
        if filtered_dest_blobs else 0
    )

    logging.info(
        f"Integrity check: "
        f"source_size={source_size} "
        f"dest_size={dest_size}"
    )

    return source_size == dest_size

# ==========================================================
# Container Lease Management
# ==========================================================

def acquire_container_lease(workspace_id: str, container_name: str, lease_id: Optional[str] = None,) -> Optional[str]:
    blob_service_client: BlobServiceClient = get_blob_service_client(workspace_id)

    container_client: ContainerClient = blob_service_client.get_container_client(
        container_name
    )

    lease_client = BlobLeaseClient(
        client=container_client,
        lease_id=lease_id,
    )

    try:
        lease_client.acquire(lease_duration=-1)
        return lease_client.id

    except Exception as exc:
        logging.warning("Failed to acquire lease: %s", exc)
        return None

def release_container_lease(workspace_id: str, container_name: str, lease_id: str) -> None:
    blob_service_client: BlobServiceClient = get_blob_service_client(workspace_id)

    container_client: ContainerClient = blob_service_client.get_container_client(
        container_name
    )

    lease_client = BlobLeaseClient(
        client=container_client,
        lease_id=lease_id,
    )

    lease_client.release()
