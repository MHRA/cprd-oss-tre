import azure.durable_functions as df
from shared.blob_client import check_container_integrity

@df.activity_trigger(input_name="file_data")
def check_integrity(file_data: dict) -> bool:
    transaction_id = file_data["transaction_id"]
    req = file_data["req"]
    # Check integrity between source and destination containers
    return check_container_integrity(req["workspaceId"], req["protocol_id"], req["amsl_workspace_id"])
