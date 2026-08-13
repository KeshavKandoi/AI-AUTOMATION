"""
Regression test for the fallback-gating bug found during live testing:
a query can return many raw cards (Internshala's search is loose) while
yielding very few actually-relevant, preference-matched jobs. Fallback
broadening must trigger based on ACCEPTED jobs (query_new_jobs), not raw
card count -- otherwise a query that sees 86 cards but only 1 relevant
job never broadens, defeating the purpose of the fallback mechanism.
"""
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from job_hunter.platforms.base import RawJob
from job_hunter.platforms.internshala import InternshalaProvider, MIN_RESULTS_BEFORE_FALLBACK


def test_fallback_triggers_on_low_accepted_count_despite_high_raw_cards():
    """Exact reproduction of the bug: 86 raw cards, only 1 accepted job,
    threshold=5 -- fallback queries MUST be attempted."""
    assert MIN_RESULTS_BEFORE_FALLBACK == 5, "test assumes default threshold of 5"

    provider = InternshalaProvider()
    call_log = []

    async def fake_goto_with_retry(page, url):
        call_log.append(url)

    # Exact phrase 'backend engineer' -> 86 cards, but only 1 accepted.
    # Fallback 'backend' -> 40 cards, 5 accepted (enough to satisfy
    # SUBSTANTIAL_RESULTS_THRESHOLD isn't relevant here since default is 30
    # and exact+backend only gives 6 total -- fallback 'engineer' also runs).
    query_card_counts = {"backend%20engineer": 86, "backend": 40, "engineer": 30}
    accepted_counts = {"backend%20engineer": 1, "backend": 5, "engineer": 0}

    async def fake_query_selector_all(selector):
        last_url = call_log[-1]
        if "page-" in last_url:
            return []  # only page 1 has cards in this simulation
        for key, count in query_card_counts.items():
            if key in last_url:
                return [f"card_{key}_{i}" for i in range(count)]
        return []

    async def fake_extract_card(card, preferences, employment_type):
        for key, n_accepted in accepted_counts.items():
            if card.startswith(f"card_{key}_"):
                idx = int(card.rsplit("_", 1)[-1])
                if idx < n_accepted:
                    return RawJob(
                        company_name="TestCo", job_title="Test Role",
                        original_apply_url="http://x", platform="internshala",
                        platform_url="http://x", platform_job_id=f"{key}_{idx}",
                    ), None
                return None, "rejected"
        return None, "rejected"

    fake_page = MagicMock()
    fake_page.query_selector_all = fake_query_selector_all
    fake_page.wait_for_timeout = AsyncMock()

    preferences = {
        "desired_roles": ["backend engineer"],
        "skills": [],
        "employment_types": ["Full-time"],
    }

    async def run_test():
        with patch.object(provider, "goto_with_retry", side_effect=fake_goto_with_retry), \
             patch.object(provider, "_extract_card", side_effect=fake_extract_card):
            return await provider.extract_jobs(fake_page, preferences)

    jobs = asyncio.run(run_test())

    result_ids = {j.platform_job_id for j in jobs}
    assert "backend%20engineer_0" in result_ids, "exact-phrase job must be included"
    assert any(jid.startswith("backend_") for jid in result_ids), (
        "fallback query 'backend' must have been attempted and contributed jobs, "
        "since the exact phrase only yielded 1 accepted job (below threshold of 5)"
    )
    assert len(result_ids) == 6, f"expected 1 (exact) + 5 (backend fallback) = 6 unique jobs, got {len(result_ids)}"


def test_fallback_skipped_when_exact_phrase_yields_enough_accepted_jobs():
    """Inverse case: exact phrase alone yields >= threshold accepted jobs
    -- fallback queries must NOT run (avoids unnecessary requests)."""
    provider = InternshalaProvider()
    call_log = []

    async def fake_goto_with_retry(page, url):
        call_log.append(url)

    async def fake_query_selector_all(selector):
        last_url = call_log[-1]
        if "page-" in last_url:
            return []
        if "backend%20engineer" in last_url:
            return [f"card_{i}" for i in range(10)]
        # Should never be reached if fallback correctly skipped
        return [f"unexpected_fallback_card_{i}" for i in range(10)]

    async def fake_extract_card(card, preferences, employment_type):
        idx = int(card.rsplit("_", 1)[-1])
        if card.startswith("unexpected_fallback_card_"):
            return RawJob(
                company_name="TestCo", job_title="Should Not Appear",
                original_apply_url="http://x", platform="internshala",
                platform_url="http://x", platform_job_id=f"unexpected_{idx}",
            ), None
        if idx < 5:  # 5 accepted, meets threshold of 5
            return RawJob(
                company_name="TestCo", job_title="Test Role",
                original_apply_url="http://x", platform="internshala",
                platform_url="http://x", platform_job_id=f"exact_{idx}",
            ), None
        return None, "rejected"

    fake_page = MagicMock()
    fake_page.query_selector_all = fake_query_selector_all
    fake_page.wait_for_timeout = AsyncMock()

    preferences = {
        "desired_roles": ["backend engineer"],
        "skills": [],
        "employment_types": ["Full-time"],
    }

    async def run_test():
        with patch.object(provider, "goto_with_retry", side_effect=fake_goto_with_retry), \
             patch.object(provider, "_extract_card", side_effect=fake_extract_card):
            return await provider.extract_jobs(fake_page, preferences)

    jobs = asyncio.run(run_test())
    result_ids = {j.platform_job_id for j in jobs}
    assert len(result_ids) == 5
    assert all(jid.startswith("exact_") for jid in result_ids), (
        "no fallback job should appear -- exact phrase already met the threshold"
    )
