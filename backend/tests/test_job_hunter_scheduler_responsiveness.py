import asyncio
import time
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
