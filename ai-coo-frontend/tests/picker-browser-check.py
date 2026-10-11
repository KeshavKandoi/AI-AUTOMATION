"""Run against `npm run dev -- --host 127.0.0.1` with Playwright installed."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"


def main():
    ARTIFACTS.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=os.environ.get("PLAYWRIGHT_CHROME_PATH"))
        for name, width, height in (("desktop", 1440, 900), ("mobile", 390, 680), ("zoomed", 800, 600)):
            page = browser.new_page(viewport={"width": width, "height": height})
            page.set_default_timeout(5000)
            page.goto("http://127.0.0.1:5173/tests/picker-harness.html")
            for label in ("Starts", "Ends"):
                page.get_by_role("button", name="Select date & time").first.click()
                panel = page.get_by_role("dialog", name=f"{label} date and time")
                days = panel.locator("div.grid.grid-cols-7.gap-1").last.locator("button:not([disabled])")
                if label == "Ends" and days.count() == 1:
                    panel.get_by_role("button", name="Next month").click()
                    days = panel.locator("div.grid.grid-cols-7.gap-1").last.locator("button:not([disabled])")
                    days.first.click()
                else:
                    days.nth(1 if label == "Ends" else 0).click()
                panel.locator('input[type="time"]').fill("23:59")
                box = panel.bounding_box()
                assert box and box["y"] >= 0 and box["y"] + box["height"] <= height + 1, (name, label, box)
                assert panel.get_by_role("button", name="Set").is_visible()
                assert panel.get_by_role("button", name="Cancel").is_visible()
                page.screenshot(path=str(ARTIFACTS / f"calendar-after-{name}-{label.lower()}.png"))
                panel.get_by_role("button", name="Set").click()
            end_trigger = page.locator('button[aria-haspopup="dialog"]').last
            end_trigger.focus()
            page.keyboard.press('Enter')
            page.get_by_role('dialog', name='Ends date and time').wait_for()
            page.keyboard.press('Escape')
            assert page.get_by_role('dialog', name='Ends date and time').count() == 0
            assert end_trigger.evaluate('(button) => document.activeElement === button')
            page.close()
        browser.close()
    print("Calendar Starts and Ends passed at desktop, mobile, and reduced CSS viewport (zoom equivalent)")


if __name__ == "__main__":
    main()
