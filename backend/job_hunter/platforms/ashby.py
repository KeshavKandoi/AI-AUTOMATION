import httpx

from config import logger
from job_hunter import repository
from job_hunter.platforms.base import BaseJobProvider, RawJob, RateLimiter, retry_with_backoff, ProviderError
from job_hunter.platforms.matching import normalize_employment_type, normalize_work_mode
from job_hunter.platforms.registry import register_provider


class AshbyProvider(BaseJobProvider):
    platform = "ashby"
    method = "api"

    def __init__(self):
        self._rate_limiter = RateLimiter(min_interval_seconds=0.5)

    async def search(self, organization_id: str, preferences: dict) -> list[RawJob]:
        companies = repository.list_enabled_companies("ashby")
        results: list[RawJob] = []

        async with httpx.AsyncClient(timeout=20) as client:
            for company in companies:
                await self._rate_limiter.wait()
                try:
                    jobs = await retry_with_backoff(
                        lambda c=company: self._fetch_company_jobs(client, c),
                        max_attempts=2,
                        base_delay_seconds=1.0,
                        retry_on=(ProviderError, httpx.HTTPError),
                    )
                    repository.mark_company_sync_status(company["id"], "ok")
                except Exception as e:
                    status = "not_found" if "404" in str(e) else "error"
                    logger.warning(f"[ashby] {company['company_name']} ({company['board_token']}) sync failed: {e}")
                    repository.mark_company_sync_status(company["id"], status)
                    continue

                for job in jobs:
                    title = job.get("title", "")
                    location = job.get("location", "") or ""
                    if job.get("isRemote") and "remote" not in location.lower():
                        location = f"{location} (Remote)".strip()
                    work_mode = normalize_work_mode("Remote") if job.get("isRemote") else None
                    employment_type = normalize_employment_type(job.get("employmentType"))
                    description = job.get("descriptionPlain", "") or ""

                    # ARCHITECTURE CHANGE: preference matching removed from
                    # discovery. Every technically valid parsed job (has a
                    # title, real IDs, etc.) is stored regardless of whether
                    # it matches this org's CURRENT desired_roles/skills/
                    # work_modes/etc. User-specific filtering now happens
                    # only at query time via service.list_jobs() /
                    # repository.list_jobs(), against the database -- never
                    # during scraping. matches_preferences() is kept in
                    # matching.py (unused here) in case it's needed
                    # elsewhere later.
                    apply_url = job.get("applyUrl") or job.get("jobUrl", "")
                    results.append(RawJob(
                        company_name=company["company_name"],
                        job_title=title,
                        original_apply_url=apply_url,
                        platform="ashby",
                        platform_url=job.get("jobUrl", apply_url),
                        platform_job_id=job.get("id"),
                        location=location or None,
                        work_mode=work_mode,
                        employment_type=employment_type,
                        description=description[:5000] if description else None,
                        posted_at=job.get("publishedAt"),
                    ))

        return results

    async def _fetch_company_jobs(self, client: httpx.AsyncClient, company: dict) -> list[dict]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{company['board_token']}"
        res = await client.get(url)
        if res.status_code == 404:
            raise ProviderError(f"404 not found for board token '{company['board_token']}'")
        if res.status_code != 200:
            raise ProviderError(f"HTTP {res.status_code} for '{company['board_token']}'")
        return res.json().get("jobs", [])


register_provider(AshbyProvider())
