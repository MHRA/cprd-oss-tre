import os
import logging

BLOB_CONN_STR = "YOUR_BLOB_CONNECTION"
COSMOS_ENDPOINT = "https://cosmos-{}.documents.azure.com:443/"
SERVICE_BUS_CONN_STR = "YOUR_SERVICE_BUS_CONNECTION"

COSMOS_DB = "AzureTRE"
COSMOS_CONTAINER = "DataMoveTransactions"
COSMOS_RESOURCE_CONTAINER = "Resources"
QUEUE_NAME = "data-move-requests"

# Container naming patterns
STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS = "ssbsws{}"
WORKSPACE_RESOURCE_GROUP_NAME = "rg-{}-ws-{}"

SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE = os.getenv(
    "SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE", ""
)
SERVICE_BUS_DATA_MOVE_QUEUE_NAME = os.getenv(
    "SERVICE_BUS_DATA_MOVE_QUEUE_NAME", "data-move-requests"
)

SERVICE_BUS_CONNECTION_NAME = "AzureWebJobsServiceBus"

A_MSL_WORKSPACE = "tre-workspace-a-msl"
E_MSL_WORKSPACE = "tre-workspace-e-msl"
EMPTY_FILE_NAME = ".emptyFile"
EXPLORE_WORKSPACE_SSBS_ORIGIN_FOLDER = "SendToAnalysee"
ANALYSE_WORKSPACE_SSBS_DESTINATION = "ReceiveFromExplorea"

NOTIFY_UK_TEMPLATE_ID: str = os.getenv("NOTIFY_UK_TEMPLATE_ID", default="")
NOTIFY_UK_URL: str = os.getenv("NOTIFY_UK_URL", default="")
NOTIFY_UK_SECRET: str = os.getenv("NOTIFY_UK_SECRET", default="")
NOTIFY_UK_ISS_ID: str = os.getenv("NOTIFY_UK_ISS_ID", default="")
NOTIFY_UK_EMAIL_SUBJECT_TAG: str = os.getenv("NOTIFY_UK_EMAIL_SUBJECT_TAG", default="")

def get_tre_id():
    tre_id = os.getenv("TRE_ID")
    if not tre_id:
        logging.error("Missing environment variable: TRE_ID")
    return tre_id
