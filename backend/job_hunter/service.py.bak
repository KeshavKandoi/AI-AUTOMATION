"""
Business logic for Job Hunter: preferences, job discovery/dedup/merge, and
application tracking. Platform adapters (LinkedIn, Indeed, Greenhouse, etc.)
and the 6-hourly scheduler call ingest_discovered_job() — they never touch
the repository or notifications/audit_logs directly, so every discovery
path gets consistent dedup, audit logging, and notification behavior for
free.
"""
import hashlib
import re
from typing import Optional
from fastapi import HTTPException

from config import logger
from job_hunter import repository
from job_hunter.schemas import JobHunterPreferencesCreate, JobHunterPreferencesUpdate
from audit_logs.service import log_event
from notifications.service import notify

MODULE = "job_hunter"


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

def get_preferences(organization_id: str) -> Optional[dict]:
    return repository.get_preferences(organization_id)


def save_preferences(organization_id: str, payload: JobHunterPreferencesCreate) -> dict:
    row = payload.model_dump(mode="json")
    row["onboarding_completed"] = True
    saved = repository.upsert_preferences(organization_id, row)

    log_event(
        organization_id=organization_id,
        module=MODULE,
        action="preferences_saved",
        summary="Job Hunter preferences saved and onboarding completed",
        status="success",
        resource_type="job_hunter_preferences",
        resource_id=saved["id"],
        metadata={"desired_roles": row.get("desired_roles"), "skills_count": len(row.get("skills", []))},
        source="backend",
    )
    return saved


def update_preferences(organization_id: str, payload: JobHunterPreferencesUpdate) -> dict:
    existing = repository.get_preferences(organization_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Job Hunter preferences not found — complete onboarding first")

    updates = {k: v for k, v in payload.model_dump(mode="json").items() if v is not None}
    saved = repository.upsert_preferences(organization_id, updates)

    log_event(
        organization_id=organization_id,
        module=MODULE,
        action="preferences_updated",
        summary="Job Hunter preferences updated",
        status="success",
        resource_type="job_hunter_preferences",
        resource_id=saved["id"],
        metadata={"updated_fields": list(updates.keys())},
        source="backend",
    )
    return saved


# ---------------------------------------------------------------------------
# Job discovery, dedup, merge
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    """Strips scheme, query params, and trailing slash so the same posting
    linked with different tracking params still dedups correctly."""
    url = re.sub(r"^https?://", "", url.strip().lower())
    url = url.split("?")[0].split("#")[0]
    return url.rstrip("/")


def build_dedup_key(company_name: str, job_title: str, location: Optional[str], original_apply_url: str) -> str:
    """Deterministic key used to merge the same real-world job posting found
    across multiple platforms. Prefers the normalized apply URL when present
    since it's the most reliable identifier; falls back to company+title+
    location so postings without a stable canonical URL still dedup."""
    normalized_url = _normalize_url(original_apply_url) if original_apply_url else ""
    parts = "|".join([
        company_name.strip().lower(),
        job_title.strip().lower(),
        (location or "").strip().lower(),
        normalized_url,
    ])
    return hashlib.sha256(parts.encode()).hexdigest()[:32]


def ingest_discovered_job(
    organization_id: str,
    company_name: str,
    job_title: str,
    original_apply_url: str,
    platform: str,
    platform_url: str,
    platform_job_id: Optional[str] = None,
    location: Optional[str] = None,
    work_mode: Optional[str] = None,
    employment_type: Optional[str] = None,
    experience_required: Optional[str] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    salary_currency: Optional[str] = None,
    description: Optional[str] = None,
    responsibilities: Optional[str] = None,
    required_skills: Optional[list[str]] = None,
    qualifications: Optional[str] = None,
    benefits: Optional[str] = None,
    company_info: Optional[str] = None,
    posted_at: Optional[str] = None,
) -> dict:
    """
    Single entry point every platform adapter calls when it finds a job
    posting. Handles: dedup/merge against existing jobs, recording which
    platform(s) a job was found on, and raising a "new job match"
    notification exactly once per job (never re-notifies on re-discovery
    unless content meaningfully changed — see _content_changed below).
    """
    from datetime import datetime, timezone

    dedup_key = build_dedup_key(company_name, job_title, location, original_apply_url)
    existing = repository.get_job_by_dedup_key(organization_id, dedup_key)

    if existing:
        job = existing
        content_changed = _content_changed(existing, description, salary_min, salary_max)
        repository.update_job(job["id"], {
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            **({"description": description} if description else {}),
            **({"salary_min": salary_min} if salary_min is not None else {}),
            **({"salary_max": salary_max} if salary_max is not None else {}),
        })
        is_new = False
    else:
        job = repository.create_job({
            "organization_id": organization_id,
            "dedup_key": dedup_key,
            "company_name": company_name,
            "job_title": job_title,
            "location": location,
            "work_mode": work_mode,
            "employment_type": employment_type,
            "experience_required": experience_required,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "description": description,
            "responsibilities": responsibilities,
            "required_skills": required_skills or [],
            "qualifications": qualifications,
            "benefits": benefits,
            "company_info": company_info,
            "original_apply_url": original_apply_url,
            "posted_at": posted_at,
        })
        is_new = True
        content_changed = False

    # Record this platform as a source for the job (badge on the job card).
    # No-ops if this exact (job, platform, url) was already recorded.
    repository.add_job_source({
        "job_id": job["id"],
        "platform": platform,
        "platform_job_id": platform_job_id,
        "platform_url": platform_url,
    })

    if is_new or content_changed:
        notify(
            organization_id=organization_id,
            module=MODULE,
            category="new_job_match" if is_new else "job_updated",
            priority="normal",
            title=f"{'New job match' if is_new else 'Job updated'}: {job_title} at {company_name}",
            body=f"{company_name} — {job_title}" + (f" ({location})" if location else ""),
            resource_type="job_hunter_job",
            resource_id=job["id"],
            action_url=f"/job-hunter/jobs/{job['id']}",
            action_label="View Job",
            metadata={"platform": platform, "company_name": company_name, "job_title": job_title},
            dedup_key=f"job_hunter:job_match:{job['id']}" if is_new else f"job_hunter:job_updated:{job['id']}:{datetime.now(timezone.utc).date().isoformat()}",
        )
        log_event(
            organization_id=organization_id,
            module=MODULE,
            action="job_discovered" if is_new else "job_updated",
            summary=f"{'Discovered' if is_new else 'Updated'} job: {job_title} at {company_name} (via {platform})",
            status="success",
            resource_type="job_hunter_job",
            resource_id=job["id"],
            metadata={"platform": platform},
            source="scheduler",
        )

    return job


def _content_changed(existing: dict, new_description: Optional[str], new_salary_min, new_salary_max) -> bool:
    """Meaningful-change detection so re-discovery doesn't spam notifications
    — only flags a change when description or salary actually differ."""
    if new_description and new_description != existing.get("description"):
        return True
    if new_salary_min is not None and new_salary_min != existing.get("salary_min"):
        return True
    if new_salary_max is not None and new_salary_max != existing.get("salary_max"):
        return True
    return False


def list_jobs(organization_id: str, limit: int = 50, offset: int = 0, **filters) -> dict:
    jobs, total = repository.list_jobs(organization_id, limit=limit, offset=offset, **filters)
    sources_by_job = repository.get_sources_for_jobs([j["id"] for j in jobs])
    for job in jobs:
        job["sources"] = sources_by_job.get(job["id"], [])
    return {"items": jobs, "total": total, "limit": limit, "offset": offset}


def get_job_with_sources(job_id: str, organization_id: str) -> dict:
    job = repository.get_job(job_id, organization_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job["sources"] = repository.get_job_sources(job_id)
    return job


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

def get_or_create_application(organization_id: str, job_id: str, initial_status: str = "saved") -> dict:
    job = repository.get_job(job_id, organization_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = repository.get_application_by_job(organization_id, job_id)
    if existing:
        return existing

    application = repository.create_application({
        "organization_id": organization_id,
        "job_id": job_id,
        "status": initial_status,
    })
    repository.add_activity({
        "application_id": application["id"],
        "event_type": "status_changed",
        "summary": f"Job {'saved' if initial_status == 'saved' else 'added with status ' + initial_status}",
        "metadata": {"status": initial_status},
        "source": "user",
    })
    log_event(
        organization_id=organization_id,
        module=MODULE,
        action="application_created",
        summary=f"Started tracking: {job['job_title']} at {job['company_name']} ({initial_status})",
        status="success",
        resource_type="job_hunter_application",
        resource_id=application["id"],
        metadata={"job_id": job_id, "status": initial_status},
        source="backend",
    )
    return application


NOTIFY_WORTHY_STATUSES = {
    "interview": ("interview_invite", "high", "Interview scheduled"),
    "hr_round": ("interview_invite", "high", "HR round scheduled"),
    "technical_round": ("interview_invite", "high", "Technical round scheduled"),
    "final_round": ("interview_invite", "high", "Final round scheduled"),
    "offer": ("offer", "urgent", "Offer received"),
    "rejected": ("rejection", "normal", "Application rejected"),
}


def update_application_status(organization_id: str, application_id: str, new_status: str) -> dict:
    application = repository.get_application(application_id, organization_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    old_status = application["status"]
    if old_status == new_status:
        return application

    updates = {"status": new_status}
    from datetime import datetime, timezone
    if new_status == "applied" and not application.get("applied_at"):
        updates["applied_at"] = datetime.now(timezone.utc).isoformat()

    updated = repository.update_application(application_id, updates)

    job = repository.get_job(application["job_id"], organization_id)
    job_label = f"{job['job_title']} at {job['company_name']}" if job else "job"

    repository.add_activity({
        "application_id": application_id,
        "event_type": "status_changed",
        "summary": f"Status changed from {old_status} to {new_status}",
        "metadata": {"old_status": old_status, "new_status": new_status},
        "source": "user",
    })

    log_event(
        organization_id=organization_id,
        module=MODULE,
        action="application_status_changed",
        summary=f"{job_label}: {old_status} -> {new_status}",
        status="success",
        resource_type="job_hunter_application",
        resource_id=application_id,
        metadata={"old_status": old_status, "new_status": new_status},
        source="backend",
    )

    if new_status in NOTIFY_WORTHY_STATUSES:
        category, priority, label = NOTIFY_WORTHY_STATUSES[new_status]
        notify(
            organization_id=organization_id,
            module=MODULE,
            category=category,
            priority=priority,
            title=f"{label}: {job_label}",
            body=f"Your application for {job_label} moved to '{new_status.replace('_', ' ')}'.",
            resource_type="job_hunter_application",
            resource_id=application_id,
            action_url=f"/job-hunter/applications/{application_id}",
            action_label="View Application",
            metadata={"old_status": old_status, "new_status": new_status},
            dedup_key=f"job_hunter:status:{application_id}:{new_status}",
        )

    return updated


def get_application_detail(organization_id: str, application_id: str) -> dict:
    application = repository.get_application(application_id, organization_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job = repository.get_job(application["job_id"], organization_id)
    if job:
        job["sources"] = repository.get_job_sources(job["id"])

    application["job"] = job
    application["activity"] = repository.list_activity(application_id)
    application["notes"] = repository.list_notes(application_id)
    application["attachments"] = repository.list_attachments(application_id)
    application["reminders"] = repository.list_reminders(application_id)
    return application


def list_applications(organization_id: str, status: Optional[str] = None) -> list[dict]:
    return repository.list_applications(organization_id, status=status)


def add_note(organization_id: str, application_id: str, content: str) -> dict:
    application = repository.get_application(application_id, organization_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    note = repository.add_note({"application_id": application_id, "content": content})
    log_event(
        organization_id=organization_id,
        module=MODULE,
        action="note_added",
        summary="Private note added to application",
        status="success",
        resource_type="job_hunter_application",
        resource_id=application_id,
        source="backend",
    )
    return note


ALLOWED_ATTACHMENT_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
    "text/plain",
}
MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10MB — matches the bucket-level cap


def add_attachment(
    organization_id: str,
    application_id: str,
    file_name: str,
    file_bytes: bytes,
    content_type: str,
    file_type: str,
) -> dict:
    """Real upload: validates the file, uploads bytes to the private
    Supabase Storage bucket under an org-and-application-scoped path
    (never a client-supplied path), then creates the DB row pointing at
    the real storage path. Raises on validation failure or upload
    failure — never creates a DB row for a file that didn't actually
    upload."""
    application = repository.get_application(application_id, organization_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(file_bytes) > MAX_ATTACHMENT_SIZE_BYTES:
        raise HTTPException(status_code=400, detail=f"File exceeds the 10MB size limit")
    if content_type not in ALLOWED_ATTACHMENT_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type}")

    try:
        storage_path = repository.upload_attachment_file(
            organization_id, application_id, file_name, file_bytes, content_type
        )
    except Exception as e:
        logger.error(f"Attachment upload failed for application {application_id}: {e}")
        raise HTTPException(status_code=502, detail="Failed to upload file. Please try again.")

    attachment = repository.add_attachment({
        "application_id": application_id,
        "file_name": file_name,
        "storage_path": storage_path,
        "file_type": file_type,
        "size_bytes": len(file_bytes),
    })
    log_event(
        organization_id=organization_id,
        module=MODULE,
        action="attachment_added",
        summary=f"Attachment added: {file_name} ({file_type})",
        status="success",
        resource_type="job_hunter_application",
        resource_id=application_id,
        metadata={"file_type": file_type, "size_bytes": len(file_bytes)},
        source="backend",
    )
    return attachment


def get_attachment_download_url(organization_id: str, application_id: str, attachment_id: str) -> str:
    """Returns a short-lived signed URL for downloading a private
    attachment. Verifies the attachment actually belongs to an
    application under this organization before generating the URL —
    never trusts attachment_id alone."""
    application = repository.get_application(application_id, organization_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    attachment = repository.get_attachment(attachment_id)
    if not attachment or attachment["application_id"] != application_id:
        raise HTTPException(status_code=404, detail="Attachment not found")

    try:
        return repository.get_attachment_signed_url(attachment["storage_path"])
    except Exception as e:
        logger.error(f"Failed to generate signed URL for attachment {attachment_id}: {e}")
        raise HTTPException(status_code=502, detail="Failed to generate download link. Please try again.")


def delete_attachment(organization_id: str, application_id: str, attachment_id: str) -> None:
    """Deletes both the storage object and the DB row. Deletes the DB
    row only after the storage delete succeeds, to avoid an orphaned
    file with no DB row pointing at it (a silent storage leak) — but
    if the storage object is already gone (e.g. manual cleanup), we
    still remove the stale DB row rather than leave it dangling
    forever."""
    application = repository.get_application(application_id, organization_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    attachment = repository.get_attachment(attachment_id)
    if not attachment or attachment["application_id"] != application_id:
        raise HTTPException(status_code=404, detail="Attachment not found")

    try:
        repository.delete_attachment_file(attachment["storage_path"])
    except Exception as e:
        logger.warning(f"Storage delete failed for attachment {attachment_id} (removing DB row anyway): {e}")

    repository.delete_attachment_row(attachment_id)
    log_event(
        organization_id=organization_id,
        module=MODULE,
        action="attachment_deleted",
        summary=f"Attachment deleted: {attachment['file_name']}",
        status="success",
        resource_type="job_hunter_application",
        resource_id=application_id,
        source="backend",
    )


def create_reminder(organization_id: str, application_id: str, remind_at: str, note: Optional[str]) -> dict:
    application = repository.get_application(application_id, organization_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    reminder = repository.add_reminder({
        "application_id": application_id,
        "organization_id": organization_id,
        "remind_at": remind_at,
        "note": note,
    })
    log_event(
        organization_id=organization_id,
        module=MODULE,
        action="reminder_created",
        summary=f"Follow-up reminder set for {remind_at}",
        status="success",
        resource_type="job_hunter_application",
        resource_id=application_id,
        metadata={"remind_at": remind_at},
        source="backend",
    )
    return reminder


def process_due_reminders() -> int:
    """Called by the scheduler (not by the user) — raises a notification for
    each due reminder and marks it notified. Never sends an email; the
    person follows up manually."""
    due = repository.get_due_reminders()
    count = 0
    for reminder in due:
        application = repository.get_application(reminder["application_id"], reminder["organization_id"])
        job_label = "your application"
        if application:
            job = repository.get_job(application["job_id"], reminder["organization_id"])
            if job:
                job_label = f"{job['job_title']} at {job['company_name']}"

        notify(
            organization_id=reminder["organization_id"],
            module=MODULE,
            category="follow_up_reminder",
            priority="normal",
            title=f"Follow-up reminder: {job_label}",
            body=reminder.get("note") or f"Time to follow up on {job_label}.",
            resource_type="job_hunter_application",
            resource_id=reminder["application_id"],
            action_url=f"/job-hunter/applications/{reminder['application_id']}",
            action_label="View Application",
            dedup_key=f"job_hunter:reminder:{reminder['id']}",
        )
        repository.mark_reminder_notified(reminder["id"])
        log_event(
            organization_id=reminder["organization_id"],
            module=MODULE,
            action="reminder_triggered",
            summary=f"Follow-up reminder triggered: {job_label}",
            status="success",
            resource_type="job_hunter_application",
            resource_id=reminder["application_id"],
            source="scheduler",
        )
        count += 1
    return count
