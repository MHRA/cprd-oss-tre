import azure.functions as func
import azure.durable_functions as df

@df.activity_trigger(input_name="req")
def snapshot_files(req: dict) -> list:
    # Extract file names from the files array
    return [f["file_name"] for f in req["files"]]
