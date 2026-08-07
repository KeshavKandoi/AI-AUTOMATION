"""
Provider registry. Adapters call register_provider(instance) at import
time (see bottom of greenhouse.py, lever.py, etc). Core Job Hunter code
(service.py, routes.py, scheduler_jobs.py) only ever calls
run_all_providers() / get_registered_platforms() here — never imports a
specific platform module directly, so adding/removing/fixing one
provider never requires touching anything else.
"""
import asyncio
from typing import Optional

from config import logger
from job_hunter import repository
from job_hunter.platforms.base import BaseJobProvider, RawJob, NotConfiguredError, ProviderError

_PROVIDERS: dict[str, BaseJobProvider] = {}


def register_provider(provider: BaseJobProvider) -> BaseJobProvider:
    _PROVIDERS[provider.platform] = provider
    return provider


def get_registered_platforms() -> list[str]:
    return list(_PROVIDERS.keys())


async def _run_single_provider(provider: BaseJobProvider, organization_id: str, preferences: dict) -> tuple[str, list[RawJob], str, Optional[str]]:
    """Runs one provider in isolation. Always returns a result tuple —
    never raises — so one broken provider can never take down the sweep
    for the rest. Returns (platform, jobs, status, error_message)."""
    if not provider.is_configured(organization_id):
        return provider.platform, [], "not_configured", None

    try:
        jobs = await provider.search(organization_id, preferences)
        return provider.platform, jobs, "active", None
    except NotConfiguredError as e:
        return provider.platform, [], "not_configured", str(e)
    except ProviderError as e:
        logger.error(f"[{provider.platform}] provider error: {e}")
        return provider.platform, [], "error", str(e)
    except Exception as e:
        logger.exception(f"[{provider.platform}] unexpected error")
        return provider.platform, [], "error", str(e)


async def run_all_providers(organization_id: str, preferences: dict, platforms: Optional[list[str]] = None) -> dict:
    """
    Runs every registered provider concurrently for one org, isolating
    failures per-provider. Writes each provider's outcome to
    job_hunter_provider_status and returns an aggregated result:

        {"jobs": [RawJob, ...], "statuses": {platform: {"status": ..., "jobs_found": N, "error": ...}}}
    """
    selected = {
        name: p for name, p in _PROVIDERS.items()
        if platforms is None or name in platforms
    }

    if not selected:
        return {"jobs": [], "statuses": {}}

    results = await asyncio.gather(*[
        _run_single_provider(p, organization_id, preferences) for p in selected.values()
    ])

    all_jobs: list[RawJob] = []
    statuses: dict[str, dict] = {}

    for platform, jobs, status, error in results:
        all_jobs.extend(jobs)
        statuses[platform] = {"status": status, "jobs_found": len(jobs), "error": error}
        try:
            repository.upsert_provider_status(
                organization_id=organization_id,
                platform=platform,
                status=status,
                jobs_found=len(jobs),
                error=error,
            )
        except Exception as e:
            logger.error(f"Failed to write provider_status for {platform}: {e}")

    return {"jobs": all_jobs, "statuses": statuses}
