import azure.durable_functions as df

from shared.blob_client import check_container_integrity


@df.activity_trigger(input_name="file_data")
def check_integrity(file_data: dict) -> bool:

    if not isinstance(file_data, dict):
        return False

    req = file_data.get("req") or {}

    workspace_id = req.get("workspaceId")
    protocol_id = req.get("protocol_id")
    amsl_workspace_id = req.get("amsl_workspace_id")

    if not all([workspace_id, protocol_id, amsl_workspace_id]):
        return False

    return check_container_integrity(
        workspace_id,
        protocol_id,
        amsl_workspace_id,
    )
