"""
Internshala job board adapter — searches both /jobs/ (full-time roles)
and /internships/ (internships), since Student/Fresher personas
(explicitly supported in onboarding) are underserved by jobs-only search.

Verified live (2026-08-08) against https://internshala.com/jobs/ and
https://internshala.com/internships/:
- Both are public, no login required for browsing.
- Same card structure ([internshipid], a.job-title-href, .company-name,
  .about_job .text, .job_skill) on both listing types — genuinely
  reusable extraction, not superficially similar.
- Real keyword search on both: /jobs/keywords-<term>/ and
  /internships/keywords-<term>/ (confirmed relevant results on both).
- Detail URL differs: /job/detail/... vs /internship/detail/... (both
  come through data-href on the card, so no special-casing needed there).
- Internship cards report a stipend (monthly, via .stipend span) and a
  duration ("6 Months", via a calendar-icon .row-1-item) instead of
  salary/experience. These are semantically different from annual salary
  and years-of-experience — deliberately NOT mapped into salary_min/max
  or experience_required (which would corrupt salary-based filtering:
  a real ₹10k/month stipend would look like an absurd "annual salary" and
  get wrongly rejected against any real expectation). Stipend and
  duration are folded into the description text instead, which is the
  correct place for free-text info the schema doesn't model.
- Pagination via /jobs/page-N/ and /internships/page-N/ (same pattern,
  confirmed working on /jobs/ earlier; consistent site-wide convention).
"""
import re
from urllib.parse import quote

from job_hunter.platforms.playwright_base import PlaywrightJobProvider
from job_hunter.platforms.base import RawJob
from job_hunter.platforms.matching import matches_preferences, normalize_employment_type
from job_hunter.platforms.registry import register_provider
from playwright.async_api import Page

BASE_URL = "https://internshala.com"
MAX_PAGES_PER_ROLE = 2   # 50 cards/page — 2 pages per role keeps a multi-role sweep reasonable
MAX_ROLES_PER_SWEEP = 5  # cap distinct role searches per org per run

# Which listing types to search, and their URL path segment / employment type.
LISTING_TYPES = [
    {"path": "jobs", "employment_type": "Full-time"},
    {"path": "internships", "employment_type": "Internship"},
]


class InternshalaProvider(PlaywrightJobProvider):
    platform = "internshala"
    rate_limit_seconds = 2.0

    async def extract_jobs(self, page: Page, preferences: dict) -> list[RawJob]:
        roles = preferences.get("desired_roles", [])[:MAX_ROLES_PER_SWEEP]
        if not roles:
            return []

        # Only search internships if the user's preferences actually
        # include "Internship" as a desired employment type — searching
        # internships for a user who only wants Full-time would just
        # waste requests on results that will always be filtered out.
        employment_types = preferences.get("employment_types", [])
        wants_internships = not employment_types or "Internship" in employment_types
        wants_fulltime = not employment_types or "Full-time" in employment_types

        listing_types = []
        if wants_fulltime:
            listing_types.append(LISTING_TYPES[0])
        if wants_internships:
            listing_types.append(LISTING_TYPES[1])

        results: list[RawJob] = []
        seen_job_ids: set[str] = set()

        for listing in listing_types:
            for role in roles:
                encoded = quote(role)
                for page_num in range(1, MAX_PAGES_PER_ROLE + 1):
                    suffix = "" if page_num == 1 else f"page-{page_num}/"
                    url = f"{BASE_URL}/{listing['path']}/keywords-{encoded}/{suffix}"
                    await self.goto_with_retry(page, url)
                    await page.wait_for_timeout(1500)

                    cards = await page.query_selector_all("[internshipid]")
                    if not cards:
                        break  # no more results for this role/listing-type — stop paginating

                    new_on_page = 0
                    for card in cards:
                        job = await self._extract_card(card, preferences, listing["employment_type"])
                        if job is None:
                            continue
                        if job.platform_job_id in seen_job_ids:
                            continue
                        seen_job_ids.add(job.platform_job_id)
                        results.append(job)
                        new_on_page += 1

                    if new_on_page == 0:
                        break  # this page added nothing new — likely end of real results

        return results

    async def _extract_card(self, card, preferences: dict, employment_type: str):
        job_id = await card.get_attribute("internshipid")
        detail_href = await card.get_attribute("data-href")
        if not job_id or not detail_href:
            return None

        apply_url = detail_href if detail_href.startswith("http") else f"{BASE_URL}{detail_href}"

        title = await self.safe_text(card, "a.job-title-href")
        company_name = await self.safe_text(card, ".company-name") or "Unknown Company"
        location = await self.safe_text(card, ".locations a") or await self.safe_text(card, ".locations")
        description = await self.safe_text(card, ".about_job .text")

        skill_els = await card.query_selector_all(".job_skill")
        skills = []
        for s in skill_els:
            text = ((await s.text_content()) or "").strip()
            if text:
                skills.append(text)

        if employment_type == "Internship":
            # Internship cards: stipend (monthly) + duration, NOT
            # salary/experience — see module docstring for why these
            # aren't mapped into salary_min/max or experience_required.
            stipend_text = await self.safe_text(card, ".stipend")
            duration_text = None
            row_items = await card.query_selector_all(".row-1-item")
            for item in row_items:
                icon = await item.query_selector("i")
                icon_class = (await icon.get_attribute("class")) if icon else ""
                if icon_class and "calendar" in icon_class:
                    duration_text = ((await item.text_content()) or "").strip()
                    break

            extra_info = []
            if stipend_text:
                extra_info.append(f"Stipend: {stipend_text}")
            if duration_text:
                extra_info.append(f"Duration: {duration_text}")
            if extra_info and description:
                description = " | ".join(extra_info) + "\n\n" + description
            elif extra_info:
                description = " | ".join(extra_info)

            if not matches_preferences(
                preferences, title=title, description="",
                location=location or "", employment_type=employment_type,
            ):
                return None

            return RawJob(
                company_name=company_name,
                job_title=title,
                original_apply_url=apply_url,
                platform="internshala",
                platform_url=apply_url,
                platform_job_id=job_id,
                location=location or None,
                employment_type=employment_type,
                description=description or None,
                required_skills=skills,
            )

        # Full-time job cards: real salary + experience (existing logic)
        salary_text = None
        experience_text = None
        row_items = await card.query_selector_all(".row-1-item")
        for item in row_items:
            icon = await item.query_selector("i")
            icon_class = (await icon.get_attribute("class")) if icon else ""
            text = ((await item.text_content()) or "").strip()
            if icon_class and "money" in icon_class:
                salary_text = text
            elif icon_class and "briefcase" in icon_class:
                experience_text = text

        salary_min, salary_max, salary_currency = self._parse_salary(salary_text)

        if not matches_preferences(
            preferences, title=title, description="",
            location=location or "", employment_type=employment_type,
            experience_text=experience_text,
            salary_min=salary_min, salary_currency=salary_currency,
        ):
            return None

        return RawJob(
            company_name=company_name,
            job_title=title,
            original_apply_url=apply_url,
            platform="internshala",
            platform_url=apply_url,
            platform_job_id=job_id,
            location=location or None,
            employment_type=employment_type,
            experience_required=experience_text,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            description=description or None,
            required_skills=skills,
        )

    @staticmethod
    def _parse_salary(salary_text: str | None):
        """Parses strings like '₹ 2,00,000 - 2,40,000' into (min, max, currency).
        Returns (None, None, None) if unparseable — never raises, since a
        malformed salary string should never drop the whole job."""
        if not salary_text:
            return None, None, None
        try:
            numbers = re.findall(r"[\d,]+", salary_text)
            numbers = [int(n.replace(",", "")) for n in numbers if n.replace(",", "").isdigit()]
            currency = "INR" if "₹" in salary_text else None
            if len(numbers) >= 2:
                return float(numbers[0]), float(numbers[1]), currency
            elif len(numbers) == 1:
                return float(numbers[0]), float(numbers[0]), currency
        except (ValueError, IndexError):
            pass
        return None, None, None


register_provider(InternshalaProvider())
