"""
Scheduler entry points for Job Hunter. Wired into scheduler.py on a
6-hour interval (search) and independently for reminders. Mirrors the
pattern of commit_scheduler/scheduler_jobs.py and
calendar_automation/scheduler_jobs.py — a thin orchestration layer that
calls into service.py, never touches the DB or platform adapters directly.
"""
from config import logger
from job_hunter import repository, service
from job_hunter.platforms import registry
from job_hunter.platforms import __init__ as _register_platforms  # noqa: F401 — triggers adapter registration
from job_hunter.retry import RetryExhaustedError
from job_hunter.batch_ingest import ingest_discovered_jobs_batch
from audit_logs.service import log_event

MODULE = "job_hunter"

# How many days a job can go without being rediscovered by any provider
# sweep before it's soft-expired (is_active set to false). Configurable
# in one place -- change this value to adjust retention behavior without
# hunting for it scattered through the codebase. Soft expiration only:
# see repository.mark_stale_jobs_inactive() -- rows are never deleted.
JOB_HUNTER_STALE_AFTER_DAYS = 30


async def run_search_for_org(organization_id: str) -> dict:
    """
    Runs a full discovery sweep for one org: fetches saved preferences,
    runs every registered provider concurrently (failures isolated per
    provider), and feeds every result through service.ingest_discovered_job()
    for dedup/merge + notification. Records the sweep in
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

    try:
        result = await registry.run_all_providers(organization_id, preferences)
        raw_jobs = result["jobs"]
        statuses = result["statuses"]

        # Batch ingestion -- replaced the original per-job sequential loop
        # (kept in job_hunter.service.ingest_discovered_job() for any
        # other caller, e.g. a future single-job admin action) after
        # measuring it took ~2.94 hours for 22,865 jobs due to 3-6
        # sequential Supabase round-trips per job. See
        # job_hunter/batch_ingest.py for the full design rationale and
        # the guarantees it preserves (dedup, is_active reactivation,
        # work_mode/employment_type self-heal, first_discovered_at/
        # last_seen_at semantics, retry-safety).
        batch_result = await ingest_discovered_jobs_batch(organization_id, raw_jobs)
        jobs_new = batch_result["jobs_new"]
        inserted = batch_result["inserted"]
        updated = batch_result["updated"]
        permanent_failures = batch_result["permanent_failure_details"]
        permanent_failure_count = batch_result["permanent_failures"]

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
        reconciled = (inserted + updated + permanent_failure_count) == len(raw_jobs)
        if not reconciled:
            logger.warning(
                f"[job_hunter] Ingestion accounting mismatch for org {organization_id}: "
                f"discovered={len(raw_jobs)} inserted={inserted} updated={updated} "
                f"permanent_failures={permanent_failure_count} "
                f"(sum={inserted + updated + permanent_failure_count})"
            )

        repository.finish_search_run(run["id"], status="success", jobs_found=len(raw_jobs), jobs_new=jobs_new)
        log_event(
            organization_id=organization_id,
            module=MODULE,
            action="search_run_completed",
            summary=f"Job search completed: {len(raw_jobs)} jobs found ({jobs_new} new, {updated} updated, {permanent_failure_count} failed) across {len(platforms)} platforms",
            status="success",
            resource_type="job_hunter_search_run",
            resource_id=run["id"],
            metadata={
                "statuses": statuses, "jobs_found": len(raw_jobs), "jobs_new": jobs_new,
                "inserted": inserted, "updated": updated,
                "permanent_failures": permanent_failure_count,
                "reconciled": reconciled,
            },
            source="scheduler",
        )
        return {
            "jobs_found": len(raw_jobs), "jobs_new": jobs_new, "statuses": statuses,
            "inserted": inserted, "updated": updated,
            "permanent_failures": permanent_failure_count,
            "permanent_failure_details": permanent_failures,
            "reconciled": reconciled,
        }

    except Exception as e:
        logger.exception(f"[job_hunter] Search run failed for org {organization_id}")
        repository.finish_search_run(run["id"], status="failed", jobs_found=0, jobs_new=0, error_message=str(e))
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
    """Called every 6 hours by the scheduler. Loops every org with
    completed Job Hunter onboarding; one org's failure never blocks the
    rest since run_search_for_org catches its own exceptions."""
    org_ids = repository.list_orgs_with_preferences()
    logger.info(f"[job_hunter] Starting 6-hourly search sweep for {len(org_ids)} orgs")

    results = {}
    for org_id in org_ids:
        results[org_id] = await run_search_for_org(org_id)

    logger.info(f"[job_hunter] Search sweep complete for {len(org_ids)} orgs")
    return results


async def run_stale_job_cleanup() -> dict:
    """Daily task (wired into scheduler.py separately from the 6-hour
    scrape interval -- this does NOT touch or replace that schedule) that
    soft-expires jobs not rediscovered within JOB_HUNTER_STALE_AFTER_DAYS.
    Idempotent: repository.mark_stale_jobs_inactive() only updates rows
    that are currently active AND past the threshold, so running this
    multiple times (e.g. a missed run catching up, or manual trigger) is
    always safe -- it never re-processes already-inactive rows or
    produces incorrect state. Never deletes anything."""
    from datetime import datetime, timezone, timedelta
    stale_before = (datetime.now(timezone.utc) - timedelta(days=JOB_HUNTER_STALE_AFTER_DAYS)).isoformat()

    count = repository.mark_stale_jobs_inactive(stale_before)
    if count:
        logger.info(f"[job_hunter] Stale-job cleanup: marked {count} job(s) inactive (not seen in {JOB_HUNTER_STALE_AFTER_DAYS}+ days)")
    else:
        logger.info(f"[job_hunter] Stale-job cleanup: no jobs past the {JOB_HUNTER_STALE_AFTER_DAYS}-day threshold")
    return {"marked_inactive": count, "threshold_days": JOB_HUNTER_STALE_AFTER_DAYS}


async def run_due_reminders() -> int:
    """Called periodically by the scheduler — raises notifications for due
    follow-up reminders. Never sends an email; the user follows up
    manually via their own inbox."""
    count = service.process_due_reminders()
    if count:
        logger.info(f"[job_hunter] Triggered {count} due reminder(s)")
    return count


async def run_gmail_poll_for_all_orgs() -> dict:
    """Called every hour by the scheduler. Loops every org with completed
    Job Hunter onboarding; one org's failure never blocks the rest since
    poll_gmail_for_org catches its own exceptions. Orgs without a
    connected Gmail integration are skipped cheaply (poll_gmail_for_org
    checks this internally and returns early)."""
    from job_hunter.gmail_integration import poll_gmail_for_org

    org_ids = repository.list_orgs_with_preferences()
    logger.info(f"[job_hunter] Starting hourly Gmail poll sweep for {len(org_ids)} orgs")

    results = {}
    for org_id in org_ids:
        results[org_id] = await poll_gmail_for_org(org_id)

    logger.info(f"[job_hunter] Gmail poll sweep complete for {len(org_ids)} orgs")
    return results
