import azure.durable_functions as df

def orchestrator(context: df.DurableOrchestrationContext):

    req = context.get_input()

    # 1. Pre-check
    ok = yield context.call_activity("check_preconditions", req)
    if not ok:
        return "FAILED_PRECONDITIONS"

    # 2. Transaction creation
    transaction_id = yield context.call_activity("create_transaction", req)

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
                    "transaction_id": transaction_id,
                    "file": f,
                    "req": req
                }
            )
            for f in files
        ]

        results = yield context.task_all(tasks)

        success = all(results)

        # 6. Final update + notify
        if success:
            yield context.call_activity("update_transaction_status",
                                        (transaction_id, "COMPLETED"))

            yield context.call_activity("send_status_event",
                                        {"status": "SUCCESS", "transaction": transaction_id})
        else:
            yield context.call_activity("update_transaction_status",
                                        (transaction_id, "FAILED"))

            yield context.call_activity("send_status_event",
                                        {"status": "FAILED", "transaction": transaction_id})

    finally:
        yield context.call_activity("release_lock", (req, lease_id))

    return "DONE"

main = df.Orchestrator.create(orchestrator)
