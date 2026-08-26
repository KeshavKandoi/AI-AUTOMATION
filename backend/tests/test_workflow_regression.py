"""
Regression tests added after the Aug 25 2026 incident and the subsequent
Gmail-recipient-resolution fix:

  - org f1bbde89: send_email failed with generic "Missing Gmail token or org
    email" when the real cause was a missing notification_email -- which
    turned out to be a dead column nothing in the product ever writes.
  - org 8cade9c9: send_email failed the same generic way when the real cause
    was Google OAuth invalid_grant (expired/revoked refresh token).
  - Product decision: the recipient for workflow emails is the connected
    Gmail account's own address (resolved live via Google's userinfo
    endpoint), not organizations.notification_email. notification_email is
    now an optional override only, used if explicitly set.

No async test runner (pytest-asyncio) is installed and none of the existing
88 tests use one, so async code under test is driven via asyncio.run()
inside plain sync test functions, matching the existing project convention.
"""
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import workflow_engine


def _fake_result(rows):
    m = MagicMock()
    m.data = rows
    return m


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# 1. _get_org_token error-reason specificity
# ---------------------------------------------------------------------------

def test_get_org_token_no_integration_connected():
    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = _fake_result([])
        token, reason = workflow_engine._get_org_token("org-1", "gmail")
        assert token is None
        assert "No connected gmail integration" in reason


def test_get_org_token_invalid_grant_gives_reconnect_message():
    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = _fake_result(
            [{"id": "int-1"}]
        )
        with patch.object(
            workflow_engine, "get_valid_access_token",
            side_effect=ValueError("Failed to refresh token: {'error': 'invalid_grant', 'error_description': 'Token has been expired or revoked.'}")
        ):
            token, reason = workflow_engine._get_org_token("org-1", "gmail")
            assert token is None
            assert "reconnect gmail" in reason.lower()
            assert "expired or was revoked" in reason


def test_get_org_token_no_token_row_gives_reconnect_message():
    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = _fake_result(
            [{"id": "int-1"}]
        )
        with patch.object(
            workflow_engine, "get_valid_access_token",
            side_effect=ValueError("No token found for integration_id int-1")
        ):
            token, reason = workflow_engine._get_org_token("org-1", "gmail")
            assert token is None
            assert "No gmail token on record" in reason


def test_get_org_token_success_returns_token_and_no_error():
    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = _fake_result(
            [{"id": "int-1"}]
        )
        with patch.object(workflow_engine, "get_valid_access_token", return_value="ya29.fake-token"):
            token, reason = workflow_engine._get_org_token("org-1", "gmail")
            assert token == "ya29.fake-token"
            assert reason is None


# ---------------------------------------------------------------------------
# 2. _get_org_email: connected-Gmail-account resolution (new behavior)
# ---------------------------------------------------------------------------

def test_get_org_email_uses_override_when_set():
    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.execute.return_value = _fake_result(
            [{"notification_email": "override@example.com"}]
        )
        with patch.object(workflow_engine, "_get_org_token") as mock_get_token:
            email = workflow_engine._get_org_email("org-1")
            assert email == "override@example.com"
            # Override present -> must short-circuit, never call userinfo/token resolution
            mock_get_token.assert_not_called()


def test_get_org_email_resolves_connected_gmail_account_when_no_override():
    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.execute.return_value = _fake_result(
            [{"notification_email": None}]
        )
        fake_userinfo_response = MagicMock()
        fake_userinfo_response.status_code = 200
        fake_userinfo_response.json.return_value = {"email": "realuser@gmail.com"}

        with patch.object(workflow_engine, "_get_org_token", return_value=("ya29.valid-token", None)), \
             patch.object(workflow_engine.httpx, "get", return_value=fake_userinfo_response) as mock_get:
            email = workflow_engine._get_org_email("org-1")
            assert email == "realuser@gmail.com"
            called_headers = mock_get.call_args.kwargs.get("headers", {})
            assert called_headers.get("Authorization") == "Bearer ya29.valid-token"


def test_get_org_email_returns_none_when_gmail_not_connected():
    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.execute.return_value = _fake_result(
            [{"notification_email": None}]
        )
        with patch.object(workflow_engine, "_get_org_token", return_value=(None, "No connected gmail integration for this organization")):
            email = workflow_engine._get_org_email("org-1")
            assert email is None


def test_get_org_email_returns_none_on_insufficient_scope():
    """Simulates an org connected before the userinfo.email scope was added --
    userinfo call fails even though the Gmail token itself is otherwise valid."""
    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.execute.return_value = _fake_result(
            [{"notification_email": None}]
        )
        fake_response = MagicMock()
        fake_response.status_code = 403
        fake_response.text = "Insufficient Permission"

        with patch.object(workflow_engine, "_get_org_token", return_value=("ya29.old-scope-token", None)), \
             patch.object(workflow_engine.httpx, "get", return_value=fake_response):
            email = workflow_engine._get_org_email("org-1")
            assert email is None


# ---------------------------------------------------------------------------
# 3. _action_send_email surfaces the specific reason
# ---------------------------------------------------------------------------

def test_send_email_gmail_not_connected():
    with patch.object(workflow_engine, "_get_org_token", return_value=(None, "No connected gmail integration for this organization")), \
         patch.object(workflow_engine, "_get_org_email", return_value=None):
        with pytest.raises(RuntimeError) as exc:
            run(workflow_engine._action_send_email("org-1", {"title": "t", "description": "d"}))
        assert "gmail" in str(exc.value).lower()


def test_send_email_expired_token_gives_reconnect_message():
    with patch.object(workflow_engine, "_get_org_token", return_value=(None, "Gmail authorization expired or was revoked — please reconnect gmail in Settings")), \
         patch.object(workflow_engine, "_get_org_email", return_value=None):
        with pytest.raises(RuntimeError) as exc:
            run(workflow_engine._action_send_email("org-1", {"title": "t", "description": "d"}))
        assert "authorization expired" in str(exc.value).lower()


def test_send_email_token_valid_but_email_unresolvable_prompts_reconnect():
    """Token works, but _get_org_email came back None (e.g. insufficient
    scope from a pre-fix connection) -- message must point at reconnecting,
    not at a notification_email setting that no longer drives this path."""
    with patch.object(workflow_engine, "_get_org_token", return_value=("ya29.valid-token", None)), \
         patch.object(workflow_engine, "_get_org_email", return_value=None):
        with pytest.raises(RuntimeError) as exc:
            run(workflow_engine._action_send_email("org-1", {"title": "t", "description": "d"}))
        msg = str(exc.value).lower()
        assert "reconnect gmail" in msg
        assert "notification email is set" not in msg  # old wording must be gone


def test_send_email_success_path_uses_resolved_recipient():
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"id": "msg-123"}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post = AsyncMock(return_value=fake_response)

    with patch.object(workflow_engine, "_get_org_token", return_value=("ya29.valid-token", None)), \
         patch.object(workflow_engine, "_get_org_email", return_value="realuser@gmail.com"), \
         patch.object(workflow_engine.httpx, "AsyncClient", return_value=mock_client):
        result = run(workflow_engine._action_send_email("org-1", {"title": "Hi", "description": "body"}))
        assert result == {"message_id": "msg-123"}


# ---------------------------------------------------------------------------
# 4. _action_create_calendar_event surfaces the specific reason
# ---------------------------------------------------------------------------

def test_calendar_event_surfaces_specific_reason():
    with patch.object(workflow_engine, "_get_org_token", return_value=(None, "No connected calendar integration for this organization")):
        with pytest.raises(RuntimeError) as exc:
            run(workflow_engine._action_create_calendar_event("org-1", {"title": "Meeting"}))
        assert "No connected calendar integration" in str(exc.value)


# ---------------------------------------------------------------------------
# 5. GitHub PUSH trigger matching: org_id resolved server-side, only that
#    org's workflows fire
# ---------------------------------------------------------------------------

def test_run_workflows_only_fires_for_matching_org_and_trigger():
    push_context = {"repo": "acme/repo", "branch": "main", "author": "octocat",
                     "commit_message": "fix", "commit_sha": "abc123",
                     "files_changed": [], "commit_count": 1, "timestamp": ""}

    matching_workflow = {
        "id": "wf-1", "organization_id": "org-A", "trigger_type": "push",
        "status": "active", "conditions": {}, "actions": ["send_email"],
        "lifetime_mode": "continuous",
    }

    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = _fake_result(
            [matching_workflow]
        )
        with patch.object(workflow_engine, "execute_workflow", new=AsyncMock()) as mock_execute:
            run(workflow_engine.run_workflows("org-A", "push", push_context))
            mock_execute.assert_called_once()
            called_workflow, called_context = mock_execute.call_args[0][0], mock_execute.call_args[0][1]
            assert called_workflow["organization_id"] == "org-A"
            assert called_context["repo"] == "acme/repo"


def test_run_workflows_no_workflows_for_org_is_a_noop():
    with patch.object(workflow_engine.supabase_admin, "table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = _fake_result([])
        with patch.object(workflow_engine, "execute_workflow", new=AsyncMock()) as mock_execute:
            run(workflow_engine.run_workflows("org-with-no-workflows", "push", {}))
            mock_execute.assert_not_called()


# ---------------------------------------------------------------------------
# 6. Run status recording: success / partial_failure
# ---------------------------------------------------------------------------

def test_execute_workflow_records_partial_failure_on_action_error():
    workflow = {
        "id": "wf-1", "organization_id": "org-A", "name": "Test WF",
        "trigger_type": "push", "conditions": {}, "actions": ["send_email"],
        "lifetime_mode": "continuous", "status": "active",
    }
    inserted = {}

    def fake_insert(payload):
        inserted.update(payload)
        m = MagicMock()
        m.execute.return_value.data = [payload]
        return m

    with patch.dict(workflow_engine.ACTION_REGISTRY, {"send_email": AsyncMock(side_effect=RuntimeError("Gmail authorization expired or was revoked — please reconnect gmail in Settings"))}), \
         patch.object(workflow_engine.supabase_admin, "table") as mock_table, \
         patch.object(workflow_engine, "log_event"):
        mock_table.return_value.insert.side_effect = fake_insert
        result = run(workflow_engine.execute_workflow(workflow, {"title": "t"}, record_skipped=False))

    assert inserted["status"] == "partial_failure"
    assert "authorization expired" in inserted["error_message"].lower()
    assert result["status"] == "partial_failure"


def test_execute_workflow_records_success_and_retires_run_once():
    workflow = {
        "id": "wf-1", "organization_id": "org-A", "name": "Test WF",
        "trigger_type": "push", "conditions": {}, "actions": ["send_email"],
        "lifetime_mode": "run_once", "status": "active",
    }
    inserted = {}
    updated = {}

    def fake_insert(payload):
        inserted.update(payload)
        m = MagicMock()
        m.execute.return_value.data = [payload]
        return m

    def fake_update(payload):
        updated.update(payload)
        m = MagicMock()
        m.eq.return_value.execute.return_value = MagicMock()
        return m

    with patch.dict(workflow_engine.ACTION_REGISTRY, {"send_email": AsyncMock(return_value={"message_id": "m1"})}), \
         patch.object(workflow_engine.supabase_admin, "table") as mock_table, \
         patch.object(workflow_engine, "log_event"):
        mock_table.return_value.insert.side_effect = fake_insert
        mock_table.return_value.update.side_effect = fake_update
        result = run(workflow_engine.execute_workflow(workflow, {"title": "t"}, record_skipped=False))

    assert inserted["status"] == "success"
    assert result["status"] == "success"
    assert updated.get("status") == "completed"
