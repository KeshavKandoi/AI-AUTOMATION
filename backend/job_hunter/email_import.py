import hashlib
import re
from datetime import datetime

from config import logger
from job_hunter import repository, service
from job_hunter.gmail_classifier import classify_email
from job_hunter.gmail_matcher import find_best_match
from job_hunter.interview_datetime_extractor import extract_interview_datetime
from job_hunter.calendar_integration import sync_interview_event, update_interview_event, cancel_interview_event
from audit_logs.service import log_event

MODULE = "job_hunter"

TERMINAL_STATUSES = ("rejected", "archived", "offer")

STATUS_MAP = {
    "interview_invite": "interview",
    "assessment": "assessment",
    "rejection": "rejected",
    "offer": "offer",
    "withdrawal": "archived",
}


def _get_verified_domain_for_job(job: dict):
    if job.get("original_apply_url"):
        sources = repository.get_job_sources(job["id"])
        career_page_sources = [s for s in sources if s["platform"] == "career_pages"]
        if career_page_sources:
            match = re.search(r"https?://(?:www\.)?([a-zA-Z0-9.-]+)", career_page_sources[0]["platform_url"])
            if match:
                return match.group(1).lower()
    return None


def _import_message_id(subject: str, sender: str, body: str) -> str:
    normalized = " ".join(f"{subject} {body}".split()).lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:40]
    return f"manual:{digest}"


def _same_start(existing: dict, start) -> bool:
    try:
        return datetime.fromisoformat(str(existing["extracted_start_time"]).replace("Z", "+00:00")) == start
    except Exception:
        return False


async def process_imported_email(
    organization_id: str,
    subject: str,
    body: str,
    sender: str = "",
    recipient: str = "",
    application_id_hint: str | None = None,
) -> dict:
    subject = subject or ""
    body = body or ""
    sender = sender or ""
    recipient = recipient or ""
    message_id = _import_message_id(subject, sender, body)

    all_applications = repository.list_applications(organization_id, status=None)
    hinted = None
    if application_id_hint:
        hinted = next((a for a in all_applications if a["id"] == application_id_hint), None)
        if not hinted:
            raise LookupError("application not found")

    if repository.gmail_message_already_processed(organization_id, message_id):
        return {
            "duplicate": True, "message_id": message_id, "category": None,
            "application_id": None, "applications_updated": 0, "calendar_action": None,
        }

    preferences = repository.get_preferences(organization_id) or {}
    onboarding_email = preferences.get("email", "")

    candidates = []
    job_map = {}
    for app in all_applications:
        is_hinted = bool(hinted and app["id"] == hinted["id"])
        is_terminal = app["status"] in TERMINAL_STATUSES
        if is_terminal and not is_hinted:
            continue
        job = repository.get_job(app["job_id"], organization_id)
        if not job:
            continue
        job_map[app["id"]] = job
        if not is_terminal:
            candidates.append((app, job, _get_verified_domain_for_job(job)))

    classification = classify_email(subject, body[:2000])
    category = classification.category

    match_result = None
    if category != "not_recruitment" and candidates and not hinted:
        match_result = find_best_match(
            sender_email=sender,
            subject=subject,
            body_snippet=body[:1000],
            recipient_email=recipient,
            onboarding_email=onboarding_email,
            candidates=candidates,
        )

    application_id = None
    final_category = category
    applications_updated = 0
    calendar_action = None

    if category != "not_recruitment":
        if hinted:
            application_id = hinted["id"]
        elif match_result and match_result.is_confident:
            application_id = match_result.application_id

    if application_id:
        new_status = STATUS_MAP.get(category)
        if new_status:
            try:
                service.update_application_status(organization_id, application_id, new_status)
                applications_updated += 1
            except Exception as e:
                logger.error(f"[job_hunter] Failed to update application {application_id} from imported email: {e}")

        if category == "reschedule":
            repository.add_activity({
                "application_id": application_id,
                "event_type": "gmail_detected",
                "summary": f"Interview reschedule email imported: {subject}",
                "metadata": {"import_message_id": message_id},
                "source": "user",
            })

        job_for_app = job_map.get(application_id)

        if category == "interview_invite":
            extracted = extract_interview_datetime({}, subject, body)
            existing_event = repository.get_active_calendar_event_for_application(organization_id, application_id) if extracted else None
            if extracted and job_for_app and existing_event and _same_start(existing_event, extracted.start_time):
                pass
            elif extracted and job_for_app:
                await sync_interview_event(
                    organization_id=organization_id,
                    application_id=application_id,
                    job=job_for_app,
                    gmail_message_id=message_id,
                    gmail_thread_id=None,
                    gmail_history_id=None,
                    extracted=extracted,
                )
                calendar_action = "create"
        elif category == "reschedule":
            extracted = extract_interview_datetime({}, subject, body)
            if extracted:
                updated_event = await update_interview_event(
                    organization_id=organization_id,
                    application_id=application_id,
                    gmail_message_id=message_id,
                    gmail_history_id=None,
                    extracted=extracted,
                )
                if updated_event is not None:
                    calendar_action = "update"
                elif job_for_app:
                    await sync_interview_event(
                        organization_id=organization_id,
                        application_id=application_id,
                        job=job_for_app,
                        gmail_message_id=message_id,
                        gmail_thread_id=None,
                        gmail_history_id=None,
                        extracted=extracted,
                    )
                    calendar_action = "create"
        elif category in ("withdrawal", "rejection"):
            if await cancel_interview_event(organization_id, application_id):
                calendar_action = "cancel"
    elif category == "unmatched" or match_result:
        final_category = "unmatched"

    repository.create_gmail_event({
        "organization_id": organization_id,
        "gmail_message_id": message_id,
        "gmail_thread_id": None,
        "gmail_history_id": None,
        "application_id": application_id,
        "category": final_category,
        "match_score": match_result.score if match_result else None,
        "match_signals": match_result.signals if match_result else {},
        "raw_subject": subject,
        "raw_sender": sender,
        "recipient_email": recipient,
        "has_attachments": False,
        "attachment_count": 0,
        "attachment_metadata": [],
        "extracted_metadata": classification.extracted_metadata,
    })

    if application_id:
        log_event(
            organization_id=organization_id,
            module=MODULE,
            action="email_import_status_detected",
            summary=f"Imported email: {category} detected for application (score={match_result.score if match_result else 0})",
            status="success",
            resource_type="job_hunter_application",
            resource_id=application_id,
            metadata={"category": final_category, "import_message_id": message_id},
            source="user",
        )

    return {
        "duplicate": False,
        "message_id": message_id,
        "category": final_category,
        "application_id": application_id,
        "applications_updated": applications_updated,
        "calendar_action": calendar_action,
        "match_score": match_result.score if match_result else None,
    }
