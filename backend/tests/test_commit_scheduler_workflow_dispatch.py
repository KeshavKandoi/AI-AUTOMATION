"""
Regression tests for Commit Scheduler dispatching events through the shared
workflow engine (dispatch_workflow_event) after a successful commit or PR,
so a Push/PR-triggered workflow (send_email, create_task, notify_discord,
create_calendar_event, save_audit_log) executes automatically -- without a
separate, hardcoded email/action implementation living in the scheduler.
"""
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from commit_scheduler import service


def run(coro):
    return asyncio.run(coro)


def _base_job(**overrides):
    job = {
        "id": "job-1",
        "organization_id": "org-A",
        "provider": "github",
        "repo_full_name": "acme/repo",
        "branch": "main",
        "folder_path": "notes",
        "file_name": "log.txt",
        "file_content": "hello",
        "commit_message": "auto commit",
        "mode": "scheduled",
        "use_pr": False,
    }
    job.update(overrides)
    return job


# ---------------------------------------------------------------------------
# Successful non-PR commit dispatches a push event with the real commit SHA
# ---------------------------------------------------------------------------

def test_successful_commit_dispatches_push_event_with_real_sha():
    job = _base_job()

    commit_result = {"sha": "realsha123", "html_url": "https://x", "commit_url": "https://x/commit"}
    fake_run = {"id": "run-1", "job_id": "job-1", "status": "success", "commit_sha": "realsha123"}

    with patch.object(service, "_get_github_token_for_org", return_value="gh-token"), \
         patch.object(service.repository, "get_run_for_date", return_value=None), \
         patch.object(service.repository, "create_run", return_value=fake_run) as mock_create_run, \
         patch.object(service.repository, "update_job"), \
         patch.object(service, "_resolve_files_for_run", new=AsyncMock(return_value=[{"folder_path": "notes", "file_name": "log.txt", "content": "hi"}])), \
         patch.object(service.git_ops, "get_provider") as mock_get_provider, \
         patch.object(service, "dispatch_workflow_event", new=AsyncMock()) as mock_dispatch:

        mock_provider = AsyncMock()
        mock_provider.get_file = AsyncMock(return_value=None)
        mock_provider.commit_file = AsyncMock(return_value=commit_result)
        mock_get_provider.return_value = mock_provider

        result = run(service.execute_job(job))

    assert result["status"] == "success"
    mock_dispatch.assert_called_once()
    called_org, called_trigger, called_context, kwargs = (
        mock_dispatch.call_args[0][0],
        mock_dispatch.call_args[0][1],
        mock_dispatch.call_args[0][2],
        mock_dispatch.call_args[1],
    )
    assert called_org == "org-A"
    assert called_trigger == "push"
    assert called_context["repo"] == "acme/repo"
    assert called_context["commit_sha"] == "realsha123"
    assert kwargs["event_key"] == "realsha123"


# ---------------------------------------------------------------------------
# Failed commit never dispatches anything
# ---------------------------------------------------------------------------

def test_failed_commit_does_not_dispatch():
    job = _base_job()

    with patch.object(service, "_get_github_token_for_org", side_effect=RuntimeError("no token")), \
         patch.object(service.repository, "get_run_for_date", return_value=None), \
         patch.object(service.repository, "create_run", return_value={"status": "failed"}), \
         patch.object(service, "dispatch_workflow_event", new=AsyncMock()) as mock_dispatch:
        result = run(service.execute_job(job))

    assert result["status"] == "failed"
    mock_dispatch.assert_not_called()


# ---------------------------------------------------------------------------
# Skip paths (no files staged) never dispatch anything
# ---------------------------------------------------------------------------

def test_no_files_staged_skip_does_not_dispatch():
    job = _base_job()

    with patch.object(service, "_get_github_token_for_org", return_value="gh-token"), \
         patch.object(service.repository, "get_run_for_date", return_value=None), \
         patch.object(service.repository, "create_run", return_value={"status": "skipped"}), \
         patch.object(service, "_resolve_files_for_run", new=AsyncMock(return_value=[])), \
         patch.object(service, "dispatch_workflow_event", new=AsyncMock()) as mock_dispatch:
        result = run(service.execute_job(job))

    assert result["status"] == "skipped"
    mock_dispatch.assert_not_called()


# ---------------------------------------------------------------------------
# use_pr mode dispatches pull_request_opened, not push
# ---------------------------------------------------------------------------

def test_use_pr_mode_dispatches_pull_request_opened_not_push():
    job = _base_job(use_pr=True)

    commit_result = {"sha": "prsha456", "html_url": "https://x", "commit_url": "https://x/commit"}
    pr_result = {"html_url": "https://github.com/acme/repo/pull/7", "number": 7, "status": "created"}
    fake_run = {"id": "run-2", "job_id": "job-1", "status": "success", "commit_sha": "prsha456"}

    with patch.object(service, "_get_github_token_for_org", return_value="gh-token"), \
         patch.object(service.repository, "get_run_for_date", return_value=None), \
         patch.object(service.repository, "create_run", return_value=fake_run), \
         patch.object(service.repository, "update_job"), \
         patch.object(service, "_resolve_files_for_run", new=AsyncMock(return_value=[{"folder_path": "notes", "file_name": "log.txt", "content": "hi"}])), \
         patch.object(service.git_ops, "get_provider") as mock_get_provider, \
         patch.object(service, "dispatch_workflow_event", new=AsyncMock()) as mock_dispatch:

        mock_provider = AsyncMock()
        mock_provider.get_file = AsyncMock(return_value=None)
        mock_provider.commit_file = AsyncMock(return_value=commit_result)
        mock_provider.create_branch = AsyncMock(return_value={"status": "created"})
        mock_provider.create_pull_request = AsyncMock(return_value=pr_result)
        mock_get_provider.return_value = mock_provider

        run(service.execute_job(job))

    mock_dispatch.assert_called_once()
    called_org, called_trigger, called_context, kwargs = (
        mock_dispatch.call_args[0][0],
        mock_dispatch.call_args[0][1],
        mock_dispatch.call_args[0][2],
        mock_dispatch.call_args[1],
    )
    assert called_org == "org-A"
    assert called_trigger == "pull_request_opened"
    assert called_context["pr_number"] == 7
    assert kwargs["event_key"] == "pr-7-prsha456"


# ---------------------------------------------------------------------------
# A dispatch failure never fails the commit job
# ---------------------------------------------------------------------------

def test_dispatch_failure_does_not_fail_the_commit_job():
    job = _base_job()

    commit_result = {"sha": "sha789", "html_url": "https://x", "commit_url": "https://x/commit"}
    fake_run = {"id": "run-3", "job_id": "job-1", "status": "success", "commit_sha": "sha789"}

    with patch.object(service, "_get_github_token_for_org", return_value="gh-token"), \
         patch.object(service.repository, "get_run_for_date", return_value=None), \
         patch.object(service.repository, "create_run", return_value=fake_run), \
         patch.object(service.repository, "update_job"), \
         patch.object(service, "_resolve_files_for_run", new=AsyncMock(return_value=[{"folder_path": "notes", "file_name": "log.txt", "content": "hi"}])), \
         patch.object(service.git_ops, "get_provider") as mock_get_provider, \
         patch.object(service, "dispatch_workflow_event", new=AsyncMock(side_effect=RuntimeError("dispatch exploded"))):

        mock_provider = AsyncMock()
        mock_provider.get_file = AsyncMock(return_value=None)
        mock_provider.commit_file = AsyncMock(return_value=commit_result)
        mock_get_provider.return_value = mock_provider

        result = run(service.execute_job(job))

    # The commit job itself must still report success -- a dispatch failure
    # is logged internally (_dispatch_push_workflow_event catches it) and
    # must never surface as a commit-job failure.
    assert result["status"] == "success"
    assert result["commit_sha"] == "sha789"


# ---------------------------------------------------------------------------
# End-to-end through the REAL dispatch_workflow_event (not mocked): scheduler
# dispatch and a simulated webhook dispatch for the identical commit SHA
# must result in run_workflows executing only once.
# ---------------------------------------------------------------------------

def test_scheduler_and_webhook_dispatch_for_same_commit_execute_workflow_only_once():
    import workflow_engine

    job = _base_job()
    fake_run = {"id": "run-4", "job_id": "job-1", "status": "success", "commit_sha": "shared-sha-999"}

    call_log = []

    def fake_record_event_if_new(organization_id, repo_full_name, event_type, event_key):
        key = (organization_id, repo_full_name, event_type, event_key)
        if key in call_log:
            return False
        call_log.append(key)
        return True

    with patch.object(workflow_engine, "_record_event_if_new", side_effect=fake_record_event_if_new), \
         patch.object(workflow_engine, "run_workflows", new=AsyncMock()) as mock_run_workflows:

        # First: Commit Scheduler's own dispatch for this commit.
        run(service._dispatch_push_workflow_event(job, fake_run))
        # Second: a real GitHub webhook arriving for the SAME commit SHA
        # (simulated directly via dispatch_workflow_event, as webhooks/routes.py would call it).
        run(workflow_engine.dispatch_workflow_event(
            "org-A", "push", {"repo": "acme/repo", "commit_sha": "shared-sha-999"}, event_key="shared-sha-999"
        ))

    assert mock_run_workflows.call_count == 1
