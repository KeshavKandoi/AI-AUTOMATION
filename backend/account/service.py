"""Account deletion with an explicit organization membership check.

Supabase Auth and PostgREST cannot share one transaction. Cleanup stops at the
first error and reports a partial failure; the Auth user is deleted last so a
failed cleanup never masquerades as a completed deletion.
"""
from fastapi import HTTPException
from supabase_auth.errors import AuthApiError, AuthInvalidCredentialsError
from postgrest.exceptions import APIError
from config import supabase_admin, logger, get_auth_client
from auth import repository as auth_repository
from job_hunter import repository as job_hunter_repository


def _delete_by_org(table: str, organization_id: str):
    supabase_admin.table(table).delete().eq("organization_id", organization_id).execute()


def _delete_optional_legacy_by_org(table: str, organization_id: str):
    try:
        _delete_by_org(table, organization_id)
    except APIError as exc:
        # These retired job-hunter tables exist only in some older deployments.
        if str(getattr(exc, "code", "")) not in {"PGRST205", "42P01"}:
            raise


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


def _delete_job_sources(organization_id: str):
    jobs = supabase_admin.table("job_hunter_jobs").select("id").eq("organization_id", organization_id).execute()
    if jobs.data:
        supabase_admin.table("job_hunter_job_sources").delete().in_("job_id", [row["id"] for row in jobs.data]).execute()


def delete_account(user_id: str, email: str, password: str) -> None:
    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Session is incomplete. Please sign in again.")
    profile = auth_repository.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Account not found")
    if profile.get("email", "").lower() != email.lower():
        raise HTTPException(status_code=403, detail="Account confirmation failed. Please sign in again.")
    email = profile["email"]

    auth_client = get_auth_client()
    try:
        signed_in = auth_client.auth.sign_in_with_password({"email": email, "password": password})
    except AuthInvalidCredentialsError:
        raise HTTPException(status_code=403, detail="Incorrect password") from None
    except AuthApiError as exc:
        if str(getattr(exc, "code", "")) == "invalid_credentials":
            raise HTTPException(status_code=403, detail="Incorrect password") from None
        raise HTTPException(status_code=502, detail="Authentication service is unavailable. Please try again.") from None
    except Exception:
        raise HTTPException(status_code=502, detail="Authentication service is unavailable. Please try again.") from None
    if not signed_in.user or signed_in.user.id != user_id:
        raise HTTPException(status_code=403, detail="Account confirmation failed. Please sign in again.")

    organization_id = profile["organization_id"]
    members = supabase_admin.table("user_profiles").select("id").eq("organization_id", organization_id).limit(2).execute().data
    if not members or (len(members) == 1 and members[0]["id"] != user_id):
        raise HTTPException(status_code=409, detail="Organization membership changed. Please try again.")
    sole_member = len(members) == 1

    stage = "account data"
    try:
        if sole_member:
            stage = "organization data"
            _delete_job_hunter_attachments(organization_id)
            _delete_job_sources(organization_id)
            for table in (
                "job_hunter_calendar_events", "job_hunter_gmail_events", "job_hunter_gmail_poll_runs"
            ):
                _delete_optional_legacy_by_org(table, organization_id)
            for table in [
                "job_hunter_notes", "job_hunter_reminders", "job_hunter_activity", "job_hunter_applications",
                "job_hunter_search_runs",
                "job_hunter_provider_status", "job_hunter_preferences", "job_hunter_jobs",
                "commit_job_files", "commit_job_runs", "commit_jobs",
                "email_job_runs", "email_jobs", "scheduled_commits",
                "workflow_runs", "workflows", "processed_github_events",
                "lunch_block_runs", "lunch_block_settings",
                "memory", "tasks", "notifications", "audit_logs",
                "github_poll_state", "github_processed_events", "oauth_states",
            ]:
                _delete_by_org(table, organization_id)
            stage = "integration credentials"
            _delete_integrations_and_tokens(organization_id)
        else:
            # Shared organization records and credentials belong to its other members.
            stage = "personal audit identifiers"
            supabase_admin.table("audit_logs").update({"user_id": None}).eq("organization_id", organization_id).eq("user_id", user_id).execute()

        stage = "personal verification codes"
        supabase_admin.table("auth_otps").delete().eq("email", email).execute()
        stage = "account profile"
        deleted_profile = supabase_admin.table("user_profiles").delete().eq("id", user_id).eq("organization_id", organization_id).select("id").execute()
        if not deleted_profile.data:
            raise RuntimeError("Profile deletion did not return a row")
        if sole_member:
            stage = "organization"
            deleted_org = supabase_admin.table("organizations").delete().eq("id", organization_id).select("id").execute()
            if not deleted_org.data:
                raise RuntimeError("Organization deletion did not return a row")

        stage = "authentication account"
        auth_client.auth.admin.delete_user(user_id)
        stage = "authentication verification"
        try:
            get_auth_client().auth.sign_in_with_password({"email": email, "password": password})
        except AuthInvalidCredentialsError:
            pass
        except AuthApiError as exc:
            if str(getattr(exc, "code", "")) != "invalid_credentials":
                raise RuntimeError("Could not verify Auth deletion") from None
        else:
            raise RuntimeError("Deleted account can still sign in")
        logger.info("Account deleted: user_id=%s organization_id=%s", user_id, organization_id)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Account deletion failed at %s for user_id=%s (%s)", stage, user_id, type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail=f"Account deletion stopped during {stage}. Some data may already be removed. Please contact support; do not assume deletion finished.",
        ) from None
