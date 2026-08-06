"""
All Supabase access for the audit_logs module lives here.
service.py should never call supabase_admin directly — only through this file.
"""
from typing import Optional
from config import supabase_admin


def insert_log(row: dict) -> dict:
    result = supabase_admin.table("audit_logs").insert(row).execute()
    return result.data[0]


def list_logs(
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
    query = supabase_admin.table("audit_logs").select("*", count="exact").eq("organization_id", organization_id)

    if module:
        query = query.eq("module", module)
    if action:
        query = query.eq("action", action)
    if status:
        query = query.eq("status", status)
    if resource_type:
        query = query.eq("resource_type", resource_type)
    if resource_id:
        query = query.eq("resource_id", resource_id)
    if start_date:
        query = query.gte("created_at", start_date)
    if end_date:
        query = query.lte("created_at", end_date)
    if search:
        # Matches against summary or action — the two human-readable text fields.
        query = query.or_(f"summary.ilike.%{search}%,action.ilike.%{search}%")

    query = query.order("created_at", desc=(sort_dir != "asc")).range(offset, offset + limit - 1)
    result = query.execute()
    return result.data, (result.count or 0)


def get_log(log_id: str) -> Optional[dict]:
    result = supabase_admin.table("audit_logs").select("*").eq("id", log_id).execute()
    return result.data[0] if result.data else None


def distinct_modules(organization_id: str) -> list[str]:
    result = supabase_admin.table("audit_logs").select("module").eq("organization_id", organization_id).execute()
    return sorted({row["module"] for row in result.data if row.get("module")})


def distinct_actions(organization_id: str) -> list[str]:
    result = supabase_admin.table("audit_logs").select("action").eq("organization_id", organization_id).execute()
    return sorted({row["action"] for row in result.data if row.get("action")})
