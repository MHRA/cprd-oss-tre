from shared.blob_client import release_container_lease


def release_lock(data: dict) -> None:
    """
    Releases a container lease.
    Safe to call multiple times and safe for Durable replay.
    """

    if not isinstance(data, dict):
        return

    req = data.get("req") or {}
    lease_id = data.get("lease_id")

    if not lease_id:
        return

    workspace_id = req.get("workspaceId")
    protocol_id = req.get("protocol_id")

    if not workspace_id or not protocol_id:
        return

    release_container_lease(
        workspace_id,
        protocol_id,
        lease_id,
    )
