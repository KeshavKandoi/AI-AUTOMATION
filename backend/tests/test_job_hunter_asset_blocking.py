import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from job_hunter.platforms.playwright_base import block_nonessential_assets


def test_job_search_blocks_visual_assets_but_keeps_page_data():
    async def check():
        context = SimpleNamespace(route=AsyncMock())
        await block_nonessential_assets(context)
        pattern, handler = context.route.call_args.args
        assert pattern == "**/*"

        for resource_type in ("image", "media", "font", "document", "stylesheet", "script", "xhr", "fetch"):
            route = SimpleNamespace(
                request=SimpleNamespace(resource_type=resource_type),
                abort=AsyncMock(),
                continue_=AsyncMock(),
            )
            await handler(route)
            if resource_type in {"image", "media", "font", "stylesheet"}:
                route.abort.assert_awaited_once()
                route.continue_.assert_not_awaited()
            else:
                route.continue_.assert_awaited_once()
                route.abort.assert_not_awaited()

    asyncio.run(check())
