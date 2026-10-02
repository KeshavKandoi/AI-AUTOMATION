"""
Unit tests for job_hunter.platforms.greenhouse._extract_work_mode().

Confirms extraction uses ONLY the structured location.name field and
never scans free-text descriptions -- a real false positive was found
during live testing where a job's description contained "This role can
either be fully remote depending on which US state you live in, or
based in our New York City office" (a conditional arrangement, not an
unconditional Remote statement), which a description-scanning approach
incorrectly classified as Remote.
"""
from job_hunter.platforms.greenhouse import _extract_work_mode


def test_explicit_remote_location():
    assert _extract_work_mode("Remote") == "Remote"


def test_remote_with_region():
    assert _extract_work_mode("Remote - USA") == "Remote"


def test_remote_select_locations():
    assert _extract_work_mode("Remote - US: Select locations") == "Remote"


def test_hybrid_location():
    assert _extract_work_mode("Hybrid - Austin, TX") == "Hybrid"


def test_onsite_location():
    assert _extract_work_mode("On-site - San Francisco") == "On-site"


def test_in_office_location():
    assert _extract_work_mode("In-office - New York") == "On-site"


def test_generic_country_stays_null():
    assert _extract_work_mode("United States") is None


def test_worldwide_stays_null():
    assert _extract_work_mode("Worldwide") is None


def test_anywhere_stays_null():
    assert _extract_work_mode("Anywhere") is None


def test_bare_city_stays_null():
    assert _extract_work_mode("New York City") is None


def test_multi_city_list_stays_null():
    assert _extract_work_mode("SF, NYC, SEA, CHI") is None


def test_function_no_longer_accepts_description_param():
    """Regression guard: _extract_work_mode must only take location --
    if a description param is ever re-added, this test signature will
    force a deliberate review rather than silently reintroducing the
    description-scanning false-positive risk."""
    import inspect
    sig = inspect.signature(_extract_work_mode)
    assert list(sig.parameters.keys()) == ["location"]


def test_phase4_api_providers_rate_limit_every_retry_attempt(monkeypatch):
    import asyncio
    import types
    import httpx
    from job_hunter.platforms import base
    from job_hunter.platforms import greenhouse as gh, lever, ashby

    async def no_sleep(*a, **k):
        return None

    monkeypatch.setattr(base.asyncio, "sleep", no_sleep)

    for mod, cls_name in ((gh, "GreenhouseProvider"), (lever, "LeverProvider"), (ashby, "AshbyProvider")):
        waits = []
        gets = []

        class FakeLimiter:
            async def wait(self):
                waits.append(1)

        class FakeClient:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, *a, **k):
                gets.append(1)
                return types.SimpleNamespace(status_code=500, text="", json=lambda: {})

            async def post(self, *a, **k):
                gets.append(1)
                return types.SimpleNamespace(status_code=500, text="", json=lambda: {})

        monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
        monkeypatch.setattr(mod.repository, "list_enabled_companies", lambda p: [{"id": "c1", "company_name": "Co", "board_token": "t", "company_token": "t", "slug": "t"}])
        monkeypatch.setattr(mod.repository, "mark_company_sync_status", lambda *a, **k: None)
        provider = getattr(mod, cls_name)()
        provider._rate_limiter = FakeLimiter()
        asyncio.run(provider.search("org", {}))
        assert len(gets) >= 2
        assert len(waits) == len(gets), cls_name


def test_phase4_ats_detector_navigation_is_rate_limited(monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from job_hunter.platforms import ats_detector
    waits = []

    class FakeLimiter:
        async def wait(self):
            waits.append(1)

    monkeypatch.setattr(ats_detector, "_nav_limiter", FakeLimiter())
    page = MagicMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.content = AsyncMock(return_value="<html></html>")
    result = asyncio.run(ats_detector.detect_ats(page, "https://example.com/careers"))
    assert waits == [1] and result.detected is False
