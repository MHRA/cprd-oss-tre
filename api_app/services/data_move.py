import logging
from azure.storage.blob import BlobServiceClient
from azure.storage.blob._container_client import ContainerClient
from resources import constants
from core import credentials


async def get_folder_size(workspace_id: str, protocol_id: str) -> float:
    try:
        account_name: str = constants.STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS.format(workspace_id[-4])

        blob_service_client = BlobServiceClient(
            account_url=get_account_url(account_name),
            credential=credentials.get_credential()
        )

        container_client: ContainerClient = blob_service_client.get_container_client(protocol_id)

        total_size_bytes = 0

        blobs = container_client.list_blobs(name_starts_with="SendToAnalyse")

        for blob in blobs:
            total_size_bytes += blob.size

        total_size_gb: float = total_size_bytes / (1024 * 1024 * 1024)

        return total_size_gb

    except Exception as e:
        logging.error(f"Error calculating folder size: {e}")
        return 0.0


def get_account_url(account_name: str) -> str:
    return f"https://{account_name}.blob.core.windows.net/"
