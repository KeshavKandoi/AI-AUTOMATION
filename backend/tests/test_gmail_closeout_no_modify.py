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
        return {}

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
