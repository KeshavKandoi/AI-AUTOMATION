import hmac
import hashlib
import json
from fastapi import APIRouter, Request, HTTPException, Header

from config import settings, logger, supabase_admin
from orchestrator import coo_graph
from workflow_engine import run_workflows
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


def _extract_priority_from_labels(labels: list) -> str:
    """Looks for a label like 'priority:high' / 'priority: high' (case-insensitive).
    Defaults to 'medium' if no matching label is present."""
    for label in labels or []:
        name = (label.get("name") or "").lower().replace(" ", "")
        if name.startswith("priority:"):
            value = name.split(":", 1)[1]
            if value in ("high", "medium", "low"):
                return value
    return "medium"


def _resolve_org_for_webhook(body: bytes, signature: str, repo_full_name: str) -> dict:
    """Identifies which single organization a GitHub webhook delivery belongs
    to, when multiple organizations may have connected the same repository.

    There is currently no GitHub-native identifier (e.g. a stored webhook id)
    persisted per-org that could unambiguously answer this without touching
    the request body, so the org is resolved by finding the one candidate
    organization whose own server-side webhook_secret actually verifies this
    delivery's HMAC signature. The organization is never taken from the
    request payload, headers, or any client-suppliable value -- only from
    which stored secret cryptographically matches.

    Raises HTTPException(401) if zero candidates verify (invalid/forged
    signature, or repo not connected to any org), and HTTPException(409) if
    more than one candidate verifies (an organization-secret collision -- not
    expected in normal operation, but must never be resolved by arbitrarily
    picking one candidate)."""
    org_res = supabase_admin.table("organizations").select("*").eq("github_repo", repo_full_name).execute()
    candidates = org_res.data or []
    if not candidates:
        logger.error(f"Webhook received for unregistered repo: {repo_full_name}")
        raise HTTPException(status_code=404, detail="No organization connected to this repo")

    matches = [
        org for org in candidates
        if verify_signature_with_secret(body, signature, org.get("webhook_secret"))
    ]

    if not matches:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if len(matches) > 1:
        matched_ids = [m["id"] for m in matches]
        logger.error(
            f"Webhook signature matched multiple organizations for repo {repo_full_name}: {matched_ids} "
            f"-- refusing to arbitrarily select one. This indicates a webhook_secret collision."
        )
        raise HTTPException(status_code=409, detail="Ambiguous webhook: matched multiple organizations")

    return matches[0]


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
):
    body = await request.body()
    payload = json.loads(body)

    repo_full_name = payload.get("repository", {}).get("full_name")
    if not repo_full_name:
        raise HTTPException(status_code=400, detail="Missing repository in payload")

    org = _resolve_org_for_webhook(body, x_hub_signature_256, repo_full_name)

    logger.info(f"GitHub webhook received: event={x_github_event} repo={repo_full_name} org={org['id']}")

    if x_github_event not in REACTIVE_EVENTS:
        return {"status": "ignored", "event": x_github_event}

    org_id = org["id"]

    # --- New: single-issue events go through the configurable workflow engine ---
    if x_github_event == "issues" and payload.get("action") == "opened":
        issue = payload.get("issue", {})
        context = {
            "title": issue.get("title", "Untitled issue"),
            "description": issue.get("body") or "",
            "priority": _extract_priority_from_labels(issue.get("labels", [])),
            "issue_number": issue.get("number"),
            "issue_url": issue.get("html_url"),
            "repo": repo_full_name,
            "labels": [l.get("name") for l in issue.get("labels", [])],
            "assignee": (issue.get("assignee") or {}).get("login", ""),
            "author": (issue.get("user") or {}).get("login", ""),
        }

        await run_workflows(org_id, "issue_created", context)

        logger.info(f"Workflow dispatch complete for issue #{context['issue_number']} (priority={context['priority']})")

        return {
            "status": "triggered",
            "event": x_github_event,
            "trigger_type": "issue_created",
            "priority": context["priority"]
        }

    # --- New: push events also go through the configurable workflow engine,
    # in addition to (not instead of) the existing orchestrator run below,
    # so existing push-triggered orchestrator behavior is unchanged. ---
    if x_github_event == "push":
        head_commit = payload.get("head_commit") or {}
        push_context = {
            "repo": repo_full_name,
            "branch": (payload.get("ref") or "").replace("refs/heads/", ""),
            "author": (head_commit.get("author") or {}).get("name", "unknown"),
            "commit_message": head_commit.get("message", ""),
            "commit_sha": payload.get("after"),
            "files_changed": list(dict.fromkeys(
                (head_commit.get("added") or [])
                + (head_commit.get("removed") or [])
                + (head_commit.get("modified") or [])
            )),
            "commit_count": len(payload.get("commits") or []),
            "timestamp": head_commit.get("timestamp", ""),
        }
        await run_workflows(org_id, "push", push_context)
        logger.info(f"Workflow dispatch complete for push to {push_context['branch']} ({push_context['commit_sha']})")

    # --- New: pull_request "opened" actions also go through the configurable
    # workflow engine, in addition to the existing orchestrator run below for
    # all pull_request actions (unchanged). ---
    if x_github_event == "pull_request" and payload.get("action") == "opened":
        pr = payload.get("pull_request", {})
        pr_context = {
            "repo": repo_full_name,
            "title": pr.get("title", "Untitled PR"),
            "author": (pr.get("user") or {}).get("login", "unknown"),
            "source_branch": (pr.get("head") or {}).get("ref", ""),
            "target_branch": (pr.get("base") or {}).get("ref", ""),
            "draft": pr.get("draft", False),
            "labels": [l.get("name") for l in pr.get("labels", [])],
            "pr_number": pr.get("number"),
            "pr_url": pr.get("html_url"),
        }
        await run_workflows(org_id, "pull_request_opened", pr_context)
        logger.info(f"Workflow dispatch complete for PR #{pr_context['pr_number']} opened")

    # --- Existing behavior: push / pull_request / other issue actions still run the orchestrator ---
    token_res = supabase_admin.table("integrations").select("id").eq("organization_id", org_id).eq("provider", "github").eq("connected", True).order("created_at", desc=True).execute()
    if not token_res.data:
        raise HTTPException(status_code=400, detail="No connected GitHub integration for this org")
    integration_ids = [row["id"] for row in token_res.data]
    oauth_res = supabase_admin.table("oauth_tokens").select("access_token").in_("integration_id", integration_ids).order("created_at", desc=True).execute()
    if not oauth_res.data:
        raise HTTPException(status_code=400, detail="No GitHub token found for this org")
    access_token = oauth_res.data[0]["access_token"]

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
