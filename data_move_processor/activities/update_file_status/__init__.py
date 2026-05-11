import azure.durable_functions as df

from shared.cosmos_client import log_file_status as log_file_status_func


@df.activity_trigger(input_name="data")
def log_file_status(data: dict) -> None:
    """
    Logs per-file processing status to Cosmos DB.
    """

    if not isinstance(data, dict):
        return

    transaction_id = data.get("transaction_id")
    file_name = data.get("file")
    status = data.get("status")

    if not transaction_id or not file_name or not status:
        return

    log_file_status_func(
        transaction_id=transaction_id,
        file_name=file_name,
        status=status,
    )
