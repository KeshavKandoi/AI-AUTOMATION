from datetime import date
from email_scheduler import repository, service
from commit_scheduler.scheduler_jobs import is_due_today
from config import logger

async def run_due_email_jobs():
    today = date.today()
    logger.info(f"Checking email_jobs due for {today.isoformat()}")

    active_jobs = repository.list_active_jobs()
    due_jobs = [job for job in active_jobs if is_due_today(job, today)]
    logger.info(f"{len(due_jobs)} of {len(active_jobs)} active email jobs due today")

    for job in due_jobs:
        try:
            run = await service.execute_job(job)
            logger.info(f"Email job {job['id']} ({job['to_email']}) -> {run['status']}")
            if job["end_date"] == today.isoformat() and run["status"] == "success":
                repository.update_job(job["id"], {"status": "completed"})
        except Exception as e:
            logger.error(f"Email job {job['id']} failed unexpectedly: {e}")
