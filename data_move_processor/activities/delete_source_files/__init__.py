from shared.blob_client import delete_blob


def delete_source_files(file_data: dict) -> None:

    if not isinstance(file_data, dict):
        return

    file_name = file_data.get("file")
    req = file_data.get("req") or {}

    workspace_id = req.get("workspaceId")
    protocol_id = req.get("protocol_id")

    if not file_name or not workspace_id or not protocol_id:
        return

    delete_blob(
        workspace_id,
        protocol_id,
        file_name,
    )
