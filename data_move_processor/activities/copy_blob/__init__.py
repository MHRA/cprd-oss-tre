import azure.durable_functions as df
from shared.blob_client import copy_blob as copy_blob_func

@df.activity_trigger(input_name="file_data")
def copy_blob(file_data: dict) -> dict:
    file_name = file_data["file"]
    req = file_data["req"]
    return copy_blob_func(req["workspaceId"], req["protocol_id"], file_name, req["amsl_workspace_id"])
