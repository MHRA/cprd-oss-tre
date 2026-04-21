import azure.functions as func
import azure.durable_functions as df
from shared.blob_client import release_container_lease

@df.activity_trigger(input_name="data")
def release_lock(data: tuple) -> None:
    req, lease_id = data
    if lease_id:
        release_container_lease(req["workspaceId"], req["protocol_id"], lease_id)
