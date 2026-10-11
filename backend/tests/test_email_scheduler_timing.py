from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch

import email_scheduler.scheduler_jobs as scheduler_jobs
import email_scheduler.service as email_service

IST = ZoneInfo("Asia/Kolkata")


def test_scheduled_email_waits_for_configured_send_time_in_ist():
    job = {
        "start_date": "2026-10-11",
        "end_date": "2026-10-11",
        "frequency": "daily",
        "send_time": "09:00:00",
    }
    assert not scheduler_jobs.is_job_due(job, datetime(2026, 10, 11, 8, 59, tzinfo=IST))
    assert scheduler_jobs.is_job_due(job, datetime(2026, 10, 11, 9, 0, tzinfo=IST))
    assert scheduler_jobs.is_job_due(job, datetime(2026, 10, 11, 3, 30, tzinfo=ZoneInfo("UTC")))


def test_recorded_failed_send_is_not_retried_automatically(monkeypatch):
    monkeypatch.setattr(email_service.repository, "get_run_for_date", lambda job_id, run_date: {"status": "failed"})
    with patch.object(email_service, "reserve_gmail_send") as reserve, \
         patch.object(email_service.repository, "create_run") as create_run:
        run = __import__("asyncio").run(email_service.execute_job({"id": "job-1"}))

    assert run["status"] == "skipped"
    reserve.assert_not_called()
    create_run.assert_not_called()


def test_run_now_does_not_repeat_a_successful_same_day_email(monkeypatch):
    monkeypatch.setattr(email_service.repository, "get_run_for_date", lambda job_id, run_date: {"status": "success"})
    with patch.object(email_service, "reserve_gmail_send") as reserve:
        run = __import__("asyncio").run(email_service.execute_job({"id": "job-1"}, force=True))
    assert run["status"] == "skipped"
    reserve.assert_not_called()
