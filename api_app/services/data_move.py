import logging
from typing import List
from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from models.domain.data_move_transactions import DataMoveFile
from resources import constants
from core import credentials


async def get_files(workspace_id: str, protocol_id: str) -> List["DataMoveFile"]:
    try:
        account_name: str = constants.STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS.format(workspace_id[-4:])+"e"

        blob_service_client = BlobServiceClient(
            account_url=get_account_url(account_name),
            credential=credentials.get_credential()
        )


        container_client: ContainerClient = blob_service_client.get_container_client(protocol_id)
        files: List[DataMoveFile] = []

        # async for blob in container_client.list_blobs(name_starts_with="SendToAnalyse/"):

        #     relative_path = blob.name.replace("SendToAnalyse/", "")
        async for blob in container_client.list_blobs(name_starts_with=f"{constants.EXPLORE_WORKSPACE_SSBS_ORIGIN_FOLDER}/"):

            relative_path = blob.name.replace(f"{constants.EXPLORE_WORKSPACE_SSBS_ORIGIN_FOLDER}/", "")

            # only files in root of folder
            if "/" not in relative_path and not relative_path.endswith("/"):
                data_move_file = DataMoveFile(
                    file_name=relative_path,
                    file_size=blob.size
                )
                files.append(data_move_file)


        return files

    except Exception as e:
        logging.error(
            f"Error retrieving files from container {protocol_id}: {type(e).__name__}: {e}",
            exc_info=True
        )
        return []

    finally:

        try:
            await blob_service_client.close()
        except Exception:
            pass


def get_account_url(account_name: str) -> str:
    return f"https://{account_name}.blob.core.windows.net/"
