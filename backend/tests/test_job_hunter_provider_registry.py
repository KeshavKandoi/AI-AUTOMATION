import asyncio
from unittest.mock import patch

from job_hunter.platforms import registry
from job_hunter.platforms.base import BaseJobProvider, RawJob


class _FakeProvider(BaseJobProvider):
    def __init__(self, platform: str, delay: float = 0):
        self.platform = platform
        self.delay = delay

    async def search(self, organization_id: str, preferences: dict) -> list[RawJob]:
        await asyncio.sleep(self.delay)
        return [RawJob(
            company_name="Example",
            job_title=f"Engineer ({self.platform})",
            original_apply_url=f"https://example.com/{self.platform}",
            platform=self.platform,
            platform_url=f"https://example.com/{self.platform}",
        )]


def test_completed_provider_results_are_delivered_before_the_whole_sweep_finishes():
    completed = []

    async def on_provider_complete(platform, jobs, status, error):
        completed.append((platform, len(jobs), status, error))

    with patch.dict(
        registry._PROVIDERS,
        {"quick": _FakeProvider("quick"), "slow": _FakeProvider("slow", delay=0.03)},
        clear=True,
    ), patch.object(registry.repository, "upsert_provider_status"):
        result = asyncio.run(registry.run_all_providers(
            "org1", {}, on_provider_complete=on_provider_complete
        ))

    assert completed[0][0] == "quick"
    assert {item[0] for item in completed} == {"quick", "slow"}
    assert len(result["jobs"]) == 2
    assert set(result["statuses"]) == {"quick", "slow"}


def test_collect_jobs_false_does_not_retain_aggregated_provider_results():
    with patch.dict(registry._PROVIDERS, {"quick": _FakeProvider("quick")}, clear=True), \
         patch.object(registry.repository, "upsert_provider_status"):
        result = asyncio.run(registry.run_all_providers("org1", {}, collect_jobs=False))

    assert result["jobs"] == []
    assert result["statuses"]["quick"]["jobs_found"] == 1


def test_streamed_company_results_are_ingested_before_next_company():
    events = []

    class StreamingProvider(_FakeProvider):
        async def search(self, organization_id, preferences):
            raise AssertionError("streaming sweep must not build a full provider result")

        async def iter_search(self, organization_id, preferences):
            for company in ("first", "second"):
                events.append(f"fetch:{company}")
                yield [RawJob(
                    company_name=company,
                    job_title="Engineer",
                    original_apply_url=f"https://example.com/{company}",
                    platform=self.platform,
                    platform_url=f"https://example.com/{company}",
                )]

    async def ingest_batch(platform, jobs):
        events.append(f"ingest:{jobs[0].company_name}")

    with patch.dict(registry._PROVIDERS, {"streaming": StreamingProvider("streaming")}, clear=True), \
         patch.object(registry.repository, "upsert_provider_status"):
        result = asyncio.run(registry.run_all_providers(
            "org1", {}, on_job_batch=ingest_batch, collect_jobs=False
        ))

    assert events == ["fetch:first", "ingest:first", "fetch:second", "ingest:second"]
    assert result["jobs"] == []
    assert result["statuses"]["streaming"]["jobs_found"] == 2


def test_provider_progress_is_written_before_completion():
    events = []

    class StreamingProvider(_FakeProvider):
        async def iter_search(self, organization_id, preferences):
            yield [RawJob(
                company_name="Example", job_title="Engineer",
                original_apply_url="https://example.com/1", platform=self.platform,
                platform_url="https://example.com/1",
            )]

    async def ingest_batch(platform, jobs):
        events.append("ingested")

    def write_status(*args, **kwargs):
        events.append((kwargs.get("status", args[2] if len(args) > 2 else None), kwargs.get("jobs_found")))

    with patch.dict(registry._PROVIDERS, {"streaming": StreamingProvider("streaming")}, clear=True), \
         patch.object(registry.repository, "upsert_provider_status", side_effect=write_status):
        asyncio.run(registry.run_all_providers(
            "org1", {}, on_job_batch=ingest_batch, collect_jobs=False
        ))

    assert events == [("running", 0), "ingested", ("running", 1), ("active", 1)]
