"""
Background scheduler that finds all active commit_jobs across every org
and executes the ones that are due right now, based on their mode:
  - scheduled: one-time, fires once execution_at has passed
  - recurring: fires on due days per start/end/frequency (any time of day)
  - guard: fires on due days, only once the guard cutoff time has passed
"""
from datetime import date, datetime, time as dt_time
from zoneinfo import ZoneInfo
from commit_scheduler import repository, service
from config import logger

IST = ZoneInfo("Asia/Kolkata")


def _matches_frequency(job: dict, today: date) -> bool:
    start = date.fromisoformat(job["start_date"])
    end = date.fromisoformat(job["end_date"])

    if today < start or today > end:
        return False

    freq = job["frequency"]

    if freq == "daily":
        return True

    if freq == "every_2_days":
        days_since_start = (today - start).days
        return days_since_start % 2 == 0

    if freq == "weekdays":
        return today.weekday() < 5  # Mon=0 ... Fri=4

    if freq == "custom":
        custom_dates = job.get("custom_dates") or []
        return today.isoformat() in [d if isinstance(d, str) else d.isoformat() for d in custom_dates]

    return False


def _is_scheduled_due(job: dict, now_ist: datetime) -> bool:
    exec_at = job.get("execution_at")
    if not exec_at:
        return False
    exec_dt = datetime.fromisoformat(exec_at) if isinstance(exec_at, str) else exec_at
    if exec_dt.tzinfo is None:
        exec_dt = exec_dt.replace(tzinfo=IST)
    return now_ist >= exec_dt


def _is_guard_due(job: dict, today: date, now_ist: datetime) -> bool:
    if not _matches_frequency(job, today):
        return False
    cutoff = job.get("guard_cutoff_time")
    if not cutoff:
        return False
    cutoff_time = dt_time.fromisoformat(cutoff) if isinstance(cutoff, str) else cutoff
    return now_ist.time() >= cutoff_time


def is_due_now(job: dict, today: date, now_ist: datetime) -> bool:
    mode = job.get("mode", "recurring")
    if mode == "scheduled":
        return _is_scheduled_due(job, now_ist)
    if mode == "guard":
        return _is_guard_due(job, today, now_ist)
    return _matches_frequency(job, today)  # recurring


async def run_due_commit_jobs():
    now_ist = datetime.now(IST)
    today = now_ist.date()

    active_jobs = repository.list_active_jobs()
    if not active_jobs:
        return

    # Catches recurring/guard jobs whose end_date has already passed without
    # ever being marked terminal — e.g. the scheduler was down on the exact
    # end_date, so the normal "just processed the last day" completion path
    # below never ran for them. Without this, such jobs stay active forever,
    # never due again, but never marked completed either.
    for job in active_jobs:
        if job.get("mode") in ("recurring", "guard") and job.get("end_date"):
            end_date = date.fromisoformat(job["end_date"])
            if today > end_date:
                logger.info(f"Job {job['id']} ({job['repo_full_name']}) past end_date {end_date} with no terminal status — marking completed")
                repository.update_job(job["id"], {"status": "completed"})
    active_jobs = [j for j in active_jobs if j["id"] not in {
        updated["id"] for updated in []
    }]  # placeholder no-op, real filtering below via re-fetch is simpler
    active_jobs = repository.list_active_jobs()

    due_jobs = [job for job in active_jobs if is_due_now(job, today, now_ist)]
    if not due_jobs:
        return

    logger.info(f"{len(due_jobs)} of {len(active_jobs)} active commit jobs due at {now_ist.isoformat()}")

    for job in due_jobs:
        try:
            run = await service.execute_job(job)
            logger.info(f"Job {job['id']} ({job['repo_full_name']}) -> {run['status']}")

            # Recurring/guard jobs that have reached the end of their date range
            # auto-complete after their final eligible day is processed. This
            # includes both 'success' (a real run happened) and 'skipped' (guard
            # mode correctly found a real commit already existed and intentionally
            # did nothing) — both are legitimate terminal outcomes for that day.
            # 'failed' is deliberately excluded: a failure on the last day should
            # not be treated as "done," even though the job also has no future day
            # left to retry on — that gap is a separate, unresolved issue.
            if (
                job.get("mode") in ("recurring", "guard")
                and job.get("end_date") == today.isoformat()
                and run["status"] in ("success", "skipped")
            ):
                repository.update_job(job["id"], {"status": "completed"})

        except Exception as e:
            logger.error(f"Job {job['id']} failed unexpectedly: {e}")


# Backward-compatible alias — email_scheduler/scheduler_jobs.py imports this
# name directly. Keep it pointing at the same day-of-week/frequency logic.
is_due_today = _matches_frequency
