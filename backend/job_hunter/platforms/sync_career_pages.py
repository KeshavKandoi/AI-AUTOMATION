"""
One-time/periodic sync: runs ATS detection across every career page in
job_provider_career_pages that hasn't been classified yet. Companies
found to use a known ATS get registered into job_provider_companies
(picked up automatically by the real API adapter from then on).
Companies with no detected ATS remain candidates for the custom-site
fallback scraper (career_pages.py).

Run manually via: python3 -m job_hunter.platforms.sync_career_pages
Not wired into the 6-hourly search scheduler — this is a registry
maintenance operation, not a per-org job search.
"""
import asyncio
from playwright.async_api import async_playwright

from config import logger
from job_hunter import repository
from job_hunter.platforms.ats_detector import detect_ats

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


async def sync_all_career_pages() -> dict:
    pages = repository.list_undetected_career_pages()
    logger.info(f"[career_pages_sync] Checking {len(pages)} undetected career page(s)")

    detected = 0
    custom = 0
    errors = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for page_row in pages:
            try:
                context = await browser.new_context(user_agent=DEFAULT_USER_AGENT)
                page = await context.new_page()
                result = await detect_ats(page, page_row["career_page_url"])
                await context.close()

                if result.detected:
                    repository.mark_career_page_detected(page_row["id"], result.ats, result.token)
                    repository.upsert_detected_company(
                        provider=result.ats,
                        company_name=page_row["company_name"],
                        board_token=result.token,
                        website=page_row["career_page_url"],
                    )
                    logger.info(f"[career_pages_sync] {page_row['company_name']}: detected {result.ats} (token={result.token})")
                    detected += 1
                else:
                    repository.mark_career_page_status(page_row["id"], "ok")
                    logger.info(f"[career_pages_sync] {page_row['company_name']}: no known ATS — custom-site candidate")
                    custom += 1

            except Exception as e:
                logger.error(f"[career_pages_sync] {page_row['company_name']} failed: {e}")
                repository.mark_career_page_status(page_row["id"], "error")
                errors += 1

        await browser.close()

    result = {"checked": len(pages), "ats_detected": detected, "custom_candidates": custom, "errors": errors}
    logger.info(f"[career_pages_sync] Done: {result}")
    return result


if __name__ == "__main__":
    asyncio.run(sync_all_career_pages())
