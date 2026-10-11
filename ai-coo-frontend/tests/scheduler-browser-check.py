"""Run against `npm run dev -- --host 127.0.0.1` with Playwright installed.

All API calls are intercepted. Run Now is deliberately never sent to a backend.
"""
from datetime import datetime, timedelta
import os
from playwright.sync_api import sync_playwright

USER = {
    "id": "test-user", "email": "test@example.invalid", "full_name": "Test User",
    "organization_id": "test-org", "organization_name": "Test Org", "created_at": "2026-01-01T00:00:00Z",
}


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=os.environ.get("PLAYWRIGHT_CHROME_PATH"))
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        errors = []
        state = {"jobs": []}
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" and "422 (Unprocessable Entity)" not in message.text else None)

        def mock_api(route):
            request = route.request
            if request.url.startswith("http://127.0.0.1:5173/"):
                return route.continue_()
            path = request.url.split("?", 1)[0]
            if path.endswith("/auth/refresh"):
                return route.fulfill(json={"user": USER, "access_token": "local-test-token"})
            if "/notifications" in path:
                return route.fulfill(json={"items": [], "total": 0, "unread_count": 0})
            if path.endswith("/commit-jobs/meta/repos"):
                return route.fulfill(json=[{"full_name": "test/repo", "name": "repo", "default_branch": "main"}])
            if path.endswith("/commit-jobs/meta/branches"):
                return route.fulfill(json=[{"name": "main"}])
            if path.endswith("/commit-jobs") and request.method == "GET":
                return route.fulfill(json=state["jobs"])
            if path.endswith("/commit-jobs") and request.method == "POST":
                return route.fulfill(status=422, json={"detail": [{"type": "value_error", "loc": ["body", "execution_at"], "msg": "Execution time is invalid", "input": "test", "ctx": {}}]})
            if "/commit-jobs/" in path and request.method == "PATCH":
                import json
                state["jobs"][0].update(json.loads(request.post_data or "{}"))
                return route.fulfill(json={"status": "updated", "job": state["jobs"][0]})
            if path.endswith("/commit-jobs/job-1"):
                return route.fulfill(json={**state["jobs"][0], "runs": []})
            if path.endswith("/commit-jobs/job-1/files"):
                return route.fulfill(json=[])
            if path.endswith("/commit-jobs/job-1/run-now"):
                return route.fulfill(json={"status": "triggered", "run": {"id": "mock-run", "job_id": "job-1", "run_date": "2026-10-11", "status": "skipped", "commit_sha": None, "commit_url": None, "error_message": None, "executed_at": "2026-10-11T00:00:00Z"}})
            if path.endswith("/workflows"):
                return route.fulfill(json=[])
            return route.fulfill(json={})

        page.route("**/*", mock_api)
        page.goto("http://127.0.0.1:5173/commit-scheduler")
        page.get_by_role("heading", name="Commit Scheduler").wait_for()
        page.get_by_role("button", name="New scheduled commit").click()
        page.get_by_role("combobox").first.select_option("test/repo")
        page.get_by_role("combobox").nth(1).select_option("main")
        page.get_by_role("textbox", name="Commit message").fill("Test commit")
        future = datetime.now() + timedelta(days=1)
        page.locator('input[type="datetime-local"]').fill(future.strftime("%Y-%m-%dT%H:%M"))
        page.get_by_role("button", name="Create scheduled commit").click()
        page.get_by_text("Execution time is invalid").wait_for()
        assert page.get_by_role("heading", name="Commit Scheduler").is_visible()
        assert not errors, errors
        page.keyboard.press("Escape")
        page.locator('a[href="/workflows"]').evaluate('(link) => link.click()')
        assert page.url.endswith('/workflows')
        page.locator('a[href="/commit-scheduler"]').evaluate('(link) => link.click()')
        page.get_by_role("heading", name="Commit Scheduler").wait_for()
        assert not errors, errors
        state["jobs"] = [{"id": "job-1", "organization_id": "test-org", "provider": "github", "repo_full_name": "test/repo", "branch": "main", "folder_path": None, "file_name": None, "file_content": None, "commit_message": "Test commit", "start_date": None, "end_date": None, "frequency": "daily", "custom_dates": None, "execution_at": future.isoformat(), "mode": "scheduled", "guard_cutoff_time": "23:30:00", "use_pr": False, "status": "active", "created_at": "2026-10-11T00:00:00Z", "updated_at": "2026-10-11T00:00:00Z"}]
        page.reload()
        page.get_by_role("button", name="test/repo").wait_for()
        page.get_by_role("button", name="Edit").click()
        page.get_by_role("textbox", name="Commit message").fill("Edited commit")
        page.get_by_role("button", name="Save changes").click()
        page.get_by_role("button", name="Pause").click()
        page.get_by_role("button", name="Resume").wait_for()
        page.get_by_role("button", name="Details").click()
        page.get_by_role("button", name="Run now").click()
        page.get_by_text("Run skipped").wait_for()
        assert not errors, errors
        print("scheduler direct/in-app navigation, create error, list, edit, pause, and mocked Run Now passed")
        browser.close()


if __name__ == "__main__":
    main()
