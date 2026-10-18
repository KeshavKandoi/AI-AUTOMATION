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
