import logging
import os
from typing import Optional

from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
from azure.identity.aio import DefaultAzureCredential

from shared.config import (
    SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE,
    SERVICE_BUS_DATA_MOVE_QUEUE_NAME,
)

# ==========================================================
# Credential (SAFE, ASYNC)
# ==========================================================

def get_credential() -> DefaultAzureCredential:
    """
    Returns a DefaultAzureCredential.
    Uses Managed Identity if MANAGED_IDENTITY_CLIENT_ID is set.
    """
    managed_identity: Optional[str] = os.getenv("MANAGED_IDENTITY_CLIENT_ID")

    if managed_identity:
        logging.info("Using managed identity for Service Bus")
        return DefaultAzureCredential(
            managed_identity_client_id=managed_identity,
            exclude_shared_token_cache_credential=True,
        )

    return DefaultAzureCredential()


# ==========================================================
# Service Bus Sender
# ==========================================================

async def send_message(message_body: str) -> None:


    if not SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE:
        raise RuntimeError("SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE is not set")

    if not SERVICE_BUS_DATA_MOVE_QUEUE_NAME:
        raise RuntimeError("SERVICE_BUS_DATA_MOVE_QUEUE_NAME is not set")

    credential = get_credential()

    service_bus_client = ServiceBusClient(
        fully_qualified_namespace=SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE,
        credential=credential,
    )

    async with service_bus_client:
        sender = service_bus_client.get_queue_sender(
            queue_name=SERVICE_BUS_DATA_MOVE_QUEUE_NAME
        )

        async with sender:
            message = ServiceBusMessage(message_body)
            await sender.send_messages(message)
