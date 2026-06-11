from datetime import datetime, timezone
import logging

from shared.cosmos_client import update_transaction


def update_transaction_status(data: dict) -> None:
    transaction_id = data.get("transaction_id")
    workspace_id = data.get("workspaceId")
    status = data.get("status")
    logging.info(f"Updating transaction {transaction_id} in workspace {workspace_id} to status {status}")

    if not transaction_id or not workspace_id or not status:
        return

    update_transaction(
        item_id=transaction_id,
        partition_key=transaction_id,
        patch={
            "status": status,
           "updatedWhen": datetime.now(timezone.utc).timestamp(),
        },
    )
