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


class _P4Query:
    def __init__(self, data):
        self._data = data

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def execute(self):
        import types
        return types.SimpleNamespace(data=self._data)


class _P4DB:
    def __init__(self, data):
        self._data = data

    def table(self, name):
        return _P4Query(self._data)


def _p4_setup(monkeypatch, module, org_rows):
    import httpx
    import types
    posts = []

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **kw):
            posts.append(url)
            return types.SimpleNamespace(status_code=204, text="")

    from config import settings
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(module, "supabase_admin", _P4DB(org_rows))
    monkeypatch.setattr(settings, "TEST_ORG_ID", "operator-org")
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/9/global")
    return posts


def test_phase4_discord_workflow_uses_own_webhook(monkeypatch):
    import asyncio
    import workflow_engine
    posts = _p4_setup(monkeypatch, workflow_engine, [{"discord_webhook_url": "https://discord.com/api/webhooks/1/own"}])
    asyncio.run(workflow_engine._action_notify_discord("org-a", {"title": "t"}))
    assert posts == ["https://discord.com/api/webhooks/1/own"]


def test_phase4_discord_workflow_never_uses_global_for_other_org(monkeypatch):
    import asyncio
    import pytest
    import workflow_engine
    posts = _p4_setup(monkeypatch, workflow_engine, [{"discord_webhook_url": None}])
    with pytest.raises(RuntimeError):
        asyncio.run(workflow_engine._action_notify_discord("org-a", {"title": "t"}))
    assert posts == []


def test_phase4_discord_workflow_operator_org_uses_global(monkeypatch):
    import asyncio
    import workflow_engine
    posts = _p4_setup(monkeypatch, workflow_engine, [{"discord_webhook_url": None}])
    asyncio.run(workflow_engine._action_notify_discord("operator-org", {"title": "t"}))
    assert posts == ["https://discord.com/api/webhooks/9/global"]


def test_phase4_discord_rejects_non_discord_webhook_url(monkeypatch):
    import asyncio
    import pytest
    import workflow_engine
    posts = _p4_setup(monkeypatch, workflow_engine, [{"discord_webhook_url": "https://evil.example.com/api/webhooks/1/x"}])
    with pytest.raises(RuntimeError):
        asyncio.run(workflow_engine._action_notify_discord("org-a", {"title": "t"}))
    assert posts == []


def test_phase4_orchestrator_does_not_post_to_global_for_other_org(monkeypatch):
    import asyncio
    import orchestrator
    posts = _p4_setup(monkeypatch, orchestrator, [{"discord_webhook_url": None}])
    state = {"org_id": "org-a", "tasks": [], "report": ""}
    result = asyncio.run(orchestrator.node_notify_discord(state))
    assert posts == []
    assert result["report"]


class _P4Chain:
    def __init__(self, data=None, count=0):
        self._data = data if data is not None else []
        self._count = count

    def table(self, name):
        return self

    def __getattr__(self, name):
        return lambda *a, **k: self

    def execute(self):
        import types
        return types.SimpleNamespace(data=self._data, count=self._count)


class _P4Rec:
    def __init__(self):
        self._last = {}

    def table(self, name):
        return self

    def insert(self, row):
        self._last = row
        return self

    def __getattr__(self, name):
        return lambda *a, **k: self

    def execute(self):
        import types
        return types.SimpleNamespace(data=[self._last], count=0)


def test_phase4_gmail_budget_blocks_at_limit(monkeypatch):
    import pytest
    import config
    import audit_logs.service as audit
    logged = []
    monkeypatch.setattr(config, "supabase_admin", _P4Chain(count=30))
    monkeypatch.setattr(config.settings, "GMAIL_SEND_MAX_PER_HOUR", 30)
    monkeypatch.setattr(audit, "log_event", lambda **k: logged.append(k))
    with pytest.raises(config.GmailSendLimitExceeded):
        config.reserve_gmail_send("org-a", "workflow")
    assert logged == []


def test_phase4_gmail_budget_records_attempt_under_limit(monkeypatch):
    import config
    import audit_logs.service as audit
    logged = []
    monkeypatch.setattr(config, "supabase_admin", _P4Chain(count=3))
    monkeypatch.setattr(config.settings, "GMAIL_SEND_MAX_PER_HOUR", 30)
    monkeypatch.setattr(audit, "log_event", lambda **k: logged.append(k))
    config.reserve_gmail_send("org-a", "workflow")
    assert len(logged) == 1 and logged[0]["action"] == "email_send_attempt"


def test_phase4_workflow_send_email_stops_at_limit(monkeypatch):
    import asyncio
    import pytest
    import workflow_engine
    from config import GmailSendLimitExceeded
    posts = _p4_setup(monkeypatch, workflow_engine, [])
    monkeypatch.setattr(workflow_engine, "_get_org_token", lambda o, p: ("tok", None))
    monkeypatch.setattr(workflow_engine, "_get_org_email", lambda o: "a@example.com")

    def blocked(o, s):
        raise GmailSendLimitExceeded("limit")

    monkeypatch.setattr(workflow_engine, "reserve_gmail_send", blocked)
    with pytest.raises(GmailSendLimitExceeded):
        asyncio.run(workflow_engine._action_send_email("org-a", {"title": "t"}))
    assert posts == []


def test_phase4_workflow_send_email_error_hides_provider_text(monkeypatch):
    import asyncio
    import types
    import httpx
    import pytest
    import workflow_engine

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **kw):
            return types.SimpleNamespace(status_code=500, text="leaky-provider-detail")

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(workflow_engine, "_get_org_token", lambda o, p: ("tok", None))
    monkeypatch.setattr(workflow_engine, "_get_org_email", lambda o: "a@example.com")
    monkeypatch.setattr(workflow_engine, "reserve_gmail_send", lambda o, s: None)
    with pytest.raises(RuntimeError) as exc:
        asyncio.run(workflow_engine._action_send_email("org-a", {"title": "t"}))
    assert "leaky-provider-detail" not in str(exc.value)


def test_phase4_workflow_run_cap_raises(monkeypatch):
    import asyncio
    import pytest
    import workflow_engine
    monkeypatch.setattr(workflow_engine, "_org_run_budget_exceeded", lambda o: True)
    wf = {"id": "w1", "organization_id": "org-a", "name": "n", "conditions": {}, "actions": ["save_audit_log"], "trigger_type": "push"}
    with pytest.raises(workflow_engine.WorkflowRateLimited):
        asyncio.run(workflow_engine.execute_workflow(wf, {}, record_skipped=False))


def test_phase4_workflow_action_timeout_is_bounded_and_scrubbed(monkeypatch):
    import asyncio
    import workflow_engine

    async def slow(o, c):
        await asyncio.sleep(2)

    rec = _P4Rec()
    monkeypatch.setitem(workflow_engine.ACTION_REGISTRY, "slow", slow)
    monkeypatch.setattr(workflow_engine, "supabase_admin", rec)
    monkeypatch.setattr(workflow_engine, "log_event", lambda **k: None)
    monkeypatch.setattr(workflow_engine, "_org_run_budget_exceeded", lambda o: False)
    monkeypatch.setattr(workflow_engine.settings, "WORKFLOW_ACTION_TIMEOUT_SECONDS", 0.05)
    wf = {"id": "w1", "organization_id": "org-a", "name": "n", "conditions": {}, "actions": ["slow"], "trigger_type": "push"}
    run = asyncio.run(workflow_engine.execute_workflow(wf, {}, record_skipped=False))
    assert run["status"] == "partial_failure" and run["error_message"] == "Action timed out"


def test_phase4_run_now_returns_429_when_rate_limited():
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from main import app
    from auth.dependencies import get_current_org_id
    import workflow_routes
    from workflow_engine import WorkflowRateLimited

    async def limited(*a, **k):
        raise WorkflowRateLimited("x")

    row = {"id": "w", "organization_id": "org-a", "status": "active", "trigger_type": "push"}
    app.dependency_overrides[get_current_org_id] = lambda: "org-a"
    try:
        with patch.object(workflow_routes, "supabase_admin", _P4Chain(data=[row])), \
             patch.object(workflow_routes, "execute_workflow", limited):
            res = TestClient(app).post("/workflows/w/run-now")
        assert res.status_code == 429
    finally:
        app.dependency_overrides.clear()


def test_phase4_email_job_stops_at_send_limit(monkeypatch):
    import asyncio
    import httpx
    import email_scheduler.service as es
    from config import GmailSendLimitExceeded
    posts = []

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def post(self, *a, **k):
            posts.append(1)

    def blocked(o, s):
        raise GmailSendLimitExceeded("limit")

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(es, "reserve_gmail_send", blocked)
    monkeypatch.setattr(es.repository, "has_run_for_date", lambda j, d: False)
    monkeypatch.setattr(es.repository, "create_run", lambda r: r)
    job = {"id": "j", "organization_id": "org-a", "to_email": "a@example.com", "subject": "s", "body": "b"}
    run = asyncio.run(es.execute_job(job))
    assert run["status"] == "failed" and posts == []


import pytest as _p4pytest


@_p4pytest.fixture(autouse=True)
def _p4_stub_gmail_budget(monkeypatch):
    import workflow_engine
    monkeypatch.setattr(workflow_engine, "reserve_gmail_send", lambda o, s: None)


def _p4_wf(**over):
    from workflow_schemas import WorkflowCreate
    base = {"organization_id": "x", "name": "n", "trigger_type": "push", "actions": ["save_audit_log"]}
    base.update(over)
    return WorkflowCreate(**base)


def test_phase4_workflow_schema_accepts_valid_definition():
    wf = _p4_wf(conditions={"logic": "AND", "rules": [{"field": "repo", "op": "eq", "value": "a/b"}]})
    assert wf.name == "n"


def test_phase4_workflow_schema_rejects_oversized_input():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        _p4_wf(name="x" * 201)
    with pytest.raises(ValidationError):
        _p4_wf(name="   ")
    with pytest.raises(ValidationError):
        _p4_wf(actions=["save_audit_log"] * 11)
    with pytest.raises(ValidationError):
        _p4_wf(conditions={"blob": "x" * 20000})
    with pytest.raises(ValidationError):
        _p4_wf(conditions={"logic": "AND", "rules": [{"field": "a", "op": "eq", "value": 1}] * 21})


def test_phase4_workflow_update_schema_rejects_oversized_input():
    import pytest
    from pydantic import ValidationError
    from workflow_schemas import WorkflowUpdate
    with pytest.raises(ValidationError):
        WorkflowUpdate(name="x" * 201)
    with pytest.raises(ValidationError):
        WorkflowUpdate(actions=["save_audit_log"] * 11)
    with pytest.raises(ValidationError):
        WorkflowUpdate(conditions={"blob": "x" * 20000})
    assert WorkflowUpdate(name="ok").name == "ok"


def test_phase4_integrations_response_strips_credential_fields():
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    import main
    from auth.dependencies import get_current_org_id
    row = {"id": "i1", "provider": "gmail", "connected": True, "access_token": "SECRET-A", "refresh_token": "SECRET-R", "webhook_secret": "SECRET-W"}
    main.app.dependency_overrides[get_current_org_id] = lambda: "org-a"
    try:
        with patch.object(main, "supabase_admin", _P4Chain(data=[row])):
            res = TestClient(main.app).get("/integrations")
        assert res.status_code == 200
        assert "SECRET" not in res.text
        assert res.json()[0]["provider"] == "gmail"
    finally:
        main.app.dependency_overrides.clear()
