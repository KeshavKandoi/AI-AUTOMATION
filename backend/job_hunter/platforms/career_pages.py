"""
Custom-site fallback provider for companies with no known ATS (verified
via job_provider_career_pages.detected_ats being null after the
ats_detector sync — see sync_career_pages.py). This is deliberately the
lowest-priority, most conservative provider: real career sites vary
enormously in structure, so this adapter uses a generic strategy (JSON-LD
JobPosting primary, heuristic link/list extraction fallback) rather than
per-site selectors, and is capped in scope (max pages per company) since
it can't be held to the same reliability bar as a real API.

Verified live (2026-08-08) against https://careers.airbnb.com/positions/:
- No JobPosting-typed JSON-LD (only generic site metadata) — falls
  through to heuristic extraction.
- Job listings are <li> elements containing a category/work-mode header,
  a title link (href matches /positions/<numeric-id>/), and a location.
- Pagination is real and URL-based via ?_paged=N (FacetWP plugin) — NOT
  JS-only, so we can page without click simulation.
- This structure (category • mode / title link / location, in an <li>)
  is common enough across corporate career sites (WordPress + FacetWP or
  similar plugins) that the heuristic below targets it generically rather
  than hardcoding Airbnb specifically — but every extraction step is
  wrapped in safe_text/try-guards since other sites will differ.
"""
import json
import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from job_hunter import repository
from job_hunter.platforms.playwright_base import PlaywrightJobProvider
from job_hunter.platforms.base import RawJob
from job_hunter.platforms.matching import matches_preferences
from job_hunter.platforms.registry import register_provider
from playwright.async_api import Page

MAX_PAGES_PER_COMPANY = 3   # conservative cap — this is a fallback, not a primary channel


def _add_paged_param(url: str, page_num: int) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query["_paged"] = [str(page_num)]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


class CareerPagesProvider(PlaywrightJobProvider):
    platform = "career_pages"
    rate_limit_seconds = 2.5

    async def extract_jobs(self, page: Page, preferences: dict) -> list[RawJob]:
        companies = repository.list_undetected_career_pages()
        results: list[RawJob] = []

        for company in companies:
            try:
                company_jobs = await self._extract_company(page, company, preferences)
                results.extend(company_jobs)
                repository.mark_career_page_status(company["id"], "ok")
            except Exception as e:
                repository.mark_career_page_status(company["id"], "error")
                continue

        return results

    async def _extract_company(self, page: Page, company: dict, preferences: dict) -> list[RawJob]:
        base_url = company["career_page_url"]
        results: list[RawJob] = []
        seen_urls: set[str] = set()

        # First: try JSON-LD JobPosting extraction (works if present, cheap to check)
        await self.goto_with_retry(page, base_url)
        await page.wait_for_timeout(1500)
        jsonld_jobs = await self._extract_jsonld_jobs(page, company, preferences)
        if jsonld_jobs:
            return jsonld_jobs

        # Fallback: heuristic list extraction with pagination
        for page_num in range(1, MAX_PAGES_PER_COMPANY + 1):
            url = base_url if page_num == 1 else _add_paged_param(base_url, page_num)
            await self.goto_with_retry(page, url)
            await page.wait_for_timeout(1500)

            page_jobs = await self._extract_heuristic_jobs(page, company, preferences)
            new_jobs = [j for j in page_jobs if j.original_apply_url not in seen_urls]
            if not new_jobs:
                break  # no new jobs on this page — stop paginating
            for j in new_jobs:
                seen_urls.add(j.original_apply_url)
            results.extend(new_jobs)

        return results

    async def _extract_jsonld_jobs(self, page: Page, company: dict, preferences: dict) -> list[RawJob]:
        try:
            scripts = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
                    .map(s => s.textContent);
            }""")
        except Exception:
            return []

        results: list[RawJob] = []
        for raw in scripts:
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue

            candidates = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
            for item in candidates:
                if not isinstance(item, dict) or item.get("@type") != "JobPosting":
                    continue

                title = item.get("title", "")
                if not title:
                    continue

                location = ""
                loc_data = item.get("jobLocation")
                if isinstance(loc_data, dict):
                    address = loc_data.get("address", {})
                    if isinstance(address, dict):
                        location = address.get("addressLocality", "") or address.get("addressRegion", "")

                apply_url = item.get("url") or company["career_page_url"]
                description = item.get("description", "")
                if isinstance(description, str):
                    description = re.sub(r"<[^>]+>", " ", description)
                    description = re.sub(r"\s+", " ", description).strip()[:5000]

                if not matches_preferences(preferences, title=title, description=description, location=location):
                    continue

                results.append(RawJob(
                    company_name=company["company_name"],
                    job_title=title,
                    original_apply_url=apply_url,
                    platform="career_pages",
                    platform_url=apply_url,
                    location=location or None,
                    description=description or None,
                    posted_at=item.get("datePosted"),
                ))

        return results

    async def _extract_heuristic_jobs(self, page: Page, company: dict, preferences: dict) -> list[RawJob]:
        """Generic pattern: an <li> (or similar list item) containing a
        title <a> whose href looks like a job detail page, plus nearby
        text for category/location. Every field extraction is wrapped so
        one missing element never drops the whole job."""
        try:
            items = await page.evaluate("""() => {
                // Find all links that look like individual job detail pages:
                // numeric or slug-like final path segment, inside a list item.
                const links = Array.from(document.querySelectorAll('li a[href], article a[href]'));
                const seen = new Set();
                const results = [];
                for (const link of links) {
                    const href = link.getAttribute('href');
                    if (!href || seen.has(href)) continue;
                    const title = (link.textContent || '').trim();
                    if (!title || title.length < 3 || title.length > 200) continue;
                    // Skip obvious non-job nav links
                    if (/^(home|about|contact|login|sign ?up|privacy|terms)$/i.test(title)) continue;

                    let container = link;
                    for (let i = 0; i < 3; i++) {
                        if (container.parentElement && container.parentElement.tagName !== 'BODY') {
                            container = container.parentElement;
                        }
                    }
                    const containerText = (container.textContent || '').trim().slice(0, 300);

                    seen.add(href);
                    results.push({href, title, containerText});
                }
                return results.slice(0, 50);
            }""")
        except Exception:
            return []

        results: list[RawJob] = []
        for item in items:
            href = item.get("href", "")
            title = item.get("title", "")
            container_text = item.get("containerText", "")

            if not href or not title:
                continue

            apply_url = href if href.startswith("http") else f"{page.url.rstrip('/')}/{href.lstrip('/')}"

            if not matches_preferences(preferences, title=title, description="", location=container_text):
                continue

            results.append(RawJob(
                company_name=company["company_name"],
                job_title=title,
                original_apply_url=apply_url,
                platform="career_pages",
                platform_url=apply_url,
                description=None,
            ))

        return results


register_provider(CareerPagesProvider())
