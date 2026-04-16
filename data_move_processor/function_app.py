import azure.functions as func
import azure.durable_functions as df
import json

# Import orchestrators
from orchestrators.data_move_orchestrator import main as data_move_orchestrator
from orchestrators.file_processor_orchestrator import main as file_processor_orchestrator

# Import activities
from activities.check_preconditions import check_preconditions
from activities.create_transaction import create_transaction
from activities.acquire_lock import acquire_lock
from activities.snapshot_files import snapshot_files
from activities.copy_blob import copy_blob
from activities.check_integrity import check_integrity
from activities.update_file_status import log_file_status
from activities.update_transaction_status import update_transaction_status
from activities.delete_source_files import delete_source_files
from activities.release_lock import release_lock
from activities.send_notification import send_notification
from activities.send_status_event import send_status_event

@func.ServiceBusQueueTrigger(arg_name="msg", queue_name="datamove-events", connection="SERVICE_BUS_CONN_STR")
@df.DurableOrchestrationClient.input(starter)
async def data_move_trigger(msg: func.ServiceBusMessage, starter: str):

    client = df.DurableOrchestrationClient(starter)

    body = json.loads(msg.get_body().decode("utf-8"))

    instance_id = await client.start_new(
        "data_move_orchestrator",
        None,
        body["payload"]
    )

    return instance_id
