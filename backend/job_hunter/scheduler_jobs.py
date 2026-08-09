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
from audit_logs.service import log_event

MODULE = "job_hunter"


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

        jobs_new = 0
        for raw_job in raw_jobs:
            try:
                job = service.ingest_discovered_job(
                    organization_id=organization_id,
                    company_name=raw_job.company_name,
                    job_title=raw_job.job_title,
                    original_apply_url=raw_job.original_apply_url,
                    platform=raw_job.platform,
                    platform_url=raw_job.platform_url,
                    platform_job_id=raw_job.platform_job_id,
                    location=raw_job.location,
                    work_mode=raw_job.work_mode,
                    employment_type=raw_job.employment_type,
                    experience_required=raw_job.experience_required,
                    salary_min=raw_job.salary_min,
                    salary_max=raw_job.salary_max,
                    salary_currency=raw_job.salary_currency,
                    description=raw_job.description,
                    responsibilities=raw_job.responsibilities,
                    required_skills=raw_job.required_skills,
                    qualifications=raw_job.qualifications,
                    benefits=raw_job.benefits,
                    company_info=raw_job.company_info,
                    posted_at=raw_job.posted_at,
                )
                if job.get("first_discovered_at") == job.get("last_seen_at"):
                    jobs_new += 1
            except Exception as e:
                # One bad job record should never abort the whole sweep —
                # log and continue to the next.
                logger.error(f"[job_hunter] Failed to ingest job '{raw_job.job_title}' @ {raw_job.company_name}: {e}")

        repository.finish_search_run(run["id"], status="success", jobs_found=len(raw_jobs), jobs_new=jobs_new)
        log_event(
            organization_id=organization_id,
            module=MODULE,
            action="search_run_completed",
            summary=f"Job search completed: {len(raw_jobs)} jobs found ({jobs_new} new) across {len(platforms)} platforms",
            status="success",
            resource_type="job_hunter_search_run",
            resource_id=run["id"],
            metadata={"statuses": statuses, "jobs_found": len(raw_jobs), "jobs_new": jobs_new},
            source="scheduler",
        )
        return {"jobs_found": len(raw_jobs), "jobs_new": jobs_new, "statuses": statuses}

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
