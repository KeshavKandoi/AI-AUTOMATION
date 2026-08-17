"""
All Supabase access for the job_hunter module lives here.
service.py should never call supabase_admin directly — only through this file.
"""
from typing import Optional
from config import supabase_admin
from job_hunter.retry import retry_db_call


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

def get_preferences(organization_id: str) -> Optional[dict]:
    result = supabase_admin.table("job_hunter_preferences") \
        .select("*").eq("organization_id", organization_id).execute()
    return result.data[0] if result.data else None


def upsert_preferences(organization_id: str, row: dict) -> dict:
    row = {**row, "organization_id": organization_id}
    result = supabase_admin.table("job_hunter_preferences") \
        .upsert(row, on_conflict="organization_id").execute()
    return result.data[0]


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

def get_existing_by_dedup_keys(organization_id: str, dedup_keys: list[str]) -> dict[str, dict]:
    """Batch version of get_job_by_dedup_key -- one SELECT ... WHERE
    dedup_key IN (...) instead of N individual lookups. Returns a dict
    keyed by dedup_key for O(1) lookup while building the upsert batch.
    Used only to preserve existing work_mode/employment_type/is_active
    values during the self-heal/reactivation logic -- the actual
    insert-vs-update determination still comes from comparing
    first_discovered_at == last_seen_at on the upsert response, exactly
    as the original per-job path did."""
    if not dedup_keys:
        return {}
    result = retry_db_call(
        lambda: supabase_admin.table("job_hunter_jobs")
            .select("id, dedup_key, work_mode, employment_type, is_active, description, salary_min, salary_max")
            .eq("organization_id", organization_id)
            .in_("dedup_key", dedup_keys)
            .execute(),
        operation_name="get_existing_by_dedup_keys",
    )
    return {row["dedup_key"]: row for row in result.data}


def batch_upsert_jobs(rows: list[dict]) -> list[dict]:
    """Upserts many job rows in a single Supabase request, matched on the
    existing (organization_id, dedup_key) unique constraint -- the same
    constraint create_job()/update_job() have always relied on, so this
    introduces no new duplicate-creation risk. default_to_null=False so
    any column NOT included in a given row's payload is left untouched
    on conflict (verified empirically: is_active and first_discovered_at
    are preserved correctly across upsert when omitted). Idempotent by
    construction -- retrying the same batch re-applies the same values,
    which is safe whether or not the original request actually succeeded
    server-side before the client saw a transient error."""
    if not rows:
        return []
    result = retry_db_call(
        lambda: supabase_admin.table("job_hunter_jobs")
            .upsert(rows, on_conflict="organization_id,dedup_key", default_to_null=False)
            .execute(),
        operation_name="batch_upsert_jobs",
    )
    return result.data


def get_job_by_dedup_key(organization_id: str, dedup_key: str) -> Optional[dict]:
    result = retry_db_call(
        lambda: supabase_admin.table("job_hunter_jobs")
            .select("*")
            .eq("organization_id", organization_id)
            .eq("dedup_key", dedup_key)
            .execute(),
        operation_name="get_job_by_dedup_key",
    )
    return result.data[0] if result.data else None


def create_job(row: dict) -> dict:
    result = retry_db_call(
        lambda: supabase_admin.table("job_hunter_jobs").insert(row).execute(),
        operation_name="create_job",
    )
    return result.data[0]


def update_job(job_id: str, updates: dict) -> dict:
    result = retry_db_call(
        lambda: supabase_admin.table("job_hunter_jobs").update(updates).eq("id", job_id).execute(),
        operation_name="update_job",
    )
    return result.data[0]


def get_job(job_id: str, organization_id: str) -> Optional[dict]:
    result = supabase_admin.table("job_hunter_jobs") \
        .select("*") \
        .eq("id", job_id).eq("organization_id", organization_id) \
        .execute()
    return result.data[0] if result.data else None


def list_jobs(
    organization_id: str,
    limit: int = 50,
    offset: int = 0,
    employment_type: Optional[str] = None,
    work_mode: Optional[str] = None,
    search: Optional[str] = None,
    include_inactive: bool = False,
    roles: Optional[list[str]] = None,
    skills: Optional[list[str]] = None,
) -> tuple[list[dict], int]:
    """Normal Job Hunter browsing/filtering defaults to active jobs only
    (is_active=true) -- a job not rediscovered within
    JOB_HUNTER_STALE_AFTER_DAYS is soft-expired (see
    mark_stale_jobs_inactive below) and excluded from these results by
    default. Pass include_inactive=True for historical/audit access to
    the full record set, e.g. an admin view or a job a user previously
    tracked. This never deletes rows -- inactive jobs remain fully
    queryable via this flag.

    roles/skills: optional query-time personalization filter for the
    Discover "For You" view. Every term across BOTH lists is OR'd
    together as a job_title ilike match -- mirrors the permissive OR
    semantics matching.matches_preferences() used to apply at discovery
    time, now applied at query time instead against the already-stored
    database inventory. Purely a DB filter; never triggers scraping."""
    query = supabase_admin.table("job_hunter_jobs").select("*", count="exact") \
        .eq("organization_id", organization_id)

    if not include_inactive:
        query = query.eq("is_active", True)
    if employment_type:
        query = query.eq("employment_type", employment_type)
    if work_mode:
        query = query.eq("work_mode", work_mode)
    if search:
        query = query.or_(f"job_title.ilike.%{search}%,company_name.ilike.%{search}%")
    if roles or skills:
        terms = [t.strip() for t in (roles or []) + (skills or []) if t and t.strip()]
        if terms:
            or_clause = ",".join(f"job_title.ilike.%{t}%" for t in terms)
            query = query.or_(or_clause)

    query = query.order("last_seen_at", desc=True).range(offset, offset + limit - 1)
    result = query.execute()
    return result.data, (result.count or 0)


def get_last_completed_search_run(organization_id: str) -> Optional[dict]:
    """Most recent finished (success or failed) search run for this org --
    powers the Discover page's "Last synced: X ago" indicator. Pure read,
    no scraping triggered."""
    result = supabase_admin.table("job_hunter_search_runs") \
        .select("id, status, finished_at, jobs_found, jobs_new") \
        .eq("organization_id", organization_id) \
        .not_.is_("finished_at", "null") \
        .order("finished_at", desc=True) \
        .limit(1) \
        .execute()
    return result.data[0] if result.data else None


def mark_stale_jobs_inactive(stale_before_iso: str) -> int:
    """Soft-expires active jobs not rediscovered since stale_before_iso.
    Never deletes rows -- only flips is_active to false. Idempotent by
    construction: only touches rows that are currently is_active=true AND
    past the threshold, so running this repeatedly (e.g. the daily
    cleanup job firing more than once, or overlapping with a manual
    trigger) simply re-selects an empty or smaller set on subsequent
    runs rather than causing any incorrect state change. Returns the
    number of jobs newly marked inactive."""
    result = supabase_admin.table("job_hunter_jobs") \
        .update({"is_active": False}) \
        .eq("is_active", True) \
        .lt("last_seen_at", stale_before_iso) \
        .execute()
    return len(result.data)


def add_job_source(row: dict) -> Optional[dict]:
    """Insert a (job, platform, platform_url) row. Silently no-ops on the
    unique constraint if this exact source was already recorded for this
    job — same platform re-discovering the same posting on a later sweep
    shouldn't create a duplicate badge."""
    existing = retry_db_call(
        lambda: supabase_admin.table("job_hunter_job_sources")
            .select("id")
            .eq("job_id", row["job_id"])
            .eq("platform", row["platform"])
            .eq("platform_url", row["platform_url"])
            .execute(),
        operation_name="add_job_source_check_existing",
    )
    if existing.data:
        return None
    result = retry_db_call(
        lambda: supabase_admin.table("job_hunter_job_sources").insert(row).execute(),
        operation_name="add_job_source_insert",
    )
    return result.data[0] if result.data else None


def get_job_sources(job_id: str) -> list[dict]:
    result = supabase_admin.table("job_hunter_job_sources") \
        .select("*").eq("job_id", job_id).order("discovered_at").execute()
    return result.data


def get_sources_for_jobs(job_ids: list[str]) -> dict[str, list[dict]]:
    """Batch-fetch sources for many jobs at once (dashboard list view),
    grouped by job_id, instead of N+1 querying per job card."""
    if not job_ids:
        return {}
    result = supabase_admin.table("job_hunter_job_sources") \
        .select("*").in_("job_id", job_ids).execute()
    grouped: dict[str, list[dict]] = {jid: [] for jid in job_ids}
    for row in result.data:
        grouped.setdefault(row["job_id"], []).append(row)
    return grouped


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

def get_application_by_job(organization_id: str, job_id: str) -> Optional[dict]:
    result = supabase_admin.table("job_hunter_applications") \
        .select("*") \
        .eq("organization_id", organization_id).eq("job_id", job_id) \
        .execute()
    return result.data[0] if result.data else None


def create_application(row: dict) -> dict:
    result = supabase_admin.table("job_hunter_applications").insert(row).execute()
    return result.data[0]


def update_application(application_id: str, updates: dict) -> dict:
    result = supabase_admin.table("job_hunter_applications") \
        .update(updates).eq("id", application_id).execute()
    return result.data[0]


def get_application(application_id: str, organization_id: str) -> Optional[dict]:
    result = supabase_admin.table("job_hunter_applications") \
        .select("*") \
        .eq("id", application_id).eq("organization_id", organization_id) \
        .execute()
    return result.data[0] if result.data else None


def list_applications(organization_id: str, status: Optional[str] = None) -> list[dict]:
    query = supabase_admin.table("job_hunter_applications").select("*") \
        .eq("organization_id", organization_id)
    if status:
        query = query.eq("status", status)
    result = query.order("updated_at", desc=True).execute()
    return result.data


# ---------------------------------------------------------------------------
# Activity / Notes / Attachments / Reminders
# ---------------------------------------------------------------------------

def add_activity(row: dict) -> dict:
    result = supabase_admin.table("job_hunter_activity").insert(row).execute()
    return result.data[0]


def list_activity(application_id: str) -> list[dict]:
    result = supabase_admin.table("job_hunter_activity") \
        .select("*").eq("application_id", application_id) \
        .order("created_at", desc=True).execute()
    return result.data


def add_note(row: dict) -> dict:
    result = supabase_admin.table("job_hunter_notes").insert(row).execute()
    return result.data[0]


def list_notes(application_id: str) -> list[dict]:
    result = supabase_admin.table("job_hunter_notes") \
        .select("*").eq("application_id", application_id) \
        .order("created_at", desc=True).execute()
    return result.data


def add_attachment(row: dict) -> dict:
    result = supabase_admin.table("job_hunter_attachments").insert(row).execute()
    return result.data[0]


def list_attachments(application_id: str) -> list[dict]:
    result = supabase_admin.table("job_hunter_attachments") \
        .select("*").eq("application_id", application_id) \
        .order("created_at", desc=True).execute()
    return result.data


def add_reminder(row: dict) -> dict:
    result = supabase_admin.table("job_hunter_reminders").insert(row).execute()
    return result.data[0]


def list_reminders(application_id: str) -> list[dict]:
    result = supabase_admin.table("job_hunter_reminders") \
        .select("*").eq("application_id", application_id) \
        .order("remind_at").execute()
    return result.data


def get_due_reminders() -> list[dict]:
    """Pending reminders whose remind_at has passed — used by the scheduler
    to raise a notification (never to auto-send an email)."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    result = supabase_admin.table("job_hunter_reminders") \
        .select("*").eq("status", "pending").lte("remind_at", now).execute()
    return result.data


def mark_reminder_notified(reminder_id: str) -> dict:
    result = supabase_admin.table("job_hunter_reminders") \
        .update({"status": "notified"}).eq("id", reminder_id).execute()
    return result.data[0]


# ---------------------------------------------------------------------------
# Search runs (6-hourly sweep audit trail)
# ---------------------------------------------------------------------------

def create_search_run(organization_id: str, platforms: list[str]) -> dict:
    result = supabase_admin.table("job_hunter_search_runs").insert({
        "organization_id": organization_id,
        "platforms_run": platforms,
        "status": "running",
    }).execute()
    return result.data[0]


def finish_search_run(run_id: str, status: str, jobs_found: int, jobs_new: int, error_message: Optional[str] = None) -> dict:
    from datetime import datetime, timezone
    result = supabase_admin.table("job_hunter_search_runs").update({
        "status": status,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "jobs_found": jobs_found,
        "jobs_new": jobs_new,
        "error_message": error_message,
    }).eq("id", run_id).execute()
    return result.data[0]


def list_orgs_with_preferences() -> list[str]:
    """Every org that has completed Job Hunter onboarding — the scheduler
    loops over these every 6 hours."""
    result = supabase_admin.table("job_hunter_preferences") \
        .select("organization_id").eq("onboarding_completed", True).execute()
    return [row["organization_id"] for row in result.data]


# ---------------------------------------------------------------------------
# Company registry (Greenhouse / Lever / Ashby — per-company ATS APIs)
# ---------------------------------------------------------------------------

def list_enabled_companies(provider: str) -> list[dict]:
    result = supabase_admin.table("job_provider_companies") \
        .select("*").eq("provider", provider).eq("enabled", True).execute()
    return result.data


def mark_company_sync_status(company_id: str, status: str) -> None:
    from datetime import datetime, timezone
    supabase_admin.table("job_provider_companies").update({
        "last_status": status,
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", company_id).execute()


# ---------------------------------------------------------------------------
# Provider status (per-org, per-platform — Active/Disabled/Not Configured/Error)
# ---------------------------------------------------------------------------

def upsert_provider_status(organization_id: str, platform: str, status: str, jobs_found: int = 0, error: Optional[str] = None) -> dict:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "organization_id": organization_id,
        "platform": platform,
        "status": status,
        "last_run_at": now,
        "jobs_found_last_run": jobs_found,
        "updated_at": now,
        "last_error": error,
    }
    if status == "active":
        row["last_success_at"] = now
    result = supabase_admin.table("job_hunter_provider_status") \
        .upsert(row, on_conflict="organization_id,platform").execute()
    return result.data[0]


def get_provider_statuses(organization_id: str) -> list[dict]:
    result = supabase_admin.table("job_hunter_provider_status") \
        .select("*").eq("organization_id", organization_id).execute()
    return result.data


# ---------------------------------------------------------------------------
# Career pages registry (auto-detection source + custom-site fallback list)
# ---------------------------------------------------------------------------

def list_enabled_career_pages() -> list[dict]:
    result = supabase_admin.table("job_provider_career_pages") \
        .select("*").eq("enabled", True).execute()
    return result.data


def list_undetected_career_pages() -> list[dict]:
    """Career pages that haven't been matched to a known ATS yet — these
    are candidates for the custom-site fallback scraper."""
    result = supabase_admin.table("job_provider_career_pages") \
        .select("*").eq("enabled", True).is_("detected_ats", "null").execute()
    return result.data


def mark_career_page_detected(page_id: str, ats: str, token: str) -> None:
    from datetime import datetime, timezone
    supabase_admin.table("job_provider_career_pages").update({
        "detected_ats": ats,
        "detected_token": token,
        "last_status": "ok",
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", page_id).execute()


def mark_career_page_status(page_id: str, status: str) -> None:
    from datetime import datetime, timezone
    supabase_admin.table("job_provider_career_pages").update({
        "last_status": status,
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", page_id).execute()


def upsert_detected_company(provider: str, company_name: str, board_token: str, website: str) -> None:
    """Called when the ATS detector finds a company using a known provider
    (Greenhouse/Lever/Ashby) via its career page — registers it into
    job_provider_companies so the real API-based adapter picks it up
    automatically from then on, instead of scraping it."""
    supabase_admin.table("job_provider_companies").upsert({
        "provider": provider,
        "company_name": company_name,
        "board_token": board_token,
        "website": website,
        "enabled": True,
    }, on_conflict="provider,board_token").execute()


# ---------------------------------------------------------------------------
# Attachment file storage (Supabase Storage — private bucket)
# ---------------------------------------------------------------------------

ATTACHMENTS_BUCKET = "job-hunter-attachments"


def upload_attachment_file(organization_id: str, application_id: str, file_name: str, file_bytes: bytes, content_type: str) -> str:
    """Uploads file bytes to the private attachments bucket under a path
    scoped by organization and application, so one org can never guess or
    access another org's file path. Returns the storage path (not a URL —
    the bucket is private, so callers must request a signed URL to
    actually read the file). Raises on failure; never silently drops
    a failed upload."""
    import uuid
    safe_name = "".join(c for c in file_name if c.isalnum() or c in "._-") or "file"
    storage_path = f"{organization_id}/{application_id}/{uuid.uuid4().hex}_{safe_name}"

    supabase_admin.storage.from_(ATTACHMENTS_BUCKET).upload(
        storage_path,
        file_bytes,
        file_options={"content-type": content_type or "application/octet-stream"},
    )
    return storage_path


def get_attachment_signed_url(storage_path: str, expires_in_seconds: int = 300) -> str:
    """Returns a time-limited signed URL for reading a private attachment.
    Default 5 minutes — short-lived since this is regenerated per request,
    never stored or reused."""
    result = supabase_admin.storage.from_(ATTACHMENTS_BUCKET).create_signed_url(
        storage_path, expires_in_seconds
    )
    return result["signedURL"] if "signedURL" in result else result.get("signed_url")


def delete_attachment_file(storage_path: str) -> None:
    supabase_admin.storage.from_(ATTACHMENTS_BUCKET).remove([storage_path])


def get_attachment(attachment_id: str) -> Optional[dict]:
    result = supabase_admin.table("job_hunter_attachments").select("*").eq("id", attachment_id).execute()
    return result.data[0] if result.data else None


def delete_attachment_row(attachment_id: str) -> None:
    supabase_admin.table("job_hunter_attachments").delete().eq("id", attachment_id).execute()


def has_running_search(organization_id: str) -> bool:
    """Checks if a search sweep is already in progress for this org —
    used to prevent overlapping sweeps (manual /run-now trigger racing
    the 6-hourly scheduled job, or two manual triggers close together).
    A run is considered stale (and treated as NOT blocking) if it's been
    'running' for more than 15 minutes, since that almost certainly means
    a previous process crashed mid-sweep without reaching finish_search_run
    — otherwise a genuine crash would permanently lock that org out of
    ever searching again."""
    from datetime import datetime, timezone, timedelta
    stale_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()

    result = supabase_admin.table("job_hunter_search_runs") \
        .select("id, started_at") \
        .eq("organization_id", organization_id) \
        .eq("status", "running") \
        .gte("started_at", stale_cutoff) \
        .execute()
    return len(result.data) > 0


def get_provider_health_summary(organization_id: str) -> list[dict]:
    """Enriches raw provider_status rows with a computed health verdict.
    A provider is flagged 'degraded' if its last_error is set (an actual
    failure), or 'error' status from the most recent run. This is
    deliberately based on the single most recent run rather than a
    rolling window — job_hunter_provider_status only stores one row per
    (org, platform) via upsert, so there's no history to average over
    without querying job_hunter_search_runs separately, which stores
    aggregate counts across ALL providers per run, not per-provider
    detail. Flagging on the latest known state is the honest signal
    available with the current schema."""
    statuses = get_provider_statuses(organization_id)
    summary = []
    for s in statuses:
        is_healthy = s["status"] == "active" and not s.get("last_error")
        summary.append({
            **s,
            "is_healthy": is_healthy,
        })
    return summary


# ---------------------------------------------------------------------------
# Gmail poll tracking + events (application-status detection)
# ---------------------------------------------------------------------------

def has_running_gmail_poll(organization_id: str) -> bool:
    """Same pattern as has_running_search — prevents overlapping Gmail
    polls for the same org. 15-minute staleness cutoff so a crashed poll
    never permanently locks the org out."""
    from datetime import datetime, timezone, timedelta
    stale_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    result = supabase_admin.table("job_hunter_gmail_poll_runs") \
        .select("id") \
        .eq("organization_id", organization_id) \
        .eq("status", "running") \
        .gte("started_at", stale_cutoff) \
        .execute()
    return len(result.data) > 0


def create_gmail_poll_run(organization_id: str) -> dict:
    result = supabase_admin.table("job_hunter_gmail_poll_runs").insert({
        "organization_id": organization_id,
        "status": "running",
    }).execute()
    return result.data[0]


def finish_gmail_poll_run(
    run_id: str, status: str, messages_scanned: int, messages_processed: int,
    applications_updated: int, error_message: Optional[str] = None,
) -> dict:
    from datetime import datetime, timezone
    result = supabase_admin.table("job_hunter_gmail_poll_runs").update({
        "status": status,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "messages_scanned": messages_scanned,
        "messages_processed": messages_processed,
        "applications_updated": applications_updated,
        "error_message": error_message,
    }).eq("id", run_id).execute()
    return result.data[0]


def gmail_message_already_processed(organization_id: str, gmail_message_id: str) -> bool:
    result = supabase_admin.table("job_hunter_gmail_events") \
        .select("id") \
        .eq("organization_id", organization_id) \
        .eq("gmail_message_id", gmail_message_id) \
        .execute()
    return len(result.data) > 0


def create_gmail_event(row: dict) -> dict:
    result = supabase_admin.table("job_hunter_gmail_events").insert(row).execute()
    return result.data[0]


def list_gmail_events(organization_id: str, category: Optional[str] = None, limit: int = 50) -> list[dict]:
    query = supabase_admin.table("job_hunter_gmail_events").select("*") \
        .eq("organization_id", organization_id)
    if category:
        query = query.eq("category", category)
    result = query.order("processed_at", desc=True).limit(limit).execute()
    return result.data


# ---------------------------------------------------------------------------
# Calendar events (interview scheduling from Gmail detection)
# ---------------------------------------------------------------------------

def get_calendar_event_by_gmail_message(organization_id: str, gmail_message_id: str) -> Optional[dict]:
    """Idempotency check — same gmail_message_id can never produce two
    calendar events for this org."""
    result = supabase_admin.table("job_hunter_calendar_events") \
        .select("*") \
        .eq("organization_id", organization_id) \
        .eq("gmail_message_id", gmail_message_id) \
        .execute()
    return result.data[0] if result.data else None


def get_active_calendar_event_for_application(organization_id: str, application_id: str) -> Optional[dict]:
    """Finds the most recent non-cancelled calendar event for an
    application — used by reschedule/cancellation handling to find the
    existing google_calendar_event_id to update/cancel, rather than
    creating a new event."""
    result = supabase_admin.table("job_hunter_calendar_events") \
        .select("*") \
        .eq("organization_id", organization_id) \
        .eq("application_id", application_id) \
        .in_("sync_status", ["created", "updated"]) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()
    return result.data[0] if result.data else None


def create_calendar_event_row(row: dict) -> dict:
    result = supabase_admin.table("job_hunter_calendar_events").insert(row).execute()
    return result.data[0]


def update_calendar_event_row(event_id: str, updates: dict) -> dict:
    from datetime import datetime, timezone
    updates = {**updates, "updated_at": datetime.now(timezone.utc).isoformat()}
    result = supabase_admin.table("job_hunter_calendar_events").update(updates).eq("id", event_id).execute()
    return result.data[0]
