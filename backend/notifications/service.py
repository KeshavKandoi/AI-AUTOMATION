"""
Centralized notifications service. Any module in AI COO (Job Hunter, Commit
Scheduler, Workflow Automation, Chat, GitHub, Gmail, Calendar, Analytics,
etc.) should call notify() below to raise a user-facing notification,
instead of writing to the notifications table directly.

notify() is deliberately forgiving: a notification failure must never break
the caller's actual business logic, so all exceptions are caught and logged
via the app logger instead of propagating — same contract as
audit_logs.service.log_event().

Deduplication: pass a deterministic dedup_key (e.g.
f"job_hunter:job_match:{job_id}") and repeated calls for the same event are
safely no-ops — the DB unique index on (organization_id, dedup_key) is the
source of truth, repository.insert_notification() just checks it first.
"""
from datetime import datetime, timezone
from typing import Optional
from config import logger
from notifications import repository
from notifications.schemas import NotificationCreate, Priority


def notify(
    organization_id: str,
    module: str,
    title: str,
    body: str,
    category: Optional[str] = None,
    priority: Priority = "normal",
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    action_url: Optional[str] = None,
    action_label: Optional[str] = None,
    metadata: Optional[dict] = None,
    dedup_key: Optional[str] = None,
) -> Optional[dict]:
    """
    Creates a single notification. Returns the created row, or None if it
    was a duplicate (same dedup_key already notified) or if writing failed
    (failure is logged, never raised).

    Args:
        organization_id: org this notification belongs to (required).
        module: which part of AI COO this came from, e.g. "job_hunter",
            "commit_scheduler", "chat", "github", "gmail", "calendar".
            Free text — new modules don't need a backend change to start
            publishing notifications.
        title / body: short human-readable text for the notification.
        category: free-text sub-type within the module, e.g.
            "new_job_match", "interview_invite", "offer", "follow_up_reminder".
        priority: "low" | "normal" | "high" | "urgent".
        resource_type / resource_id: the entity this notification is about,
            e.g. resource_type="job_hunter_application", resource_id=<id>.
        action_url: deep link the future bell/drawer UI opens on click.
        action_label: button label for action_url, e.g. "View Job".
        metadata: any extra structured detail (JSON-serializable dict).
        dedup_key: deterministic key that prevents duplicate notifications
            for the same underlying event, e.g.
            f"job_hunter:job_match:{job_id}" or
            f"job_hunter:reminder:{reminder_id}".
    """
    try:
        payload = NotificationCreate(
            organization_id=organization_id,
            module=module,
            category=category,
            priority=priority,
            title=title,
            body=body,
            resource_type=resource_type,
            resource_id=resource_id,
            action_url=action_url,
            action_label=action_label,
            metadata=metadata or {},
            dedup_key=dedup_key,
        )
    except Exception as e:
        logger.error(f"Failed to validate notification payload (module={module}, category={category}): {e}")
        return None

    row = payload.model_dump()

    try:
        created = repository.insert_notification(row)
        if created is None and dedup_key:
            logger.info(f"Notification skipped (duplicate dedup_key={dedup_key})")
        return created
    except Exception as e:
        logger.error(f"Failed to write notification ({module}.{category}): {e}")
        return None


def list_for_org(
    organization_id: str,
    limit: int = 50,
    offset: int = 0,
    module: Optional[str] = None,
    category: Optional[str] = None,
    unread_only: bool = False,
) -> dict:
    items, total = repository.list_notifications(
        organization_id=organization_id,
        limit=limit,
        offset=offset,
        module=module,
        category=category,
        unread_only=unread_only,
    )
    return {
        "items": items,
        "total": total,
        "unread_count": repository.count_unread(organization_id),
        "limit": limit,
        "offset": offset,
    }


def mark_notification_read(notification_id: str) -> Optional[dict]:
    read_at = datetime.now(timezone.utc).isoformat()
    return repository.mark_read(notification_id, read_at)


def mark_all_read_for_org(organization_id: str) -> int:
    read_at = datetime.now(timezone.utc).isoformat()
    return repository.mark_all_read(organization_id, read_at)
