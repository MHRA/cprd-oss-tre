from typing import Optional

from shared.blob_client import acquire_container_lease


def acquire_lock(req: dict) -> Optional[str]:


    if not isinstance(req, dict):
        return None

    workspace_id = req.get("workspaceId")
    protocol_id = req.get("protocol_id")

    if not workspace_id or not protocol_id:
        return None

    return acquire_container_lease(workspace_id, protocol_id)
