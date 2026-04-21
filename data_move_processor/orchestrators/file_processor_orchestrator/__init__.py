import azure.durable_functions as df

def orchestrator(context: df.DurableOrchestrationContext):

    data = context.get_input()
    file = data["file"]
    req = data["req"]
    tid = data["transaction_id"]

    retry = 0
    max_retry = 3
    ok = False

    while retry < max_retry:
        try:
            result = yield context.call_activity("copy_blob", {"file": file, "req": req})
            ok = result.get("success", False) if isinstance(result, dict) else bool(result)
            
            if ok:
                break
        except Exception as e:
            ok = False
        
        retry += 1

    # Log file status
    yield context.call_activity(
        "log_file_status",
        (tid, file, "SUCCESS" if ok else "FAILED")
    )

    return ok

main = df.Orchestrator.create(orchestrator)
