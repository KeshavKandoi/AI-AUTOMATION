"""
Business logic for the memory module. Any current or future module (AI COO
Chat, Job Hunter, Workflow Automation, GitHub analysis, Pull Requests, etc.)
should read/write memory through these functions rather than the repository
directly, so audit logging and validation stay consistent everywhere.
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException

from memory import repository
from memory.schemas import MemoryCreate, MemoryUpdate
from audit_logs.service import log_event


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_memory(payload: MemoryCreate, organization_id: str) -> dict:
    row = payload.model_dump()
    row["organization_id"] = organization_id
    row["status"] = "active"
    row["pinned"] = False
    row["favorited"] = False
    row["access_count"] = 0
    row["updated_at"] = _now_iso()

    memory = repository.insert_memory(row)

    log_event(
        organization_id=organization_id,
        module="memory",
        action="memory_created",
        summary=f"Memory created: {payload.title}",
        status="success",
        user_id=payload.user_id,
        resource_type="memory",
        resource_id=memory["id"],
        metadata={"category": payload.category, "importance": payload.importance, "source": payload.source},
        source="backend",
    )
    return memory


def get_memory_or_404(memory_id: str, organization_id: Optional[str] = None) -> dict:
    memory = repository.get_memory(memory_id)
    if not memory or memory.get("status") == "deleted":
        raise HTTPException(status_code=404, detail="Memory not found")
    if organization_id and memory["organization_id"] != organization_id:
        raise HTTPException(status_code=403, detail="You do not have access to this memory")
    return memory


def list_memories_for_org(
    organization_id: str,
    limit: int = 50,
    offset: int = 0,
    category: Optional[str] = None,
    status: Optional[str] = None,
    importance: Optional[str] = None,
    pinned: Optional[bool] = None,
    favorited: Optional[bool] = None,
    tags: Optional[list[str]] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
) -> tuple[list[dict], int]:
    return repository.list_memories(
        organization_id=organization_id,
        limit=limit,
        offset=offset,
        category=category,
        status=status,
        importance=importance,
        pinned=pinned,
        favorited=favorited,
        tags=tags,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


def update_memory(memory_id: str, organization_id: str, payload: MemoryUpdate) -> dict:
    memory = get_memory_or_404(memory_id, organization_id)
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")
    updates["updated_at"] = _now_iso()

    updated = repository.update_memory(memory_id, updates)

    log_event(
        organization_id=organization_id,
        module="memory",
        action="memory_updated",
        summary=f"Memory updated: {updated.get('title', memory.get('title', 'Untitled'))}",
        status="success",
        resource_type="memory",
        resource_id=memory_id,
        metadata={"fields_updated": list(updates.keys())},
        source="backend",
    )
    return updated


def access_memory(memory_id: str, organization_id: str) -> dict:
    """Called whenever another module reads a specific memory (e.g. AI COO
    Chat pulling context). Bumps access_count / last_accessed_at so the
    Dashboard's 'recently accessed' widget and future ranking logic have
    real signal to work with."""
    memory = get_memory_or_404(memory_id, organization_id)
    updates = {
        "access_count": (memory.get("access_count") or 0) + 1,
        "last_accessed_at": _now_iso(),
    }
    updated = repository.update_memory(memory_id, updates)

    log_event(
        organization_id=organization_id,
        module="memory",
        action="memory_accessed",
        summary=f"Memory accessed: {memory.get('title', 'Untitled')}",
        status="info",
        resource_type="memory",
        resource_id=memory_id,
        metadata={"access_count": updates["access_count"]},
        source="backend",
    )
    return updated


def set_pinned(memory_id: str, organization_id: str, pinned: bool) -> dict:
    memory = get_memory_or_404(memory_id, organization_id)
    updated = repository.update_memory(memory_id, {"pinned": pinned, "updated_at": _now_iso()})

    log_event(
        organization_id=organization_id,
        module="memory",
        action="memory_pinned" if pinned else "memory_unpinned",
        summary=f"Memory {'pinned' if pinned else 'unpinned'}: {memory.get('title', 'Untitled')}",
        status="info",
        resource_type="memory",
        resource_id=memory_id,
        source="backend",
    )
    return updated


def set_favorited(memory_id: str, organization_id: str, favorited: bool) -> dict:
    memory = get_memory_or_404(memory_id, organization_id)
    updated = repository.update_memory(memory_id, {"favorited": favorited, "updated_at": _now_iso()})

    log_event(
        organization_id=organization_id,
        module="memory",
        action="memory_favorited" if favorited else "memory_unfavorited",
        summary=f"Memory {'favorited' if favorited else 'unfavorited'}: {memory.get('title', 'Untitled')}",
        status="info",
        resource_type="memory",
        resource_id=memory_id,
        source="backend",
    )
    return updated


def archive_memory(memory_id: str, organization_id: str) -> dict:
    memory = get_memory_or_404(memory_id, organization_id)
    updated = repository.update_memory(memory_id, {"status": "archived", "updated_at": _now_iso()})

    log_event(
        organization_id=organization_id,
        module="memory",
        action="memory_archived",
        summary=f"Memory archived: {memory.get('title', 'Untitled')}",
        status="warning",
        resource_type="memory",
        resource_id=memory_id,
        source="backend",
    )
    return updated


def restore_memory(memory_id: str, organization_id: str) -> dict:
    memory = repository.get_memory(memory_id)
    if not memory or memory["organization_id"] != organization_id:
        raise HTTPException(status_code=404, detail="Memory not found")
    updated = repository.update_memory(memory_id, {"status": "active", "deleted_at": None, "updated_at": _now_iso()})

    log_event(
        organization_id=organization_id,
        module="memory",
        action="memory_restored",
        summary=f"Memory restored: {memory.get('title', 'Untitled')}",
        status="success",
        resource_type="memory",
        resource_id=memory_id,
        source="backend",
    )
    return updated


def delete_memory(memory_id: str, organization_id: str) -> dict:
    """Soft delete — sets status='deleted' + deleted_at, never removes the row.
    Matches restore_memory's expectations and keeps the audit trail intact."""
    memory = get_memory_or_404(memory_id, organization_id)
    updated = repository.soft_delete_memory(memory_id, {
        "status": "deleted",
        "deleted_at": _now_iso(),
        "updated_at": _now_iso(),
    })

    log_event(
        organization_id=organization_id,
        module="memory",
        action="memory_deleted",
        summary=f"Memory deleted: {memory.get('title', 'Untitled')}",
        status="warning",
        resource_type="memory",
        resource_id=memory_id,
        source="backend",
    )
    return updated


def list_filter_options(organization_id: str) -> dict:
    return {
        "categories": repository.distinct_categories(organization_id),
        "tags": repository.distinct_tags(organization_id),
    }


def recent_memories_for_org(organization_id: str, limit: int = 5) -> list[dict]:
    return repository.recent_memories(organization_id, limit)
