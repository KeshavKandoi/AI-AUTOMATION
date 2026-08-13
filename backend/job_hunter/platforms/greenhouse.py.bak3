import re
from typing import Optional
import httpx

from config import logger
from job_hunter import repository
from job_hunter.platforms.base import BaseJobProvider, RawJob, RateLimiter, retry_with_backoff, ProviderError
from job_hunter.platforms.matching import matches_preferences, normalize_work_mode
from job_hunter.platforms.registry import register_provider


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:5000]


# Explicit-only phrases. Matched against the structured location string
# first, then the stripped job description -- never inferred from a bare
# country/region name like "United States", "Worldwide", or "Anywhere",
# which are NOT reliable remote signals on their own.
_GREENHOUSE_WORK_MODE_PATTERNS = [
    (re.compile(r"\bfully\s+remote\b", re.IGNORECASE), "Remote"),
    (re.compile(r"\bremote\b", re.IGNORECASE), "Remote"),
    (re.compile(r"\bhybrid\b", re.IGNORECASE), "Hybrid"),
    (re.compile(r"\bon-?site\b", re.IGNORECASE), "On-site"),
    (re.compile(r"\bin-?office\b", re.IGNORECASE), "On-site"),
]


def _extract_work_mode(location: str, description: str) -> Optional[str]:
    """Scans the structured location string first, then the stripped job
    description, for an explicit work-mode phrase. Returns None (never
    guesses) when neither contains one of these unambiguous signals."""
    for text in (location or "", (description or "")[:2000]):
        for pattern, mode in _GREENHOUSE_WORK_MODE_PATTERNS:
            if pattern.search(text):
                return normalize_work_mode(mode)
    return None


class GreenhouseProvider(BaseJobProvider):
    platform = "greenhouse"
    method = "api"

    def __init__(self):
        self._rate_limiter = RateLimiter(min_interval_seconds=0.5)

    async def search(self, organization_id: str, preferences: dict) -> list[RawJob]:
        companies = repository.list_enabled_companies("greenhouse")
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
                    logger.warning(f"[greenhouse] {company['company_name']} ({company['board_token']}) sync failed: {e}")
                    repository.mark_company_sync_status(company["id"], status)
                    continue

                for job in jobs:
                    title = job.get("title", "")
                    location = (job.get("location") or {}).get("name", "")
                    description_html = job.get("content", "") or ""
                    description = _strip_html(description_html)
                    work_mode = _extract_work_mode(location, description)

                    if not matches_preferences(
                        preferences, title=title, description=description,
                        location=location, work_mode=work_mode,
                    ):
                        continue

                    url = job.get("absolute_url", "")
                    results.append(RawJob(
                        company_name=company["company_name"],
                        job_title=title,
                        original_apply_url=url,
                        platform="greenhouse",
                        platform_url=url,
                        platform_job_id=str(job.get("id", "")),
                        location=location or None,
                        work_mode=work_mode,
                        description=description or None,
                        posted_at=job.get("updated_at"),
                    ))

        return results

    async def _fetch_company_jobs(self, client: httpx.AsyncClient, company: dict) -> list[dict]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company['board_token']}/jobs"
        res = await client.get(url, params={"content": "true"})
        if res.status_code == 404:
            raise ProviderError(f"404 not found for board token '{company['board_token']}'")
        if res.status_code != 200:
            raise ProviderError(f"HTTP {res.status_code} for '{company['board_token']}'")
        return res.json().get("jobs", [])


register_provider(GreenhouseProvider())
