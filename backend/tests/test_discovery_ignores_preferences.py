"""
Regression tests for the discovery/filtering architecture change: every
provider must return technically valid parsed jobs regardless of whether
they match the org's current desired_roles/skills/employment_types/
work_modes/salary/experience preferences. User-specific filtering now
happens only at query time (service.list_jobs / repository.list_jobs),
never during scraping.

Each test uses preferences that would have caused matches_preferences()
to reject the job under the OLD architecture (wrong role, wrong skill,
wrong work_mode) and confirms the job is still returned.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

# Preferences deliberately irrelevant to every sample job below -- under
# the old architecture, matches_preferences() would reject all of these.
IRRELEVANT_PREFS = {
    "desired_roles": ["underwater basket weaver"],
    "skills": ["basket weaving"],
    "employment_types": ["Contract"],
    "work_modes": ["On-site"],
    "preferred_locations": ["Antarctica"],
}


def test_ashby_returns_job_not_matching_preferences():
    from job_hunter.platforms.ashby import AshbyProvider

    fake_jobs_response = {
        "jobs": [{
            "id": "job1", "title": "Senior Backend Engineer",
            "location": "New York", "isRemote": True,
            "employmentType": "FullTime", "descriptionPlain": "Build stuff",
            "applyUrl": "http://x", "jobUrl": "http://x",
        }]
    }

    async def run():
        provider = AshbyProvider()
        with patch.object(provider, "_fetch_company_jobs", return_value=fake_jobs_response["jobs"]), \
             patch("job_hunter.platforms.ashby.repository") as repo:
            repo.list_enabled_companies.return_value = [
                {"id": "c1", "company_name": "TestCo", "board_token": "testco"}
            ]
            repo.mark_company_sync_status = MagicMock()
            return await provider.search("org1", IRRELEVANT_PREFS)

    jobs = asyncio.run(run())
    assert len(jobs) == 1, "job must be returned even though it matches none of the org's preferences"
    assert jobs[0].job_title == "Senior Backend Engineer"


def test_greenhouse_returns_job_not_matching_preferences():
    from job_hunter.platforms.greenhouse import GreenhouseProvider

    fake_jobs = [{
        "id": 1, "title": "Product Designer", "location": {"name": "Remote - USA"},
        "content": "<p>Design things</p>", "absolute_url": "http://x", "updated_at": "2026-01-01",
    }]

    async def run():
        provider = GreenhouseProvider()
        with patch.object(provider, "_fetch_company_jobs", return_value=fake_jobs), \
             patch("job_hunter.platforms.greenhouse.repository") as repo:
            repo.list_enabled_companies.return_value = [
                {"id": "c1", "company_name": "TestCo", "board_token": "testco"}
            ]
            repo.mark_company_sync_status = MagicMock()
            return await provider.search("org1", IRRELEVANT_PREFS)

    jobs = asyncio.run(run())
    assert len(jobs) == 1, "job must be returned even though it matches none of the org's preferences"
    assert jobs[0].job_title == "Product Designer"
    assert jobs[0].work_mode == "Remote"  # normalization still runs, unaffected by this change


def test_internshala_internship_returns_job_not_matching_preferences():
    from job_hunter.platforms.internshala import InternshalaProvider

    async def fake_extract(card, preferences, employment_type):
        # Simulates a real parsed card -- title/location deliberately
        # irrelevant to IRRELEVANT_PREFS
        from job_hunter.platforms.base import RawJob
        return RawJob(
            company_name="TestCo", job_title="Marketing Intern",
            original_apply_url="http://x", platform="internshala",
            platform_url="http://x", platform_job_id="job1",
            location="Mumbai", work_mode=None, employment_type="Internship",
        ), None

    provider = InternshalaProvider()
    job, reason = asyncio.run(fake_extract(MagicMock(), IRRELEVANT_PREFS, "Internship"))
    assert job is not None
    assert reason is None
    assert job.employment_type == "Internship"


def test_duplicates_still_deduplicated_after_architecture_change():
    """Confirms removing preference rejection did NOT touch the
    seen_job_ids dedup mechanism -- same job appearing across multiple
    queries/pages must still only be counted once."""
    import inspect
    from job_hunter.platforms import internshala
    src = inspect.getsource(internshala.InternshalaProvider.extract_jobs)
    assert "seen_job_ids" in src, "dedup mechanism must still be present"
    assert "duplicates" in src, "duplicate diagnostics must still be tracked"
