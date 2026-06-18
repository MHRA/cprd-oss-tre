import logging
from typing import List
from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from models.domain.data_move_transactions import DataMoveFile
from resources import constants
from core import credentials

# =====================================================
# Generate final SSBS storage account name
# =====================================================
async def generate_final_account_name(self, workspace_id, step):
    # Add backwards compatibility. There may be SSBS storage accounts names without suffix.
    # First we try storage accounts with suffix.
    account_name = constants.STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS.format(
        workspace_id[-4:]
    )
    suffix = await self._get_workspace_type(workspace_id)

    try:
        final_account_name = f"{account_name}{suffix}"
        logging.info(
            "Looking for Storage Account %s. Step: %s.",
            final_account_name,
            step
        )
        addr = socket.gethostbyname(f"{final_account_name}.blob.core.windows.net")

    except:
        logging.info(
            "Storage Account %s does not exist. Trying without suffix. Step %s.",
            final_account_name,
            step
        )

        try:
            final_account_name = f"{account_name}"
            addr = socket.gethostbyname(f"{final_account_name}.blob.core.windows.net")

        except:
            logging.error(
                "Storage Account %s does not exist. Workspace ID: %s. Step: %s.",
                final_account_name,
                workspace_id,
                step
            )
            raise

    logging.info(
            "Storage Account %s found. Proceed with saga. Step: %s",
            final_account_name,
            step
        )

    return final_account_name


async def get_files(workspace_id: str, protocol_id: str) -> List["DataMoveFile"]:
    try:
        # account_name: str = constants.STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS.format(workspace_id[-4:])+"e"
        account_name = generate_final_account_name(workspace_id, "LIST_BLOBS_FOR_UI")

        blob_service_client = BlobServiceClient(
            account_url=get_account_url(account_name),
            credential=credentials.get_credential()
        )

        container_client: ContainerClient = blob_service_client.get_container_client(protocol_id)
        files: List[DataMoveFile] = []

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
