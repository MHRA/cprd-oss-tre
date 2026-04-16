

import os
from api_app.services import logging

BLOB_CONN_STR = "YOUR_BLOB_CONNECTION"
COSMOS_ENDPOINT = "https://cosmos-{}.documents.azure.com:443/"
SERVICE_BUS_CONN_STR = "YOUR_SERVICE_BUS_CONNECTION"

COSMOS_DB = "AzureTRE"
COSMOS_CONTAINER = "DataMoveTransactions"
QUEUE_NAME = "datamove-events"

# Container naming patterns
STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS = "ssbsws{}"
WORKSPACE_RESOURCE_GROUP_NAME = "rg-{}-ws-{}"

SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE: str = os.getenv("SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE", "")
SERVICE_BUS_DATA_MOVE_QUEUE_NAME: str = os.getenv("SERVICE_BUS_DATA_MOVE_QUEUE_NAME", "")

def get_tre_id():
    try:
        tre_id = os.environ["TRE_ID"]
    except KeyError as e:
        logging.error(f'Missing environment variable: {e}')
        raise
    return tre_id
