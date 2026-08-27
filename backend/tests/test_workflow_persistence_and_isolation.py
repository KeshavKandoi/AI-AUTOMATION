"""
Regression tests for:
  - Persistent ("continuous") push workflows surviving repeated executions,
    vs run_once workflows still retiring to "completed" as before.
  - Correct per-organization isolation when multiple orgs share a repo and
    each has its own Gmail integration -- run_workflows must only ever
    touch the resolved organization's own workflows and Gmail token.
  - Run Now not disabling a continuous workflow.

These complement tests/test_webhook_multi_org_routing.py (org resolution)
and tests/test_workflow_regression.py (send_email/token error handling).
"""
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

import workflow_engine


def run(coro):
    return asyncio.run(coro)


def _fake_result(rows):
    m = MagicMock()
    m.data = rows
    return m


# ---------------------------------------------------------------------------
# Continuous workflows survive repeated successful executions
# ---------------------------------------------------------------------------

def test_continuous_workflow_stays_active_across_two_pushes():
    workflow = {
        "id": "wf-continuous", "organization_id": "org-A", "name": "Persistent push alert",
        "trigger_type": "push", "conditions": {}, "actions": ["send_email"],
        "lifetime_mode": "continuous", "status": "active",
    }
    inserted_rows = []
    updates_called = []

    def fake_insert(payload):
        inserted_rows.append(payload)
        m = MagicMock()
        m.execute.return_value.data = [payload]
        return m

    def fake_update(payload):
        updates_called.append(payload)
        m = MagicMock()
        m.eq.return_value.execute.return_value = MagicMock()
        return m

    with patch.dict(workflow_engine.ACTION_REGISTRY, {"send_email": AsyncMock(return_value={"message_id": "m1"})}), \
         patch.object(workflow_engine.supabase_admin, "table") as mock_table, \
         patch.object(workflow_engine, "log_event"):
        mock_table.return_value.insert.side_effect = fake_insert
        mock_table.return_value.update.side_effect = fake_update

        # Push #1
        result1 = run(workflow_engine.execute_workflow(workflow, {"title": "push 1"}, record_skipped=False))
        # Push #2 -- same workflow dict, simulating it being reloaded fresh from
        # the DB each time (status was never mutated to "completed")
        result2 = run(workflow_engine.execute_workflow(workflow, {"title": "push 2"}, record_skipped=False))

    assert result1["status"] == "success"
    assert result2["status"] == "success"
    assert len(inserted_rows) == 2
    # A continuous workflow must NEVER have its status updated to "completed"
    assert not any(u.get("status") == "completed" for u in updates_called)


def test_run_once_workflow_still_completes_after_success_unchanged():
    workflow = {
        "id": "wf-run-once", "organization_id": "org-A", "name": "One-shot alert",
        "trigger_type": "push", "conditions": {}, "actions": ["send_email"],
        "lifetime_mode": "run_once", "status": "active",
    }
    updates_called = []

    def fake_insert(payload):
        m = MagicMock()
        m.execute.return_value.data = [payload]
        return m

    def fake_update(payload):
        updates_called.append(payload)
        m = MagicMock()
        m.eq.return_value.execute.return_value = MagicMock()
        return m

    with patch.dict(workflow_engine.ACTION_REGISTRY, {"send_email": AsyncMock(return_value={"message_id": "m1"})}), \
         patch.object(workflow_engine.supabase_admin, "table") as mock_table, \
         patch.object(workflow_engine, "log_event"):
        mock_table.return_value.insert.side_effect = fake_insert
        mock_table.return_value.update.side_effect = fake_update
        run(workflow_engine.execute_workflow(workflow, {"title": "push 1"}, record_skipped=False))

    assert any(u.get("status") == "completed" for u in updates_called)


def test_run_now_on_continuous_workflow_does_not_disable_it():
    """record_skipped=True is the Run Now path -- must not flip a continuous
    workflow's status even though it does for run_once (existing, correct
    behavior preserved above)."""
    workflow = {
        "id": "wf-continuous", "organization_id": "org-A", "name": "Persistent push alert",
        "trigger_type": "push", "conditions": {}, "actions": ["send_email"],
        "lifetime_mode": "continuous", "status": "active",
    }
    updates_called = []

    def fake_insert(payload):
        m = MagicMock()
        m.execute.return_value.data = [payload]
        return m

    def fake_update(payload):
        updates_called.append(payload)
        m = MagicMock()
        m.eq.return_value.execute.return_value = MagicMock()
        return m

    with patch.dict(workflow_engine.ACTION_REGISTRY, {"send_email": AsyncMock(return_value={"message_id": "m1"})}), \
         patch.object(workflow_engine.supabase_admin, "table") as mock_table, \
         patch.object(workflow_engine, "log_event"):
        mock_table.return_value.insert.side_effect = fake_insert
        mock_table.return_value.update.side_effect = fake_update
        result = run(workflow_engine.execute_workflow(workflow, {"title": "manual run"}, record_skipped=True))

    assert result["status"] == "success"
    assert not any(u.get("status") == "completed" for u in updates_called)


def test_multiple_pushes_each_create_a_separate_workflow_run_row():
    workflow = {
        "id": "wf-continuous", "organization_id": "org-A", "name": "Persistent push alert",
        "trigger_type": "push", "conditions": {}, "actions": ["send_email"],
        "lifetime_mode": "continuous", "status": "active",
    }
    inserted_rows = []

    def fake_insert(payload):
        inserted_rows.append(payload)
        m = MagicMock()
        m.execute.return_value.data = [payload]
        return m

    with patch.dict(workflow_engine.ACTION_REGISTRY, {"send_email": AsyncMock(return_value={"message_id": "m1"})}), \
         patch.object(workflow_engine.supabase_admin, "table") as mock_table, \
         patch.object(workflow_engine, "log_event"):
        mock_table.return_value.insert.side_effect = fake_insert
        mock_table.return_value.update.side_effect = lambda payload: MagicMock(eq=MagicMock(return_value=MagicMock(execute=MagicMock())))

        for i in range(3):
            run(workflow_engine.execute_workflow(workflow, {"title": f"push {i}"}, record_skipped=False))

    assert len(inserted_rows) == 3
    assert all(r["status"] == "success" for r in inserted_rows)


# ---------------------------------------------------------------------------
# Per-organization isolation when two orgs share a repo
# ---------------------------------------------------------------------------

def test_run_workflows_only_loads_resolved_orgs_workflows_not_the_others():
    """Simulates the exact scenario this whole investigation was about: two
    orgs (A and B) both connected to the same repo, each with their own
    push workflow. A push resolved to org A must only ever query and
    execute org A's workflows -- org B's workflow must never be touched."""
    org_a_workflow = {
        "id": "wf-org-a", "organization_id": "org-A", "trigger_type": "push",
        "status": "active", "conditions": {}, "actions": ["send_email"],
        "lifetime_mode": "continuous",
    }

    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        # The query is scoped by .eq("organization_id", organization_id) --
        # simulate that scoping actually filtering to org A only, the way
        # the real Supabase query would.
        mock_table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = _fake_result(
            [org_a_workflow]
        )
        with patch.object(workflow_engine, "execute_workflow", new=AsyncMock()) as mock_execute:
            run(workflow_engine.run_workflows("org-A", "push", {"repo": "acme/repo"}))

            mock_execute.assert_called_once()
            called_workflow = mock_execute.call_args[0][0]
            assert called_workflow["organization_id"] == "org-A"
            # Confirm the query was scoped by org-A's id, not org-B's or none
            mock_table.return_value.select.return_value.eq.assert_any_call("organization_id", "org-A")


def test_send_email_for_org_a_never_uses_org_bs_token_or_email():
    """Direct isolation check on the action itself: _get_org_token and
    _get_org_email are always called with the specific organization_id
    execute_workflow passes in -- never a different org's id, and never a
    client-suppliable value."""
    workflow = {
        "id": "wf-org-a", "organization_id": "org-A", "name": "Org A alert",
        "trigger_type": "push", "conditions": {}, "actions": ["send_email"],
        "lifetime_mode": "continuous", "status": "active",
    }

    calls = {"token_org_ids": [], "email_org_ids": []}

    def fake_get_token(org_id, provider):
        calls["token_org_ids"].append(org_id)
        return ("ya29.org-a-token", None)

    def fake_get_email(org_id):
        calls["email_org_ids"].append(org_id)
        return "org-a-owner@gmail.com"

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"id": "msg-org-a"}
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post = AsyncMock(return_value=fake_response)

    with patch.object(workflow_engine, "_get_org_token", side_effect=fake_get_token), \
         patch.object(workflow_engine, "_get_org_email", side_effect=fake_get_email), \
         patch.object(workflow_engine.httpx, "AsyncClient", return_value=mock_client):
        result = run(workflow_engine._action_send_email("org-A", {"title": "t", "description": "d"}))

    assert result == {"message_id": "msg-org-a"}
    assert calls["token_org_ids"] == ["org-A"]
    assert calls["email_org_ids"] == ["org-A"]
    assert "org-B" not in calls["token_org_ids"]
    assert "org-B" not in calls["email_org_ids"]
