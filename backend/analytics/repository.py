"""
All Supabase access for the analytics module lives here.
service.py should never call supabase_admin directly — only through this file.

Note: workflow_runs and commit_job_runs have no organization_id column of
their own (confirmed against workflow_engine.py and commit_scheduler/repository.py)
— they only carry workflow_id / job_id. So every org-scoped run query here
goes through the parent table first to get the id list, then filters runs
by that list. This mirrors how workflow_routes.py and commit_scheduler
already handle it (e.g. get_workflow -> fetch recent_runs by workflow_id).
"""
from typing import Optional
from config import supabase_admin

# Analytics reads full ranges rather than paginating like the audit-logs API
# does (that 200-row cap is a UI list-page concern, not a DB limit). Capped
# here at 5000 rows per range as a sane ceiling — if an org's audit_logs
# volume in a 90-day window regularly exceeds this, that's worth revisiting
# with real pagination, but there's no evidence of that scale yet.
AUDIT_LOG_FETCH_CAP = 10000


def get_tasks_in_range(organization_id: str, start_date: str, end_date: str) -> list[dict]:
    """Paginated per the row-cap note on get_audit_logs_in_range — PostgREST
    caps rows per request (confirmed at 1000) regardless of whether .range()
    is specified. Safe today at low task volumes, but this guards against
    silent truncation as an org's task history grows."""
    page_size = 1000
    all_rows: list[dict] = []
    offset = 0
    while offset < AUDIT_LOG_FETCH_CAP:
        query = supabase_admin.table("tasks").select("*").eq("organization_id", organization_id)
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)
        page_end = min(offset + page_size, AUDIT_LOG_FETCH_CAP) - 1
        page = query.range(offset, page_end).execute().data
        all_rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return all_rows


def get_workflows_for_org(organization_id: str) -> list[dict]:
    return supabase_admin.table("workflows") \
        .select("id, status") \
        .eq("organization_id", organization_id) \
        .execute().data


def get_workflow_runs_in_range(workflow_ids: list[str], start_date: str, end_date: str) -> list[dict]:
    """Paginated per the row-cap note on get_audit_logs_in_range."""
    if not workflow_ids:
        return []
    page_size = 1000
    all_rows: list[dict] = []
    offset = 0
    while offset < AUDIT_LOG_FETCH_CAP:
        query = supabase_admin.table("workflow_runs") \
            .select("id, workflow_id, status, executed_at") \
            .in_("workflow_id", workflow_ids)
        if start_date:
            query = query.gte("executed_at", start_date)
        if end_date:
            query = query.lte("executed_at", end_date)
        page_end = min(offset + page_size, AUDIT_LOG_FETCH_CAP) - 1
        page = query.order("executed_at", desc=False).range(offset, page_end).execute().data
        all_rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return all_rows


def get_commit_jobs_for_org(organization_id: str) -> list[dict]:
    return supabase_admin.table("commit_jobs") \
        .select("id, status") \
        .eq("organization_id", organization_id) \
        .execute().data


def get_commit_job_runs_in_range(job_ids: list[str], start_date: str, end_date: str) -> list[dict]:
    """Paginated per the row-cap note on get_audit_logs_in_range."""
    if not job_ids:
        return []
    page_size = 1000
    all_rows: list[dict] = []
    offset = 0
    while offset < AUDIT_LOG_FETCH_CAP:
        query = supabase_admin.table("commit_job_runs") \
            .select("id, job_id, status, executed_at") \
            .in_("job_id", job_ids)
        if start_date:
            query = query.gte("executed_at", start_date)
        if end_date:
            query = query.lte("executed_at", end_date)
        page_end = min(offset + page_size, AUDIT_LOG_FETCH_CAP) - 1
        page = query.order("executed_at", desc=False).range(offset, page_end).execute().data
        all_rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return all_rows


def get_audit_logs_in_range(organization_id: str, start_date: str, end_date: str) -> list[dict]:
    """
    PostgREST enforces its own server-side max-rows-per-request cap
    (confirmed empirically at 1000 for this project) independent of the
    .range() upper bound requested -- a single-call fetch silently drops
    everything past that cap instead of erroring. Paginate in fixed-size
    pages until either a short page comes back (no more rows) or we hit
    AUDIT_LOG_FETCH_CAP, so analytics counts reflect real data rather
    than a quietly truncated subset.
    """
    page_size = 1000
    all_rows: list[dict] = []
    offset = 0
    while offset < AUDIT_LOG_FETCH_CAP:
        query = supabase_admin.table("audit_logs") \
            .select("module, status, created_at") \
            .eq("organization_id", organization_id)
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)
        page_end = min(offset + page_size, AUDIT_LOG_FETCH_CAP) - 1
        query = query.order("created_at", desc=False).range(offset, page_end)
        page = query.execute().data
        all_rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return all_rows


def get_audit_log_counts(organization_id: str, start_date: str, end_date: str) -> tuple[int, int]:
    """
    Cheap, always-accurate totals via count='exact' -- unlike get_audit_logs_in_range,
    this is NOT subject to the row-fetch cap: PostgREST returns the true count
    regardless of how many rows would be returned (confirmed empirically -- count
    stayed accurate at 1195 even when only 1000 rows came back). Used for the
    total_events / failed_events KPIs so those numbers are never truncated,
    even when activity_trend/module_breakdown (which need actual rows) are.
    """
    base = supabase_admin.table("audit_logs").select("id", count="exact").eq("organization_id", organization_id)
    if start_date:
        base = base.gte("created_at", start_date)
    if end_date:
        base = base.lte("created_at", end_date)
    total = base.execute().count or 0

    failed_query = supabase_admin.table("audit_logs").select("id", count="exact") \
        .eq("organization_id", organization_id).eq("status", "failed")
    if start_date:
        failed_query = failed_query.gte("created_at", start_date)
    if end_date:
        failed_query = failed_query.lte("created_at", end_date)
    failed = failed_query.execute().count or 0

    return total, failed
