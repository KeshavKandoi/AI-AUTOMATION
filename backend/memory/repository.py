"""
All Supabase access for the memory module lives here.
service.py should never call supabase_admin directly — only through this file.
"""
from typing import Optional
from config import supabase_admin


def insert_memory(row: dict) -> dict:
    result = supabase_admin.table("memory").insert(row).execute()
    return result.data[0]


def get_memory(memory_id: str) -> Optional[dict]:
    result = supabase_admin.table("memory").select("*").eq("id", memory_id).execute()
    return result.data[0] if result.data else None


def update_memory(memory_id: str, updates: dict) -> Optional[dict]:
    result = supabase_admin.table("memory").update(updates).eq("id", memory_id).execute()
    return result.data[0] if result.data else None


def list_memories(
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
    query = supabase_admin.table("memory").select("*", count="exact").eq("organization_id", organization_id)

    # Default view excludes soft-deleted rows unless the caller explicitly
    # asks for status="deleted" (e.g. a future "Trash" filter).
    # status filter is tri-state from the frontend's Active/Archived/All tabs:
    #   "active" (or no filter) -> active tab, the default view. Legacy rows
    #     written before this module existed have status IS NULL -- treated
    #     as active so they don't silently disappear from the default view.
    #   "archived" -> archived tab only.
    #   "all"      -> everything except soft-deleted.
    #   anything else (e.g. "deleted") -> exact match, for internal use.
    # Archived is NEVER included in the default/active view -- this is an
    # archive, not a "completed items still visible" list.
    effective_status = status or "active"
    if effective_status == "active":
        query = query.or_("status.is.null,status.eq.active")
    elif effective_status == "all":
        query = query.or_("status.is.null,status.neq.deleted")
    else:
        query = query.eq("status", effective_status)

    if category:
        query = query.eq("category", category)
    if importance:
        query = query.eq("importance", importance)
    if pinned is not None:
        query = query.eq("pinned", pinned)
    if favorited is not None:
        query = query.eq("favorited", favorited)
    if tags:
        query = query.contains("tags", tags)
    if search:
        query = query.or_(f"title.ilike.%{search}%,content.ilike.%{search}%")

    sort_column = sort_by if sort_by in ("created_at", "updated_at", "last_accessed_at", "importance", "title") else "created_at"
    query = query.order(sort_column, desc=(sort_dir != "asc")).range(offset, offset + limit - 1)

    result = query.execute()
    return result.data, (result.count or 0)


def soft_delete_memory(memory_id: str, updates: dict) -> Optional[dict]:
    result = supabase_admin.table("memory").update(updates).eq("id", memory_id).execute()
    return result.data[0] if result.data else None


def distinct_categories(organization_id: str) -> list[str]:
    result = supabase_admin.table("memory").select("category").eq("organization_id", organization_id).or_("status.is.null,status.neq.deleted").execute()
    return sorted({row["category"] for row in result.data if row.get("category")})


def distinct_tags(organization_id: str) -> list[str]:
    result = supabase_admin.table("memory").select("tags").eq("organization_id", organization_id).or_("status.is.null,status.neq.deleted").execute()
    all_tags: set[str] = set()
    for row in result.data:
        if row.get("tags"):
            all_tags.update(row["tags"])
    return sorted(all_tags)


def recent_memories(organization_id: str, limit: int = 5) -> list[dict]:
    """Used by the Dashboard widget: pinned memories first, then most recently
    accessed, excluding archived/deleted."""
    pinned_result = supabase_admin.table("memory") \
        .select("*") \
        .eq("organization_id", organization_id) \
        .eq("pinned", True) \
        .eq("status", "active") \
        .order("updated_at", desc=True) \
        .limit(limit) \
        .execute()
    pinned = pinned_result.data

    if len(pinned) >= limit:
        return pinned[:limit]

    remaining = limit - len(pinned)
    pinned_ids = [p["id"] for p in pinned]
    recent_result = supabase_admin.table("memory") \
        .select("*") \
        .eq("organization_id", organization_id) \
        .eq("status", "active") \
        .order("last_accessed_at", desc=True, nullsfirst=False) \
        .limit(remaining + len(pinned_ids)) \
        .execute()
    recent = [r for r in recent_result.data if r["id"] not in pinned_ids][:remaining]

    return pinned + recent
