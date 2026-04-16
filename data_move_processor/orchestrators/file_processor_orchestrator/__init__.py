import azure.durable_functions as df

def orchestrator(context: df.DurableOrchestrationContext):

    data = context.get_input()
    file = data["file"]
    req = data["req"]
    tid = data["transaction_id"]

    retry = 0
    max_retry = 3

    while retry < max_retry:

        yield context.call_activity("copy_blob", file)

        ok = yield context.call_activity("check_integrity", file)

        yield context.call_activity(
            "log_file_status",
            (tid, file["name"], "SUCCESS" if ok else "FAILED")
        )

        if ok:
            yield context.call_activity("delete_source_files", {"file": file, "req": req})
            return True

        retry += 1

    return False

main = df.Orchestrator.create(orchestrator)
