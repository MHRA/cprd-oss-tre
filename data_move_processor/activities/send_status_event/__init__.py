import azure.functions as func
import azure.durable_functions as df
from shared.service_bus_client import send_message

@df.activity_trigger(input_name="message")
def send_status_event(message: func.InputStream) -> None:
    send_message(message)
