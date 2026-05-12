import azure.durable_functions as df

def orchestrator(context: df.DurableOrchestrationContext):

    data = context.get_input() or {}

    file = data.get("file")
    req = data.get("req")
    tid = data.get("transaction_id")

    if not file or not req or not tid:
        return False

    max_retry = 3
    retry = 0
    ok = False

    while retry < max_retry:
        result = yield context.call_activity(
            "copy_blob",
            {"file": file, "req": req}
        )

        ok = isinstance(result, dict) and result.get("success", False)
        if ok:
            break

        retry += 1

    yield context.call_activity(
        "log_file_status",
        {
            "transaction_id": tid,
            "file": file,
            "status": "SUCCESS" if ok else "FAILED"
        }
    )

    return ok

# Export for v2 SDK - decorator-based approach
main = orchestrator
