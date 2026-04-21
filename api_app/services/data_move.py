import logging
from typing import List
from azure.storage.blob import BlobServiceClient
from azure.storage.blob._container_client import ContainerClient
from models.domain.data_move_transactions import DataMoveFile
from resources import constants
from core import credentials


def get_files(workspace_id: str, protocol_id: str) -> List[DataMoveFile]:
    try:
        account_name: str = constants.STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS.format(workspace_id[-4])

        blob_service_client = BlobServiceClient(
            account_url=get_account_url(account_name),
            credential=credentials.get_credential()
        )

        container_client: ContainerClient = blob_service_client.get_container_client(protocol_id)

        files: List[DataMoveFile] = []

        blobs = container_client.list_blobs(name_starts_with="SendToAnalyse")

        for blob in blobs:
            dataMoveFile = DataMoveFile(
                file_name=blob.name,
                file_size=blob.size
            )
            files.append(dataMoveFile)

        return files

    except Exception as e:
        logging.error(f"Error retrieving files from container {protocol_id}: {e}")
        return []


def get_account_url(account_name: str) -> str:
    return f"https://{account_name}.blob.core.windows.net/"
