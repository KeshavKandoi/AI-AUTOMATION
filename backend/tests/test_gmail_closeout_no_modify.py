"""
Regression test: Gmail closeout must never call Gmail's messages.modify
API. WorkForge's Gmail OAuth scopes are read + send only (gmail.readonly,
gmail.send) — closing out a Gmail-sourced task (on approval or rejection)
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
