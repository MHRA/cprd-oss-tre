import azure.functions as func
import azure.durable_functions as df
from shared.blob_client import copy_blob as copy_blob_func

@df.activity_trigger(input_name="file_data")
def copy_blob(file_data: func.InputStream) -> dict:
    file = file_data["file"]
    req = file_data["req"]
    return copy_blob_func(req["workspace_id"], req["source_container"], file, req["dest_container"], file)
