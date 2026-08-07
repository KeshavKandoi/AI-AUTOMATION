from datetime import datetime, timezone
import httpx

from config import logger
from job_hunter import repository
from job_hunter.platforms.base import BaseJobProvider, RawJob, RateLimiter, retry_with_backoff, ProviderError
from job_hunter.platforms.matching import matches_preferences, normalize_employment_type
from job_hunter.platforms.registry import register_provider


class LeverProvider(BaseJobProvider):
    platform = "lever"
    method = "api"

    def __init__(self):
        self._rate_limiter = RateLimiter(min_interval_seconds=0.5)

    async def search(self, organization_id: str, preferences: dict) -> list[RawJob]:
        companies = repository.list_enabled_companies("lever")
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
                    logger.warning(f"[lever] {company['company_name']} ({company['board_token']}) sync failed: {e}")
                    repository.mark_company_sync_status(company["id"], status)
                    continue

                for job in jobs:
                    title = job.get("text", "")
                    categories = job.get("categories", {}) or {}
                    location = categories.get("location", "") or ""
                    employment_type = normalize_employment_type(categories.get("commitment"))
                    description = job.get("descriptionPlain") or job.get("description") or ""

                    if not matches_preferences(
                        preferences, title=title, description=description,
                        location=location, employment_type=employment_type or "",
                    ):
                        continue

                    posted_at = None
                    if job.get("createdAt"):
                        try:
                            posted_at = datetime.fromtimestamp(job["createdAt"] / 1000, tz=timezone.utc).isoformat()
                        except (ValueError, OSError):
                            posted_at = None

                    apply_url = job.get("applyUrl") or job.get("hostedUrl", "")
                    results.append(RawJob(
                        company_name=company["company_name"],
                        job_title=title,
                        original_apply_url=apply_url,
                        platform="lever",
                        platform_url=job.get("hostedUrl", apply_url),
                        platform_job_id=job.get("id"),
                        location=location or None,
                        employment_type=employment_type,
                        description=description[:5000] if description else None,
                        posted_at=posted_at,
                    ))

        return results

    async def _fetch_company_jobs(self, client: httpx.AsyncClient, company: dict) -> list[dict]:
        url = f"https://api.lever.co/v0/postings/{company['board_token']}"
        res = await client.get(url, params={"mode": "json"})
        if res.status_code == 404:
            raise ProviderError(f"404 not found for board token '{company['board_token']}'")
        if res.status_code != 200:
            raise ProviderError(f"HTTP {res.status_code} for '{company['board_token']}'")
        data = res.json()
        return data if isinstance(data, list) else []


register_provider(LeverProvider())
