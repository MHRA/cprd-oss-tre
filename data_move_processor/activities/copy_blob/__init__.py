import azure.durable_functions as df
from shared.blob_client import copy_blob as copy_blob_func

@df.activity_trigger(input_name="file_data")
def copy_blob(file_data: dict) -> dict:
    file = file_data["file"]
    req = file_data["req"]
    return copy_blob_func(req["workspace_id"], req["protocol_id"], file, req["amsl_workspace_id"], file)
