import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

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

# ------------------------------------------------------------------------------
# Credential handling
# ------------------------------------------------------------------------------

def get_credential() -> DefaultAzureCredential:

    managed_identity_client_id = os.environ.get("MANAGED_IDENTITY_CLIENT_ID")

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


# ------------------------------------------------------------------------------
# Cosmos client initialization
# ------------------------------------------------------------------------------

credential: DefaultAzureCredential = get_credential()

client = CosmosClient(
    url=COSMOS_ENDPOINT.format(get_tre_id()),
    credential=credential,
)

database = client.get_database_client(COSMOS_DB)
container = database.get_container_client(COSMOS_CONTAINER)


def create_transaction(document: Dict[str, Any]):

    return container.create_item(body=document)


def update_transaction(
    item_id: str,
    partition_key: str,
    patch: Dict[str, Any],
):

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
    """
    Reads a single transaction item.
    """
    return container.read_item(
        item=item_id,
        partition_key=partition_key,
    )


def log_file_status(
    transaction_id: str,
    file_name: str,
    status: str,
):

    item = {
        "id": f"{transaction_id}:{file_name}",
        "transactionId": transaction_id,
        "file": file_name,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return container.upsert_item(body=item)


def delete_transaction(item_id: str, partition_key: str):

    return container.delete_item(
        item=item_id,
        partition_key=partition_key,
    )


def get_workspace_type(workspace_id: str):
    query = f"SELECT * FROM {COSMOS_CONTAINER} r WHERE r.id = @workspaceId"
    parameters = [ dict(name='@workspaceId', value=workspace_id) ]
    results = container.query_items(
        query=query,
        parameters=parameters
    )

    for item in results:
        if item['templateName'] == A_MSL_WORKSPACE:
            suffix = "a"
        elif item['templateName'] == E_MSL_WORKSPACE:
            suffix = "e"
        else:
            logging.error(
               "Unable do define Workspace Type for workspace %s with workspace type %s",
               workspace_id,
               item['templateName']
            )
            raise

    return suffix
