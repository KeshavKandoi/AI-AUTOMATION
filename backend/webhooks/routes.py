import hmac
import hashlib
import json
from fastapi import APIRouter, Request, HTTPException, Header

from config import settings, logger, supabase_admin
from orchestrator import coo_graph
from commit_scheduler import repository as commit_repo, service as commit_service
from email_scheduler import repository as email_repo, service as email_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_signature_with_secret(payload_body: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header or not secret:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


REACTIVE_EVENTS = {"push", "issues", "pull_request"}


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
):
    body = await request.body()

    if not verify_github_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = json.loads(body)
    logger.info(f"GitHub webhook received: event={x_github_event}")

    if x_github_event not in REACTIVE_EVENTS:
        return {"status": "ignored", "event": x_github_event}

    org_id = settings.TEST_ORG_ID
    access_token = settings.TEST_GITHUB_ACCESS_TOKEN

    initial_state = {
        "github_token": access_token,
        "gmail_token": "",
        "calendar_token": "",
        "org_id": org_id,
        "issues_data": [],
        "emails_data": [],
        "events_data": [],
        "tasks": [],
        "report": ""
    }

    final_state = await coo_graph.ainvoke(initial_state)
    logger.info(f"Webhook-triggered orchestrator run complete: {final_state['report']}")

    return {
        "status": "triggered",
        "event": x_github_event,
        "tasks_created": len(final_state["tasks"])
    }


def verify_generic_secret(secret: str):
    if not secret or not hmac.compare_digest(secret, settings.GENERIC_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid or missing webhook secret")


@router.post("/commit-jobs/{job_id}")
async def trigger_commit_job(job_id: str, secret: str):
    verify_generic_secret(secret)
    job = commit_repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Commit job not found")
    run = await commit_service.execute_job(job)
    logger.info(f"Webhook-triggered commit job {job_id} -> {run['status']}")
    return {"status": "triggered", "run": run}


@router.post("/email-jobs/{job_id}")
async def trigger_email_job(job_id: str, secret: str):
    verify_generic_secret(secret)
    job = email_repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Email job not found")
    run = await email_service.execute_job(job)
    logger.info(f"Webhook-triggered email job {job_id} -> {run['status']}")
    return {"status": "triggered", "run": run}
