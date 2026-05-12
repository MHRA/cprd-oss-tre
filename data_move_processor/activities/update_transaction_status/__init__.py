from datetime import datetime, timezone

from shared.cosmos_client import update_transaction


def update_transaction_status(data: dict) -> None:


    if not isinstance(data, dict):
        return

    transaction_id = data.get("transaction_id")
    partition_key = data.get("partition_key") or transaction_id
    status = data.get("status")

    if not transaction_id or not status:
        return

    update_transaction(
        item_id=transaction_id,
        partition_key=partition_key,
        patch={
            "status": status,
            "updatedWhen": datetime.now(timezone.utc).isoformat(),
        },
    )
