from shared.cosmos_client import log_file_status as log_file_status_func


def log_file_status(data: dict) -> None:
    """
    Logs per-file processing status to Cosmos DB.
    """

    if not isinstance(data, dict):
        return

