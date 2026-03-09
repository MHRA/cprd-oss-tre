from datetime import datetime, timezone
import json
import logging, math
import uuid

import httpx
from db.repositories.workspaces import WorkspaceRepository
from models.schemas.container_reation_request import ContainerCreateRequest, EntraGroup, EntraGroupRequest, RoleAssignmentRequest
from models.domain.data_usage import MHRAProtocolItem, MHRAProtocolList, MHRAWorkspaceDataUsage, MHRAContainerUsageItem, MHRAFileshareUsageItem, MHRAStorageAccountLimits, MHRAStorageAccountLimitsItem, StorageAccountLimitsInput, WorkspaceDataUsage
from models.schemas.storage_info_request import StorageInfoRequest
from core import config, credentials
from resources import constants, strings
from functools import lru_cache
from fastapi import HTTPException, status
from azure.data.tables import TableServiceClient, UpdateMode
from azure.servicebus.aio import ServiceBusClient
from azure.keyvault.secrets import SecretClient
from azure.servicebus import ServiceBusMessage
from azure.core.exceptions import HttpResponseError

# make sure CostService is singleton
@lru_cache(maxsize=None)
class DataUsageService:
    scope: str
    account_endpoint: str
    client: TableServiceClient
    RATE_LIMIT_RETRY_AFTER_HEADER_KEY: str = "x-ms-ratelimit-microsoft.costmanagement-entity-retry-after"
    SERVICE_UNAVAILABLE_RETRY_AFTER_HEADER_KEY: str = "Retry-After"

    def __init__(self) -> None:
        self.scope = "/subscriptions/{}".format(config.SUBSCRIPTION_ID)
        self.account_name = constants.STORAGE_ACCOUNT_NAME_CORE_RESOURCE_GROUP.format(config.TRE_ID)
        self.account_endpoint = f"https://{self.account_name}.table.core.windows.net"
        # We add a custom ClientType header to avoid small limits for Azure API calls.
        self.client = TableServiceClient(
            endpoint=self.account_endpoint,
            credential=credentials.get_credential(),
            headers={"ClientType": config.CLIENT_TYPE_CUSTOM_HEADER}
        )

    def _get_latest_entity_by_timestamp(self, entities):
        latest = None
        latest_ts = None

        if entities:

            for entity in entities:

                ts = entity.get("Timestamp")
                if latest_ts is None or ts > latest_ts:
                    latest = entity
                    latest_ts = ts
        return latest

    async def get_workspace_data_usage(self) -> MHRAWorkspaceDataUsage:
        container_usage_table = constants.WORKSPACE_CONTAINER_USAGE_TABLE_NAME
        fileshare_usage_table = constants.WORKSPACE_FILESHARE_USAGE_TABLE_NAME

        try:
            container_usage_items = []
            fileshare_usage_items = []

            # We set the filter used to find the latest entry.
            # Only the latest entries will be selected.
            parameters = {"latest": True}
            latest_entity_filter = "Latest eq @latest"

            # For performing this operation, the identity used for running the API must have the role
            # "Storage Table Data Reader" (the scope is the storage account holding the table).
            table_client = self.client.get_table_client(table_name=container_usage_table)

            # Filter table entities using workspace name and storage account name.
            latest_entities = table_client.query_entities(
                query_filter=latest_entity_filter,
                parameters=parameters
            )

            entities = list(latest_entities)
            # entities = table_client.list_entities()

            for entity in entities:
                container_usage_items.append(
                    MHRAContainerUsageItem(
                        workspace_name=entity['WorkspaceName'],
                        workspace_id=entity['WorkspaceId'],
                        storage_name=entity['StorageName'],
                        storage_usage=entity['StorageUsage'],
                        storage_limits=entity['StorageLimits'],
                        storage_remaining=entity['StorageLimits']-entity['StorageUsage'],
                        storage_percentage=entity['StoragePercentage'],
                        timestamp=entity.metadata['timestamp']
                    )
                )

            # For performing this operation, the identity used for running the API must have the role
            # "Storage Table Data Reader" (the scope is the storage account holding the table).
            table_client = self.client.get_table_client(table_name=fileshare_usage_table)

            # Filter table entities using workspace name and storage account name.
            latest_entities = table_client.query_entities(
                query_filter=latest_entity_filter,
                parameters=parameters
            )

            entities = list(latest_entities)
            # entities = table_client.list_entities()

            for entity in entities:
                fileshare_usage_items.append(
                    MHRAFileshareUsageItem(
                        workspace_name=entity['WorkspaceName'],
                        workspace_id=entity['WorkspaceId'],
                        storage_name=entity['StorageName'],
                        fileshare_usage=entity['FileshareUsage'],
                        fileshare_limits=entity['FileshareLimits'],
                        fileshare_remaining=entity['FileshareLimits']-entity['FileshareUsage'],
                        fileshare_percentage=entity['FilesharePercentage'],
                        timestamp=entity.metadata['timestamp']
                    )
                )

            return MHRAWorkspaceDataUsage(workspace_container_usage_items=container_usage_items,workspace_fileshare_usage_items=fileshare_usage_items)

        except HttpResponseError:
            logging.exception("HTTP error when calling table_client.")
            raise HttpResponseError
        except:
            logging.exception("Unknown error when calling table_client.")
            raise Exception("Unknown error when calling table_client.")

    async def get_storage_account_limits(self) -> MHRAStorageAccountLimits:
        container_usage_table = constants.WORKSPACE_CONTAINER_USAGE_TABLE_NAME

        try:
            storage_account_limits_items = []

            # We set the filter used to find the latest entry.
            # Only the latest entries will be selected.
            parameters = {"latest": True}
            latest_entity_filter = "Latest eq @latest"

            # For performing this operation, the identity used for running the API must have the role
            # "Storage Table Data Reader" (the scope is the storage account holding the table).
            table_client = self.client.get_table_client(table_name=container_usage_table)

            # Filter table entities using workspace name and storage account name.
            latest_entities = table_client.query_entities(
                query_filter=latest_entity_filter,
                parameters=parameters
            )

            entities = list(latest_entities)
            # entities = table_client.list_entities()

            for entity in entities:
                storage_account_limits_items.append(
                    MHRAStorageAccountLimitsItem(
                        workspace_name=entity['WorkspaceName'],
                        workspace_id=entity['WorkspaceId'],
                        storage_name=entity['StorageName'],
                        storage_limits=entity['StorageLimits'],
                    )
                )

            return MHRAStorageAccountLimits(storage_account_limits_items=storage_account_limits_items)

        except HttpResponseError:
            logging.exception("HTTP error when calling table_client.")
            raise HttpResponseError
        except:
            logging.exception("Unknown error when calling table_client.")
            raise Exception("Unknown error when calling table_client.")

    async def set_storage_account_limits(self, storage_account_lits_properties: StorageAccountLimitsInput) -> MHRAStorageAccountLimitsItem:
        # storage_limits_update_time = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
        container_usage_table = constants.WORKSPACE_CONTAINER_USAGE_TABLE_NAME

        try:
            # Creating filter for selecting the correct storage account
            workspace_id = storage_account_lits_properties.workspace_id
            storage_name = storage_account_lits_properties.storage_name
            storage_limits = storage_account_lits_properties.storage_limits

            # Control new limits.
            if storage_limits < 0:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.DATA_USAGE_LIMITS_MUST_BE_POSITIVE)

            # For performing this operation, the identity used for running the API must have the role
            # "Storage Table Data Reader" (the scope is the storage account holding the table).
            table_client = self.client.get_table_client(table_name=container_usage_table)

            parameters = {"workspaceid": workspace_id, "storagename": storage_name, "latest": True}
            workspace_filter = "WorkspaceId eq @workspaceid and StorageName eq @storagename and Latest eq @latest"

            # Filter table entities using workspace name and storage account name.
            entities = table_client.query_entities(
                query_filter=workspace_filter,
                parameters=parameters
            )

            # Fail if entity is not found
            entities_list = list(entities)
            if len(list(entities_list)) == 0:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.DATA_USAGE_WORKSPACE_OR_STORAGE_ACCOUNT_NOT_FOUND)

            # Only 1 interation should happen.
            for entity in entities_list:
                # Create a new entity to replace the old one.
                new_entity = {
                    "PartitionKey": entity['PartitionKey'],
                    "RowKey": entity['RowKey'],
                    "WorkspaceName": entity['WorkspaceName'],
                    "WorkspaceId": entity['WorkspaceId'],
                    "StorageName": entity['StorageName'],
                    "StorageUsage": entity['StorageUsage'],
                    "StorageLimits": storage_limits,
                    "StoragePercentage": math.floor(((entity['StorageUsage'] * 100.0) / storage_limits)),
                    "Latest": entity['Latest']
                }

                logging.info(f"Updating data limits for storage account {entity['StorageName']} - New limit: {storage_limits}")

                # Merge the entity
                table_client.update_entity(mode=UpdateMode.MERGE, entity=new_entity)

            storage_account_limit_item = MHRAStorageAccountLimitsItem(
                workspace_id=workspace_id,
                storage_name=storage_name,
                storage_limits=storage_limits
            )

            return storage_account_limit_item

        except:
            logging.exception("Unknown error when calling table_client.")
            raise Exception("Unknown error when calling table_client.")

    async def get_workspace_storage_info(self, storage_info_request: StorageInfoRequest) -> MHRAWorkspaceDataUsage:
        container_usage_table = constants.WORKSPACE_CONTAINER_USAGE_TABLE_NAME
        fileshare_usage_table = constants.WORKSPACE_FILESHARE_USAGE_TABLE_NAME

        try:
            container_usage_items = []
            fileshare_usage_items = []

            query_filter = " and ".join([f"WorkspaceName eq '{workspaceId}'" for workspaceId in storage_info_request.workspaceIds])

            # For performing this operation, the identity used for running the API must have the role
            # "Storage Table Data Reader" (the scope is the storage account holding the table).
            table_client = self.client.get_table_client(table_name=container_usage_table)
            entities = table_client.query_entities(query_filter)

            for entity in entities:
                container_usage_items.append(
                    MHRAContainerUsageItem(
                        workspace_name=entity['WorkspaceName'],
                        workspace_id=entity['WorkspaceId'],
                        storage_name=entity['StorageName'],
                        storage_usage=entity['StorageUsage'],
                        storage_limits=entity['StorageLimits'],
                        storage_remaining=entity['StorageLimits']-entity['StorageUsage'],
                        storage_percentage = math.floor(entity['StoragePercentage']),
                        # timestamp = entity['Timestamp']
                        timestamp = entity.metadata['timestamp']
                    )
                )
            if storage_info_request.workspaceType in ["eMSL", "", None]:
                # For performing this operation, the identity used for running the API must have the role
                # "Storage Table Data Reader" (the scope is the storage account holding the table).
                table_client = self.client.get_table_client(table_name=fileshare_usage_table)
                entities = table_client.query_entities(query_filter)

                for entity in entities:
                    fileshare_usage_items.append(
                        MHRAFileshareUsageItem(
                            workspace_name=entity['WorkspaceName'],
                            storage_name=entity['StorageName'],
                            fileshare_usage=entity['FileshareUsage'],
                            fileshare_limits=entity['FileshareLimits'],
                            fileshare_remaining=entity['FileshareLimits']-entity['FileshareUsage'],
                            fileshare_limits_update_time=entity['FileshareLimitsUpdateTime'],
                            fileshare_percentage_used=entity['FilesharePercentage'],
                            update_time=entity.metadata['timestamp']

                        )
                    )

            return MHRAWorkspaceDataUsage(workspace_container_usage_items=container_usage_items,workspace_fileshare_usage_items=fileshare_usage_items)

        except HttpResponseError:
            logging.exception("HTTP error when calling table_client.")
            raise HttpResponseError
        except:
            logging.exception("Unknown error when calling table_client.")
            raise Exception("Unknown error when calling table_client.")

    async def get_perstudy_items(self, workspaceId: str) -> MHRAProtocolList:
        container_perstudy_table = constants.WORKSPACE_PERSTUDY_USAGE_TABLE_NAME

        try:
            protocol_items = []
            query_filter = f"WorkspaceName eq '{workspaceId}' and Latest eq true"
            table_client = self.client.get_table_client(table_name=container_perstudy_table)
            entities = list(table_client.query_entities(query_filter))

            for entity in entities:
                protocol_items.append(
                    MHRAProtocolItem(
                        workspace_name=entity.get('WorkspaceName', ''),
                        workspace_id=entity.get('WorkspaceId', ''),
                        storage_name=entity.get('StorageName', ''),
                        storage_limits=self._format_size(entity.get('StorageLimits', 0)),
                        protocol_id=entity.get('ProtocolId', ''),
                        protocol_data_usage=self._format_size(entity.get('ProtocolDataUsage', 0)),
                        protocol_data_remaining=self._format_size(

                            (entity.get('StorageLimits', 0) - entity.get('ProtocolDataUsage', 0))
                        ),
                        protocol_percentage_usage=math.floor(entity.get('ProtocolPercentageUsage',0)),
                        timestamp=entity.metadata['timestamp']
                    )
                )

            return MHRAProtocolList(protocol_items=protocol_items)

        except HttpResponseError as e:
            logging.exception("HTTP error when calling table_client.")
            raise
        except Exception as e:
            logging.exception("Unknown error when calling table_client.")
            raise

    async def get_protocolItem(self, protocolId: str) -> MHRAProtocolItem:
        container_perstudy_table = constants.WORKSPACE_PERSTUDY_USAGE_TABLE_NAME

        try:
            query_filter = f"ProtocolId eq '{protocolId}'"
            table_client = self.client.get_table_client(table_name=container_perstudy_table)
            entities = list(table_client.query_entities(query_filter))

            if not entities:
                return None

            entity = entities[0]

            return MHRAProtocolItem(
                workspace_name=entity.get('WorkspaceName', ''),
                workspace_id=entity.get('WorkspaceId', ''),
                storage_name=entity.get('StorageName', ''),
                storage_limits=self._format_size(entity.get('StorageLimits', 0)),
                protocol_id=entity.get('ProtocolId', ''),
                protocol_data_usage=self._format_size(entity.get('ProtocolDataUsage', 0)),
                protocol_data_remaining=self._format_size(
                    entity.get('StorageLimits', 0) - entity.get('ProtocolDataUsage', 0)
                ),
                status=entity.get('Status', ''),
                protocol_percentage_usage=math.floor(entity.get('ProtocolPercentageUsage', 0)),
                timestamp=entity.metadata['timestamp']
            )

        except HttpResponseError:
            logging.exception("HTTP error when calling table_client.")
            raise
        except Exception:
            logging.exception("Unknown error when calling table_client.")
            raise


    async def get_data_usage_for_workspace(self, workspaceId: str) -> WorkspaceDataUsage:
        container_usage_table = constants.WORKSPACE_CONTAINER_USAGE_TABLE_NAME
        fileshare_usage_table = constants.WORKSPACE_FILESHARE_USAGE_TABLE_NAME

        tre_id = config.TRE_ID
        workspace = constants.WORKSPACE_RESOURCE_GROUP_NAME.format(tre_id, workspaceId[-4:])

        try:
            # query_filter = f"WorkspaceName eq '{workspace}'"
            query_filter = f"WorkspaceName eq '{workspace}' and Latest eq true"

            # Container usage
            table_client = self.client.get_table_client(table_name=container_usage_table)
            entities = table_client.query_entities(query_filter)
            container_usage_item = None
            latest = self._get_latest_entity_by_timestamp(entities)
            if latest:

                container_usage_item = MHRAContainerUsageItem(
                    workspace_name=latest.get('WorkspaceName', ''),
                    workspace_id=latest.get('WorkspaceId', ''),
                    storage_name=latest.get('StorageName', ''),
                    storage_usage=self._format_size(latest.get('StorageUsage')),
                    storage_limits=self._format_size(latest.get('StorageLimits')),
                    storage_remaining=self._format_size(
                        (latest.get('StorageLimits', 0) - latest.get('StorageUsage', 0))
                    ),
                    storage_percentage=math.floor(latest.get('StoragePercentage', 0)),
                    timestamp=latest.metadata['timestamp']
                )

            # Fileshare usage
            table_client = self.client.get_table_client(table_name=fileshare_usage_table)
            entities = table_client.query_entities(query_filter)

            fileshare_usage_item = None
            latest = self._get_latest_entity_by_timestamp(entities)

            if latest:

                fileshare_usage_item = MHRAFileshareUsageItem(
                    workspace_name = latest.get('WorkspaceName', ''),
                    workspace_id=latest.get('WorkspaceId', ''),
                    storage_name = latest.get('StorageName', ''),
                    fileshare_usage = self._format_size(latest.get('FileshareUsage')),
                    fileshare_limits = self._format_size(latest.get('FileshareLimits')),
                    fileshare_remaining = self._format_size(
                        (latest.get('FileshareLimits', 0) - latest.get('FileshareUsage', 0))
                    ),
                    fileshare_percentage = math.floor(latest.get('FilesharePercentage', 0)),
                    timestamp=latest.metadata['timestamp']
                )

            return WorkspaceDataUsage(
                container_usage_item=container_usage_item,
                fileshare_usage_item=fileshare_usage_item
            )

        except HttpResponseError:
            logging.exception("HTTP error when calling table_client.")
            raise
        except Exception:
            logging.exception("Unknown error when calling table_client.")
            raise

    async def set_perstudy_items(self, workspaceId: str, protocolId: str) :
        container_perstudy_table = constants.WORKSPACE_PERSTUDY_USAGE_TABLE_NAME

        try:
            tre_id = config.TRE_ID
            workspace = constants.WORKSPACE_RESOURCE_GROUP_NAME.format(tre_id, workspaceId[-4:])
            table_client = self.client.get_table_client(table_name=container_perstudy_table)
            key_vault_name = constants.WS_KEYVAULT_NAME.format(tre_id,workspaceId[-4:])
            storageLimit = await self._fetch_key_valut("ssbs-storage-limits",key_vault_name)

            new_entity = {
                   "PartitionKey": "None",
                    "RowKey": str(uuid.uuid4()),
                    "Timestamp": datetime.now(timezone.utc).isoformat(),
                    "ProtocolDataUsage": 0.0,
                    "ProtocolId": protocolId,
                    "ProtocolPercentageUsage": 0.0,
                    'StorageLimits': float(storageLimit),
                    "StorageName": constants.STORAGE_ACCOUNT_NAME_WORKSPACE_RESOURCE_GROUP_SSBS.format(workspaceId[-4:]),
                    "WorkspaceName": workspace,
                    "WorkspaceId": workspaceId,
                    "Status": "Started",
                    "Latest": True
                }
            table_client.upsert_entity(mode=UpdateMode.MERGE, entity=new_entity)

        except HttpResponseError as e:
            logging.exception(
                "Table storage error for workspaceId=%s, protocolId=%s",
                workspaceId,
                protocolId,
            )
            raise
        except Exception as e:
            logging.exception(
                "Unexpected error in set_perstudy_items for workspaceId=%s",
                workspaceId,
            )
            raise

    async def create_container(self, container_create_request: ContainerCreateRequest, workspace_repo: WorkspaceRepository):
        workspace = await workspace_repo.get_workspace_by_id(container_create_request.workspaceId)

        template = workspace.templateName
        if template.endswith("a-msl"):
            container_name = f"{container_create_request.protocolId}a"
        else:
            container_name = f"{container_create_request.protocolId}e"

        payload = {
                "workspaceId": container_create_request.workspaceId,
                "protocolId": container_name,
            }

        message = ServiceBusMessage(body=json.dumps(payload), correlation_id=container_name, session_id=container_create_request.workspaceId)
        async with credentials.get_credential_async() as credential:
            service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)

            async with service_bus_client:
                sender = service_bus_client.get_queue_sender(queue_name=config.SERVICE_BUS_STUDY_CONTAINER_CREATE_QUEUE_NAME)

                async with sender:
                    await sender.send_messages(message)
        await self.set_perstudy_items(container_create_request.workspaceId, container_name)
        return {"container": container_name, "status": "Study item creation request submitted"}

    def _format_size(self, size_gb):

            if size_gb is None or not isinstance(size_gb, (int, float)) or size_gb < 0:
                return "0.00GB"
            if size_gb < 1024:
                return f"{size_gb:.2f}GB"
            else:
                size_tb = size_gb / 1024
                return f"{size_tb:.2f}TB"

    async def _fetch_key_valut(self, secret_name:str, key_vault_name:str) -> str:
            key_vault_url = f"https://{key_vault_name}.vault.azure.net/"
            credential = credentials.get_credential()
            client = SecretClient(vault_url=key_vault_url, credential=credential)
            retrieved_secret = client.get_secret(secret_name)
            return retrieved_secret.value

@lru_cache(maxsize=None)
def data_usage_service_factory() -> DataUsageService:
    return DataUsageService()
