"""
Security tests for task approval/action routes: authentication required,
cross-organization IDOR blocked, client-supplied access_token no longer
accepted.
"""
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


def _override_auth(app, org_id="org-1", user_id="user-1"):
    from auth.dependencies import get_current_user, get_current_org_id
    app.dependency_overrides[get_current_user] = lambda: {"sub": user_id, "email": "test@example.com"}
    app.dependency_overrides[get_current_org_id] = lambda: org_id


def _clear(app):
    app.dependency_overrides.clear()


def test_approve_task_requires_auth():
    from main import app
    client = TestClient(app)
    res = client.post("/tasks/task-123/approve")
    assert res.status_code == 401


def test_approve_task_blocks_cross_org_access():
    from main import app
    _override_auth(app, org_id="org-attacker")
    try:
        with patch("main.supabase_admin") as sb:
            select_result = MagicMock()
            select_result.data = [{"id": "task-123", "organization_id": "org-victim", "title": "t"}]
            sb.table.return_value.select.return_value.eq.return_value.execute.return_value = select_result

            client = TestClient(app)
            res = client.post("/tasks/task-123/approve")
            assert res.status_code == 404
    finally:
        _clear(app)


def test_approve_task_succeeds_for_owning_org():
    from main import app
    _override_auth(app, org_id="org-victim")
    try:
        with patch("main.supabase_admin") as sb, patch("main.log_event"):
            select_result = MagicMock()
            select_result.data = [{"id": "task-123", "organization_id": "org-victim", "title": "t"}]
            update_result = MagicMock()
            update_result.data = [{"id": "task-123", "organization_id": "org-victim", "status": "approved", "title": "t"}]

            table_mock = sb.table.return_value
            table_mock.select.return_value.eq.return_value.execute.return_value = select_result
            table_mock.update.return_value.eq.return_value.execute.return_value = update_result

            client = TestClient(app)
            res = client.post("/tasks/task-123/approve")
            assert res.status_code == 200
            assert res.json()["status"] == "approved"
    finally:
        _clear(app)


def test_approve_and_create_issue_rejects_client_supplied_access_token():
    """The route signature must no longer accept access_token at all --
    passing one should be silently ignored (FastAPI drops unknown query
    params) rather than used, and the route must still resolve its own
    token server-side."""
    from main import app
    _override_auth(app, org_id="org-victim")
    try:
        with patch("main.supabase_admin") as sb, \
             patch("main._resolve_access_token", create=True) as _unused, \
             patch("closeout._resolve_access_token") as mock_resolve, \
             patch("main.github_post", new_callable=AsyncMock) as mock_github_post, \
             patch("main.log_event"):

            task_row = {
                "id": "task-123", "organization_id": "org-victim",
                "status": "approved", "title": "t", "description": "d",
                "source_ref": None,
            }
            select_result = MagicMock()
            select_result.data = [task_row]
            sb.table.return_value.select.return_value.eq.return_value.execute.return_value = select_result
            sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[task_row])

            mock_resolve.return_value = "server-side-real-token"
            mock_github_post.return_value = MagicMock(
                status_code=201,
                json=lambda: {"number": 1, "html_url": "https://github.com/x/y/issues/1"},
            )

            client = TestClient(app)
            res = client.post(
                "/tasks/task-123/approve-and-create-issue",
                params={"repo_full_name": "x/y", "access_token": "attacker-supplied-token"},
            )

            assert res.status_code == 200
            # Confirm the server resolved its own token rather than trusting
            # any client-supplied value.
            mock_resolve.assert_called_once_with("org-victim", "github")
            called_token = mock_github_post.call_args.args[1]
            assert called_token == "server-side-real-token"
            assert called_token != "attacker-supplied-token"
    finally:
        _clear(app)


def test_pending_approval_requires_auth():
    from main import app
    client = TestClient(app)
    res = client.get("/tasks/pending-approval")
    assert res.status_code == 401


def test_get_tasks_requires_auth():
    from main import app
    client = TestClient(app)
    res = client.get("/tasks")
    assert res.status_code == 401
