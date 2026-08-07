"""
All Supabase access for the notifications module lives here.
service.py should never call supabase_admin directly — only through this file.
"""
from typing import Optional
from config import supabase_admin


def insert_notification(row: dict) -> Optional[dict]:
    """Inserts a notification, deduplicating on (organization_id, dedup_key)
    when dedup_key is provided. Returns the created row, or None if a
    notification with the same dedup_key already existed (no-op, not an
    error) — callers can treat None as "already notified, nothing to do"."""
    if row.get("dedup_key"):
        existing = supabase_admin.table("notifications") \
            .select("id") \
            .eq("organization_id", row["organization_id"]) \
            .eq("dedup_key", row["dedup_key"]) \
            .execute()
        if existing.data:
            return None

    result = supabase_admin.table("notifications").insert(row).execute()
    return result.data[0] if result.data else None


def list_notifications(
    organization_id: str,
    limit: int = 50,
    offset: int = 0,
    module: Optional[str] = None,
    category: Optional[str] = None,
    unread_only: bool = False,
) -> tuple[list[dict], int]:
    query = supabase_admin.table("notifications").select("*", count="exact") \
        .eq("organization_id", organization_id)

    if module:
        query = query.eq("module", module)
    if category:
        query = query.eq("category", category)
    if unread_only:
        query = query.eq("read", False)

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    result = query.execute()
    return result.data, (result.count or 0)


def count_unread(organization_id: str) -> int:
    result = supabase_admin.table("notifications") \
        .select("id", count="exact") \
        .eq("organization_id", organization_id) \
        .eq("read", False) \
        .execute()
    return result.count or 0


def get_notification(notification_id: str) -> Optional[dict]:
    result = supabase_admin.table("notifications").select("*").eq("id", notification_id).execute()
    return result.data[0] if result.data else None


def mark_read(notification_id: str, read_at: str) -> Optional[dict]:
    result = supabase_admin.table("notifications") \
        .update({"read": True, "read_at": read_at}) \
        .eq("id", notification_id) \
        .execute()
    return result.data[0] if result.data else None


def mark_all_read(organization_id: str, read_at: str) -> int:
    result = supabase_admin.table("notifications") \
        .update({"read": True, "read_at": read_at}) \
        .eq("organization_id", organization_id) \
        .eq("read", False) \
        .execute()
    return len(result.data)
