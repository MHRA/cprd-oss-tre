import azure.functions as func
import azure.durable_functions as df
from shared.blob_client import release_container_lease

@df.activity_trigger(input_name="data")
def release_lock(data: func.InputStream) -> None:
    req, lease_id = data
    if lease_id:
        release_container_lease(req["workspace_id"], req["source_container"], lease_id)
