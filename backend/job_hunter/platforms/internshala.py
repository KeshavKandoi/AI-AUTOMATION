"""
Internshala job board adapter.

Verified live (2026-08-08) against https://internshala.com/jobs/:
- Public, no login required for browsing.
- Real keyword search via URL path: /jobs/keywords-<url-encoded term>/
  (confirmed: "backend developer" search returned 6 genuinely relevant
  results; a wrong path pattern silently falls through to the unfiltered
  firehose, so we verified the exact working pattern rather than guess).
- Card selector: [internshipid] with a data-href to the detail page —
  50 cards per page.
- Rich structured data per card: title (a.job-title-href), company
  (.company-name), location (.locations a), salary/experience
  (.row-1-item, disambiguated by icon class), full description
  (.about_job .text), skills (.job_skill elements).
- Pagination via /jobs/page-N/ (confirmed: different job IDs on page 2).
- We search once per org's desired_role (not the generic firehose +
  client-side filter) since Internshala's own keyword search is precise
  enough to trust as the primary relevance signal, same principle as
  YC's category pages — still run matches_preferences() afterward for
  location/employment-type refinement.
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


class InternshalaProvider(PlaywrightJobProvider):
    platform = "internshala"
    rate_limit_seconds = 2.0

    async def extract_jobs(self, page: Page, preferences: dict) -> list[RawJob]:
        roles = preferences.get("desired_roles", [])[:MAX_ROLES_PER_SWEEP]
        if not roles:
            return []

        results: list[RawJob] = []
        seen_job_ids: set[str] = set()

        for role in roles:
            encoded = quote(role)
            for page_num in range(1, MAX_PAGES_PER_ROLE + 1):
                suffix = "" if page_num == 1 else f"page-{page_num}/"
                url = f"{BASE_URL}/jobs/keywords-{encoded}/{suffix}"
                await self.goto_with_retry(page, url)
                await page.wait_for_timeout(1500)

                cards = await page.query_selector_all("[internshipid]")
                if not cards:
                    break  # no more results for this role — stop paginating it

                new_on_page = 0
                for card in cards:
                    job = await self._extract_card(card, preferences)
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

    async def _extract_card(self, card, preferences: dict):
        job_id = await card.get_attribute("internshipid")
        detail_href = await card.get_attribute("data-href")
        if not job_id or not detail_href:
            return None

        apply_url = detail_href if detail_href.startswith("http") else f"{BASE_URL}{detail_href}"

        title = await self.safe_text(card, "a.job-title-href")
        company_name = await self.safe_text(card, ".company-name") or "Unknown Company"
        location = await self.safe_text(card, ".locations a") or await self.safe_text(card, ".locations")

        # Disambiguate salary vs experience: both live in .row-1-item, only
        # salary's icon class contains "money" and experience's contains
        # "briefcase" — check icon presence per item rather than assuming order.
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

        description = await self.safe_text(card, ".about_job .text")

        skill_els = await card.query_selector_all(".job_skill")
        skills = []
        for s in skill_els:
            text = ((await s.text_content()) or "").strip()
            if text:
                skills.append(text)

        # employment type isn't explicit on the card (Internshala's /jobs/
        # listing is full-time by default; internships live under /internships/)
        employment_type = "Full-time"

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
