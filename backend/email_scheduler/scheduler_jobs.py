from datetime import datetime, time
from zoneinfo import ZoneInfo
from email_scheduler import repository, service
from commit_scheduler.scheduler_jobs import is_due_today
from config import logger

IST = ZoneInfo("Asia/Kolkata")


def is_job_due(job: dict, now: datetime) -> bool:
    """Check schedule frequency and configured send time in India Standard Time."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=IST)
    now_ist = now.astimezone(IST)
    if not is_due_today(job, now_ist.date()):
        return False
    send_time = job.get("send_time", "09:00:00")
    if isinstance(send_time, str):
        send_time = time.fromisoformat(send_time)
    return now_ist.time().replace(tzinfo=None) >= send_time

async def run_due_email_jobs():
    now_ist = datetime.now(IST)
    today = now_ist.date()
    logger.info(f"Checking email_jobs due for {today.isoformat()}")

    active_jobs = repository.list_active_jobs()
    due_jobs = [job for job in active_jobs if is_job_due(job, now_ist)]
    logger.info(f"{len(due_jobs)} of {len(active_jobs)} active email jobs due today")

    for job in due_jobs:
        try:
            run = await service.execute_job(job)
            logger.info(f"Email job {job['id']} ({job['to_email']}) -> {run['status']}")
            if job["end_date"] == today.isoformat() and run["status"] == "success":
                repository.update_job(job["id"], {"status": "completed"})
        except Exception as e:
            logger.error(f"Email job {job['id']} failed unexpectedly: {e}")
