"""
ATS auto-detection. Scans a company's career page for known ATS
fingerprints (Greenhouse/Lever/Ashby links embedded in the page) and, if
found, extracts the board token so the company can be registered into
job_provider_companies — meaning it gets picked up by the real API-based
adapter (greenhouse.py / lever.py / ashby.py) from then on, rather than
needing fragile HTML scraping.

This is NOT a BaseJobProvider — it doesn't return jobs itself. It's a
one-time (well, periodic) sync step that grows job_provider_companies,
run separately from the 6-hourly search sweep. See sync_career_pages.py.

Verified live (2026-08-08) against real career pages:
- Cloudflare (cloudflare.com/careers) embeds boards.greenhouse.io links
- Notion (notion.so/careers) embeds jobs.ashbyhq.com links
- Airbnb (airbnb.com/careers) has no known-ATS fingerprint — correctly
  falls through to "no ATS detected" for the custom-site fallback adapter
"""
import re
from urllib.parse import urlparse
from playwright.async_api import Page

# (regex pattern to find the URL, board-token group index in the match)
ATS_PATTERNS: dict[str, re.Pattern] = {
    "greenhouse": re.compile(r"(?:boards\.greenhouse\.io|job-boards\.greenhouse\.io)/([a-zA-Z0-9\-_]+)"),
    "lever": re.compile(r"jobs\.lever\.co/([a-zA-Z0-9\-_]+)"),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([a-zA-Z0-9\-_]+)"),
}


class DetectionResult:
    def __init__(self, ats: str | None, token: str | None):
        self.ats = ats
        self.token = token

    @property
    def detected(self) -> bool:
        return self.ats is not None


async def detect_ats(page: Page, career_page_url: str) -> DetectionResult:
    """Navigates to the career page and scans its HTML for known ATS
    link patterns. Returns the first match found — companies that split
    postings across multiple ATSes are rare enough not to special-case."""
    await page.goto(career_page_url, timeout=20000, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    html = await page.content()

    for ats_name, pattern in ATS_PATTERNS.items():
        match = pattern.search(html)
        if match:
            return DetectionResult(ats=ats_name, token=match.group(1))

    return DetectionResult(ats=None, token=None)
