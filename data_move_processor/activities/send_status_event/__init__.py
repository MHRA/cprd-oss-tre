import azure.durable_functions as df

from shared.service_bus_client import send_message


@df.activity_trigger(input_name="message")
async def send_status_event(message: dict) -> None:


    if not isinstance(message, dict):
        return

    # Convert payload to string if needed
    await send_message(message)
