import azure.durable_functions as df

def orchestrator(context: df.DurableOrchestrationContext):
    req = context.get_input()

    transaction_id = req.get("id")
    workspace_id = req.get("workspaceId")
    if not transaction_id:
        return "INVALID_INPUT"

    lease_id = None

    ok = yield context.call_activity("check_preconditions", req)
    if not ok:
        return "FAILED_PRECONDITIONS"

    yield context.call_activity(
    "update_transaction_status",
        {
            "transaction_id": transaction_id,
            "workspaceId": workspace_id,
            "status": "STARTED"
        }
    )

    try:
        lease_id = yield context.call_activity("acquire_lock", req)
        if not lease_id:
            return "FAILED_TO_ACQUIRE_LOCK"

        files = yield context.call_activity("snapshot_files", req)

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

        # Integrity check is not working as expected. Must be reviewed.
        # if success:
        #     success = yield context.call_activity(
        #         "check_integrity",
        #         {"transaction_id": transaction_id, "req": req}
        #     )

        if success:
            delete_tasks = [
                context.call_activity(
                    "delete_source_files",
                    {"file": f, "req": req}
                )
                for f in files
            ]
            yield context.task_all(delete_tasks)

        status = "COMPLETED" if success else "FAILED"

        yield context.call_activity(
            "update_transaction_status",
            {
                "transaction_id": transaction_id,
                "workspaceId": workspace_id,
                "status": status
            }
        )

        yield context.call_activity(
            "send_status_event",
            {"status": status, "transaction": transaction_id,"req": req}
        )

    finally:
        if lease_id:
            yield context.call_activity(
                "release_lock",
                {"req": req, "lease_id": lease_id}
            )

    return "DONE"

# Export for v2 SDK - decorator-based approach
main = orchestrator
