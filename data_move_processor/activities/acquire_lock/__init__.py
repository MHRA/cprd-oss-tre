import azure.functions as func
import azure.durable_functions as df
from shared.blob_client import acquire_container_lease

@df.activity_trigger(input_name="req")
def acquire_lock(req: dict) -> str:
    lease_id = acquire_container_lease(req["workspaceId"], req["protocol_id"])
    return lease_id  # Return lease_id if acquired, None if failed
