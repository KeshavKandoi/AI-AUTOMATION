from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from main import app
from auth.dependencies import get_current_org_id
import workflow_routes
import main


class _WorkflowQuery:
    def __init__(self, row):
        self.row = row

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def execute(self):
        return SimpleNamespace(data=[self.row])


class _WorkflowDb:
    def __init__(self, row):
        self.row = row

    def table(self, _name):
        return _WorkflowQuery(self.row)


def _active_workflow(status="active"):
    return {
        "id": "workflow-1", "organization_id": "org-1", "name": "Notify on push",
        "status": status, "trigger_type": "push", "conditions": {}, "actions": ["send_email"],
    }


def test_run_now_success_returns_recorded_run(monkeypatch):
    app.dependency_overrides[get_current_org_id] = lambda: "org-1"
    run = {"id": "run-1", "status": "success", "actions_executed": [], "duration_ms": 1}
    async def execute(*_args, **_kwargs):
        return run
    monkeypatch.setattr(workflow_routes, "supabase_admin", _WorkflowDb(_active_workflow()))
    monkeypatch.setattr(workflow_routes, "execute_workflow", execute)
    try:
        response = TestClient(app).post("/workflows/workflow-1/run-now")
        assert response.status_code == 200
        assert response.json() == {"status": "triggered", "run": run}
    finally:
        app.dependency_overrides.clear()


def test_run_now_failure_returns_safe_actionable_error(monkeypatch):
    app.dependency_overrides[get_current_org_id] = lambda: "org-1"
    async def execute(*_args, **_kwargs):
        raise RuntimeError("database unavailable")
    monkeypatch.setattr(workflow_routes, "supabase_admin", _WorkflowDb(_active_workflow()))
    monkeypatch.setattr(workflow_routes, "execute_workflow", execute)
    try:
        response = TestClient(app).post("/workflows/workflow-1/run-now")
        assert response.status_code == 500
        assert "backend logs" in response.json()["detail"]
        assert "database unavailable" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_run_now_rejects_inactive_workflow(monkeypatch):
    app.dependency_overrides[get_current_org_id] = lambda: "org-1"
    monkeypatch.setattr(workflow_routes, "supabase_admin", _WorkflowDb(_active_workflow("paused")))
    try:
        response = TestClient(app).post("/workflows/workflow-1/run-now")
        assert response.status_code == 409
        assert "paused" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_connect_repository_requires_authenticated_users_repo(monkeypatch):
    app.dependency_overrides[get_current_org_id] = lambda: "org-1"
    settings = main.settings
    monkeypatch.setattr(settings, "RENDER_BASE_URL", "https://api.example")
    monkeypatch.setattr("closeout._resolve_access_token", lambda *_args: "github-token")
    monkeypatch.setattr(main, "_rate_limit", lambda *_args: None)
    monkeypatch.setattr(main, "github_get_paginated", AsyncMock(return_value=[{"full_name": "acme/project"}]))
    register = AsyncMock(return_value={"id": 9})
    monkeypatch.setattr(main, "register_github_webhook", register)
    table = MagicMock()
    monkeypatch.setattr(main.supabase_admin, "table", lambda _name: table)
    try:
        client = TestClient(app)
        ok = client.post("/github/connect-repo", params={"repo_full_name": "ACME/PROJECT"})
        assert ok.status_code == 200
        assert ok.json()["repo"] == "acme/project"
        register.assert_awaited_once()

        register.reset_mock()
        missing = client.post("/github/connect-repo", params={"repo_full_name": "other/private"})
        assert missing.status_code == 404
        register.assert_not_awaited()
    finally:
        app.dependency_overrides.clear()


def test_removed_placeholder_route_is_not_registered():
    paths = app.openapi()["paths"]
    assert "/" + "ch" + "at" not in paths


def test_repository_page_displays_full_names_and_selects_only_listed_repos():
    from pathlib import Path
    page = (Path(__file__).resolve().parents[2] / "ai-coo-frontend/src/pages/github/GitHub.tsx").read_text()
    assert "repo.full_name" in page
    assert "githubService.listRepos" in page
    assert "githubService.connectRepo(orgId!, repoFullName)" in page
    assert "r.full_name.toLowerCase().includes(q)" in page
