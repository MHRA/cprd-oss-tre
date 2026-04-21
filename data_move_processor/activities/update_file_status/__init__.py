import azure.functions as func
import azure.durable_functions as df
from shared.cosmos_client import log_file_status as log_file_status_func

@df.activity_trigger(input_name="data")
def log_file_status(data: tuple) -> None:
    tid, file_name, status = data
    log_file_status_func(tid, file_name, status, str(func.datetime.datetime.utcnow()))
