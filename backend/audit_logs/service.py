"""
Centralized audit logging service. Any module in AI COO should record
significant actions by calling log_event() below instead of writing to the
audit_logs table directly.

log_event() is deliberately forgiving: a logging failure must never break
the caller's actual business logic, so all exceptions are caught and logged
via the app logger instead of propagating.
"""
from typing import Optional
from config import logger
from audit_logs import repository
from audit_logs.schemas import AuditLogCreate


def log_event(
    organization_id: str,
    module: str,
    action: str,
    summary: str,
    status: str = "info",
    user_id: Optional[str] = None,
    actor_type: str = "system",
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None,
    source: str = "backend",
) -> Optional[dict]:
    """
    Writes a single audit log entry. Returns the created row, or None if
    writing failed (failure is logged, never raised).

    Args:
        organization_id: org this event belongs to (required for every log).
        module: which part of AI COO this came from, e.g. "tasks",
            "workflows", "commit_scheduler", "github", "gmail", "calendar",
            "human_approval", "auth", "settings". Free text — new modules
            don't need a backend change to start logging.
        action: short machine-readable action name, e.g. "task_created",
            "workflow_execution_failed".
        summary: short human-readable one-liner shown in the timeline/table,
            e.g. "Task 'Fix login bug' created".
        status: "success" | "failed" | "warning" | "info".
        resource_type / resource_id: the entity this event is about, e.g.
            resource_type="task", resource_id=<task_id>.
        metadata: any extra structured detail (JSON-serializable dict) shown
            in the detail drawer's metadata viewer.
        error_message: populated for status="failed" events.
        duration_ms: for events tied to a timed operation (workflow runs,
            commit jobs, etc.).
        source: "backend" | "scheduler" | "webhook" | "frontend" — where the
            event originated.
    """
    try:
        payload = AuditLogCreate(
            organization_id=organization_id,
            module=module,
            action=action,
            summary=summary,
            status=status,
            user_id=user_id,
            actor_type=actor_type,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {},
            error_message=error_message,
            duration_ms=duration_ms,
            source=source,
        )
    except Exception as e:
        logger.error(f"Failed to validate audit log payload (module={module}, action={action}): {e}")
        return None

    row = payload.model_dump()
    # Dual-write into the legacy `details` column so any code path still
    # reading `details` (e.g. formatActivity on the frontend, until migrated)
    # keeps working unchanged during the transition.
    row["details"] = row["metadata"]

    try:
        return repository.insert_log(row)
    except Exception as e:
        logger.error(f"Failed to write audit log ({module}.{action}): {e}")
        return None


def list_events(
    organization_id: str,
    limit: int = 50,
    offset: int = 0,
    module: Optional[str] = None,
    action: Optional[str] = None,
    status: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_dir: str = "desc",
) -> tuple[list[dict], int]:
    return repository.list_logs(
        organization_id=organization_id,
        limit=limit,
        offset=offset,
        module=module,
        action=action,
        status=status,
        resource_type=resource_type,
        resource_id=resource_id,
        search=search,
        start_date=start_date,
        end_date=end_date,
        sort_dir=sort_dir,
    )


def get_event(log_id: str) -> Optional[dict]:
    return repository.get_log(log_id)


def list_filter_options(organization_id: str) -> dict:
    return {
        "modules": repository.distinct_modules(organization_id),
        "actions": repository.distinct_actions(organization_id),
    }
