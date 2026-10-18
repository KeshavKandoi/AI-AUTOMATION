"""
Scheduler entry points for Job Hunter. Wired into scheduler.py on a
24-hour interval (search) and independently for reminders. Mirrors the
pattern of commit_scheduler/scheduler_jobs.py and
the scheduler — a thin orchestration layer that
calls into service.py, never touches the DB or platform adapters directly.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor

from config import logger
from job_hunter import repository, service
from job_hunter.platforms import registry
from job_hunter.platforms import __init__ as _register_platforms  # noqa: F401 — triggers adapter registration
from job_hunter.batch_ingest import ingest_discovered_jobs_batch
from job_hunter.retention import JOB_HUNTER_RETENTION_DAYS
from audit_logs.service import log_event

MODULE = "job_hunter"

# Kept as an alias for existing imports and tests.
JOB_HUNTER_STALE_AFTER_DAYS = JOB_HUNTER_RETENTION_DAYS

# A sweep can run for hours and uses the synchronous Supabase client in many
# provider and ingestion paths. Keep those calls off the web server's event
# loop, while serializing sweeps so provider rate limiters are not shared by
# concurrent event loops.
_search_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="job-hunter-search")


async def run_search_for_org_background(organization_id: str) -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _search_executor, lambda: asyncio.run(run_search_for_org(organization_id))
    )


async def run_search_for_all_orgs_background() -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _search_executor, lambda: asyncio.run(run_search_for_all_orgs())
    )


async def run_search_for_org(organization_id: str) -> dict:
    """
    Runs a full discovery sweep for one org: fetches saved preferences,
    runs registered providers in memory-bounded sequence (failures isolated
    per provider), and ingests each batch as it arrives. Records the sweep in
    job_hunter_search_runs regardless of outcome.
    """
    preferences = repository.get_preferences(organization_id)
    if not preferences or not preferences.get("onboarding_completed"):
        logger.info(f"[job_hunter] Skipping search for org {organization_id} — onboarding not completed")
        return {"skipped": True, "reason": "onboarding_not_completed"}

    if repository.has_running_search(organization_id):
        logger.info(f"[job_hunter] Skipping search for org {organization_id} — a sweep is already in progress")
        return {"skipped": True, "reason": "search_already_running"}

    platforms = registry.get_registered_platforms()
    run = repository.create_search_run(organization_id, platforms)
    statuses = {}
    jobs_found_progress = 0
    inserted = 0
    updated = 0
    permanent_failures = []

    try:
        async def ingest_provider_results(platform, jobs):
            nonlocal inserted, updated, jobs_found_progress
            jobs_found_progress += len(jobs)
            repository.update_search_run_progress(
                run["id"],
                jobs_found=jobs_found_progress,
                jobs_new=inserted,
            )
            if jobs:
                batch_result = await ingest_discovered_jobs_batch(organization_id, jobs)
                inserted += batch_result["inserted"]
                updated += batch_result["updated"]
                permanent_failures.extend(batch_result["permanent_failure_details"])
            repository.update_search_run_progress(
                run["id"],
                jobs_found=jobs_found_progress,
                jobs_new=inserted,
            )

        result = await registry.run_all_providers(
            organization_id,
            preferences,
            on_job_batch=ingest_provider_results,
            collect_jobs=False,
        )
        statuses = result["statuses"]
        jobs_found = jobs_found_progress
        jobs_new = inserted
        permanent_failure_count = len(permanent_failures)

        for f in permanent_failures:
            logger.error(
                f"[job_hunter] Permanent ingestion failure: '{f['title']}' "
                f"@ {f['company']} (platform={f['platform']}): {f['error']}"
            )
        # Reconciliation: discovered == inserted + updated + permanent_failures
        # (there is no separate "duplicate/no-op" bucket at this layer --
        # every raw_job that isn't a genuine insert is either an update to
        # an existing job, per ingest_discovered_job()'s existing dedup-by-
        # dedup_key logic, or a permanent failure).
        reconciled = (inserted + updated + permanent_failure_count) == jobs_found
        if not reconciled:
            logger.warning(
                f"[job_hunter] Ingestion accounting mismatch for org {organization_id}: "
                f"discovered={jobs_found} inserted={inserted} updated={updated} "
                f"permanent_failures={permanent_failure_count} "
                f"(sum={inserted + updated + permanent_failure_count})"
            )

        provider_failures = [name for name, state in statuses.items() if state["status"] == "error"]
        overall_status = (
            "failed" if not any(state["status"] == "active" for state in statuses.values())
            else "partial" if provider_failures or permanent_failure_count
            else "success"
        )
        repository.finish_search_run(run["id"], status=overall_status, jobs_found=jobs_found, jobs_new=jobs_new)
        log_event(
            organization_id=organization_id,
            module=MODULE,
            action="search_run_completed",
            summary=f"Job search completed: {jobs_found} jobs found ({jobs_new} new, {updated} updated, {permanent_failure_count} failed) across {len(platforms)} platforms",
            status=overall_status,
            resource_type="job_hunter_search_run",
            resource_id=run["id"],
            metadata={
                "statuses": statuses, "jobs_found": jobs_found, "jobs_new": jobs_new,
                "inserted": inserted, "updated": updated,
                "permanent_failures": permanent_failure_count,
                "reconciled": reconciled,
            },
            source="scheduler",
        )
        return {
            "jobs_found": jobs_found, "jobs_new": jobs_new, "statuses": statuses,
            "status": overall_status,
            "inserted": inserted, "updated": updated,
            "permanent_failures": permanent_failure_count,
            "permanent_failure_details": permanent_failures,
            "reconciled": reconciled,
        }

    except Exception as e:
        logger.exception(f"[job_hunter] Search run failed for org {organization_id}")
        repository.finish_search_run(
            run["id"],
            status="failed",
            jobs_found=jobs_found_progress,
            jobs_new=inserted,
            error_message=str(e),
        )
        log_event(
            organization_id=organization_id,
            module=MODULE,
            action="search_run_failed",
            summary=f"Job search failed: {e}",
            status="failed",
            resource_type="job_hunter_search_run",
            resource_id=run["id"],
            error_message=str(e),
            source="scheduler",
        )
        return {"error": str(e)}


async def run_search_for_all_orgs() -> dict:
    """Called every 24 hours by the scheduler. Loops every org with
    completed Job Hunter onboarding; one org's failure never blocks the
    rest since run_search_for_org catches its own exceptions."""
    org_ids = repository.list_orgs_with_preferences()
    logger.info(f"[job_hunter] Starting daily search sweep for {len(org_ids)} orgs")

    results = {}
    for org_id in org_ids:
        results[org_id] = await run_search_for_org(org_id)

    logger.info(f"[job_hunter] Search sweep complete for {len(org_ids)} orgs")
    return results


async def run_stale_job_cleanup() -> dict:
    """Permanently purge listings older than five days after a recent
    successful source refresh. Application-tracked rows are retained as
    inactive history so notes and application records remain usable."""
    from datetime import datetime, timezone, timedelta
    # Require a recent complete sweep before expiring anything. If the
    # crawler is down, old listings remain available instead of being
    # hidden merely because no refresh could run.
    recent_success_cutoff = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
    org_ids = await asyncio.to_thread(repository.list_orgs_with_recent_successful_search, recent_success_cutoff)
    results = [await asyncio.to_thread(repository.purge_expired_jobs, org_id) for org_id in org_ids]
    deleted = sum(result["deleted"] for result in results)
    retained = sum(result["retained_for_applications"] for result in results)
    if deleted or retained:
        logger.info(f"[job_hunter] Retention cleanup: deleted {deleted} expired listing(s); kept {retained} for application history")
    else:
        logger.info(f"[job_hunter] Retention cleanup: no listings older than {JOB_HUNTER_RETENTION_DAYS} days")
    return {"deleted": deleted, "retained_for_applications": retained, "threshold_days": JOB_HUNTER_RETENTION_DAYS}


async def run_due_reminders() -> int:
    """Called periodically by the scheduler — raises notifications for due
    follow-up reminders. Never sends an email; the user follows up
    manually via their own inbox."""
    count = await asyncio.to_thread(service.process_due_reminders)
    if count:
        logger.info(f"[job_hunter] Triggered {count} due reminder(s)")
    return count
