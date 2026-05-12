print(">>> function_app.py LOADED <<<")
import azure.functions as func
import azure.durable_functions as df
import json

# Import orchestrator implementations
from orchestrators.data_move_orchestrator import main as data_move_orch_impl
from orchestrators.file_processor_orchestrator import main as file_processor_orch_impl

# Import activity implementations (plain functions without decorators)
from activities.check_preconditions import check_preconditions as check_preconditions_impl
from activities.acquire_lock import acquire_lock as acquire_lock_impl
from activities.snapshot_files import snapshot_files as snapshot_files_impl
from activities.copy_blob import copy_blob as copy_blob_impl
from activities.check_integrity import check_integrity as check_integrity_impl
from activities.update_file_status import log_file_status as log_file_status_impl
from activities.update_transaction_status import update_transaction_status as update_transaction_status_impl
from activities.delete_source_files import delete_source_files as delete_source_files_impl
from activities.release_lock import release_lock as release_lock_impl
from activities.send_status_event import send_status_event as send_status_event_impl

# Config
from shared.config import SERVICE_BUS_DATA_MOVE_QUEUE_NAME, SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE

app = df.DFApp()

QUEUE_NAME = SERVICE_BUS_DATA_MOVE_QUEUE_NAME or "datamove-events"
SERVICE_BUS_CONNECTION = SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE or "SERVICE_BUS_CONN_STR"


# ✅ Service Bus trigger - ENTRY POINT
@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name=QUEUE_NAME,
    connection=SERVICE_BUS_CONNECTION
)
@app.durable_client_input(client_name="client")
async def data_move_trigger(msg: func.ServiceBusMessage, client):

    body = json.loads(msg.get_body().decode("utf-8"))

    instance_id = await client.start_new(
        "data_move_orchestrator",
        None,
        body["payload"]
    )

    return instance_id


# ✅ ORCHESTRATORS - Decorate once here (names MUST match start_new / call_sub_orchestrator)
@app.orchestration_trigger(context_name="context")
def data_move_orchestrator(context):
    return data_move_orch_impl(context)


@app.orchestration_trigger(context_name="context")
def file_processor_orchestrator(context):
    return file_processor_orch_impl(context)


# ✅ ACTIVITIES - Decorate once here (names MUST match call_activity)
@app.activity_trigger(input_name="input")
def check_preconditions(input):
    return check_preconditions_impl(input)


@app.activity_trigger(input_name="input")
def acquire_lock(input):
    return acquire_lock_impl(input)


@app.activity_trigger(input_name="input")
def snapshot_files(input):
    return snapshot_files_impl(input)


@app.activity_trigger(input_name="input")
def copy_blob(input):
    return copy_blob_impl(input)


@app.activity_trigger(input_name="input")
def check_integrity(input):
    return check_integrity_impl(input)


@app.activity_trigger(input_name="input")
def log_file_status(input):
    return log_file_status_impl(input)


@app.activity_trigger(input_name="input")
def update_transaction_status(input):
    return update_transaction_status_impl(input)


@app.activity_trigger(input_name="input")
def delete_source_files(input):
    return delete_source_files_impl(input)


@app.activity_trigger(input_name="input")
def release_lock(input):
    return release_lock_impl(input)


@app.activity_trigger(input_name="input")
async def send_status_event(input):
    return await send_status_event_impl(input)
