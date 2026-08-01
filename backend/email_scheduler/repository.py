from typing import Optional
from config import supabase_admin

def create_job(job_data: dict) -> dict:
    result = supabase_admin.table("email_jobs").insert(job_data).execute()
    return result.data[0]

def get_job(job_id: str) -> Optional[dict]:
    result = supabase_admin.table("email_jobs").select("*").eq("id", job_id).execute()
    return result.data[0] if result.data else None

def list_jobs(organization_id: str) -> list[dict]:
    result = supabase_admin.table("email_jobs").select("*").eq("organization_id", organization_id).order("created_at", desc=True).execute()
    return result.data

def update_job(job_id: str, updates: dict) -> Optional[dict]:
    result = supabase_admin.table("email_jobs").update(updates).eq("id", job_id).execute()
    return result.data[0] if result.data else None

def delete_job(job_id: str) -> bool:
    result = supabase_admin.table("email_jobs").delete().eq("id", job_id).execute()
    return len(result.data) > 0

def list_active_jobs() -> list[dict]:
    result = supabase_admin.table("email_jobs").select("*").eq("status", "active").execute()
    return result.data

def create_run(run_data: dict) -> dict:
    result = supabase_admin.table("email_job_runs").insert(run_data).execute()
    return result.data[0]

def get_runs_for_job(job_id: str) -> list[dict]:
    result = supabase_admin.table("email_job_runs").select("*").eq("job_id", job_id).order("executed_at", desc=True).execute()
    return result.data

def has_run_for_date(job_id: str, run_date: str) -> bool:
    result = supabase_admin.table("email_job_runs").select("id").eq("job_id", job_id).eq("run_date", run_date).in_("status", ["success", "pending"]).execute()
    return len(result.data) > 0
