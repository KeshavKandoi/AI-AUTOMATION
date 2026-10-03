"""
Regression test: Gmail closeout must never call Gmail's messages.modify
API. WorkForge's Gmail OAuth scopes are send only (gmail.send) — closing out a Gmail-sourced task (on approval or rejection)
must complete successfully without changing the original message's state:
no UNREAD/INBOX label removal, no archiving, no other modification.
"""
import asyncio
import httpx
import pytest

import closeout
from closeout import close_gmail_loop, CLOSEOUT_HANDLERS


def test_gmail_modify_helper_does_not_exist():
    """Guards against _gmail_modify being silently reintroduced."""
    assert not hasattr(closeout, "_gmail_modify"), (
        "_gmail_modify was reintroduced — WorkForge must not modify Gmail "
        "messages (see close_gmail_loop's docstring)"
    )


def test_close_gmail_loop_never_calls_gmail_api(monkeypatch):
    """Even if the implementation changes later, close_gmail_loop must
    never make an outbound HTTP call. Constructing an httpx.AsyncClient
    at all fails the test immediately."""

    class ExplodingClient:
        def __init__(self, *a, **kw):
            raise AssertionError("close_gmail_loop must not make any HTTP calls to Gmail")

    monkeypatch.setattr(httpx, "AsyncClient", ExplodingClient)

    task = {"source_ref": "gmail:18abc123def"}

    # Must complete successfully for both approval and rejection, with no
    # HTTP call attempted in either case.
    asyncio.run(close_gmail_loop(task, access_token="fake-token", approved=True, archive=True))
    asyncio.run(close_gmail_loop(task, access_token="fake-token", approved=False))


def test_close_gmail_loop_still_validates_source_ref():
    """Removing the modify call must not also remove the guard against a
    malformed or wrong-source task."""
    bad_task = {"source_ref": "github:owner/repo#5"}
    with pytest.raises(RuntimeError, match="Cannot close Gmail loop"):
        asyncio.run(close_gmail_loop(bad_task, access_token="fake-token", approved=True))


def test_gmail_handler_still_registered():
    assert CLOSEOUT_HANDLERS["gmail"] is close_gmail_loop


import pathlib
import re
from datetime import datetime, timezone
from types import SimpleNamespace

from job_hunter import email_import

BACKEND = pathlib.Path(closeout.__file__).resolve().parent
SKIP_DIRS = {"tests", "venv", ".venv", "node_modules", "__pycache__", ".git"}


def _production_sources():
    for p in BACKEND.rglob("*.py"):
        if SKIP_DIRS & set(p.relative_to(BACKEND).parts) or p.name == "verify_oauth_login.py":
            continue
        yield p, p.read_text()


def test_no_gmail_readonly_scope_in_production_code():
    for path, text in _production_sources():
        assert "gmail.readonly" not in text, str(path)


def test_no_gmail_read_endpoints_in_production_code():
    pattern = re.compile(r"users/me/messages(?!/send)")
    for path, text in _production_sources():
        assert not pattern.search(text), str(path)


def test_gmail_send_scope_and_sending_retained():
    main_text = (BACKEND / "main.py").read_text()
    assert "auth/gmail.send" in main_text
    assert "users/me/messages/send" in main_text
    assert "userinfo.email" in main_text


def _setup(monkeypatch, processed=False, update_result=None):
    calls = {"status": [], "sync": [], "update": [], "cancel": [], "events": [], "activity": []}
    now = datetime.now(timezone.utc).isoformat()
    application = {"id": "app1", "job_id": "job1", "status": "applied", "applied_at": now, "created_at": now}
    job = {"id": "job1", "company_name": "Acme", "job_title": "Engineer", "original_apply_url": ""}
    repo = email_import.repository
    monkeypatch.setattr(repo, "list_applications", lambda org, status=None: [application])
    monkeypatch.setattr(repo, "get_job", lambda job_id, org: job)
    monkeypatch.setattr(repo, "get_job_sources", lambda job_id: [])
    monkeypatch.setattr(repo, "get_active_calendar_event_for_application", lambda org, aid: calls.get("active"))
    monkeypatch.setattr(repo, "get_preferences", lambda org: {"email": "me@example.com"})
    monkeypatch.setattr(repo, "gmail_message_already_processed", lambda org, mid: processed)
    monkeypatch.setattr(repo, "create_gmail_event", lambda row: calls["events"].append(row) or row)
    monkeypatch.setattr(repo, "add_activity", lambda row: calls["activity"].append(row))
    monkeypatch.setattr(email_import.service, "update_application_status", lambda org, aid, st: calls["status"].append(st))
    monkeypatch.setattr(email_import, "log_event", lambda **kw: None)
    monkeypatch.setattr(
        email_import, "extract_interview_datetime",
        lambda msg, subject, body: SimpleNamespace(start_time=datetime.now(timezone.utc), end_time=None),
    )

    async def fake_sync(**kw):
        calls["sync"].append(kw)
        return {"sync_status": "created"}

    async def fake_update(**kw):
        calls["update"].append(kw)
        return update_result

    async def fake_cancel(org, aid):
        calls["cancel"].append(aid)
        return True

    monkeypatch.setattr(email_import, "sync_interview_event", fake_sync)
    monkeypatch.setattr(email_import, "update_interview_event", fake_update)
    monkeypatch.setattr(email_import, "cancel_interview_event", fake_cancel)
    return calls


def _import(subject, body):
    return asyncio.run(email_import.process_imported_email(
        "org1", subject, body, sender="hr@acme.com", recipient="me@example.com",
    ))


def test_imported_interview_email_updates_status_and_creates_calendar_event(monkeypatch):
    calls = _setup(monkeypatch)
    result = _import("Interview invitation for Engineer at Acme", "We would like to schedule an interview with Acme for the Engineer role.")
    assert result["application_id"] == "app1"
    assert calls["status"] == ["interview"]
    assert len(calls["sync"]) == 1
    assert calls["sync"][0]["gmail_message_id"].startswith("manual:")
    assert calls["events"][0]["category"] == "interview_invite"


def test_imported_reschedule_without_existing_event_falls_back_to_create(monkeypatch):
    calls = _setup(monkeypatch, update_result=None)
    result = _import("Need to reschedule", "Please reschedule our interview for the Engineer role at Acme.")
    assert result["calendar_action"] == "create"
    assert len(calls["update"]) == 1
    assert len(calls["sync"]) == 1


def test_imported_reschedule_updates_existing_event(monkeypatch):
    calls = _setup(monkeypatch, update_result={"id": "row"})
    result = _import("Need to reschedule", "Please reschedule our interview for the Engineer role at Acme.")
    assert result["calendar_action"] == "update"
    assert calls["sync"] == []


def test_imported_rejection_updates_status_and_cancels_event(monkeypatch):
    calls = _setup(monkeypatch)
    result = _import("Update on your application", "Unfortunately we are not moving forward with the Engineer role at Acme.")
    assert calls["status"] == ["rejected"]
    assert calls["cancel"] == ["app1"]
    assert result["calendar_action"] == "cancel"


def test_duplicate_import_is_noop(monkeypatch):
    calls = _setup(monkeypatch, processed=True)
    result = _import("Interview invitation for Engineer at Acme", "We would like to schedule an interview with Acme for the Engineer role.")
    assert result["duplicate"] is True
    assert calls["status"] == [] and calls["sync"] == [] and calls["events"] == []


def test_unknown_application_hint_raises(monkeypatch):
    _setup(monkeypatch)
    with pytest.raises(LookupError):
        asyncio.run(email_import.process_imported_email("org1", "s", "b", application_id_hint="nope"))


def test_same_start_time_does_not_create_second_event(monkeypatch):
    calls = _setup(monkeypatch)
    fixed = datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(email_import, "extract_interview_datetime", lambda m, s, b: SimpleNamespace(start_time=fixed, end_time=None))
    calls["active"] = {"extracted_start_time": fixed.isoformat()}
    _import("Interview invitation for Engineer at Acme", "We would like to schedule an interview with Acme for the Engineer role.")
    assert calls["sync"] == []


def test_import_id_ignores_whitespace_and_case():
    a = email_import._import_message_id("Hello", "x", "Some  Body\n text")
    b = email_import._import_message_id("hello", "y", "some body text")
    assert a == b


def _scope(url):
    return re.search(r"scope=([^&]*)", url).group(1).split()


def test_gmail_login_requests_only_send_and_email(monkeypatch):
    import main
    monkeypatch.setattr(main, "_has_stored_refresh_token", lambda o, p: False)
    monkeypatch.setattr(main, "_issue_oauth_state", lambda o, p: "s")
    scopes = _scope(main.gmail_login("org")["url"])
    assert set(scopes) == {"https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/userinfo.email"}


def test_calendar_login_scope_unchanged(monkeypatch):
    import main
    monkeypatch.setattr(main, "_has_stored_refresh_token", lambda o, p: False)
    monkeypatch.setattr(main, "_issue_oauth_state", lambda o, p: "s")
    assert _scope(main.calendar_login("org")["url"]) == ["https://www.googleapis.com/auth/calendar"]


def _llm_result(monkeypatch, link):
    import json
    from job_hunter import interview_datetime_extractor as ex
    payload = {"date": _soon(), "start_time": "10:00", "end_time": "11:00", "timezone": "UTC", "meeting_link": link, "interviewer": "A", "company": "Acme", "confidence": 90, "explanation": "x"}
    fake = SimpleNamespace(models=SimpleNamespace(generate_content=lambda model, contents: SimpleNamespace(text=json.dumps(payload))))
    monkeypatch.setattr(ex, "gemini_client", fake)
    return ex.extract_via_llm("Interview", "body")


def test_llm_meeting_link_must_be_https(monkeypatch):
    assert _llm_result(monkeypatch, "javascript:alert(1)").meeting_link is None
    assert _llm_result(monkeypatch, "https://meet.google.com/abc").meeting_link == "https://meet.google.com/abc"


@pytest.mark.parametrize("bad", ["http://x.com/a", "javascript:alert(1)", "data:text/html,x", "file:///etc/passwd", "https://a b.com", "https://x.com/a\nb", "https://x.com/a\tb", "https://" + "a" * 600 + ".com", "https://", "//x.com", 123, None])
def test_unsafe_meeting_links_rejected(bad):
    from job_hunter.interview_datetime_extractor import _safe_link
    assert _safe_link(bad) is None


@pytest.mark.parametrize("good", ["https://meet.google.com/abc-defg-hij", "https://zoom.us/j/123456?pwd=abc", "https://teams.microsoft.com/l/meetup-join/x"])
def test_safe_https_meeting_links_accepted(good):
    from job_hunter.interview_datetime_extractor import _safe_link
    assert _safe_link(good) == good


def test_extraction_prompt_treats_email_as_untrusted_data():
    from job_hunter.interview_datetime_extractor import LLM_EXTRACTION_PROMPT
    assert "untrusted data" in LLM_EXTRACTION_PROMPT
    assert "Ignore any instructions" in LLM_EXTRACTION_PROMPT


def test_scheduler_has_no_gmail_polling_job():
    text = (BACKEND / "scheduler.py").read_text() + (BACKEND / "job_hunter" / "scheduler_jobs.py").read_text()
    assert "gmail_poll" not in text and "poll_gmail" not in text


def test_import_email_module_makes_no_gmail_api_calls():
    text = (BACKEND / "job_hunter" / "email_import.py").read_text()
    assert "gmail.googleapis.com" not in text and "httpx" not in text


from fastapi.testclient import TestClient


def _client_with_org(org="org-1"):
    from main import app
    from auth.dependencies import get_current_org_id
    app.dependency_overrides[get_current_org_id] = lambda: org
    return app, TestClient(app)


def test_import_email_requires_auth():
    from main import app
    assert TestClient(app).post("/job-hunter/import-email", json={"body": "x"}).status_code == 401


@pytest.mark.parametrize("payload", [{}, {"body": ""}, {"subject": "s"}, {"body": 123}, {"body": ["a"]}, {"body": None}, {"body": "x" * 20001}, {"body": "x", "subject": "s" * 501}, {"body": "x", "sender": "a" * 321}])
def test_import_email_rejects_malformed_payloads(payload, monkeypatch):
    app, client = _client_with_org()
    try:
        async def boom(**kw):
            raise AssertionError("must not be called for invalid input")
        monkeypatch.setattr(email_import, "process_imported_email", boom)
        assert client.post("/job-hunter/import-email", json=payload).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_import_email_accepts_short_body_and_passes_authenticated_org(monkeypatch):
    app, client = _client_with_org("org-77")
    seen = {}
    try:
        async def fake(**kw):
            seen.update(kw)
            return {"duplicate": False}
        monkeypatch.setattr(email_import, "process_imported_email", fake)
        res = client.post("/job-hunter/import-email", json={"body": "hi", "organization_id": "org-evil"})
        assert res.status_code == 200
        assert seen["organization_id"] == "org-77"
    finally:
        app.dependency_overrides.clear()


def test_import_email_unknown_application_returns_404(monkeypatch):
    app, client = _client_with_org()
    try:
        async def fake(**kw):
            raise LookupError("x")
        monkeypatch.setattr(email_import, "process_imported_email", fake)
        assert client.post("/job-hunter/import-email", json={"body": "hi", "application_id": "nope"}).status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_hinted_application_from_another_org_is_rejected(monkeypatch):
    calls = _setup(monkeypatch)
    by_org = {"org-A": [{"id": "appA", "job_id": "j", "status": "applied"}]}
    monkeypatch.setattr(email_import.repository, "list_applications", lambda org, status=None: by_org.get(org, []))
    with pytest.raises(LookupError):
        asyncio.run(email_import.process_imported_email(organization_id="org-B", subject="s", body="interview invitation", application_id_hint="appA"))
    assert calls["status"] == [] and calls["events"] == [] and calls["sync"] == []


def test_normal_application_confirmation_updates_nothing_and_creates_no_event(monkeypatch):
    calls = _setup(monkeypatch)
    result = _import("Thank you for applying", "Thank you for applying to the Engineer role at Acme. We have received your application.")
    assert result["application_id"] == "app1"
    assert calls["status"] == [] and calls["sync"] == [] and calls["cancel"] == []
    assert calls["events"][0]["category"] == "application_confirmation"


def test_irrelevant_email_is_ignored(monkeypatch):
    calls = _setup(monkeypatch)
    result = _import("Weekly newsletter", "Top ten pasta recipes for this week. Unsubscribe any time.")
    assert result["application_id"] is None
    assert calls["status"] == [] and calls["sync"] == [] and calls["cancel"] == []
    assert calls["events"][0]["category"] == "not_recruitment"


def test_withdrawal_archives_and_cancels_event(monkeypatch):
    calls = _setup(monkeypatch)
    result = _import("Update", "The position has been closed for the Engineer role at Acme.")
    assert calls["status"] == ["archived"] and calls["cancel"] == ["app1"]
    assert result["calendar_action"] == "cancel"


def test_failed_calendar_sync_is_not_reported_as_created(monkeypatch):
    calls = _setup(monkeypatch)

    async def failing(**kw):
        calls["sync"].append(kw)
        return {"sync_status": "pending"}

    monkeypatch.setattr(email_import, "sync_interview_event", failing)
    result = _import("Interview invitation for Engineer at Acme", "We would like to schedule an interview with Acme for the Engineer role.")
    assert result["calendar_action"] is None
    assert calls["status"] == ["interview"] and len(calls["events"]) == 1


def test_normalized_duplicate_import_is_noop(monkeypatch):
    calls = _setup(monkeypatch)
    seen = set()
    repo = email_import.repository
    monkeypatch.setattr(repo, "gmail_message_already_processed", lambda org, mid: mid in seen)
    monkeypatch.setattr(repo, "create_gmail_event", lambda row: seen.add(row["gmail_message_id"]) or calls["events"].append(row) or row)
    r1 = _import("Interview invitation for Engineer at Acme", "We would like to schedule an interview with Acme for the Engineer role.")
    r2 = _import("  INTERVIEW invitation for engineer at ACME ", "We would like  to schedule an interview\nwith Acme for the Engineer role.")
    assert r1["duplicate"] is False and r2["duplicate"] is True
    assert calls["status"] == ["interview"] and len(calls["sync"]) == 1


def test_import_flow_makes_no_http_calls_at_all(monkeypatch):
    class Exploding:
        def __init__(self, *a, **k):
            raise AssertionError("unexpected outbound HTTP call during import")
    monkeypatch.setattr(httpx, "AsyncClient", Exploding)
    calls = _setup(monkeypatch)
    _import("Interview invitation for Engineer at Acme", "We would like to schedule an interview with Acme for the Engineer role.")
    _import("Update", "Unfortunately we are not moving forward with the Engineer role at Acme.")
    assert calls["status"]


def _llm(monkeypatch, raw=None, **over):
    import json
    from job_hunter import interview_datetime_extractor as ex
    payload = {"date": _soon(), "start_time": "10:00", "end_time": "11:00", "timezone": "UTC", "meeting_link": None, "interviewer": "Bob", "company": "Acme", "confidence": 90, "explanation": "x"}
    payload.update(over)
    text = raw if raw is not None else json.dumps(payload)
    fake = SimpleNamespace(models=SimpleNamespace(generate_content=lambda model, contents: SimpleNamespace(text=text)))
    monkeypatch.setattr(ex, "gemini_client", fake)
    return ex.extract_via_llm("Interview", "body")


def test_llm_valid_extraction_is_timezone_aware_with_safe_link(monkeypatch):
    r = _llm(monkeypatch, meeting_link="https://meet.google.com/abc-defg-hij")
    assert r.start_time.tzinfo is not None and r.end_time.hour == 11
    assert r.meeting_link == "https://meet.google.com/abc-defg-hij"


def test_llm_extraction_without_meeting_link_is_valid(monkeypatch):
    r = _llm(monkeypatch)
    assert r is not None and r.meeting_link is None


@pytest.mark.parametrize("over", [{"timezone": None}, {"timezone": ""}, {"timezone": "Mars/Base"}, {"timezone": 5}, {"date": "2030-02-31"}, {"start_time": "25:00"}, {"confidence": 50}, {"confidence": "high"}, {"date": None}, {"start_time": None}])
def test_llm_unusable_results_return_none(monkeypatch, over):
    assert _llm(monkeypatch, **over) is None


@pytest.mark.parametrize("raw", ["not json", "[]", "null", '"text"', '{"date": "2030-01-01"}', ""])
def test_llm_malformed_output_returns_none(monkeypatch, raw):
    assert _llm(monkeypatch, raw=raw) is None


def test_llm_injection_values_are_sanitized_and_extra_fields_ignored(monkeypatch):
    r = _llm(monkeypatch, interviewer="<script>alert(1)</script>Bob", company="Evil", send_email=True, create_event_at="00:00")
    assert "<" not in r.interviewer and ">" not in r.interviewer
    assert not hasattr(r, "send_email") and not hasattr(r, "create_event_at")


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}
        self.text = ""

    def json(self):
        return self._payload


def _cal_setup(monkeypatch, status=200, payload=None, existing=None, token_error=False):
    from job_hunter import calendar_integration as ci
    state = {"http": [], "updates": []}
    repo = ci.repository
    monkeypatch.setattr(repo, "get_calendar_event_by_gmail_message", lambda org, mid: None)
    monkeypatch.setattr(repo, "get_active_calendar_event_for_application", lambda org, aid: existing)
    monkeypatch.setattr(repo, "create_calendar_event_row", lambda row: {"id": "row1", **row})

    def upd(eid, updates):
        state["updates"].append(updates)
        return {"id": eid, **updates}

    monkeypatch.setattr(repo, "update_calendar_event_row", upd)

    def tok(org):
        if token_error:
            raise RuntimeError("no token")
        return "tok"

    monkeypatch.setattr(ci, "_get_calendar_token_for_org", tok)
    monkeypatch.setattr(ci, "log_event", lambda **kw: None)
    monkeypatch.setattr(ci, "notify", lambda **kw: None)

    class Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            state["http"].append(("post", url, json))
            return _Resp(status, payload)

        async def patch(self, url, headers=None, json=None):
            state["http"].append(("patch", url, json))
            return _Resp(status, payload)

        async def delete(self, url, headers=None):
            state["http"].append(("delete", url, None))
            return _Resp(status, payload)

    monkeypatch.setattr(ci.httpx, "AsyncClient", Client)
    return ci, state


def _extracted(link=None):
    from job_hunter.interview_datetime_extractor import ExtractedInterview
    from zoneinfo import ZoneInfo
    start = datetime(2030, 1, 1, 10, 0, tzinfo=ZoneInfo("UTC"))
    return ExtractedInterview(start_time=start, end_time=start.replace(hour=11), timezone="UTC", meeting_link=link, interviewer="Bob", company="Evil Corp", source="llm", confidence=90.0)


JOB = {"job_title": "Engineer", "company_name": "Acme"}


def test_calendar_create_uses_trusted_job_values_and_link(monkeypatch):
    ci, state = _cal_setup(monkeypatch, payload={"id": "ev1", "status": "confirmed"})
    res = asyncio.run(ci.sync_interview_event("org1", "app1", JOB, "manual:x", None, None, _extracted("https://meet.google.com/abc")))
    kind, url, body = state["http"][0]
    assert kind == "post" and body["summary"] == "Interview: Engineer at Acme"
    assert "Evil" not in str(body) and body["location"] == "https://meet.google.com/abc"
    assert body["start"]["dateTime"] == "2030-01-01T10:00:00+00:00"
    assert res["sync_status"] == "created"


def test_calendar_create_without_meeting_link_has_no_location(monkeypatch):
    ci, state = _cal_setup(monkeypatch, payload={"id": "ev1", "status": "confirmed"})
    asyncio.run(ci.sync_interview_event("org1", "app1", JOB, "manual:x", None, None, _extracted(None)))
    body = state["http"][0][2]
    assert "location" not in body and "Meeting link" not in body["description"]


def test_calendar_api_failure_marks_row_failed(monkeypatch):
    ci, state = _cal_setup(monkeypatch, status=500)
    res = asyncio.run(ci.sync_interview_event("org1", "app1", JOB, "manual:x", None, None, _extracted()))
    assert res["sync_status"] != "created"
    assert any(u.get("sync_status") == "failed" for u in state["updates"])


def test_calendar_token_failure_makes_no_http_call_and_marks_failed(monkeypatch):
    ci, state = _cal_setup(monkeypatch, token_error=True)
    asyncio.run(ci.sync_interview_event("org1", "app1", JOB, "manual:x", None, None, _extracted()))
    assert state["http"] == []
    assert any(u.get("sync_status") == "failed" for u in state["updates"])


def test_calendar_create_is_idempotent_per_message(monkeypatch):
    ci, state = _cal_setup(monkeypatch, payload={"id": "ev1"})
    monkeypatch.setattr(ci.repository, "get_calendar_event_by_gmail_message", lambda o, m: {"id": "r", "sync_status": "created"})
    res = asyncio.run(ci.sync_interview_event("org1", "app1", JOB, "manual:x", None, None, _extracted()))
    assert state["http"] == [] and res["sync_status"] == "created"


def test_calendar_reschedule_patches_existing_event(monkeypatch):
    ci, state = _cal_setup(monkeypatch, payload={"id": "ev1"}, existing={"id": "row1", "google_calendar_event_id": "ev1"})
    res = asyncio.run(ci.update_interview_event("org1", "app1", "manual:y", None, _extracted()))
    assert [h[0] for h in state["http"]] == ["patch"] and state["http"][0][1].endswith("/ev1")
    assert res["sync_status"] == "updated"


def test_calendar_reschedule_without_existing_event_returns_none(monkeypatch):
    ci, state = _cal_setup(monkeypatch, existing=None)
    assert asyncio.run(ci.update_interview_event("org1", "app1", "manual:y", None, _extracted())) is None
    assert state["http"] == []


@pytest.mark.parametrize("status,expected", [(204, True), (404, True), (410, True)])
def test_calendar_cancel_deletes_existing_event(monkeypatch, status, expected):
    ci, state = _cal_setup(monkeypatch, status=status, existing={"id": "row1", "google_calendar_event_id": "ev1"})
    assert asyncio.run(ci.cancel_interview_event("org1", "app1")) is expected
    assert state["http"][0][0] == "delete" and state["http"][0][1].endswith("/ev1")


@pytest.mark.parametrize("status", [500, 503])
def test_calendar_cancel_transient_error_raises_for_retry(monkeypatch, status):
    ci, state = _cal_setup(monkeypatch, status=status, existing={"id": "row1", "google_calendar_event_id": "ev1"})
    with pytest.raises(ci.CalendarUpdateFailed):
        asyncio.run(ci.cancel_interview_event("org1", "app1"))
    assert state["http"][0][0] == "delete"


def test_calendar_cancel_without_existing_event_is_noop(monkeypatch):
    ci, state = _cal_setup(monkeypatch, existing=None)
    assert asyncio.run(ci.cancel_interview_event("org1", "app1")) is False
    assert state["http"] == []


import json as _p3_json
from datetime import datetime as _p3_dt, timedelta as _p3_td, timezone as _p3_tz
from unittest.mock import MagicMock as _p3_mm, patch as _p3_patch


def _p3_llm(date, end=None, tz="Asia/Kolkata", conf=90):
    m = _p3_mm()
    m.models.generate_content.return_value.text = _p3_json.dumps({
        "date": date, "start_time": "10:00", "end_time": end, "timezone": tz,
        "meeting_link": None, "interviewer": None, "company": None,
        "confidence": conf, "explanation": "x",
    })
    return m


def _p3_day(offset):
    return (_p3_dt.now(_p3_tz.utc) + _p3_td(days=offset)).strftime("%Y-%m-%d")


def test_llm_extraction_rejects_past_date():
    from job_hunter import interview_datetime_extractor as ex
    with _p3_patch.object(ex, "gemini_client", _p3_llm(_p3_day(-30))):
        assert ex.extract_via_llm("s", "b") is None


def test_llm_extraction_rejects_date_beyond_400_days():
    from job_hunter import interview_datetime_extractor as ex
    with _p3_patch.object(ex, "gemini_client", _p3_llm(_p3_day(500))):
        assert ex.extract_via_llm("s", "b") is None


def test_llm_extraction_defaults_end_to_one_hour_after_start():
    from job_hunter import interview_datetime_extractor as ex
    with _p3_patch.object(ex, "gemini_client", _p3_llm(_p3_day(10))):
        result = ex.extract_via_llm("s", "b")
    assert result is not None
    assert result.end_time - result.start_time == _p3_td(hours=1)


def test_llm_extraction_without_timezone_is_skipped():
    from job_hunter import interview_datetime_extractor as ex
    with _p3_patch.object(ex, "gemini_client", _p3_llm(_p3_day(10), tz=None)):
        assert ex.extract_via_llm("s", "b") is None


def _soon():
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")


def test_calendar_failed_row_is_retried_with_deterministic_event_id(monkeypatch):
    import asyncio
    ci, state = _cal_setup(monkeypatch, payload={"id": "ev1", "status": "confirmed"})
    monkeypatch.setattr(ci.repository, "get_calendar_event_by_gmail_message", lambda o, m: {"id": "row1", "sync_status": "failed"})
    res = asyncio.run(ci.sync_interview_event("org1", "app1", JOB, "manual:x", None, None, _extracted()))
    kind, url, body = state["http"][0]
    assert kind == "post" and body["id"] == "row1"
    assert res["sync_status"] == "created"


def test_calendar_conflict_on_deterministic_id_counts_as_created(monkeypatch):
    import asyncio
    ci, state = _cal_setup(monkeypatch, status=409)
    res = asyncio.run(ci.sync_interview_event("org1", "app1", JOB, "manual:x", None, None, _extracted()))
    assert res["sync_status"] == "created"


def _p3_import_with_sync(monkeypatch, sync_status, extractor=None):
    import asyncio
    from types import SimpleNamespace
    from job_hunter import email_import as ei
    app = {"id": "a1", "job_id": "j1", "status": "applied"}
    job = {"id": "j1", "company_name": "Acme", "job_title": "Engineer"}
    recorded = []
    repo = ei.repository
    monkeypatch.setattr(repo, "list_applications", lambda org, status=None: [app])
    monkeypatch.setattr(repo, "gmail_message_already_processed", lambda o, m: False)
    monkeypatch.setattr(repo, "get_preferences", lambda o: {})
    monkeypatch.setattr(repo, "get_job", lambda j, o: job)
    monkeypatch.setattr(repo, "get_active_calendar_event_for_application", lambda o, a: None)
    monkeypatch.setattr(repo, "create_gmail_event", lambda row: recorded.append(row))
    monkeypatch.setattr(ei.service, "update_application_status", lambda o, a, st: app)
    monkeypatch.setattr(ei, "_get_verified_domain_for_job", lambda j: None)
    monkeypatch.setattr(ei, "find_best_match", lambda **kw: SimpleNamespace(is_confident=True, application_id="a1", score=90, signals={}))
    monkeypatch.setattr(ei, "extract_interview_datetime", extractor or (lambda msg, s, b: SimpleNamespace(start_time=1)))
    monkeypatch.setattr(ei, "log_event", lambda **kw: None)

    async def fake_sync(**kw):
        return {"sync_status": sync_status}

    monkeypatch.setattr(ei, "sync_interview_event", fake_sync)
    result = asyncio.run(ei.process_imported_email("org1", "Interview invitation for Engineer at Acme", "We would like to schedule an interview with Acme for the Engineer role."))
    return result, recorded


def test_failed_calendar_sync_does_not_mark_import_processed(monkeypatch):
    result, recorded = _p3_import_with_sync(monkeypatch, "failed")
    assert result["calendar_failed"] is True and result["calendar_action"] is None
    assert recorded == []


def test_successful_calendar_sync_marks_import_processed(monkeypatch):
    result, recorded = _p3_import_with_sync(monkeypatch, "created")
    assert result["calendar_failed"] is False and result["calendar_action"] == "create"
    assert len(recorded) == 1


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True])
def test_llm_confidence_non_finite_or_boolean_is_rejected(monkeypatch, bad):
    assert _llm(monkeypatch, confidence=bad) is None


def test_llm_api_error_raises_extraction_unavailable(monkeypatch):
    from types import SimpleNamespace
    from job_hunter import interview_datetime_extractor as ex

    def boom(model, contents):
        raise RuntimeError("503")

    monkeypatch.setattr(ex, "gemini_client", SimpleNamespace(models=SimpleNamespace(generate_content=boom)))
    with pytest.raises(ex.ExtractionUnavailable):
        ex.extract_via_llm("s", "b")


def test_llm_oversized_output_is_rejected(monkeypatch):
    assert _llm(monkeypatch, raw="x" * 25000) is None


def test_llm_free_text_fields_are_sanitized_and_capped(monkeypatch):
    r = _llm(monkeypatch, company="<b>Acme</b>" + "y" * 500, explanation="z" * 5000)
    assert "<" not in r.company and len(r.company) <= 100 and len(r.explanation) <= 300


def test_extraction_unavailable_import_is_not_recorded_as_processed(monkeypatch):
    from job_hunter import interview_datetime_extractor as ex

    def boom(msg, s, b):
        raise ex.ExtractionUnavailable("503")

    result, recorded = _p3_import_with_sync(monkeypatch, "created", extractor=boom)
    assert result["calendar_failed"] is True and result["calendar_action"] is None
    assert recorded == []


@pytest.mark.parametrize("subject,body,expected", [
    ("Application update", "Unfortunately we have decided not to proceed with your application for the Engineer role.", "rejection"),
    ("Application update", "We will not be moving forward with your candidacy for this role.", "rejection"),
    ("Application update", "We have decided to move forward with other candidates for the role.", "rejection"),
    ("Application update", "We are withdrawing your application because the position has been closed.", "withdrawal"),
    ("Interview confirmed", "Your interview has been confirmed for Monday at 10 AM.", "interview_invite"),
    ("Interview", "Unfortunately I need to move our interview to Friday afternoon.", "reschedule"),
    ("Interview", "We are interviewing other candidates this week and your interview is scheduled for Monday.", "interview_invite"),
    ("Interview", "Unfortunately the video link was broken, here is the new interview link.", "interview_invite"),
    ("Your order", "Unfortunately your package is delayed until Tuesday.", "not_recruitment"),
])
def test_classifier_does_not_treat_generic_words_as_rejection(subject, body, expected):
    from job_hunter.gmail_classifier import classify_email
    assert classify_email(subject, body).category == expected


def test_repository_has_no_gmail_poll_helpers():
    from job_hunter import repository
    for name in ("has_running_gmail_poll", "create_gmail_poll_run", "finish_gmail_poll_run"):
        assert not hasattr(repository, name)


@pytest.mark.parametrize("subject,body,expected", [
    ("Update", "Unfortunately, we have decided not to proceed with your application.", "rejection"),
    ("Update", "We will not be moving forward with your candidacy.", "rejection"),
    ("Update", "We have decided to move forward with other candidates.", "rejection"),
    ("Application update", "We regret that you were not selected for the role.", "rejection"),
    ("Interview", "Unfortunately I need to move our interview to Friday.", "reschedule"),
    ("Interview", "Unfortunately I need to move our interview to Friday. Here is the new link.", "reschedule"),
    ("Interview", "Unfortunately the video link was broken. Here is the new link.", "interview_invite"),
    ("Interview", "Unfortunately, the hiring manager is unavailable today.", "reschedule"),
    ("Your order", "Unfortunately your package is delayed.", "not_recruitment"),
    ("Password reset", "Unfortunately the link was broken. Here is the new link.", "not_recruitment"),
    ("Interview invitation", "We would like to schedule an interview. If you are not selected for this round we will let you know.", "interview_invite"),
])
def test_phase4_classifier_context_rules(subject, body, expected):
    from job_hunter.gmail_classifier import classify_email
    assert classify_email(subject, body).category == expected


@pytest.mark.parametrize("subject,body", [
    ("Application", "Unfortunately the recruiter will be out. Please send your resume."),
    ("Update", "Unfortunately, the interview room changed. See the new details."),
    ("Update", "If you are not selected we will contact you."),
])
def test_phase4_classifier_ambiguous_never_rejection(subject, body):
    from job_hunter.gmail_classifier import classify_email
    assert classify_email(subject, body).category != "rejection"


def test_interview_extraction_runs_off_the_event_loop(monkeypatch):
    import asyncio
    import threading
    from types import SimpleNamespace
    from job_hunter import email_import as ei

    seen = {}
    loop_thread = {}

    def fake_extract(msg, subject, body):
        seen["thread"] = threading.get_ident()
        return SimpleNamespace(start_time=1, end_time=None)

    async def fake_sync(**kwargs):
        return {"sync_status": "created"}

    monkeypatch.setattr(ei.repository, "list_applications", lambda org, status=None: [{"id": "a1", "job_id": "j1", "status": "applied"}])
    monkeypatch.setattr(ei.repository, "gmail_message_already_processed", lambda org, mid: False)
    monkeypatch.setattr(ei.repository, "get_preferences", lambda org: {})
    monkeypatch.setattr(ei.repository, "get_job", lambda jid, org: {"id": "j1", "job_title": "Dev", "company_name": "Acme"})
    monkeypatch.setattr(ei.repository, "get_active_calendar_event_for_application", lambda org, app: None)
    monkeypatch.setattr(ei.repository, "create_gmail_event", lambda row: None)
    monkeypatch.setattr(ei.service, "update_application_status", lambda org, app, status: None)
    monkeypatch.setattr(ei, "log_event", lambda **kwargs: None)
    monkeypatch.setattr(ei, "extract_interview_datetime", fake_extract)
    monkeypatch.setattr(ei, "sync_interview_event", fake_sync)

    async def run():
        loop_thread["id"] = threading.get_ident()
        return await ei.process_imported_email("org-1", "Interview invitation", "We would like to schedule an interview.", application_id_hint="a1")

    result = asyncio.run(run())
    assert result["calendar_action"] == "create"
    assert seen["thread"] != loop_thread["id"]
