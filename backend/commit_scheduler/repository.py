"""
All Supabase access for the commit_scheduler module lives here.
service.py should never call supabase_admin directly — only through this file.
"""
from typing import Optional
from config import supabase_admin


def create_job(job_data: dict) -> dict:
    result = supabase_admin.table("commit_jobs").insert(job_data).execute()
    return result.data[0]


def get_job(job_id: str) -> Optional[dict]:
    result = supabase_admin.table("commit_jobs").select("*").eq("id", job_id).execute()
    return result.data[0] if result.data else None


def list_jobs(organization_id: str) -> list[dict]:
    result = supabase_admin.table("commit_jobs") \
        .select("*") \
        .eq("organization_id", organization_id) \
        .order("created_at", desc=True) \
        .execute()
    return result.data


def update_job(job_id: str, updates: dict) -> Optional[dict]:
    result = supabase_admin.table("commit_jobs").update(updates).eq("id", job_id).execute()
    return result.data[0] if result.data else None


def delete_job(job_id: str) -> bool:
    result = supabase_admin.table("commit_jobs").delete().eq("id", job_id).execute()
    return len(result.data) > 0


def find_duplicate_job(organization_id: str, repo_full_name: str, branch: str, folder_path: str, file_name: str) -> Optional[dict]:
    """Used to prevent scheduling two active jobs writing to the same file/branch/repo."""
    result = supabase_admin.table("commit_jobs") \
        .select("*") \
        .eq("organization_id", organization_id) \
        .eq("repo_full_name", repo_full_name) \
        .eq("branch", branch) \
        .eq("folder_path", folder_path) \
        .eq("file_name", file_name) \
        .eq("status", "active") \
        .execute()
    return result.data[0] if result.data else None


def list_active_jobs() -> list[dict]:
    """Used by the scheduler to find all active jobs across all orgs."""
    result = supabase_admin.table("commit_jobs").select("*").eq("status", "active").execute()
    return result.data


def create_run(run_data: dict) -> dict:
    result = supabase_admin.table("commit_job_runs").insert(run_data).execute()
    return result.data[0]


def get_runs_for_job(job_id: str) -> list[dict]:
    result = supabase_admin.table("commit_job_runs") \
        .select("*") \
        .eq("job_id", job_id) \
        .order("executed_at", desc=True) \
        .execute()
    return result.data


def has_run_for_date(job_id: str, run_date: str) -> bool:
    """Prevents double-committing if scheduler runs twice for the same day."""
    result = supabase_admin.table("commit_job_runs") \
        .select("id") \
        .eq("job_id", job_id) \
        .eq("run_date", run_date) \
        .in_("status", ["success", "pending"]) \
        .execute()
    return len(result.data) > 0


def create_job_files(job_id: str, files: list[dict]) -> list[dict]:
    if not files:
        return []
    rows = [{**f, "job_id": job_id} for f in files]
    result = supabase_admin.table("commit_job_files").insert(rows).execute()
    return result.data


def get_files_for_job(job_id: str) -> list[dict]:
    result = supabase_admin.table("commit_job_files").select("*").eq("job_id", job_id).execute()
    return result.data


def get_files_for_date(job_id: str, target_date: str) -> list[dict]:
    """Files scoped to this exact date, OR files with no target_date (apply every due day)."""
    result = supabase_admin.table("commit_job_files") \
        .select("*") \
        .eq("job_id", job_id) \
        .execute()
    all_files = result.data
    return [
        f for f in all_files
        if f.get("target_date") == target_date or f.get("target_date") is None
    ]


def delete_job_file(file_id: str) -> bool:
    result = supabase_admin.table("commit_job_files").delete().eq("id", file_id).execute()
    return len(result.data) > 0


def get_run_for_date(job_id: str, run_date: str, statuses: Optional[list[str]] = None) -> Optional[dict]:
    """Returns the most recent existing run for this job/date matching any of the
    given statuses, or None. Used to avoid re-evaluating (and re-writing) a job
    that's already been checked today — unlike has_run_for_date, this returns the
    actual run row so callers can reuse it instead of inserting a duplicate."""
    statuses = statuses or ["success", "pending"]
    result = supabase_admin.table("commit_job_runs") \
        .select("*") \
        .eq("job_id", job_id) \
        .eq("run_date", run_date) \
        .in_("status", statuses) \
        .order("executed_at", desc=True) \
        .execute()
    return result.data[0] if result.data else None
