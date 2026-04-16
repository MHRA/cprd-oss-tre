import azure.functions as func
import azure.durable_functions as df
from shared.blob_client import acquire_container_lease

@df.activity_trigger(input_name="req")
def acquire_lock(req: func.InputStream) -> str:
    lease_id = acquire_container_lease(req["workspace_id"], req["source_container"])
    return lease_id  # Return lease_id if acquired, None if failed
