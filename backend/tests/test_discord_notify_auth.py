"""
Security test: /discord/notify must require authentication and a valid
organization before posting to the (global) Discord webhook.
"""
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


def _client():
    from main import app
    return TestClient(app)


def test_discord_notify_rejects_unauthenticated_request():
    client = _client()
    res = client.post("/discord/notify", params={"message": "hello"})
    assert res.status_code == 401


def test_discord_notify_allows_authenticated_user_with_org():
    from main import app
    from auth.dependencies import get_current_user, get_current_org_id

    app.dependency_overrides[get_current_user] = lambda: {"sub": "user-1", "email": "test@example.com"}
    app.dependency_overrides[get_current_org_id] = lambda: "org-1"

    try:
        mock_response = MagicMock(status_code=204, text="")
        with patch("main.httpx.AsyncClient") as mock_client_cls, \
             patch("main.log_event") as mock_log_event, \
             patch("main._org_discord_webhook", return_value="https://discord.com/api/webhooks/1/x"):
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            client = TestClient(app)
            res = client.post("/discord/notify", params={"message": "hello"})

            assert res.status_code == 200
            assert res.json()["status"] == "sent"
            mock_log_event.assert_called_once()
            assert mock_log_event.call_args.kwargs["organization_id"] == "org-1"
    finally:
        app.dependency_overrides.clear()


def test_discord_notify_no_org_returns_404():
    from main import app
    from auth.dependencies import get_current_user, get_current_org_id
    from fastapi import HTTPException

    app.dependency_overrides[get_current_user] = lambda: {"sub": "user-1", "email": "test@example.com"}

    def _raise_no_org():
        raise HTTPException(status_code=404, detail="No organization found for this user")
    app.dependency_overrides[get_current_org_id] = _raise_no_org

    try:
        client = TestClient(app)
        res = client.post("/discord/notify", params={"message": "hello"})
        assert res.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_phase4_discord_daily_report_rejects_unauthenticated_request():
    client = _client()
    res = client.post("/discord/daily-report", params={"org_id": "org-1"})
    assert res.status_code == 401


def _phase4_no_webhook_post(path, params):
    from main import app
    from auth.dependencies import get_current_user, get_current_org_id

    app.dependency_overrides[get_current_user] = lambda: {"sub": "user-1", "email": "t@example.com"}
    app.dependency_overrides[get_current_org_id] = lambda: "org-a"
    try:
        with patch("main.supabase_admin") as sb, patch("main.httpx.AsyncClient") as mock_client_cls:
            sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"discord_webhook_url": None}])
            res = TestClient(app).post(path, params=params)
            return res, mock_client_cls
    finally:
        app.dependency_overrides.clear()


def test_phase4_discord_notify_never_posts_to_global_for_other_org():
    res, client_cls = _phase4_no_webhook_post("/discord/notify", {"message": "hello"})
    assert res.status_code == 400
    client_cls.assert_not_called()


def test_phase4_discord_daily_report_never_posts_to_global_for_other_org():
    res, client_cls = _phase4_no_webhook_post("/discord/daily-report", {})
    assert res.status_code == 400
    client_cls.assert_not_called()


def test_phase4_discord_notify_rejects_oversized_message():
    from main import app
    from auth.dependencies import get_current_user, get_current_org_id

    app.dependency_overrides[get_current_user] = lambda: {"sub": "user-1", "email": "t@example.com"}
    app.dependency_overrides[get_current_org_id] = lambda: "org-a"
    try:
        res = TestClient(app).post("/discord/notify", params={"message": "x" * 2000})
        assert res.status_code == 422
    finally:
        app.dependency_overrides.clear()
