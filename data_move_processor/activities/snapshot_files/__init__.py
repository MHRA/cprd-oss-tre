import azure.functions as func
import azure.durable_functions as df
from shared.blob_client import list_blobs

@df.activity_trigger(input_name="req")
def snapshot_files(req: func.InputStream) -> list:
    return list_blobs(req["workspace_id"], req["source_container"], req.get("prefix"))
