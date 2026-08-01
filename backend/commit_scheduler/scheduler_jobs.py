"""
Background scheduler that finds all active commit_jobs across every org
and executes the ones that are due today, based on their frequency.
"""
from datetime import date, timedelta
from commit_scheduler import repository, service
from config import logger


def is_due_today(job: dict, today: date) -> bool:
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


async def run_due_commit_jobs():
    today = date.today()
    logger.info(f"Checking commit_jobs due for {today.isoformat()}")

    active_jobs = repository.list_active_jobs()
    if not active_jobs:
        logger.info("No active commit jobs found")
        return

    due_jobs = [job for job in active_jobs if is_due_today(job, today)]
    logger.info(f"{len(due_jobs)} of {len(active_jobs)} active jobs are due today")

    for job in due_jobs:
        try:
            run = await service.execute_job(job)
            logger.info(f"Job {job['id']} ({job['repo_full_name']}) -> {run['status']}")

            if job["end_date"] == today.isoformat() and run["status"] == "success":
                repository.update_job(job["id"], {"status": "completed"})

        except Exception as e:
            logger.error(f"Job {job['id']} failed unexpectedly: {e}")
