"""
Shared Playwright infrastructure for browser-automation providers
(YC Jobs, Internshala, Wellfound, Indeed, LinkedIn fallback, X fallback,
company career pages, ...). Every Playwright-based adapter extends
PlaywrightJobProvider instead of BaseJobProvider directly, inheriting
browser lifecycle management, retry/rate-limiting, and consistent error
handling — so provider-specific code only ever contains selectors and
extraction logic, never browser plumbing.

Design principle: this file must stay 100% provider-agnostic. If a new
provider needs something this file doesn't offer, extend this file's
generic capability (e.g. "supports pagination via infinite scroll") —
never bake a specific site's quirk in here.
"""
import asyncio
from abc import abstractmethod
from typing import Optional
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError

from config import logger
from job_hunter.platforms.base import BaseJobProvider, RawJob, RateLimiter, ProviderError

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class PlaywrightJobProvider(BaseJobProvider):
    """Base class for browser-automation providers. Subclasses implement
    extract_jobs(page, preferences) — everything else (launching the
    browser, navigation retries, rate limiting, cleanup) is handled here."""

    method = "playwright"

    #: minimum seconds between page navigations for this provider
    rate_limit_seconds: float = 2.0

    #: navigation timeout in ms
    nav_timeout_ms: int = 20000

    #: max retry attempts for a failed page navigation
    max_nav_attempts: int = 2

    def __init__(self):
        self._rate_limiter = RateLimiter(min_interval_seconds=self.rate_limit_seconds)

    async def search(self, organization_id: str, preferences: dict) -> list[RawJob]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(user_agent=DEFAULT_USER_AGENT)
                page = await context.new_page()
                try:
                    jobs = await self.extract_jobs(page, preferences)
                finally:
                    await context.close()
            finally:
                await browser.close()
        return jobs

    async def goto_with_retry(self, page: Page, url: str) -> None:
        """Navigates to a URL with retry + rate limiting. Raises
        ProviderError (not a raw Playwright exception) on final failure,
        so the registry's error isolation works consistently across API
        and Playwright providers."""
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_nav_attempts + 1):
            await self._rate_limiter.wait()
            try:
                await page.goto(url, timeout=self.nav_timeout_ms, wait_until="domcontentloaded")
                return
            except PlaywrightTimeoutError as e:
                last_exc = e
                logger.warning(f"[{self.platform}] nav timeout on attempt {attempt}/{self.max_nav_attempts} for {url}")
                if attempt < self.max_nav_attempts:
                    await asyncio.sleep(2.0 * attempt)
            except Exception as e:
                last_exc = e
                logger.warning(f"[{self.platform}] nav error on attempt {attempt}/{self.max_nav_attempts} for {url}: {e}")
                if attempt < self.max_nav_attempts:
                    await asyncio.sleep(2.0 * attempt)
        raise ProviderError(f"Failed to navigate to {url} after {self.max_nav_attempts} attempts: {last_exc}")

    async def safe_text(self, page_or_el, selector: str, default: str = "") -> str:
        """Extracts text content from a selector, returning `default`
        instead of raising if the selector doesn't match — page structure
        drift on one field should never abort extraction of the whole job.
        Works on either a Page or an ElementHandle (for scoped queries
        within a single job card)."""
        try:
            el = await page_or_el.query_selector(selector)
            if not el:
                return default
            text = await el.text_content()
            return (text or default).strip()
        except Exception:
            return default

    async def safe_attr(self, page_or_el, selector: str, attr: str, default: str = "") -> str:
        try:
            el = await page_or_el.query_selector(selector)
            if not el:
                return default
            value = await el.get_attribute(attr)
            return value or default
        except Exception:
            return default

    @abstractmethod
    async def extract_jobs(self, page: Page, preferences: dict) -> list[RawJob]:
        """Provider-specific extraction logic. Given a live Playwright
        Page and the org's preferences, navigate, paginate, and extract
        RawJob entries. This is the ONLY method a subclass must implement."""
        raise NotImplementedError
