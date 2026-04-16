import azure.functions as func
import azure.durable_functions as df
from shared.cosmos_client import create_transaction as create_transaction_db
import uuid

@df.activity_trigger(input_name="req")
def create_transaction(req: func.InputStream) -> str:
    transaction_id = str(uuid.uuid4())
    doc = {
        "id": transaction_id,
        "source_container": req["source_container"],
        "dest_container": req["dest_container"],
        "status": "STARTED",
        "created_at": str(func.datetime.datetime.utcnow())
    }
    create_transaction_db(doc)
    return transaction_id
