import base64
from email.mime.text import MIMEText
from datetime import date
import httpx
from fastapi import HTTPException

from email_scheduler import repository
from email_scheduler.schemas import EmailJobCreate, EmailJobUpdate
from config import supabase_admin, decrypt_token


def _get_gmail_token_for_org(organization_id: str) -> str:
    integration_res = supabase_admin.table("integrations") \
        .select("id") \
        .eq("organization_id", organization_id) \
        .eq("provider", "gmail") \
        .eq("connected", True) \
        .order("created_at", desc=True) \
        .execute()

    if not integration_res.data:
        raise HTTPException(status_code=400, detail="No connected Gmail integration for this organization")

    integration_ids = [row["id"] for row in integration_res.data]

    token_res = supabase_admin.table("oauth_tokens") \
        .select("access_token, integration_id, created_at") \
        .in_("integration_id", integration_ids) \
        .order("created_at", desc=True) \
        .execute()

    if not token_res.data:
        raise HTTPException(status_code=400, detail="No Gmail token found for this organization")

    return decrypt_token(token_res.data[0]["access_token"])


async def create_scheduled_job(payload: EmailJobCreate) -> dict:
    job_data = payload.model_dump(mode="json")
    return repository.create_job(job_data)


def get_job_or_404(job_id: str, organization_id: str = None) -> dict:
    job = repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled email job not found")
    if organization_id and job["organization_id"] != organization_id:
        raise HTTPException(status_code=403, detail="You do not have access to this job")
    return job


def list_jobs_for_org(organization_id: str) -> list[dict]:
    return repository.list_jobs(organization_id)


def update_job(job_id: str, organization_id: str, payload: EmailJobUpdate) -> dict:
    get_job_or_404(job_id, organization_id)
    updates = payload.model_dump(mode="json", exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")
    return repository.update_job(job_id, updates)


def delete_job(job_id: str, organization_id: str) -> None:
    get_job_or_404(job_id, organization_id)
    repository.delete_job(job_id)


def get_job_with_runs(job_id: str, organization_id: str) -> dict:
    job = get_job_or_404(job_id, organization_id)
    runs = repository.get_runs_for_job(job_id)
    return {**job, "runs": runs}


async def execute_job(job: dict) -> dict:
    run_date = date.today().isoformat()

    if repository.has_run_for_date(job["id"], run_date):
        return repository.create_run({
            "job_id": job["id"], "run_date": run_date, "status": "skipped",
            "error_message": "Already ran for this date"
        })

    try:
        access_token = _get_gmail_token_for_org(job["organization_id"])

        mime_msg = MIMEText(job["body"])
        mime_msg["to"] = job["to_email"]
        mime_msg["subject"] = job["subject"]
        raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()

        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"raw": raw}
            )

        if res.status_code != 200:
            raise RuntimeError(f"Gmail send failed ({res.status_code}): {res.text}")

        message_id = res.json().get("id")

        return repository.create_run({
            "job_id": job["id"], "run_date": run_date, "status": "success",
            "message_id": message_id
        })

    except Exception as e:
        return repository.create_run({
            "job_id": job["id"], "run_date": run_date, "status": "failed",
            "error_message": str(e)
        })
