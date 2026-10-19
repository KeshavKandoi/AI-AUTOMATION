"""Google OAuth returns browser users to the app without leaking tokens."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

import calendar_routes
import main
import oauth_redirect


def _mock_google_callback(monkeypatch, module, provider):
    monkeypatch.setattr(module, "_consume_oauth_state", lambda state, name: "org-1")
    monkeypatch.setattr(module, "encrypt_token", lambda value: f"encrypted:{value}" if value else None)

    integration_table = MagicMock()
    integration_table.insert.return_value.execute.return_value.data = [{"id": "integration-1"}]
    token_table = MagicMock()
    monkeypatch.setattr(
        module.supabase_admin, "table",
        lambda name: {"integrations": integration_table, "oauth_tokens": token_table}[name],
    )

    google_client = AsyncMock()
    google_client.__aenter__.return_value = google_client
    google_response = MagicMock()
    google_response.json.return_value = {
        "access_token": "secret-access",
        "refresh_token": "secret-refresh",
        "expires_in": 3600,
    }
    google_client.post.return_value = google_response
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: google_client)
    return token_table


def test_google_callbacks_redirect_browser_to_integrations(monkeypatch):
    monkeypatch.setattr(oauth_redirect.settings, "FRONTEND_URL", "https://workforge.tech")
    monkeypatch.setattr(oauth_redirect.settings, "ALLOWED_ORIGINS", "https://workforge.tech")
    client = TestClient(main.app)

    for provider, module in (("gmail", main), ("calendar", calendar_routes)):
        token_table = _mock_google_callback(monkeypatch, module, provider)
        response = client.get(
            f"/{provider}/callback",
            params={"code": "google-code", "state": "valid-state"},
            headers={"Accept": "text/html"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"https://workforge.tech/integrations?integration={provider}&status=connected"
        assert "secret-access" not in response.text + response.headers["location"]
        assert token_table.insert.call_args.args[0]["access_token"] == "encrypted:secret-access"


def test_google_callbacks_redirect_cancelled_browser_without_token_exchange(monkeypatch):
    monkeypatch.setattr(oauth_redirect.settings, "FRONTEND_URL", "https://workforge.tech")
    monkeypatch.setattr(oauth_redirect.settings, "ALLOWED_ORIGINS", "https://workforge.tech")
    client = TestClient(main.app)

    for provider, module in (("gmail", main), ("calendar", calendar_routes)):
        monkeypatch.setattr(module, "_consume_oauth_state", lambda state, name: "org-1")
        google_client = AsyncMock(side_effect=AssertionError("Google token exchange must not run"))
        monkeypatch.setattr(module.httpx, "AsyncClient", google_client)
        response = client.get(
            f"/{provider}/callback",
            params={"error": "access_denied", "state": "valid-state"},
            headers={"Accept": "text/html"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"https://workforge.tech/integrations?integration={provider}&status=cancelled"
        google_client.assert_not_called()
