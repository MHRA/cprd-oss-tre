from shared.service_bus_client import send_message


async def send_status_event(message: dict) -> None:


    if not isinstance(message, dict):
        return


