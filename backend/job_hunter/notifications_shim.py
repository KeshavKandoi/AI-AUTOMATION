"""
Shared notify()+log_event() logic for a discovered/updated job, extracted
from the notification block inside the original
job_hunter.service.ingest_discovered_job() so job_hunter/batch_ingest.py
can reuse the exact same behavior without duplicating it. Verbatim
extraction -- no logic changes from the original inline block.
"""
from datetime import datetime, timezone

from job_hunter.service import MODULE
from audit_logs.service import log_event
from notifications.service import notify


def notify_job_match(organization_id: str, job: dict, raw_job, is_new: bool) -> None:
    """job is the upserted/created DB row (must have 'id'). raw_job is the
    RawJob this came from (must have job_title, company_name, location,
    platform)."""
    notify(
        organization_id=organization_id,
        module=MODULE,
        category="new_job_match" if is_new else "job_updated",
        priority="normal",
        title=f"{'New job match' if is_new else 'Job updated'}: {raw_job.job_title} at {raw_job.company_name}",
        body=f"{raw_job.company_name} — {raw_job.job_title}" + (f" ({raw_job.location})" if raw_job.location else ""),
        resource_type="job_hunter_job",
        resource_id=job["id"],
        action_url=f"/job-hunter/jobs/{job['id']}",
        action_label="View Job",
        metadata={"platform": raw_job.platform, "company_name": raw_job.company_name, "job_title": raw_job.job_title},
        dedup_key=f"job_hunter:job_match:{job['id']}" if is_new else f"job_hunter:job_updated:{job['id']}:{datetime.now(timezone.utc).date().isoformat()}",
    )
    log_event(
        organization_id=organization_id,
        module=MODULE,
        action="job_discovered" if is_new else "job_updated",
        summary=f"{'Discovered' if is_new else 'Updated'} job: {raw_job.job_title} at {raw_job.company_name} (via {raw_job.platform})",
        status="success",
        resource_type="job_hunter_job",
        resource_id=job["id"],
        metadata={"platform": raw_job.platform},
        source="scheduler",
    )
