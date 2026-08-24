"""
Security tests for OAuth state CSRF protection: state must be required,
single-use, provider-specific, short-lived, and never derived from
client-supplied org_id. Also verifies OAuth callback responses never
leak provider access/refresh tokens to the frontend.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


def _override_org(app, org_id="org-1"):
    from auth.dependencies import get_current_org_id
    app.dependency_overrides[get_current_org_id] = lambda: org_id


def _clear(app):
    app.dependency_overrides.clear()


def _mock_state_row(state="valid-state", org_id="org-victim", provider="github",
                     consumed_at=None, expired=False):
    expires_at = datetime.now(timezone.utc) + (timedelta(minutes=-5) if expired else timedelta(minutes=10))
    return {
        "id": "state-row-1",
        "state": state,
        "organization_id": org_id,
        "provider": provider,
        "consumed_at": consumed_at,
        "expires_at": expires_at.isoformat(),
    }


# ---------------- login endpoints require auth ----------------

def test_github_login_requires_auth():
    from main import app
    client = TestClient(app)
    res = client.get("/github/login", follow_redirects=False)
    assert res.status_code == 401


def test_gmail_login_requires_auth():
    from main import app
    client = TestClient(app)
    res = client.get("/gmail/login", follow_redirects=False)
    assert res.status_code == 401


def test_calendar_login_requires_auth():
    from main import app
    client = TestClient(app)
    res = client.get("/calendar/login", follow_redirects=False)
    assert res.status_code == 401


# ---------------- login issues a real state, not org_id ----------------

def test_github_login_issues_random_state_not_org_id():
    from main import app
    _override_org(app, org_id="org-victim")
    try:
        with patch("main.supabase_admin") as sb:
            insert_result = MagicMock()
            sb.table.return_value.insert.return_value.execute.return_value = insert_result

            client = TestClient(app)
            res = client.get("/github/login", follow_redirects=False)

            assert res.status_code == 200
            body = res.json()
            assert "state=org-victim" not in body["url"]
            assert "state=" in body["url"]

            insert_call = sb.table.return_value.insert.call_args.args[0]
            assert insert_call["organization_id"] == "org-victim"
            assert insert_call["provider"] == "github"
            assert len(insert_call["state"]) > 20
    finally:
        _clear(app)


# ---------------- callback: missing/invalid state ----------------

def test_github_callback_rejects_unknown_state():
    from main import app
    with patch("main.supabase_admin") as sb:
        empty_result = MagicMock()
        empty_result.data = []
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = empty_result

        client = TestClient(app)
        res = client.get("/github/callback", params={"code": "abc", "state": "made-up-state"})
        assert res.status_code == 400


# ---------------- callback: expired state ----------------

def test_github_callback_rejects_expired_state():
    from main import app
    with patch("main.supabase_admin") as sb:
        row = _mock_state_row(provider="github", expired=True)
        select_result = MagicMock(data=[row])
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = select_result

        client = TestClient(app)
        res = client.get("/github/callback", params={"code": "abc", "state": "valid-state"})
        assert res.status_code == 400


# ---------------- callback: wrong provider (state issued for gmail, used on github) ----------------

def test_github_callback_rejects_state_issued_for_different_provider():
    from main import app
    with patch("main.supabase_admin") as sb:
        row = _mock_state_row(provider="gmail")
        select_result = MagicMock(data=[row])
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = select_result

        client = TestClient(app)
        res = client.get("/github/callback", params={"code": "abc", "state": "valid-state"})
        assert res.status_code == 400


# ---------------- callback: already-consumed state (replay) ----------------

def test_github_callback_rejects_replayed_state():
    from main import app
    with patch("main.supabase_admin") as sb:
        row = _mock_state_row(provider="github", consumed_at=datetime.now(timezone.utc).isoformat())
        select_result = MagicMock(data=[row])
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = select_result

        client = TestClient(app)
        res = client.get("/github/callback", params={"code": "abc", "state": "valid-state"})
        assert res.status_code == 400


# ---------------- callback: race-condition replay (consumed_at was null at SELECT time,
# but the atomic claim UPDATE returns no rows because another request already claimed it) ----------------

def test_github_callback_rejects_concurrent_replay_race():
    from main import app
    with patch("main.supabase_admin") as sb:
        row = _mock_state_row(provider="github", consumed_at=None)
        select_result = MagicMock(data=[row])

        claim_result = MagicMock()
        claim_result.data = []  # simulates another concurrent request already claimed it

        table_mock = sb.table.return_value
        table_mock.select.return_value.eq.return_value.execute.return_value = select_result
        table_mock.update.return_value.eq.return_value.is_.return_value.execute.return_value = claim_result

        client = TestClient(app)
        res = client.get("/github/callback", params={"code": "abc", "state": "valid-state"})
        assert res.status_code == 400


# ---------------- callback: valid state resolves org_id from the STATE ROW, not client input ----------------

def test_github_callback_uses_org_id_from_state_not_query_param():
    """Even though nothing in this callback's URL carries an org_id anymore,
    this test guards against a future regression where someone re-adds an
    org_id query param to the callback and wires it in by mistake."""
    from main import app
    with patch("main.supabase_admin") as sb, \
         patch("main.httpx.AsyncClient") as mock_client_cls, \
         patch("main.register_github_webhook"):
        row = _mock_state_row(provider="github", org_id="org-from-state-row", consumed_at=None)
        select_result = MagicMock(data=[row])
        claim_result = MagicMock(data=[{**row, "consumed_at": "now"}])

        table_mock = sb.table.return_value
        table_mock.select.return_value.eq.return_value.execute.return_value = select_result
        table_mock.update.return_value.eq.return_value.is_.return_value.execute.return_value = claim_result

        insert_result = MagicMock()
        insert_result.data = [{"id": "integration-1"}]
        table_mock.insert.return_value.execute.return_value = insert_result

        mock_http_client = AsyncMock()
        mock_http_client.__aenter__.return_value = mock_http_client
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "gh-token-xyz"}
        mock_http_client.post.return_value = token_response
        mock_client_cls.return_value = mock_http_client

        client = TestClient(app)
        res = client.get("/github/callback", params={"code": "abc", "state": "valid-state"})

        assert res.status_code == 200
        insert_calls = [c.args[0] for c in table_mock.insert.call_args_list]
        integrations_insert = next(c for c in insert_calls if "provider" in c)
        assert integrations_insert["organization_id"] == "org-from-state-row"


# ---------------- OAuth callback responses must never leak tokens ----------------

def test_github_callback_response_never_contains_access_token():
    from main import app
    with patch("main.supabase_admin") as sb, \
         patch("main.httpx.AsyncClient") as mock_client_cls, \
         patch("main.register_github_webhook"):
        row = _mock_state_row(provider="github", org_id="org-1", consumed_at=None)
        select_result = MagicMock(data=[row])
        claim_result = MagicMock(data=[{**row, "consumed_at": "now"}])

        table_mock = sb.table.return_value
        table_mock.select.return_value.eq.return_value.execute.return_value = select_result
        table_mock.update.return_value.eq.return_value.is_.return_value.execute.return_value = claim_result

        insert_result = MagicMock()
        insert_result.data = [{"id": "integration-1"}]
        table_mock.insert.return_value.execute.return_value = insert_result

        mock_http_client = AsyncMock()
        mock_http_client.__aenter__.return_value = mock_http_client
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "super-secret-real-token"}
        mock_http_client.post.return_value = token_response
        mock_client_cls.return_value = mock_http_client

        client = TestClient(app)
        res = client.get("/github/callback", params={"code": "abc", "state": "valid-state"})

        assert res.status_code == 200
        body = res.json()
        assert "access_token" not in body
        assert "super-secret-real-token" not in res.text
