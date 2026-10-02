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


import types as _p4types
from datetime import datetime as _p4dt, timezone as _p4tz


def _p4_extracted():
    return _p4types.SimpleNamespace(
        start_time=_p4dt(2030, 1, 1, 10, 0, tzinfo=_p4tz.utc), end_time=None,
        meeting_link=None, source="llm", confidence=90.0, interviewer=None,
    )


def _p4_cal(monkeypatch, status=200, raises=False, existing_start="2030-01-01T10:00:00+00:00"):
    import httpx
    from job_hunter import calendar_integration as ci
    calls = []
    rows = []

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def _go(self, verb):
            calls.append(verb)
            if raises:
                raise httpx.ConnectError("down")
            return _p4types.SimpleNamespace(status_code=status, text="", json=lambda: {})

        async def patch(self, url, **kw):
            return await self._go("patch")

        async def delete(self, url, **kw):
            return await self._go("delete")

        async def post(self, url, **kw):
            return await self._go("post")

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(ci.repository, "get_active_calendar_event_for_application",
                        lambda o, a: {"id": "row1", "google_calendar_event_id": "evt1", "extracted_start_time": existing_start})
    monkeypatch.setattr(ci.repository, "update_calendar_event_row", lambda rid, f: rows.append(f) or {"id": rid, **f})
    monkeypatch.setattr(ci, "_get_calendar_token_for_org", lambda o: "tok")
    monkeypatch.setattr(ci, "log_event", lambda **k: None)
    monkeypatch.setattr(ci, "notify", lambda **k: None)
    return ci, calls, rows


def test_phase4_calendar_update_success(monkeypatch):
    import asyncio
    ci, calls, rows = _p4_cal(monkeypatch, status=200)
    out = asyncio.run(ci.update_interview_event("o", "a", "m", None, _p4_extracted()))
    assert out is not None and calls == ["patch"] and rows[-1]["sync_status"] == "updated"


def test_phase4_calendar_update_404_returns_none_and_marks_cancelled(monkeypatch):
    import asyncio
    ci, calls, rows = _p4_cal(monkeypatch, status=404)
    assert asyncio.run(ci.update_interview_event("o", "a", "m", None, _p4_extracted())) is None
    assert calls == ["patch"] and rows[-1]["sync_status"] == "cancelled"


def test_phase4_calendar_update_transient_failure_raises_without_creating(monkeypatch):
    import asyncio
    import pytest
    for status, raises in ((503, False), (429, False), (500, False), (200, True)):
        ci, calls, rows = _p4_cal(monkeypatch, status=status, raises=raises)
        with pytest.raises(ci.CalendarUpdateFailed):
            asyncio.run(ci.update_interview_event("o", "a", "m", None, _p4_extracted()))
        assert "post" not in calls and rows == []


def test_phase4_calendar_update_retry_is_idempotent(monkeypatch):
    import asyncio
    import pytest
    ci, calls, rows = _p4_cal(monkeypatch, status=503)
    with pytest.raises(ci.CalendarUpdateFailed):
        asyncio.run(ci.update_interview_event("o", "a", "m", None, _p4_extracted()))
    ci, calls, rows = _p4_cal(monkeypatch, status=200)
    assert asyncio.run(ci.update_interview_event("o", "a", "m", None, _p4_extracted())) is not None
    assert calls == ["patch"]


def test_phase4_calendar_cancel_treats_missing_event_as_success(monkeypatch):
    import asyncio
    for status in (204, 404, 410):
        ci, calls, rows = _p4_cal(monkeypatch, status=status)
        assert asyncio.run(ci.cancel_interview_event("o", "a")) is True
        assert rows[-1]["sync_status"] == "cancelled"


def test_phase4_calendar_cancel_transient_failure_raises(monkeypatch):
    import asyncio
    import pytest
    for status, raises in ((500, False), (503, False), (200, True)):
        ci, calls, rows = _p4_cal(monkeypatch, status=status, raises=raises)
        with pytest.raises(ci.CalendarUpdateFailed):
            asyncio.run(ci.cancel_interview_event("o", "a"))
        assert rows == []


def _p4_import(monkeypatch, update=None, cancel=None, existing_start="2030-01-01T10:00:00+00:00", extracted=None, processed=False):
    from job_hunter import email_import as ei
    log = {"sync": 0, "events": [], "update": 0, "cancel": 0}

    async def fake_update(**k):
        log["update"] += 1
        if isinstance(update, Exception):
            raise update
        return update

    async def fake_cancel(*a, **k):
        log["cancel"] += 1
        if isinstance(cancel, Exception):
            raise cancel
        return cancel

    async def fake_sync(**k):
        log["sync"] += 1
        return {"sync_status": "created"}

    monkeypatch.setattr(ei.repository, "list_applications", lambda o, status=None: [{"id": "app1", "job_id": "j1", "status": "interview"}])
    monkeypatch.setattr(ei.repository, "gmail_message_already_processed", lambda o, m: processed)
    monkeypatch.setattr(ei.repository, "get_preferences", lambda o: {})
    monkeypatch.setattr(ei.repository, "get_job", lambda j, o: {"id": "j1", "job_title": "Eng", "company_name": "Co"})
    monkeypatch.setattr(ei.repository, "add_activity", lambda r: None)
    monkeypatch.setattr(ei.repository, "create_gmail_event", lambda r: log["events"].append(r))
    monkeypatch.setattr(ei.repository, "get_active_calendar_event_for_application",
                        lambda o, a: {"id": "row1", "google_calendar_event_id": "evt1", "extracted_start_time": existing_start})
    monkeypatch.setattr(ei.service, "update_application_status", lambda o, a, s: None)
    monkeypatch.setattr(ei, "log_event", lambda **k: None)
    monkeypatch.setattr(ei, "update_interview_event", fake_update)
    monkeypatch.setattr(ei, "cancel_interview_event", fake_cancel)
    monkeypatch.setattr(ei, "sync_interview_event", fake_sync)
    monkeypatch.setattr(ei, "_extract_or_flag", lambda s, b: (extracted, False))
    return ei, log


def test_phase4_import_reschedule_transient_failure_is_retryable(monkeypatch):
    import asyncio
    from job_hunter.calendar_integration import CalendarUpdateFailed
    ei, log = _p4_import(monkeypatch, update=CalendarUpdateFailed("x"), extracted=_p4_extracted())
    out = asyncio.run(ei.process_imported_email("o", "Please reschedule", "Can we reschedule?", application_id_hint="app1"))
    assert out["calendar_failed"] is True and log["sync"] == 0 and log["events"] == []


def test_phase4_import_reschedule_missing_event_creates_new(monkeypatch):
    import asyncio
    ei, log = _p4_import(monkeypatch, update=None, extracted=_p4_extracted())
    out = asyncio.run(ei.process_imported_email("o", "Please reschedule", "Can we reschedule?", application_id_hint="app1"))
    assert log["sync"] == 1 and out["calendar_action"] == "create" and len(log["events"]) == 1


def test_phase4_import_rejection_cancel_failure_is_retryable(monkeypatch):
    import asyncio
    from job_hunter.calendar_integration import CalendarUpdateFailed
    ei, log = _p4_import(monkeypatch, cancel=CalendarUpdateFailed("x"))
    out = asyncio.run(ei.process_imported_email("o", "Update", "Unfortunately, we have decided not to proceed with your application.", application_id_hint="app1"))
    assert out["category"] == "rejection" and out["calendar_failed"] is True and log["events"] == []


def test_phase4_import_duplicate_is_noop(monkeypatch):
    import asyncio
    ei, log = _p4_import(monkeypatch, processed=True, extracted=_p4_extracted())
    out = asyncio.run(ei.process_imported_email("o", "Please reschedule", "x", application_id_hint="app1"))
    assert out["duplicate"] is True and log["update"] == 0 and log["sync"] == 0


def test_phase4_import_separate_interview_start_creates_separate_event(monkeypatch):
    import asyncio
    ei, log = _p4_import(monkeypatch, existing_start="2030-01-02T14:00:00+00:00", extracted=_p4_extracted())
    asyncio.run(ei.process_imported_email("o", "Interview invitation", "We would like to schedule an interview.", application_id_hint="app1"))
    assert log["sync"] == 1


def test_phase4_import_same_interview_start_is_not_duplicated(monkeypatch):
    import asyncio
    ei, log = _p4_import(monkeypatch, existing_start="2030-01-01T10:00:00+00:00", extracted=_p4_extracted())
    asyncio.run(ei.process_imported_email("o", "Interview invitation", "We would like to schedule an interview.", application_id_hint="app1"))
    assert log["sync"] == 0
