"""
Security tests for task approval/action routes: authentication required,
cross-organization IDOR blocked, client-supplied access_token no longer
accepted.
"""
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


def _override_auth(app, org_id="org-1", user_id="user-1"):
    from auth.dependencies import get_current_user, get_current_org_id
    app.dependency_overrides[get_current_user] = lambda: {"sub": user_id, "email": "test@example.com"}
    app.dependency_overrides[get_current_org_id] = lambda: org_id


def _clear(app):
    app.dependency_overrides.clear()


def test_approve_task_requires_auth():
    from main import app
    client = TestClient(app)
    res = client.post("/tasks/task-123/approve")
    assert res.status_code == 401


class _FakeSB:
    def __init__(self, select_data=None, update_data=None):
        self.select_data = select_data or []
        self.update_data = update_data or []
        self.op = None
        self.updates = []

    def table(self, name):
        self.op = None
        return self

    def select(self, *a, **k):
        self.op = "select"
        return self

    def update(self, payload, *a, **k):
        self.op = "update"
        self.updates.append(payload)
        return self

    def __getattr__(self, name):
        return lambda *a, **k: self

    def execute(self):
        import types
        data = self.update_data if self.op == "update" else self.select_data
        return types.SimpleNamespace(data=data, count=0)


def test_approve_task_blocks_cross_org_access():
    from main import app
    _override_auth(app, org_id="org-attacker")
    try:
        with patch("main.supabase_admin", _FakeSB(select_data=[], update_data=[])), patch("main.log_event") as log:
            res = TestClient(app).post("/tasks/task-123/approve")
            assert res.status_code == 404
            log.assert_not_called()
    finally:
        _clear(app)


def test_approve_task_succeeds_for_owning_org():
    from main import app
    _override_auth(app, org_id="org-victim")
    try:
        row = {"id": "task-123", "organization_id": "org-victim", "status": "approved", "title": "t"}
        with patch("main.supabase_admin", _FakeSB(select_data=[row], update_data=[row])), patch("main.log_event"):
            res = TestClient(app).post("/tasks/task-123/approve")
            assert res.status_code == 200
            assert res.json()["status"] == "approved"
    finally:
        _clear(app)


def test_approve_task_in_wrong_state_returns_409_and_does_not_log():
    from main import app
    _override_auth(app, org_id="org-victim")
    try:
        row = {"id": "task-123", "organization_id": "org-victim", "status": "email_sent", "title": "t"}
        with patch("main.supabase_admin", _FakeSB(select_data=[row], update_data=[])), patch("main.log_event") as log:
            res = TestClient(app).post("/tasks/task-123/approve")
            assert res.status_code == 409
            log.assert_not_called()
    finally:
        _clear(app)


def test_reject_task_in_wrong_state_returns_409():
    from main import app
    _override_auth(app, org_id="org-victim")
    try:
        row = {"id": "task-123", "organization_id": "org-victim", "status": "email_sent", "title": "t"}
        with patch("main.supabase_admin", _FakeSB(select_data=[row], update_data=[])), patch("main.log_event") as log:
            res = TestClient(app).post("/tasks/task-123/reject")
            assert res.status_code == 409
            log.assert_not_called()
    finally:
        _clear(app)


def test_reject_task_cross_org_returns_404():
    from main import app
    _override_auth(app, org_id="org-attacker")
    try:
        with patch("main.supabase_admin", _FakeSB(select_data=[], update_data=[])), patch("main.log_event"):
            assert TestClient(app).post("/tasks/task-123/reject").status_code == 404
    finally:
        _clear(app)


def test_send_email_double_request_does_not_send_twice():
    from main import app
    _override_auth(app, org_id="org-victim")
    try:
        row = {"id": "task-123", "organization_id": "org-victim", "status": "approved", "title": "t", "description": "d", "source_ref": None}
        client_mock = AsyncMock()
        client_mock.__aenter__.return_value = client_mock
        with patch("main.supabase_admin", _FakeSB(select_data=[row], update_data=[])), \
             patch("closeout._resolve_access_token", return_value="tok"), \
             patch("main.httpx.AsyncClient", return_value=client_mock):
            res = TestClient(app).post("/tasks/task-123/approve-and-send-email", params={"to_email": "a@b.com"})
        assert res.status_code == 409
        client_mock.post.assert_not_called()
    finally:
        _clear(app)


def test_create_issue_double_request_does_not_create_twice():
    from main import app
    _override_auth(app, org_id="org-victim")
    try:
        row = {"id": "task-123", "organization_id": "org-victim", "status": "approved", "title": "t", "description": "d", "source_ref": None}
        with patch("main.supabase_admin", _FakeSB(select_data=[row], update_data=[])), \
             patch("closeout._resolve_access_token", return_value="tok"), \
             patch("main.github_post", new_callable=AsyncMock) as gp:
            res = TestClient(app).post("/tasks/task-123/approve-and-create-issue", params={"repo_full_name": "x/y"})
        assert res.status_code == 409
        gp.assert_not_called()
    finally:
        _clear(app)


def test_create_event_double_request_does_not_create_twice():
    from main import app
    _override_auth(app, org_id="org-victim")
    try:
        row = {"id": "task-123", "organization_id": "org-victim", "status": "approved", "title": "t", "description": "d", "source_ref": None}
        client_mock = AsyncMock()
        client_mock.__aenter__.return_value = client_mock
        with patch("main.supabase_admin", _FakeSB(select_data=[row], update_data=[])), \
             patch("closeout._resolve_access_token", return_value="tok"), \
             patch("main.httpx.AsyncClient", return_value=client_mock):
            res = TestClient(app).post("/tasks/task-123/approve-and-create-event", params={"start_time": "2030-01-01T10:00:00Z", "end_time": "2030-01-01T11:00:00Z"})
        assert res.status_code == 409
        client_mock.post.assert_not_called()
    finally:
        _clear(app)


def test_failed_gmail_send_releases_task_back_to_approved():
    from main import app
    _override_auth(app, org_id="org-victim")
    try:
        row = {"id": "task-123", "organization_id": "org-victim", "status": "approved", "title": "t", "description": "d", "source_ref": None}
        fake = _FakeSB(select_data=[row], update_data=[row])
        client_mock = AsyncMock()
        client_mock.__aenter__.return_value = client_mock
        client_mock.post.return_value = MagicMock(status_code=500)
        with patch("main.supabase_admin", fake), patch("config.supabase_admin", fake), patch("audit_logs.service.supabase_admin", fake, create=True), \
             patch("closeout._resolve_access_token", return_value="tok"), \
             patch("config.reserve_gmail_send"), \
             patch("main.httpx.AsyncClient", return_value=client_mock):
            res = TestClient(app).post("/tasks/task-123/approve-and-send-email", params={"to_email": "a@b.com"})
        assert res.status_code == 400
        assert {"status": "approved"} in fake.updates
    finally:
        _clear(app)


def test_approve_and_create_issue_rejects_client_supplied_access_token():
    from main import app
    _override_auth(app, org_id="org-victim")
    try:
        task_row = {
            "id": "task-123", "organization_id": "org-victim",
            "status": "approved", "title": "t", "description": "d",
            "source_ref": None,
        }
        with patch("main.supabase_admin", _FakeSB(select_data=[task_row], update_data=[task_row])), \
             patch("closeout._resolve_access_token") as mock_resolve, \
             patch("main.github_post", new_callable=AsyncMock) as mock_github_post, \
             patch("main.log_event"):
            mock_resolve.return_value = "server-side-real-token"
            mock_github_post.return_value = MagicMock(
                status_code=201,
                json=lambda: {"number": 1, "html_url": "https://github.com/x/y/issues/1"},
            )
            res = TestClient(app).post(
                "/tasks/task-123/approve-and-create-issue",
                params={"repo_full_name": "x/y", "access_token": "attacker-supplied-token"},
            )
            assert res.status_code == 200
            mock_resolve.assert_called_once_with("org-victim", "github")
            called_token = mock_github_post.call_args.args[1]
            assert called_token == "server-side-real-token"
            assert called_token != "attacker-supplied-token"
    finally:
        _clear(app)


def test_create_issue_rejects_path_traversal_repo():
    from main import app
    _override_auth(app, org_id="org-victim")
    try:
        with patch("closeout._resolve_access_token", return_value="tok"), patch("main.github_post", new_callable=AsyncMock) as gp:
            for bad in ("../x", "a/..", "a/b/c", "a b/c"):
                res = TestClient(app).post("/github/create-issue", params={"repo_full_name": bad, "title": "t"})
                assert res.status_code == 422
            gp.assert_not_called()
    finally:
        _clear(app)


def test_create_from_priorities_is_post_only():
    from main import app
    _override_auth(app, org_id="org-victim")
    try:
        assert TestClient(app).get("/tasks/create-from-priorities").status_code in (404, 405)
    finally:
        _clear(app)


def test_pending_approval_requires_auth():
    from main import app
    client = TestClient(app)
    res = client.get("/tasks/pending-approval")
    assert res.status_code == 401


def test_get_tasks_requires_auth():
    from main import app
    client = TestClient(app)
    res = client.get("/tasks")
    assert res.status_code == 401


def test_phase4_removed_unauthenticated_routes():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    assert client.get("/tokens/00000000-0000-0000-0000-000000000000/valid").status_code in (404, 405)
    assert client.post("/missed-events/run-now").status_code in (404, 405)


def test_phase4_connect_repo_requires_auth():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    res = client.post("/github/connect-repo", params={"org_id": "x", "repo_full_name": "a/b"})
    assert res.status_code in (401, 403)


def _p4_as_org(org):
    from main import app
    from auth.dependencies import get_current_org_id
    app.dependency_overrides[get_current_org_id] = lambda: org
    return app


def test_phase4_commits_run_now_requires_auth():
    from fastapi.testclient import TestClient
    from main import app
    assert TestClient(app).post("/commits/run-now").status_code == 401


def test_phase4_commits_run_now_is_operator_only():
    from unittest.mock import patch, AsyncMock
    from fastapi.testclient import TestClient
    import scheduler
    from config import settings
    app = _p4_as_org("some-other-org")
    try:
        with patch.object(scheduler, "check_and_commit_job", new=AsyncMock()) as job:
            assert TestClient(app).post("/commits/run-now").status_code == 403
            job.assert_not_called()
        app = _p4_as_org(settings.TEST_ORG_ID)
        with patch.object(scheduler, "check_and_commit_job", new=AsyncMock()) as job:
            assert TestClient(app).post("/commits/run-now").status_code == 200
            job.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_phase4_nightly_commit_job_only_reads_operator_org_rows(monkeypatch):
    import asyncio
    import types
    import scheduler

    class Rec:
        def __init__(self):
            self.eqs = []

        def table(self, n):
            return self

        def select(self, *a, **k):
            return self

        def eq(self, k, v):
            self.eqs.append((k, v))
            return self

        def execute(self):
            return types.SimpleNamespace(data=[])

    async def no_commit():
        return False

    rec = Rec()
    monkeypatch.setattr(scheduler, "supabase_admin", rec)
    monkeypatch.setattr(scheduler, "has_committed_today", no_commit)
    asyncio.run(scheduler.check_and_commit_job())
    assert ("organization_id", scheduler.TEST_ORG_ID) in rec.eqs


def test_phase4_schedule_commit_rejects_unsafe_input():
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    app = _p4_as_org("org-a")
    try:
        client = TestClient(app)
        with patch("main.supabase_admin"):
            assert client.post("/commits/schedule", params={"target_date": "not-a-date", "folder_path": "logs"}).status_code == 422
            assert client.post("/commits/schedule", params={"target_date": "2030-01-01", "folder_path": "../.github/workflows"}).status_code == 422
            assert client.post("/commits/schedule", params={"target_date": "2030-01-01", "folder_path": "logs", "file_name": "../x"}).status_code == 422
            assert client.post("/commits/schedule", params={"target_date": "2030-01-01", "folder_path": "logs", "content": "x" * 20001}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_phase4_calendar_create_event_error_does_not_leak_provider_body():
    from unittest.mock import patch, AsyncMock, MagicMock
    from fastapi.testclient import TestClient
    app = _p4_as_org("org-a")
    try:
        client_mock = AsyncMock()
        client_mock.__aenter__.return_value = client_mock
        client_mock.post.return_value = MagicMock(status_code=400, json=lambda: {"error": "leaky-detail"})
        with patch("closeout._resolve_access_token", return_value="tok"), \
             patch("main.httpx.AsyncClient", return_value=client_mock):
            res = TestClient(app).post("/calendar/create-event", params={"summary": "s", "start_time": "2030-01-01T10:00:00Z", "end_time": "2030-01-01T11:00:00Z"})
        assert res.status_code == 400 and "leaky-detail" not in res.text
    finally:
        app.dependency_overrides.clear()


def test_closeout_errors_do_not_include_provider_body():
    import asyncio
    import pytest
    import closeout
    c = AsyncMock()
    c.__aenter__.return_value = c
    c.post.return_value = MagicMock(status_code=500, text="SECRET-PROVIDER-BODY")
    c.patch.return_value = MagicMock(status_code=500, text="SECRET-PROVIDER-BODY")
    c.delete.return_value = MagicMock(status_code=500, text="SECRET-PROVIDER-BODY")
    with patch("closeout.httpx.AsyncClient", return_value=c):
        for coro in (
            closeout._github_comment("t", "a/b", "1", "x"),
            closeout._github_close("t", "a/b", "1"),
            closeout._calendar_patch("t", "e", {}),
            closeout._calendar_delete("t", "e"),
        ):
            with pytest.raises(RuntimeError) as exc:
                asyncio.run(coro)
            assert "SECRET-PROVIDER-BODY" not in str(exc.value)


def test_github_webhook_rejects_oversized_body():
    from main import app
    res = TestClient(app).post("/webhooks/github", content=b"x" * 1_100_000, headers={"Content-Type": "application/json"})
    assert res.status_code == 413


def test_otp_rejected_when_consume_claim_is_lost():
    from datetime import datetime, timedelta, timezone
    from auth import service
    rec = {"id": "1", "attempts": 0, "otp_hash": service._hash_otp("123456"),
           "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()}
    with patch.object(service.repository, "get_latest_otp", return_value=rec), \
         patch.object(service.repository, "mark_otp_consumed", return_value=False):
        assert service._verify_otp("a@b.com", "123456", "signup") is False


def test_otp_valid_code_consumed_once():
    from datetime import datetime, timedelta, timezone
    from auth import service
    rec = {"id": "1", "attempts": 0, "otp_hash": service._hash_otp("123456"),
           "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()}
    with patch.object(service.repository, "get_latest_otp", return_value=rec), \
         patch.object(service.repository, "mark_otp_consumed", return_value=True) as m:
        assert service._verify_otp("a@b.com", "123456", "signup") is True
        m.assert_called_once_with("1")


def test_otp_wrong_code_increments_attempts_and_fails():
    from datetime import datetime, timedelta, timezone
    from auth import service
    rec = {"id": "1", "attempts": 2, "otp_hash": service._hash_otp("123456"),
           "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()}
    with patch.object(service.repository, "get_latest_otp", return_value=rec), \
         patch.object(service.repository, "increment_otp_attempts", return_value=True) as inc, \
         patch.object(service.repository, "mark_otp_consumed") as consume:
        assert service._verify_otp("a@b.com", "000000", "signup") is False
        inc.assert_called_once_with("1", 3)
        consume.assert_not_called()


def test_reserve_org_action_blocks_at_limit_and_allows_below():
    import types
    import pytest
    import config

    class Fake:
        def __init__(self, count):
            self.count = count

        def __getattr__(self, name):
            return lambda *a, **k: self

        def execute(self):
            return types.SimpleNamespace(count=self.count, data=[])

    with patch.object(config, "supabase_admin", Fake(5)):
        with pytest.raises(config.ActionRateLimited):
            config.reserve_org_action("org", "ai_call", 5)
    with patch.object(config, "supabase_admin", Fake(4)), patch("audit_logs.service.log_event") as log:
        config.reserve_org_action("org", "ai_call", 5)
        log.assert_called_once()


def test_gemini_endpoints_return_429_before_any_work_when_limited():
    import config
    from main import app
    _override_auth(app, org_id="org-a")
    try:
        with patch("config.reserve_org_action", side_effect=config.ActionRateLimited("x")), \
             patch("main.supabase_admin", _FakeSB(select_data=[], update_data=[])), \
             patch("closeout._resolve_access_token") as tok, \
             patch("main.run_gemini") as gem:
            c = TestClient(app)
            for path in ("/github/summary", "/planner/priorities", "/calendar/summary"):
                assert c.get(path).status_code == 429
            assert c.post("/tasks/create-from-priorities").status_code in (429,)
            tok.assert_not_called()
            gem.assert_not_called()
    finally:
        _clear(app)


def test_discord_and_calendar_create_return_429_before_external_call():
    import config
    from main import app
    _override_auth(app, org_id="org-a")
    try:
        with patch("config.reserve_org_action", side_effect=config.ActionRateLimited("x")), \
             patch("main._post_discord", new_callable=AsyncMock) as pd, \
             patch("closeout._resolve_access_token") as tok:
            c = TestClient(app)
            assert c.post("/discord/notify", params={"message": "hi"}).status_code == 429
            assert c.post("/discord/daily-report").status_code == 429
            assert c.post("/calendar/create-event", params={"summary": "s", "start_time": "2030-01-01T10:00:00Z", "end_time": "2030-01-01T11:00:00Z"}).status_code == 429
            pd.assert_not_called()
            tok.assert_not_called()
    finally:
        _clear(app)


def test_calendar_create_event_rejects_invalid_times():
    from main import app
    _override_auth(app, org_id="org-a")
    try:
        r = TestClient(app).post("/calendar/create-event", params={"summary": "s", "start_time": "garbage", "end_time": "2030-01-01T11:00:00Z"})
        assert r.status_code == 422
    finally:
        _clear(app)
