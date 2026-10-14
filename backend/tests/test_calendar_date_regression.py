"""Regression coverage for Calendar OAuth and organization-scoped API calls."""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import calendar_routes
from main import app

ROOT = Path(__file__).resolve().parents[2]


def test_calendar_oauth_requests_only_calendar_scope(monkeypatch):
    monkeypatch.setattr(calendar_routes, "_issue_oauth_state", lambda org, provider: "state-token")
    monkeypatch.setattr(calendar_routes.settings, "GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(calendar_routes.settings, "GOOGLE_CALENDAR_REDIRECT_URI", "https://api.example/calendar/callback")
    response = calendar_routes.calendar_login("org-1")
    query = parse_qs(urlparse(response["url"]).query)
    assert query["scope"] == ["https://www.googleapis.com/auth/calendar"]
    assert query["state"] == ["state-token"]
    assert query["redirect_uri"] == ["https://api.example/calendar/callback"]


def test_calendar_routes_and_approved_task_event_route_are_registered():
    paths = app.openapi()["paths"]
    assert {"get"} <= paths["/calendar/login"].keys()
    assert {"get"} <= paths["/calendar/callback"].keys()
    assert {"get"} <= paths["/calendar/events"].keys()
    assert "/calendar/summary" not in paths
    assert {"post"} <= paths["/calendar/create-event"].keys()
    assert {"post"} <= paths["/tasks/{task_id}/approve-and-create-event"].keys()


def test_calendar_page_exposes_production_badge_and_primary_controls():
    page = (ROOT / "ai-coo-frontend/src/pages/calendar/Calendar.tsx").read_text()
    integration_cards = (ROOT / "ai-coo-frontend/src/pages/integrations/Integrations.tsx").read_text()
    assert "Production" in page and "Production" in integration_cards
    assert "Connect Calendar" in page
    assert "Refresh events" in page
    assert "Upcoming events" in page
    assert "Load AI summary" not in page
    assert "New event" in page and "Create event" in page


def test_calendar_events_use_current_utc_time_and_format_results(monkeypatch):
    response = MagicMock(status_code=200)
    response.json.return_value = {"items": [{
        "summary": "Planning", "start": {"dateTime": "2030-01-02T10:00:00Z"},
        "end": {"dateTime": "2030-01-02T10:30:00Z"},
    }]}
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.get.return_value = response
    monkeypatch.setattr(calendar_routes, "_get_calendar_token_for_org", lambda org: "calendar-token")
    monkeypatch.setattr(calendar_routes.httpx, "AsyncClient", lambda **kwargs: client)

    result = asyncio.run(calendar_routes.calendar_events("org-1"))

    params = client.get.call_args.kwargs["params"]
    assert abs((datetime.now(timezone.utc) - datetime.strptime(params["timeMin"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)).total_seconds()) < 60
    assert params["maxResults"] == 10
    assert result == {"event_count": 1, "events": [{"summary": "Planning", "start": "2030-01-02T10:00:00Z", "end": "2030-01-02T10:30:00Z"}]}


def test_calendar_create_event_posts_to_google_calendar(monkeypatch):
    response = MagicMock(status_code=200)
    response.json.return_value = {"htmlLink": "https://calendar.example/event"}
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.post.return_value = response
    monkeypatch.setattr(calendar_routes, "_get_calendar_token_for_org", lambda org: "calendar-token")
    monkeypatch.setattr(calendar_routes, "_rate_limit", lambda *args: None)
    monkeypatch.setattr(calendar_routes.httpx, "AsyncClient", lambda **kwargs: client)

    result = asyncio.run(calendar_routes.calendar_create_event(
        "Planning", "2030-01-02T10:00:00Z", "2030-01-02T10:30:00Z", "org-1"
    ))

    assert result == {"status": "created", "event_link": "https://calendar.example/event"}
    assert client.post.call_args.kwargs["json"]["summary"] == "Planning"


def test_retired_calendar_summary_cannot_read_events_or_call_ai(monkeypatch):
    from fastapi.testclient import TestClient
    import config

    ai = MagicMock(side_effect=AssertionError("Calendar must not call AI"))
    events = AsyncMock(side_effect=AssertionError("Retired endpoint must not fetch events"))
    monkeypatch.setattr(config, "run_gemini", ai)
    monkeypatch.setattr(config.gemini_client.models, "generate_content", ai)
    monkeypatch.setattr(calendar_routes, "calendar_events", events)
    client = TestClient(app)
    for method in (client.get, client.post):
        assert method("/calendar/summary").status_code == 404
    ai.assert_not_called()
    events.assert_not_called()


def test_calendar_oauth_callback_stores_encrypted_tokens(monkeypatch):
    import calendar_routes as routes

    monkeypatch.setattr(routes, "_consume_oauth_state", lambda state, provider: "org-1")
    monkeypatch.setattr(routes, "encrypt_token", lambda token: f"encrypted:{token}" if token else None)
    integration_table = MagicMock()
    integration_table.insert.return_value.execute.return_value.data = [{"id": "calendar-int"}]
    token_table = MagicMock()
    token_table.insert.return_value.execute.return_value.data = []
    table_calls = {"integrations": integration_table, "oauth_tokens": token_table}
    monkeypatch.setattr(routes.supabase_admin, "table", lambda name: table_calls[name])

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, url, data):
            response = MagicMock()
            response.json.return_value = {"access_token": "access", "refresh_token": "refresh", "expires_in": 3600}
            return response

    monkeypatch.setattr(routes.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(routes.calendar_callback("code", "state"))

    assert result == {"status": "connected", "integration_id": "calendar-int"}
    token_row = token_table.insert.call_args.args[0]
    assert token_row["access_token"] == "encrypted:access"
    assert token_row["refresh_token"] == "encrypted:refresh"
