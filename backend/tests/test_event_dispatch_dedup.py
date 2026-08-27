"""
Regression tests for the shared event-dispatch layer (dispatch_workflow_event
/ _record_event_if_new) added to unify GitHub webhook events and internally
generated events (e.g. Commit Scheduler) through the same workflow engine
with database-enforced idempotency.
"""
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

import workflow_engine


def run(coro):
    return asyncio.run(coro)


class _DuplicateKeyError(Exception):
    def __str__(self):
        return "duplicate key value violates unique constraint \"processed_github_events_organization_id_repo_full_name_event_type_event_key_key\" (23505)"


def test_record_event_if_new_returns_true_on_first_insert():
    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        mock_table.return_value.insert.return_value.execute.return_value = MagicMock()
        result = workflow_engine._record_event_if_new("org-A", "acme/repo", "push", "sha123")
        assert result is True


def test_record_event_if_new_returns_false_on_unique_violation():
    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        mock_table.return_value.insert.return_value.execute.side_effect = _DuplicateKeyError()
        result = workflow_engine._record_event_if_new("org-A", "acme/repo", "push", "sha123")
        assert result is False


def test_record_event_if_new_reraises_unexpected_errors():
    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        mock_table.return_value.insert.return_value.execute.side_effect = RuntimeError("network blip")
        try:
            workflow_engine._record_event_if_new("org-A", "acme/repo", "push", "sha123")
            assert False, "expected the unexpected error to propagate"
        except RuntimeError:
            pass


def test_dispatch_workflow_event_calls_run_workflows_on_first_occurrence():
    context = {"repo": "acme/repo", "commit_sha": "sha123"}
    with patch.object(workflow_engine, "_record_event_if_new", return_value=True), \
         patch.object(workflow_engine, "run_workflows", new=AsyncMock()) as mock_run:
        run(workflow_engine.dispatch_workflow_event("org-A", "push", context, "sha123"))
        mock_run.assert_called_once_with("org-A", "push", context)


def test_dispatch_workflow_event_skips_run_workflows_on_duplicate():
    context = {"repo": "acme/repo", "commit_sha": "sha123"}
    with patch.object(workflow_engine, "_record_event_if_new", return_value=False), \
         patch.object(workflow_engine, "run_workflows", new=AsyncMock()) as mock_run:
        run(workflow_engine.dispatch_workflow_event("org-A", "push", context, "sha123"))
        mock_run.assert_not_called()


def test_dispatch_workflow_event_dedup_key_is_scoped_by_org_repo_type_and_key():
    """Two different orgs (or two different repos, or two different event
    types) with the SAME event_key must NOT be treated as duplicates of each
    other -- only the exact same (org, repo, type, key) tuple counts."""
    calls = []

    def fake_record(organization_id, repo_full_name, event_type, event_key):
        calls.append((organization_id, repo_full_name, event_type, event_key))
        return True  # simulate: each of these is genuinely new

    with patch.object(workflow_engine, "_record_event_if_new", side_effect=fake_record), \
         patch.object(workflow_engine, "run_workflows", new=AsyncMock()) as mock_run:
        run(workflow_engine.dispatch_workflow_event("org-A", "push", {"repo": "acme/repo"}, "sha123"))
        run(workflow_engine.dispatch_workflow_event("org-B", "push", {"repo": "acme/repo"}, "sha123"))
        run(workflow_engine.dispatch_workflow_event("org-A", "acme/other-repo", {"repo": "acme/other-repo"}, "sha123"))

    assert ("org-A", "acme/repo", "push", "sha123") in calls
    assert ("org-B", "acme/repo", "push", "sha123") in calls
    assert mock_run.call_count == 3
