from unittest.mock import MagicMock, patch

import workflow_routes


def test_previous_partial_failure_completes_one_time_workflow():
    workflows = [
        {"id": "once", "status": "active", "lifetime_mode": "run_once"},
        {"id": "continuous", "status": "active", "lifetime_mode": "continuous"},
    ]
    runs = MagicMock()
    runs.execute.return_value.data = [{"workflow_id": "once"}]
    runs.select.return_value.in_.return_value.in_.return_value = runs
    updates = MagicMock()
    updates.update.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock()

    def table(name):
        return runs if name == "workflow_runs" else updates

    with patch.object(workflow_routes.supabase_admin, "table", side_effect=table):
        result = workflow_routes._complete_legacy_one_time_workflows(workflows)

    assert result[0]["status"] == "completed"
    assert result[1]["status"] == "active"
    updates.update.assert_called_once_with({"status": "completed"})
