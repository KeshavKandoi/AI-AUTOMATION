"""
Gmail polling + processing for Job Hunter application-status detection.

Reuses existing platform infrastructure end-to-end:
- Token resolution: closeout._resolve_access_token(org_id, "gmail") —
  the exact mechanism every other Gmail call in main.py already uses.
- Notifications: notifications.service.notify()
- Audit logging: audit_logs.service.log_event()
- Application status updates: job_hunter.service.update_application_status()
  (never writes to job_hunter_applications directly — reuses the existing
  function so its own notification/audit-log/activity-timeline logic
  fires exactly as it does for manual status changes, with zero
  duplication).

No new auth, no new token storage, no new notification/audit-log system —
this file is orchestration on top of what already exists.
"""
import httpx
from datetime import datetime, timezone

from config import logger
from job_hunter import repository, service
from job_hunter.gmail_classifier import classify_email
from job_hunter.gmail_matcher import find_best_match
from audit_logs.service import log_event

MODULE = "job_hunter"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

# Only scan messages from the last N days each poll — avoids re-scanning
# a user's entire inbox history every run. Combined with the
# already-processed check (gmail_message_id uniqueness), this bounds API
# usage without needing Gmail's incremental history API (a real future
# enhancement — history_id is already captured in the schema for this).
POLL_LOOKBACK_DAYS = 14
MAX_MESSAGES_PER_POLL = 50


async def _list_recent_messages(client: httpx.AsyncClient, access_token: str) -> list[dict]:
    res = await client.get(
        f"{GMAIL_API_BASE}/messages",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"q": f"newer_than:{POLL_LOOKBACK_DAYS}d", "maxResults": MAX_MESSAGES_PER_POLL},
    )
    if res.status_code != 200:
        raise RuntimeError(f"Gmail list messages failed: HTTP {res.status_code} {res.text[:200]}")
    return res.json().get("messages", [])


async def _fetch_full_message(client: httpx.AsyncClient, access_token: str, message_id: str) -> dict:
    res = await client.get(
        f"{GMAIL_API_BASE}/messages/{message_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"format": "full"},
    )
    if res.status_code != 200:
        raise RuntimeError(f"Gmail fetch message {message_id} failed: HTTP {res.status_code}")
    return res.json()


def _extract_headers(msg: dict) -> dict:
    headers = msg.get("payload", {}).get("headers", [])
    return {h["name"]: h["value"] for h in headers}


def _extract_body_text(msg: dict) -> str:
    """Extracts plain-text body content, falling back to the snippet if
    the full body can't be decoded. Gmail bodies are base64url-encoded
    and can be nested in multipart payloads — walks parts recursively,
    prefers text/plain over text/html."""
    import base64

    def decode(data: str) -> str:
        try:
            return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def walk(part: dict) -> str:
        mime_type = part.get("mimeType", "")
        body_data = part.get("body", {}).get("data")
        if mime_type == "text/plain" and body_data:
            return decode(body_data)
        for sub_part in part.get("parts", []):
            result = walk(sub_part)
            if result:
                return result
        if body_data:
            return decode(body_data)
        return ""

    payload = msg.get("payload", {})
    text = walk(payload)
    return text or msg.get("snippet", "")


def _extract_attachments(msg: dict) -> list[dict]:
    attachments = []

    def walk(part: dict):
        filename = part.get("filename")
        if filename:
            attachments.append({
                "filename": filename,
                "mime_type": part.get("mimeType", "application/octet-stream"),
            })
        for sub_part in part.get("parts", []):
            walk(sub_part)

    walk(msg.get("payload", {}))
    return attachments


def _get_verified_domain_for_job(job: dict) -> str | None:
    """A domain is 'verified' only if the job's original_apply_url is on
    the company's own site (i.e. discovered via the career_pages
    provider), not an ATS-hosted board (Greenhouse/Lever/Ashby URLs are
    never the company's own domain, so extracting a domain from those
    would be misleading, not verified)."""
    if job.get("original_apply_url"):
        # career_pages-sourced jobs point directly at the company's site;
        # ATS-sourced jobs point at boards.greenhouse.io / jobs.lever.co /
        # jobs.ashbyhq.com — check the sources to see how this job was found.
        sources = repository.get_job_sources(job["id"])
        career_page_sources = [s for s in sources if s["platform"] == "career_pages"]
        if career_page_sources:
            import re
            match = re.search(r"https?://(?:www\.)?([a-zA-Z0-9.-]+)", career_page_sources[0]["platform_url"])
            if match:
                return match.group(1).lower()
    return None


async def poll_gmail_for_org(organization_id: str) -> dict:
    """
    Runs one Gmail poll for an org: fetches recent messages, skips
    already-processed ones, classifies each new message, attempts to
    match it to an open application, and updates status only on a
    confident match. Records every processed message in
    job_hunter_gmail_events regardless of outcome (matched, unmatched,
    or not_recruitment) for idempotency and auditability.
    """
    if repository.has_running_gmail_poll(organization_id):
        logger.info(f"[job_hunter] Skipping Gmail poll for org {organization_id} — a poll is already in progress")
        return {"skipped": True, "reason": "poll_already_running"}

    preferences = repository.get_preferences(organization_id)
    if not preferences or not preferences.get("onboarding_completed"):
        return {"skipped": True, "reason": "onboarding_not_completed"}

    try:
        from closeout import _resolve_access_token
        access_token = _resolve_access_token(organization_id, "gmail")
    except Exception as e:
        logger.info(f"[job_hunter] No Gmail integration connected for org {organization_id}: {e}")
        return {"skipped": True, "reason": "gmail_not_connected"}

    run = repository.create_gmail_poll_run(organization_id)
    messages_scanned = 0
    messages_processed = 0
    applications_updated = 0

    try:
        open_applications = repository.list_applications(
            organization_id, status=None
        )
        # Only match against applications not already in a terminal state —
        # no point re-detecting emails for a job already marked rejected/archived.
        open_applications = [
            a for a in open_applications if a["status"] not in ("rejected", "archived", "offer")
        ]

        candidates = []
        for app in open_applications:
            job = repository.get_job(app["job_id"], organization_id)
            if not job:
                continue
            verified_domain = _get_verified_domain_for_job(job)
            candidates.append((app, job, verified_domain))

        async with httpx.AsyncClient(timeout=20) as client:
            message_refs = await _list_recent_messages(client, access_token)
            messages_scanned = len(message_refs)

            for ref in message_refs:
                message_id = ref["id"]

                if repository.gmail_message_already_processed(organization_id, message_id):
                    continue

                try:
                    msg = await _fetch_full_message(client, access_token, message_id)
                except Exception as e:
                    logger.error(f"[job_hunter] Failed to fetch Gmail message {message_id}: {e}")
                    continue

                headers = _extract_headers(msg)
                subject = headers.get("Subject", "")
                sender = headers.get("From", "")
                recipient = headers.get("To", "")
                body_text = _extract_body_text(msg)
                attachments = _extract_attachments(msg)

                classification = classify_email(subject, body_text[:2000])

                match_result = None
                if classification.category not in ("not_recruitment",) and candidates:
                    match_result = find_best_match(
                        sender_email=sender,
                        subject=subject,
                        body_snippet=body_text[:1000],
                        recipient_email=recipient,
                        onboarding_email=preferences.get("email", ""),
                        candidates=candidates,
                    )

                application_id = None
                final_category = classification.category

                if (
                    classification.category != "not_recruitment"
                    and match_result
                    and match_result.is_confident
                ):
                    application_id = match_result.application_id

                    if classification.category in (
                        "interview_invite", "assessment", "rejection",
                        "offer", "reschedule", "withdrawal",
                    ):
                        status_map = {
                            "interview_invite": "interview",
                            "assessment": "assessment",
                            "rejection": "rejected",
                            "offer": "offer",
                            "withdrawal": "archived",
                            # reschedule doesn't change status — logged as
                            # activity only, the existing interview status
                            # stands (see below)
                        }
                        new_status = status_map.get(classification.category)
                        if new_status:
                            try:
                                service.update_application_status(organization_id, application_id, new_status)
                                applications_updated += 1
                            except Exception as e:
                                logger.error(f"[job_hunter] Failed to update application {application_id} from Gmail event: {e}")

                        if classification.category == "reschedule":
                            repository.add_activity({
                                "application_id": application_id,
                                "event_type": "gmail_detected",
                                "summary": f"Interview reschedule email detected: {subject}",
                                "metadata": {"gmail_message_id": message_id},
                                "source": "gmail",
                            })
                elif classification.category == "unmatched" or (match_result and not match_result.is_confident):
                    final_category = "unmatched"

                repository.create_gmail_event({
                    "organization_id": organization_id,
                    "gmail_message_id": message_id,
                    "gmail_thread_id": msg.get("threadId"),
                    "gmail_history_id": msg.get("historyId"),
                    "application_id": application_id,
                    "category": final_category,
                    "match_score": match_result.score if match_result else None,
                    "match_signals": match_result.signals if match_result else {},
                    "raw_subject": subject,
                    "raw_sender": sender,
                    "recipient_email": recipient,
                    "has_attachments": len(attachments) > 0,
                    "attachment_count": len(attachments),
                    "attachment_metadata": attachments,
                    "extracted_metadata": classification.extracted_metadata,
                })
                messages_processed += 1

                if application_id:
                    log_event(
                        organization_id=organization_id,
                        module=MODULE,
                        action="gmail_status_detected",
                        summary=f"Gmail: {classification.category} detected for application (score={match_result.score if match_result else 0})",
                        status="success",
                        resource_type="job_hunter_application",
                        resource_id=application_id,
                        metadata={"category": final_category, "gmail_message_id": message_id},
                        source="scheduler",
                    )

        repository.finish_gmail_poll_run(
            run["id"], status="success",
            messages_scanned=messages_scanned, messages_processed=messages_processed,
            applications_updated=applications_updated,
        )
        return {
            "messages_scanned": messages_scanned,
            "messages_processed": messages_processed,
            "applications_updated": applications_updated,
        }

    except Exception as e:
        logger.exception(f"[job_hunter] Gmail poll failed for org {organization_id}")
        repository.finish_gmail_poll_run(
            run["id"], status="failed",
            messages_scanned=messages_scanned, messages_processed=messages_processed,
            applications_updated=applications_updated, error_message=str(e),
        )
        return {"error": str(e)}
