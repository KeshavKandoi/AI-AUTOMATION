"""
Wellfound (formerly AngelList Talent) job board adapter.

Verified live (2026-08-08) against https://wellfound.com/role/r/<slug>:
- Public, no login required for browsing listings or individual job
  detail pages (full description, salary, location all visible logged
  out).
- Real role-based search via /role/r/<slug> (confirmed: page title
  changes to "Remote Backend Engineer Jobs in 2026", and a totally
  different job set than the generic /jobs firehose).
- Real pagination via ?page=N (confirmed: different job IDs on page 2).
  No infinite scroll on a single page — count stays fixed after scrolling.
- Card structure: title link (a[href^="/jobs/"], href matches
  /jobs/<numeric-id>-<slug>) sits inside a small 2-level container with
  an employment-type badge, salary text (with a leading SVG icon, may
  include equity range after "•", $ or ₹ currency), and an optional
  location string (prefixed "In office • ", "Remote • ", or
  "Remote only • " — many postings omit location entirely, especially
  equity-heavy early-stage listings, so this must not be required).
- No dedicated skills field on the card; full description (with likely
  skill mentions) lives on the detail page, not fetched here to keep one
  sweep fast — original_apply_url takes the user to the real posting.

Role -> slug mapping is intentionally small and hand-verified rather than
a blind slugify() of the user's desired_roles, since Wellfound's /role/r/
slugs are a fixed, curated set (not every arbitrary title has a working
slug) — verified working slugs only.
"""
import re

from job_hunter.platforms.playwright_base import PlaywrightJobProvider
from job_hunter.platforms.base import RawJob
from job_hunter.platforms.matching import normalize_work_mode
from job_hunter.platforms.registry import register_provider
from playwright.async_api import Page

BASE_URL = "https://wellfound.com"
MAX_PAGES_PER_ROLE = 2
MAX_ROLES_PER_SWEEP = 3

# Verified working /role/r/<slug> pages. Extend cautiously — an unverified
# slug either 404s or silently falls back to an unfiltered/different page,
# same failure mode we saw with YC's category tabs earlier.
ROLE_SLUG_MAP = {
    "software engineer": "software-engineer",
    "backend engineer": "backend-engineer",
    "backend developer": "backend-engineer",
    "frontend engineer": "frontend-engineer",
    "frontend developer": "frontend-engineer",
    "full stack engineer": "full-stack-engineer",
    "full stack developer": "full-stack-engineer",
    "data scientist": "data-scientist",
    "product manager": "product-manager",
    "designer": "designer",
    "devops engineer": "devops-engineer",
    "machine learning engineer": "machine-learning-engineer",
    "mobile engineer": "mobile-engineer",
    "ios engineer": "ios-engineer",
    "android engineer": "android-engineer",
}


def _slugs_for_preferences(preferences: dict) -> list[str]:
    roles = [r.lower().strip() for r in preferences.get("desired_roles", [])]
    matched = []
    for role in roles:
        slug = ROLE_SLUG_MAP.get(role)
        if slug and slug not in matched:
            matched.append(slug)
    return matched[:MAX_ROLES_PER_SWEEP] if matched else ["software-engineer"]


def _parse_salary(salary_text: str):
    """Parses '$150k – $280k • 0.1% – 0.3%' or '₹10L – ₹20L' into
    (min, max, currency). Equity portion (after •) is discarded — no
    schema field for it. Returns (None, None, None) if unparseable."""
    if not salary_text:
        return None, None, None
    try:
        salary_part = salary_text.split("•")[0].strip()
        currency = "INR" if "₹" in salary_part else ("USD" if "$" in salary_part else None)

        # Handle 'k' (thousands) and 'L' (lakhs, Indian) suffixes
        numbers = re.findall(r"[\d.]+[kKlL]?", salary_part)
        parsed = []
        for n in numbers:
            multiplier = 1
            if n[-1] in "kK":
                multiplier = 1_000
                n = n[:-1]
            elif n[-1] in "lL":
                multiplier = 100_000
                n = n[:-1]
            try:
                parsed.append(float(n) * multiplier)
            except ValueError:
                continue

        if len(parsed) >= 2:
            return parsed[0], parsed[1], currency
        elif len(parsed) == 1:
            return parsed[0], parsed[0], currency
    except Exception:
        pass
    return None, None, None


def _parse_location(location_text: str):
    """'In office • San Francisco' -> ('San Francisco', 'On-site')
    'Remote only • Europe' -> ('Europe', 'Remote')
    'Remote • United Kingdom' -> ('United Kingdom', 'Remote')
    'Hybrid • Austin' -> ('Austin', 'Hybrid')
    Routes the raw mode prefix through the shared normalize_work_mode()
    so output casing always matches the canonical DB values ("On-site",
    not "Onsite") and stays consistent with every other provider."""
    if not location_text:
        return None, None
    parts = location_text.split("•")
    mode_raw = parts[0].strip().lower()
    location = parts[1].strip() if len(parts) > 1 else None

    if "hybrid" in mode_raw:
        work_mode = normalize_work_mode("Hybrid")
    elif "remote" in mode_raw:
        work_mode = normalize_work_mode("Remote")
    elif "office" in mode_raw:
        work_mode = normalize_work_mode("On-site")
    else:
        work_mode = None

    return location, work_mode


class WellfoundProvider(PlaywrightJobProvider):
    platform = "wellfound"
    rate_limit_seconds = 2.5

    async def extract_jobs(self, page: Page, preferences: dict) -> list[RawJob]:
        slugs = _slugs_for_preferences(preferences)
        results: list[RawJob] = []
        seen_job_ids: set[str] = set()

        for slug in slugs:
            for page_num in range(1, MAX_PAGES_PER_ROLE + 1):
                url = f"{BASE_URL}/role/r/{slug}" + (f"?page={page_num}" if page_num > 1 else "")
                await self.goto_with_retry(page, url)
                await page.wait_for_timeout(2000)

                cards_data = await self._extract_page_cards(page)
                new_count = 0
                for card in cards_data:
                    job_id = card["job_id"]
                    if job_id in seen_job_ids:
                        continue

                    location, work_mode = _parse_location(card["location_text"])
                    salary_min, salary_max, salary_currency = _parse_salary(card["salary_text"])

                    # ARCHITECTURE CHANGE: preference matching removed from
                    # discovery -- see ashby.py for full rationale. Every
                    # technically valid parsed job is stored regardless of
                    # current org preferences. _slugs_for_preferences()
                    # above still controls WHICH role pages get scraped --
                    # that discovery-scope logic is unchanged.
                    seen_job_ids.add(job_id)
                    new_count += 1
                    results.append(RawJob(
                        company_name=card["company_name"] or "Unknown Company",
                        job_title=card["title"],
                        original_apply_url=card["url"],
                        platform="wellfound",
                        platform_url=card["url"],
                        platform_job_id=job_id,
                        location=location,
                        work_mode=work_mode,
                        employment_type=card["employment_type"],
                        experience_required=card["experience_text"],
                        salary_min=salary_min,
                        salary_max=salary_max,
                        salary_currency=salary_currency,
                    ))

                if new_count == 0:
                    break  # no new results on this page — stop paginating this role

        return results

    async def _extract_page_cards(self, page: Page) -> list[dict]:
        """Extracts raw card data via a single evaluate() call for speed —
        30-40+ cards per page would otherwise mean 30-40+ round trips if
        done via individual query_selector calls per field."""
        try:
            return await page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a[href^="/jobs/"]'));
                const jobLinks = links.filter(l => /^\\/jobs\\/\\d+-/.test(l.getAttribute('href')));
                const results = [];
                const seen = new Set();

                for (const link of jobLinks) {
                    const href = link.getAttribute('href');
                    if (seen.has(href)) continue;
                    seen.add(href);

                    const jobIdMatch = href.match(/^\\/jobs\\/(\\d+)-/);
                    const jobId = jobIdMatch ? jobIdMatch[1] : null;
                    const title = (link.textContent || '').trim();

                    // Climb to the small container holding this job's own
                    // metadata (title + badge + salary + location) — NOT
                    // the wider company block which can hold multiple jobs.
                    let container = link;
                    for (let i = 0; i < 2; i++) {
                        if (container.parentElement) container = container.parentElement;
                    }
                    // Read each field from its OWN leaf element's text, never
                    // from flattened container text — sibling text nodes here
                    // have no separators in the DOM (e.g. "San Francisco"
                    // immediately followed by "11 months ago", or a "+2" tag
                    // immediately followed by "7 years of exp"), so
                    // concatenating them corrupts values ("San
                    // Francisco11 months ago", "27 years of exp" instead of
                    // "7 years of exp"). Same lesson learned building the
                    // YC Jobs adapter earlier.
                    let employmentType = null;
                    let salaryText = null;
                    let locationText = null;
                    let experienceText = null;

                    const badgeEls = Array.from(container.querySelectorAll('span, div')).filter(el => el.children.length === 0);
                    for (const el of badgeEls) {
                        const text = (el.textContent || '').trim();
                        if (!text) continue;
                        if (!employmentType && ['Full-time', 'Part-time', 'Contract', 'Internship', 'Freelance'].includes(text)) {
                            employmentType = text;
                            continue;
                        }
                        if (!salaryText && /^[$₹][\d.,kKlL]+\s*[–-]/.test(text)) {
                            salaryText = text;
                            continue;
                        }
                        if (!locationText && /^(In office|Remote only|Remote)\s*•/.test(text)) {
                            locationText = text;
                            continue;
                        }
                        if (!experienceText && /^\d+\s*years?\s*of\s*exp/i.test(text)) {
                            experienceText = text;
                            continue;
                        }
                    }

                    // Company name: nearest preceding h2 in the wider ancestor
                    let companyEl = link;
                    let companyName = null;
                    for (let i = 0; i < 6; i++) {
                        if (!companyEl.parentElement) break;
                        companyEl = companyEl.parentElement;
                        const h2 = companyEl.querySelector('h2');
                        if (h2) { companyName = h2.textContent.trim(); break; }
                    }

                    results.push({
                        job_id: jobId,
                        url: 'https://wellfound.com' + href,
                        title,
                        company_name: companyName,
                        employment_type: employmentType,
                        salary_text: salaryText,
                        location_text: locationText,
                        experience_text: experienceText,
                    });
                }
                return results;
            }""")
        except Exception:
            return []


register_provider(WellfoundProvider())
