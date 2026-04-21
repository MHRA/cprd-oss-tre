import azure.durable_functions as df
from shared.blob_client import check_integrity as check_integrity_func

@df.activity_trigger(input_name="file_data")
def check_integrity(file_data: dict) -> bool:
    file = file_data["file"]
    req = file_data["req"]
    return check_integrity_func(req["workspace_id"], req["source_container"], file, req["dest_container"], file)
