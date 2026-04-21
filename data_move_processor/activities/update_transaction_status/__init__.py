import azure.functions as func
import azure.durable_functions as df
from shared.cosmos_client import update_transaction

@df.activity_trigger(input_name="data")
def update_transaction_status(data: tuple) -> None:
    tid, status = data
    update_transaction(tid, {"status": status, "updatedWhen": str(func.datetime.datetime.utcnow())})
