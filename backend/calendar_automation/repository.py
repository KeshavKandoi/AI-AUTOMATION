from typing import Optional
from config import supabase_admin

def get_settings(organization_id: str) -> Optional[dict]:
    result = supabase_admin.table("lunch_block_settings").select("*").eq("organization_id", organization_id).execute()
    return result.data[0] if result.data else None

def upsert_settings(data: dict) -> dict:
    existing = get_settings(data["organization_id"])
    if existing:
        result = supabase_admin.table("lunch_block_settings").update(data).eq("organization_id", data["organization_id"]).execute()
    else:
        result = supabase_admin.table("lunch_block_settings").insert(data).execute()
    return result.data[0]

def list_enabled_settings() -> list[dict]:
    result = supabase_admin.table("lunch_block_settings").select("*").eq("enabled", True).execute()
    return result.data

def create_run(run_data: dict) -> dict:
    result = supabase_admin.table("lunch_block_runs").insert(run_data).execute()
    return result.data[0]

def has_run_for_date(organization_id: str, run_date: str) -> bool:
    result = supabase_admin.table("lunch_block_runs").select("id").eq("organization_id", organization_id).eq("run_date", run_date).in_("status", ["created", "already_exists"]).execute()
    return len(result.data) > 0

def get_runs(organization_id: str) -> list[dict]:
    result = supabase_admin.table("lunch_block_runs").select("*").eq("organization_id", organization_id).order("executed_at", desc=True).limit(30).execute()
    return result.data
