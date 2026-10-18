"""
Provider registry. Adapters call register_provider(instance) at import
time (see bottom of greenhouse.py, lever.py, etc). Core Job Hunter code
(service.py, routes.py, scheduler_jobs.py) only ever calls
run_all_providers() / get_registered_platforms() here — never imports a
specific platform module directly, so adding/removing/fixing one
provider never requires touching anything else.
"""
import asyncio
from typing import Awaitable, Callable, Optional

from config import logger
from job_hunter import repository
from job_hunter.platforms.base import BaseJobProvider, RawJob, NotConfiguredError, ProviderError

_PROVIDERS: dict[str, BaseJobProvider] = {}
ProviderCompletionHandler = Callable[[str, list[RawJob], str, Optional[str]], Awaitable[None]]
ProviderBatchHandler = Callable[[str, list[RawJob]], Awaitable[None]]
PROVIDER_TIMEOUT_SECONDS = 90 * 60


def register_provider(provider: BaseJobProvider) -> BaseJobProvider:
    _PROVIDERS[provider.platform] = provider
    return provider


def get_registered_platforms() -> list[str]:
    return list(_PROVIDERS.keys())


async def _run_single_provider(
    provider: BaseJobProvider,
    organization_id: str,
    preferences: dict,
    on_job_batch: Optional[ProviderBatchHandler] = None,
    stream_batches: bool = False,
    on_progress: Optional[Callable[[str, int], None]] = None,
) -> tuple[str, list[RawJob], int, str, Optional[str]]:
    """Runs one provider in isolation. Always returns a result tuple —
    never raises — so one broken provider can never take down the sweep
    for the rest. Returns (platform, jobs, count, status, error_message)."""
    if not provider.is_configured(organization_id):
        return provider.platform, [], 0, "not_configured", None

    job_count = 0
    try:
        if stream_batches:
            async def consume_batches():
                nonlocal job_count
                async for batch in provider.iter_search(organization_id, preferences):
                    job_count += len(batch)
                    if batch:
                        await on_job_batch(provider.platform, batch)
                        if on_progress:
                            on_progress(provider.platform, job_count)
                    del batch

            await asyncio.wait_for(consume_batches(), timeout=PROVIDER_TIMEOUT_SECONDS)
            return provider.platform, [], job_count, "active", None

        jobs = await asyncio.wait_for(
            provider.search(organization_id, preferences),
            timeout=PROVIDER_TIMEOUT_SECONDS,
        )
        job_count = len(jobs)
        if on_job_batch is not None and jobs:
            await on_job_batch(provider.platform, jobs)
        return provider.platform, jobs, job_count, "active", None
    except NotConfiguredError as e:
        return provider.platform, [], job_count, "not_configured", str(e)
    except ProviderError as e:
        logger.error(f"[{provider.platform}] provider error: {e}")
        return provider.platform, [], job_count, "error", str(e)
    except Exception as e:
        logger.exception(f"[{provider.platform}] unexpected error")
        return provider.platform, [], job_count, "error", str(e)


async def run_all_providers(
    organization_id: str,
    preferences: dict,
    platforms: Optional[list[str]] = None,
    on_provider_complete: Optional[ProviderCompletionHandler] = None,
    on_job_batch: Optional[ProviderBatchHandler] = None,
    collect_jobs: bool = True,
) -> dict:
    """
    Runs registered providers sequentially for one org to bound peak
    memory, isolating failures per provider. Writes each provider's outcome
    to job_hunter_provider_status and returns an aggregated result unless
    collect_jobs=False:

        {"jobs": [RawJob, ...], "statuses": {platform: {"status": ..., "jobs_found": N, "error": ...}}}
    """
    selected = {
        name: p for name, p in _PROVIDERS.items()
        if platforms is None or name in platforms
    }

    if not selected:
        return {"jobs": [], "statuses": {}}

    # Do not launch every provider at once. Several providers start a
    # Chromium process and the ATS APIs hold sizable response lists; running
    # them concurrently caused large memory spikes on the small web service.
    all_jobs: list[RawJob] = []
    statuses: dict[str, dict] = {}

    for provider in selected.values():
        try:
            repository.upsert_provider_status(
                organization_id, provider.platform, "running", jobs_found=0
            )
        except Exception as e:
            logger.warning(f"Failed to mark {provider.platform} as running: {e}")

        def record_progress(platform: str, count: int) -> None:
            try:
                repository.upsert_provider_status(
                    organization_id, platform, "running", jobs_found=count
                )
            except Exception as e:
                logger.warning(f"Failed to write provider progress for {platform}: {e}")

        platform, jobs, job_count, status, error = await _run_single_provider(
            provider,
            organization_id,
            preferences,
            on_job_batch=on_job_batch,
            stream_batches=bool(on_job_batch and not collect_jobs and hasattr(provider, "iter_search")),
            on_progress=record_progress,
        )
        if collect_jobs:
            all_jobs.extend(jobs)

        # Persist each source's results as soon as it finishes. A slow or
        # unresponsive provider must not hold every completed source's jobs
        # in memory until the entire sweep ends.
        if on_provider_complete is not None:
            try:
                await on_provider_complete(platform, jobs, status, error)
            except Exception as e:
                status = "error"
                error = f"provider result ingestion failed: {e}"
                logger.exception(f"Failed to ingest {platform} results for org {organization_id}")

        statuses[platform] = {"status": status, "jobs_found": job_count, "error": error}
        try:
            repository.upsert_provider_status(
                organization_id=organization_id,
                platform=platform,
                status=status,
                jobs_found=job_count,
                error=error,
            )
        except Exception as e:
            logger.error(f"Failed to write provider_status for {platform}: {e}")
        # Release provider results before starting the next source.
        del jobs

    return {"jobs": all_jobs, "statuses": statuses}
