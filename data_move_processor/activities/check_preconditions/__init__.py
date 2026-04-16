import azure.functions as func
import azure.durable_functions as df
from shared.blob_client import list_blobs

@df.activity_trigger(input_name="req")
def check_preconditions(req: func.InputStream) -> bool:
    # Check if source container has files
    files = list_blobs(req["workspace_id"], req["source_container"], req.get("prefix"))
    return len(files) > 0
