from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def test_priorities_only_use_connected_repo_issues():
    from auth.dependencies import get_current_org_id
    from main import app

    with patch("main.supabase_admin") as sb, \
         patch("main.github_get_paginated", new_callable=AsyncMock) as get_issues, \
         patch("closeout._resolve_access_token", return_value="token"), \
         patch("main.run_gemini", return_value=MagicMock(text="1. Fix login")) as ai, \
         patch("main._rate_limit"):
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"github_repo": "acme/selected"}
        ]
        get_issues.return_value = [
            {"title": "Fix login", "created_at": "2026-01-01", "comments": 2},
            {"title": "A pull request", "pull_request": {"url": "https://github.com/pr"}},
        ]
        app.dependency_overrides[get_current_org_id] = lambda: "org-1"
        try:
            response = TestClient(app).get("/planner/priorities")
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    get_issues.assert_awaited_once_with(
        "https://api.github.com/repos/acme/selected/issues", "token", params={"state": "open"}
    )
    prompt = ai.call_args.args[0]
    assert "Fix login" in prompt
    assert "A pull request" not in prompt


def test_priorities_need_connected_repo():
    from auth.dependencies import get_current_org_id
    from main import app

    with patch("main.supabase_admin") as sb, \
         patch("main.github_get_paginated", new_callable=AsyncMock) as get_issues:
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"github_repo": None}
        ]
        app.dependency_overrides[get_current_org_id] = lambda: "org-1"
        try:
            response = TestClient(app).get("/planner/priorities")
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Enable events" in response.json()["priorities"]
    get_issues.assert_not_awaited()
