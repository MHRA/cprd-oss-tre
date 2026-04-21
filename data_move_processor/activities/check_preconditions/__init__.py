import azure.functions as func
import azure.durable_functions as df

@df.activity_trigger(input_name="req")
def check_preconditions(req: dict) -> bool:
    # Check if files array exists and has files
    if not req.get("files") or not isinstance(req["files"], list):
        return False
    return len(req["files"]) > 0
