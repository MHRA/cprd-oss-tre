import azure.durable_functions as df
from shared.blob_client import delete_blob

@df.activity_trigger(input_name="file_data")
def delete_source_files(file_data: dict) -> None:
    file = file_data["file"]
    req = file_data["req"]
    delete_blob(req["workspace_id"], req["source_container"], file)
