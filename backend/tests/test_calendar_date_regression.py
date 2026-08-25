"""
Regression test: calendar/events and calendar/summary must query from the
current moment, not a hardcoded past date. Guards against the date silently
going stale again.
"""
import re
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock


def _override_org(app, org_id="org-1"):
    from auth.dependencies import get_current_org_id
    app.dependency_overrides[get_current_org_id] = lambda: org_id


def _clear(app):
    app.dependency_overrides.clear()


def test_calendar_events_uses_current_utc_time_not_hardcoded_date():
    from main import app
    from fastapi.testclient import TestClient

    _override_org(app, org_id="org-1")
    try:
        with patch("closeout._resolve_access_token", return_value="tok"), \
             patch("main.httpx.AsyncClient") as mock_client_cls:

            mock_http_client = AsyncMock()
            mock_http_client.__aenter__.return_value = mock_http_client
            events_response = MagicMock()
            events_response.json.return_value = {"items": []}
            mock_http_client.get.return_value = events_response
            mock_client_cls.return_value = mock_http_client

            client = TestClient(app)
            res = client.get("/calendar/events")
            assert res.status_code == 200

            called_params = mock_http_client.get.call_args.kwargs["params"]
            time_min = called_params["timeMin"]

            assert "2026-08-01" not in time_min
            assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", time_min)

            parsed = datetime.strptime(time_min, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            assert abs((now - parsed).total_seconds()) < 60
    finally:
        _clear(app)
