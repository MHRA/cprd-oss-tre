import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

from shared.config import (
    COSMOS_ENDPOINT,
    COSMOS_DB,
    COSMOS_CONTAINER,
    A_MSL_WORKSPACE,
    E_MSL_WORKSPACE,
    get_tre_id,
)

# ==========================================================
# Credential handling (SAFE)
# ==========================================================

def get_credential() -> DefaultAzureCredential:
    """
    Returns DefaultAzureCredential using managed identity if configured.
    SAFE: does not execute until called.
    """
    managed_identity_client_id = os.getenv("MANAGED_IDENTITY_CLIENT_ID")

    if managed_identity_client_id:
        logging.info(
            "Using managed identity for Cosmos DB (client id: %s)",
            managed_identity_client_id,
        )
        return DefaultAzureCredential(
            managed_identity_client_id=managed_identity_client_id,
            exclude_shared_token_cache_credential=True,
        )

    logging.info("Using DefaultAzureCredential for Cosmos DB")
    return DefaultAzureCredential()


# ==========================================================
# Cosmos client factory (LAZY)
# ==========================================================

def get_container():
    """
    Lazily create Cosmos container client.
    SAFE: No SDK objects created at import time.
    """
    client = CosmosClient(
        url=COSMOS_ENDPOINT.format(get_tre_id()),
        credential=get_credential(),
    )

    database = client.get_database_client(COSMOS_DB)
    return database.get_container_client(COSMOS_CONTAINER)


# ==========================================================
# CRUD Operations
# ==========================================================

def create_transaction(document: Dict[str, Any]):
    container = get_container()
    return container.create_item(body=document)


def update_transaction(
    item_id: str,
    partition_key: str,
    patch: Dict[str, Any],
):
    container = get_container()

    patch_operations = [
        {"op": "add", "path": f"/{key}", "value": value}
        for key, value in patch.items()
    ]

    return container.patch_item(
        item=item_id,
        partition_key=partition_key,
        patch_operations=patch_operations,
    )


def get_transaction(item_id: str, partition_key: str):
    container = get_container()
    return container.read_item(
        item=item_id,
        partition_key=partition_key,
    )


def log_file_status(
    transaction_id: str,
    file_name: str,
    status: str,
):
    container = get_container()

    item = {
        "id": f"{transaction_id}:{file_name}",
        "transactionId": transaction_id,
        "file": file_name,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return container.upsert_item(body=item)


def delete_transaction(item_id: str, partition_key: str):
    container = get_container()
    return container.delete_item(
        item=item_id,
        partition_key=partition_key,
    )


# ==========================================================
# Workspace Type Resolution
# ==========================================================

def get_workspace_type(workspace_id: str) -> str:
    """
    Returns workspace suffix ('a' or 'e') based on Cosmos metadata.
    SAFE and deterministic.
    """
    container = get_container()

    query = f"SELECT * FROM {COSMOS_CONTAINER} r WHERE r.id = @workspaceId"
    parameters = [{"name": "@workspaceId", "value": workspace_id}]

    results = list(
        container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True,
        )
    )

    if not results:
        raise RuntimeError(f"Workspace {workspace_id} not found in Cosmos DB")

    template_name = results[0].get("templateName")

    if template_name == A_MSL_WORKSPACE:
        return "a"

    if template_name == E_MSL_WORKSPACE:
        return "e"

    raise RuntimeError(
        f"Unable to determine workspace type for {workspace_id} ({template_name})"
    )
