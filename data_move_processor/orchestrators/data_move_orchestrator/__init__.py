import azure.durable_functions as df

def orchestrator(context: df.DurableOrchestrationContext):

    req = context.get_input()

    # 1. Pre-check
    ok = yield context.call_activity("check_preconditions", req)
    if not ok:
        return "FAILED_PRECONDITIONS"

    # 2. Transaction creation
    yield context.call_activity("update_transaction_status",
                                        (req["id"], "STARTED"))

    try:
        # 3. Lock
        lease_id = yield context.call_activity("acquire_lock", req)
        if not lease_id:
            return "FAILED_TO_ACQUIRE_LOCK"

        # 4. Get files
        files = yield context.call_activity("snapshot_files", req)

        # ⚡ 5. PARALLEL PROCESSING
        tasks = [
            context.call_sub_orchestrator(
                "file_processor_orchestrator",
                {
                    "transaction_id": req["id"],
                    "file": f,
                    "req": req
                }
            )
            for f in files
        ]

        results = yield context.task_all(tasks)

        success: bool = all(results)

        # 5a. Check integrity for all copied files
        if success:
            ok = yield context.call_activity("check_integrity", {"transaction_id": req["id"], "req": req})
            success = ok

        # 5b. Delete source files after integrity check passes
        if success:
            delete_tasks = [
                context.call_activity("delete_source_files", {"file": f, "req": req})
                for f in files
            ]
            yield context.task_all(delete_tasks)

        # 6. Final update + notify
        if success:
            yield context.call_activity("update_transaction_status",
                                        (req["id"], "COMPLETED"))

            yield context.call_activity("send_status_event",
                                        {"status": "SUCCESS", "transaction": req["id"]})
        else:
            yield context.call_activity("update_transaction_status",
                                        (req["id"], "FAILED"))

            yield context.call_activity("send_status_event",
                                        {"status": "FAILED", "transaction": req["id"]})

    finally:
        yield context.call_activity("release_lock", (req, lease_id))

    return "DONE"

main = df.Orchestrator.create(orchestrator)
