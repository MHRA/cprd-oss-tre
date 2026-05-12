from shared.blob_client import copy_blob as copy_blob_func

def copy_blob(file_data: dict) -> dict:


    if not isinstance(file_data, dict):
        return {"success": False, "error": "Invalid input"}

    file_name = file_data.get("file")
    req = file_data.get("req") or {}

    workspace_id = req.get("workspaceId")
    protocol_id = req.get("protocol_id")
    amsl_workspace_id = req.get("amsl_workspace_id")

    if not all([file_name, workspace_id, protocol_id, amsl_workspace_id]):
        return {
            "success": False,
            "error": "Missing required parameters",
            "file": file_name,
        }

    try:
        props = copy_blob_func(
            workspace_id,
            protocol_id,
            file_name,
            amsl_workspace_id,
        )

        # ✅ Return JSON-safe payload only
        return {
            "success": True,
            "file": file_name,
            "etag": getattr(props, "etag", None),
            "size": getattr(props, "size", None),
        }

    except Exception as exc:
        return {
            "success": False,
            "file": file_name,
            "error": str(exc),
        }
