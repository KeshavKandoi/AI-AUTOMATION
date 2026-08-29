"""
Google Calendar sync for Job Hunter interviews. Creates, updates, or
cancels calendar events based on Gmail-detected interview invitations,
reschedules, and cancellations.

Reuses calendar_automation.service._get_calendar_token_for_org() exactly
as-is (it's the most robust token resolution in the codebase — tries
multiple integration rows if the most recent fails) and the proven
Google Calendar API call shape already used in main.py and
calendar_automation.service. No new auth, no new API client — this file
is orchestration + persistence on top of what already exists.

Idempotency guarantee: enforced at two levels —
1. DB constraint: unique(organization_id, gmail_message_id) on
   job_hunter_calendar_events means the same email can never produce two
   rows.
2. Runtime check: sync_interview_event() checks
   get_calendar_event_by_gmail_message() before doing anything, so even
   if called twice for the same message (e.g. overlapping scheduler
   runs, though the Gmail poll concurrency lock should already prevent
   that), the second call is a safe no-op.
"""
import httpx
from datetime import datetime, timezone

from config import logger
from job_hunter import repository
from job_hunter.interview_datetime_extractor import ExtractedInterview
from calendar_automation.service import _get_calendar_token_for_org
from audit_logs.service import log_event
from notifications.service import notify

MODULE = "job_hunter"
CALENDAR_API_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


async def sync_interview_event(
    organization_id: str,
    application_id: str,
    job: dict,
    gmail_message_id: str,
    gmail_thread_id: str,
    gmail_history_id: str,
    extracted: ExtractedInterview,
) -> dict:
    """Creates a new calendar event for a fresh interview_invite. Called
    only when extraction succeeded (structured or high-confidence LLM) —
    callers must check for None from the extractor before calling this."""
    existing = repository.get_calendar_event_by_gmail_message(organization_id, gmail_message_id)
    if existing:
        logger.info(f"[job_hunter] Calendar event already exists for gmail_message_id={gmail_message_id} — skipping duplicate creation")
        return existing

    row = repository.create_calendar_event_row({
        "organization_id": organization_id,
        "application_id": application_id,
        "gmail_message_id": gmail_message_id,
        "gmail_thread_id": gmail_thread_id,
        "gmail_history_id": gmail_history_id,
        "meeting_link": extracted.meeting_link,
        "extracted_start_time": extracted.start_time.isoformat() if extracted.start_time else None,
        "extracted_end_time": extracted.end_time.isoformat() if extracted.end_time else None,
        "timezone": extracted.timezone,
        "extraction_source": extracted.source,
        "extraction_confidence": extracted.confidence,
        "extraction_explanation": extracted.explanation,
        "sync_status": "pending",
    })

    try:
        access_token = _get_calendar_token_for_org(organization_id)
    except Exception as e:
        logger.error(f"[job_hunter] No Calendar integration for org {organization_id}: {e}")
        repository.update_calendar_event_row(row["id"], {"sync_status": "failed"})
        return row

    summary = f"Interview: {job.get('job_title', 'Role')} at {job.get('company_name', 'Company')}"
    description_parts = []
    if extracted.meeting_link:
        description_parts.append(f"Meeting link: {extracted.meeting_link}")
    if extracted.interviewer:
        description_parts.append(f"Interviewer: {extracted.interviewer}")
    description_parts.append(f"Auto-created from Gmail by Workforge Job Hunter (extraction: {extracted.source}, confidence: {extracted.confidence:.0f}%)")
    description = "\n".join(description_parts)

    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": extracted.start_time.isoformat()},
        "end": {"dateTime": (extracted.end_time or extracted.start_time).isoformat()},
    }
    if extracted.meeting_link:
        event_body["location"] = extracted.meeting_link

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                CALENDAR_API_EVENTS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                json=event_body,
            )
        if res.status_code not in (200, 201):
            raise RuntimeError(f"Calendar API error {res.status_code}: {res.text[:200]}")

        event = res.json()
        updated_row = repository.update_calendar_event_row(row["id"], {
            "google_calendar_event_id": event.get("id"),
            "google_calendar_status": event.get("status"),
            "sync_status": "created",
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
        })

        log_event(
            organization_id=organization_id, module=MODULE, action="calendar_event_created",
            summary=f"Calendar event created: {summary}", status="success",
            resource_type="job_hunter_application", resource_id=application_id,
            metadata={"event_id": event.get("id"), "extraction_source": extracted.source},
            source="scheduler",
        )
        notify(
            organization_id=organization_id, module=MODULE, category="interview_scheduled",
            priority="high", title=f"Interview scheduled: {job.get('job_title')} at {job.get('company_name')}",
            body=f"Added to your calendar for {extracted.start_time.strftime('%B %d, %Y at %I:%M %p')}.",
            resource_type="job_hunter_application", resource_id=application_id,
            action_url=f"/job-hunter/applications/{application_id}", action_label="View Application",
            dedup_key=f"job_hunter:calendar_event:{gmail_message_id}",
        )
        return updated_row

    except Exception as e:
        logger.error(f"[job_hunter] Failed to create calendar event for application {application_id}: {e}")
        repository.update_calendar_event_row(row["id"], {"sync_status": "failed"})
        log_event(
            organization_id=organization_id, module=MODULE, action="calendar_event_failed",
            summary=f"Failed to create calendar event: {e}", status="failed",
            resource_type="job_hunter_application", resource_id=application_id,
            error_message=str(e), source="scheduler",
        )
        return row


async def update_interview_event(
    organization_id: str,
    application_id: str,
    gmail_message_id: str,
    gmail_history_id: str,
    extracted: ExtractedInterview,
) -> dict | None:
    """Updates the EXISTING calendar event for this application (a
    reschedule) rather than creating a new one. Returns None if there's
    no existing event to update — caller should fall back to creating a
    fresh event in that case (a reschedule email arriving with no prior
    tracked interview is a legitimate edge case, e.g. initial invite was
    missed/unparseable)."""
    existing = repository.get_active_calendar_event_for_application(organization_id, application_id)
    if not existing or not existing.get("google_calendar_event_id"):
        return None

    try:
        access_token = _get_calendar_token_for_org(organization_id)
        event_body = {
            "start": {"dateTime": extracted.start_time.isoformat()},
            "end": {"dateTime": (extracted.end_time or extracted.start_time).isoformat()},
        }
        if extracted.meeting_link:
            event_body["location"] = extracted.meeting_link

        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.patch(
                f"{CALENDAR_API_EVENTS_URL}/{existing['google_calendar_event_id']}",
                headers={"Authorization": f"Bearer {access_token}"},
                json=event_body,
            )
        if res.status_code != 200:
            raise RuntimeError(f"Calendar API update error {res.status_code}: {res.text[:200]}")

        updated_row = repository.update_calendar_event_row(existing["id"], {
            "gmail_message_id": gmail_message_id,   # track the reschedule email that triggered this update
            "gmail_history_id": gmail_history_id,
            "extracted_start_time": extracted.start_time.isoformat(),
            "extracted_end_time": (extracted.end_time or extracted.start_time).isoformat(),
            "extraction_source": extracted.source,
            "extraction_confidence": extracted.confidence,
            "sync_status": "updated",
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
        })

        log_event(
            organization_id=organization_id, module=MODULE, action="calendar_event_rescheduled",
            summary="Calendar event updated due to reschedule", status="success",
            resource_type="job_hunter_application", resource_id=application_id,
            source="scheduler",
        )
        notify(
            organization_id=organization_id, module=MODULE, category="interview_rescheduled",
            priority="high", title="Interview rescheduled",
            body=f"Updated to {extracted.start_time.strftime('%B %d, %Y at %I:%M %p')}.",
            resource_type="job_hunter_application", resource_id=application_id,
            action_url=f"/job-hunter/applications/{application_id}", action_label="View Application",
            dedup_key=f"job_hunter:calendar_reschedule:{gmail_message_id}",
        )
        return updated_row

    except Exception as e:
        logger.error(f"[job_hunter] Failed to reschedule calendar event for application {application_id}: {e}")
        return None


async def cancel_interview_event(organization_id: str, application_id: str) -> bool:
    """Cancels/deletes the existing calendar event for an application
    (e.g. on withdrawal or rejection). Safe no-op if there's no active
    event to cancel."""
    existing = repository.get_active_calendar_event_for_application(organization_id, application_id)
    if not existing or not existing.get("google_calendar_event_id"):
        return False

    try:
        access_token = _get_calendar_token_for_org(organization_id)
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.delete(
                f"{CALENDAR_API_EVENTS_URL}/{existing['google_calendar_event_id']}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        # Google returns 204 on success, 410 if already deleted — both are fine
        if res.status_code not in (204, 410):
            raise RuntimeError(f"Calendar API delete error {res.status_code}: {res.text[:200]}")

        repository.update_calendar_event_row(existing["id"], {
            "sync_status": "cancelled",
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
        })
        log_event(
            organization_id=organization_id, module=MODULE, action="calendar_event_cancelled",
            summary="Calendar event cancelled", status="success",
            resource_type="job_hunter_application", resource_id=application_id,
            source="scheduler",
        )
        return True

    except Exception as e:
        logger.error(f"[job_hunter] Failed to cancel calendar event for application {application_id}: {e}")
        return False
