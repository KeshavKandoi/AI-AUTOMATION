import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from main import app
import webhooks.routes as webhook_routes


def test_push_webhook_dispatches_workflow_immediately_with_commit_context():
    payload = {
        "ref": "refs/heads/main",
        "after": "abc123",
        "repository": {"full_name": "acme/project"},
        "head_commit": {
            "author": {"name": "Octocat"},
            "message": "Fix deployment",
            "timestamp": "2030-01-02T10:00:00Z",
            "added": ["new.txt"],
            "modified": ["README.md"],
            "removed": [],
        },
        "commits": [{"id": "abc123"}],
    }
    dispatched = AsyncMock()

    with patch.object(webhook_routes, "_resolve_org_for_webhook", return_value={"id": "org-a"}), \
         patch.object(webhook_routes, "dispatch_workflow_event", dispatched):
        response = TestClient(app).post(
            "/webhooks/github",
            content=json.dumps(payload),
            headers={"content-type": "application/json", "x-github-event": "push"},
        )

    assert response.status_code == 200
    dispatched.assert_awaited_once_with(
        "org-a",
        "push",
        {
            "repo": "acme/project",
            "branch": "main",
            "author": "Octocat",
            "commit_message": "Fix deployment",
            "commit_sha": "abc123",
            "files_changed": ["new.txt", "README.md"],
            "commit_count": 1,
            "timestamp": "2030-01-02T10:00:00Z",
        },
        event_key="abc123:main",
    )
    assert response.json() == {"status": "triggered", "event": "push", "tasks_created": 0}


def test_unopened_issue_action_is_ignored_without_running_workflows():
    payload = {"action": "closed", "repository": {"full_name": "acme/project"}}
    with patch.object(webhook_routes, "_resolve_org_for_webhook", return_value={"id": "org-a"}), \
         patch.object(webhook_routes, "dispatch_workflow_event", new=AsyncMock()) as dispatched, \
         patch.object(webhook_routes, "dispatch_workflow_event", new=AsyncMock()) as dispatched:
        response = TestClient(app).post(
            "/webhooks/github",
            content=json.dumps(payload),
            headers={"content-type": "application/json", "x-github-event": "issues"},
        )
    assert response.status_code == 200
    assert response.json() == {"status": "ignored", "event": "issues", "action": "closed"}
    dispatched.assert_not_awaited()
    dispatched.assert_not_awaited()
