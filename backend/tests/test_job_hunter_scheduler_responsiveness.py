import asyncio
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from job_hunter import scheduler_jobs


def test_job_search_does_not_block_web_event_loop():
    async def blocking_sweep():
        time.sleep(0.08)
        return {"complete": True}

    async def check():
        task = asyncio.create_task(scheduler_jobs.run_search_for_all_orgs_background())
        await asyncio.sleep(0.01)
        assert not task.done(), "The web event loop should keep running during a sweep"
        assert await task == {"complete": True}

    with patch.object(scheduler_jobs, "run_search_for_all_orgs", blocking_sweep):
        asyncio.run(check())


def test_stale_job_cleanup_runs_with_no_eligible_organizations():
    with patch.object(scheduler_jobs.repository, "list_orgs_with_recent_successful_search", return_value=[]):
        result = asyncio.run(scheduler_jobs.run_stale_job_cleanup())
    assert result["deleted"] == 0


def test_daily_search_is_not_repeated_after_free_service_restart():
    now = datetime.now(timezone.utc)
    recent = {"started_at": (now - timedelta(hours=1)).isoformat(), "status": "failed"}
    old = {"started_at": (now - timedelta(hours=25)).isoformat(), "status": "success"}

    async def search_org(org_id):
        return {"org_id": org_id}

    with patch.object(scheduler_jobs.repository, "list_orgs_with_preferences", return_value=["recent", "old"]), \
         patch.object(scheduler_jobs.repository, "get_latest_search_run", side_effect=[recent, old]), \
         patch.object(scheduler_jobs, "run_search_for_org", side_effect=search_org) as search:
        result = asyncio.run(scheduler_jobs.run_search_for_all_orgs())

    assert result["recent"] == {"skipped": True, "reason": "searched_within_24_hours"}
    assert result["old"] == {"org_id": "old"}
    search.assert_called_once_with("old")
