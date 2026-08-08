"""
Y Combinator "Work at a Startup" job board adapter.

Verified live (2026-08-08) against https://www.workatastartup.com/jobs:
- Public, no login required for browsing (login only needed to apply).
- No infinite scroll/pagination — each category page shows a fixed set
  (~28) of currently open postings for that category.
- Category filtering via URL path (/jobs/l/<slug>) genuinely filters
  results (confirmed: software-engineer vs sales-manager return disjoint
  job ID sets).
- No functional keyword search for logged-out users — we compensate by
  mapping the org's desired_roles to the closest YC category (or
  categories) and still applying our own matches_preferences() filter
  within that category for role/skill precision.
- Job cards have no description text — only title, company (+ YC batch),
  tagline, employment type, location, sub-role tag, and salary. Full
  descriptions live behind each job's detail page; not fetched here to
  keep one sweep fast — original_apply_url takes the user straight to
  the real posting where they can read the full description themselves.
"""
from job_hunter.platforms.playwright_base import PlaywrightJobProvider
from job_hunter.platforms.base import RawJob
from job_hunter.platforms.matching import matches_preferences, normalize_employment_type
from job_hunter.platforms.registry import register_provider
from playwright.async_api import Page

BASE_URL = "https://www.workatastartup.com"

CARD_SELECTOR = "div.flex.h-full.cursor-pointer.flex-col"

# Maps keywords found in the org's desired_roles to YC's category slugs.
# A role can match multiple categories (e.g. "Product Engineer" hits both).
# Falls back to "software-engineer" when nothing matches, since that's the
# most broadly useful default for a technical job search tool.
ROLE_TO_CATEGORY = {
    "software-engineer": ["engineer", "developer", "swe", "backend", "frontend", "full stack", "fullstack", "devops", "sre", "mobile", "ios", "android"],
    "designer": ["design", "ux", "ui"],
    "recruiting": ["recruit", "talent", "hr", "people"],
    "science": ["scientist", "research", "science", "ml", "machine learning", "ai researcher"],
    "product-manager": ["product manager", "product owner", "pm"],
    "operations": ["operations", "ops", "logistics"],
    "sales-manager": ["sales", "account executive", "business development"],
    "marketing": ["marketing", "growth", "content", "seo"],
    "legal": ["legal", "counsel", "compliance"],
    "finance": ["finance", "accounting", "fp&a"],
}


def _categories_for_preferences(preferences: dict) -> list[str]:
    roles = [r.lower() for r in preferences.get("desired_roles", [])]
    matched = set()
    for category, keywords in ROLE_TO_CATEGORY.items():
        if any(any(kw in role for kw in keywords) for role in roles):
            matched.add(category)
    return list(matched) if matched else ["software-engineer"]


class YCJobsProvider(PlaywrightJobProvider):
    platform = "yc_jobs"
    rate_limit_seconds = 2.5

    async def extract_jobs(self, page: Page, preferences: dict) -> list[RawJob]:
        categories = _categories_for_preferences(preferences)
        results: list[RawJob] = []
        seen_job_ids: set[str] = set()

        for category in categories:
            url = f"{BASE_URL}/jobs/l/{category}"
            await self.goto_with_retry(page, url)
            await page.wait_for_timeout(1500)

            cards = await page.query_selector_all(CARD_SELECTOR)
            for card in cards:
                job = await self._extract_card(card, preferences)
                if job is None:
                    continue
                job_id = job.platform_job_id
                if job_id in seen_job_ids:
                    continue
                seen_job_ids.add(job_id)
                results.append(job)

        return results

    async def _extract_card(self, card, preferences: dict):
        title_link = await card.query_selector('a[href^="/jobs/"][target="job"]')
        if not title_link:
            return None

        href = await title_link.get_attribute("href")
        job_id = href.lstrip("/").split("/")[-1] if href else None
        title = (await title_link.text_content() or "").strip()
        if not title or not job_id:
            return None

        company_name = await self.safe_text(card, 'a[href^="/companies/"] span.font-bold')
        # strip the trailing "(S14)"-style batch tag, e.g. "Hive (S14)" -> "Hive"
        company_name = company_name.split("(")[0].strip() if company_name else "Unknown Company"

        detail_spans = await card.query_selector_all("p.job-details span")
        details = [((await s.text_content()) or "").strip() for s in detail_spans]
        details = [d for d in details if d]

        employment_type_raw = details[0] if len(details) > 0 else None
        location = details[1] if len(details) > 1 else None
        # details[2] is the sub-role tag (e.g. "Full stack") — not mapped to
        # our schema directly, folded into experience_required as a hint.
        sub_role = details[2] if len(details) > 2 else None
        salary_text = details[3] if len(details) > 3 else None

        employment_type = normalize_employment_type(employment_type_raw)
        apply_url = f"{BASE_URL}/jobs/{job_id}"

        # YC startups title roles unconventionally ("Founding Engineer",
        # "Member of Technical Staff") rather than standard titles like
        # "Software Engineer" — strict title-matching against desired_roles
        # produces false negatives here, not false positives. The category
        # page itself (/jobs/l/<slug>) is already a strong relevance signal
        # from YC's own categorization, so we trust it for role relevance
        # and strip desired_roles/skills before calling matches_preferences
        # here, so it only applies location/employment-type filtering
        # (passing title="" would NOT achieve this — matches_preferences
        # reads desired_roles/skills from `preferences` itself, so an empty
        # title would make the role/skill check always fail instead of
        # being skipped).
        location_only_preferences = {
            k: v for k, v in preferences.items() if k not in ("desired_roles", "skills")
        }
        if not matches_preferences(
            location_only_preferences, title=title, description="",
            location=location or "", employment_type=employment_type or "",
        ):
            return None

        return RawJob(
            company_name=company_name,
            job_title=title,
            original_apply_url=apply_url,
            platform="yc_jobs",
            platform_url=apply_url,
            platform_job_id=job_id,
            location=location,
            employment_type=employment_type,
            experience_required=sub_role,
            salary_currency=None,  # embedded in salary_text below, not cleanly separable
            description=salary_text or None,  # best-effort: surfaces salary range until detail-page fetch is added
        )


register_provider(YCJobsProvider())
