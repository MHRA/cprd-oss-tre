import logging
import os

from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
from azure.identity.aio import DefaultAzureCredential
from azure.servicebus.aio._servicebus_sender_async import ServiceBusSender

from shared.config import (
    SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE,
    SERVICE_BUS_DATA_MOVE_QUEUE_NAME,
)

async def send_message(message_body: str) -> None:
    credential: DefaultAzureCredential  = get_credential()

    async with credential:
        service_bus_client = ServiceBusClient(
            fully_qualified_namespace=SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE,
            credential=credential,
        )

        async with service_bus_client:
            sender: ServiceBusSender = service_bus_client.get_queue_sender(
                queue_name=SERVICE_BUS_DATA_MOVE_QUEUE_NAME
            )

            async with sender:
                message = ServiceBusMessage(message_body)
                await sender.send_messages(message)

def get_credential() -> DefaultAzureCredential:
    managed_identity: str | None = os.environ.get("MANAGED_IDENTITY_CLIENT_ID")
    if managed_identity:
        logging.info("using the data_move_processor's managed identity to get credentials.")
    return DefaultAzureCredential(managed_identity_client_id=os.environ.get("MANAGED_IDENTITY_CLIENT_ID"),
                                  exclude_shared_token_cache_credential=True) if managed_identity else DefaultAzureCredential()
