"""
Regression tests for _derive_context_label, which fixes save_audit_log and
create_calendar_event showing generic "Untitled"/"Workflow event" labels for
push-triggered runs (push contexts have no 'title' field at all -- only
issue_created/pull_request_opened contexts do).
"""
import asyncio
from unittest.mock import patch, MagicMock

import workflow_engine


def run(coro):
    return asyncio.run(coro)


def test_prefers_title_when_present_issue_or_pr_context():
    context = {"title": "Bug: login fails", "commit_message": "should be ignored"}
    assert workflow_engine._derive_context_label(context) == "Bug: login fails"


def test_falls_back_to_commit_message_for_push_context():
    context = {"repo": "acme/repo", "branch": "main", "commit_message": "fix: typo in README"}
    assert workflow_engine._derive_context_label(context) == "fix: typo in README"


def test_falls_back_to_repo_and_branch_when_no_title_or_commit_message():
    context = {"repo": "acme/repo", "branch": "main"}
    assert workflow_engine._derive_context_label(context) == "acme/repo@main"


def test_falls_back_to_repo_alone_when_no_branch():
    context = {"repo": "acme/repo"}
    assert workflow_engine._derive_context_label(context) == "acme/repo"


def test_falls_back_to_untitled_when_nothing_available():
    assert workflow_engine._derive_context_label({}) == "Untitled"


def test_save_audit_log_uses_commit_message_for_push_context():
    context = {"repo": "acme/repo", "branch": "main", "commit_message": "add feature X"}
    with patch.object(workflow_engine, "log_event") as mock_log_event:
        run(workflow_engine._action_save_audit_log("org-A", context))
        summary = mock_log_event.call_args.kwargs["summary"]
        assert "add feature X" in summary
        assert "Untitled" not in summary


def test_calendar_event_uses_commit_message_for_push_context():
    context = {"repo": "acme/repo", "branch": "main", "commit_message": "add feature X"}
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"htmlLink": "https://calendar.google.com/x"}

    from unittest.mock import AsyncMock
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post = AsyncMock(return_value=fake_response)

    with patch.object(workflow_engine, "_get_org_token", return_value=("ya29.valid-token", None)), \
         patch.object(workflow_engine.httpx, "AsyncClient", return_value=mock_client):
        run(workflow_engine._action_create_calendar_event("org-A", context))
        sent_json = mock_client.__aenter__.return_value.post.call_args.kwargs["json"]
        assert sent_json["summary"] == "add feature X"


def test_save_audit_log_still_uses_real_title_for_issue_context_unchanged():
    context = {"title": "Bug: login fails", "repo": "acme/repo"}
    with patch.object(workflow_engine, "log_event") as mock_log_event:
        run(workflow_engine._action_save_audit_log("org-A", context))
        summary = mock_log_event.call_args.kwargs["summary"]
        assert "Bug: login fails" in summary
