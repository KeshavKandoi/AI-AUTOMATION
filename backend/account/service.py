"""
Account deletion. This project has a strict 1:1 user-to-organization
mapping (verified: every organization has exactly one user_profiles row) —
so deleting a user's account means deleting their entire organization's
data. There is currently no multi-user-per-org path in this codebase; if
that changes later, this function must be revisited before reuse.

Fail-fast: any step failing aborts immediately and raises, rather than
continuing past an error and risking a silently inconsistent partial
deletion. Order matters — children are deleted before parents to respect
foreign keys.
"""
from fastapi import HTTPException
from config import supabase_admin, logger, get_auth_client
from auth import repository as auth_repository
from job_hunter import repository as job_hunter_repository


def _delete_by_org(table: str, organization_id: str):
    supabase_admin.table(table).delete().eq("organization_id", organization_id).execute()


def _delete_job_hunter_attachments(organization_id: str):
    """Attachments involve real files in Supabase Storage, not just DB rows
    — must remove the storage objects too, or they leak forever. Reuses the
    exact same job_hunter.repository.delete_attachment_file() the app
    already uses for normal attachment deletion."""
    applications = supabase_admin.table("job_hunter_applications") \
        .select("id").eq("organization_id", organization_id).execute()
    for app_row in applications.data:
        attachments = job_hunter_repository.list_attachments(app_row["id"])
        for att in attachments:
            storage_path = att.get("storage_path")
            if storage_path:
                job_hunter_repository.delete_attachment_file(storage_path)
    supabase_admin.table("job_hunter_attachments") \
        .delete().in_("application_id", [a["id"] for a in applications.data]).execute() \
        if applications.data else None


def _delete_integrations_and_tokens(organization_id: str):
    integrations = supabase_admin.table("integrations") \
        .select("id").eq("organization_id", organization_id).execute()
    for row in integrations.data:
        supabase_admin.table("oauth_tokens").delete().eq("integration_id", row["id"]).execute()
    supabase_admin.table("integrations").delete().eq("organization_id", organization_id).execute()


def delete_account(user_id: str, email: str, password: str) -> None:
    # Re-verify the password as a final confirmation gate before doing
    # anything irreversible — same defense-in-depth as changing a password.
    auth_client = get_auth_client()
    try:
        auth_client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        raise HTTPException(status_code=401, detail="Incorrect password")

    profile = auth_repository.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Account not found")
    organization_id = profile["organization_id"]

    try:
        _delete_job_hunter_attachments(organization_id)

        for table in [
            "job_hunter_notes", "job_hunter_reminders", "job_hunter_calendar_events",
            "job_hunter_gmail_events", "job_hunter_activity", "job_hunter_applications",
            "job_hunter_search_runs", "job_hunter_gmail_poll_runs",
            "job_hunter_provider_status", "job_hunter_preferences", "job_hunter_jobs",
            "commit_job_files", "commit_job_runs", "commit_jobs",
            "email_job_runs", "email_jobs", "scheduled_commits",
            "workflow_runs", "workflows",
            "lunch_block_runs", "lunch_block_settings",
            "memory", "tasks", "notifications", "audit_logs",
            "github_poll_state", "github_processed_events",
        ]:
            _delete_by_org(table, organization_id)

        _delete_integrations_and_tokens(organization_id)

        supabase_admin.table("user_profiles").delete().eq("id", user_id).execute()
        supabase_admin.table("organizations").delete().eq("id", organization_id).execute()

        # Delete the Supabase Auth user last — once this succeeds, the user
        # can no longer authenticate, so everything else must already be gone.
        auth_client.auth.admin.delete_user(user_id)

        logger.info(f"Account deleted: user_id={user_id} organization_id={organization_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account deletion failed partway through for user_id={user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Account deletion failed partway through. Please contact support — your account may be in an inconsistent state.",
        )
