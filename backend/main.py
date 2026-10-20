from fastapi import FastAPI, Depends, Header, HTTPException
import httpx
from datetime import datetime, timedelta, timezone

import time
from config import settings, supabase_admin, logger, encrypt_token, run_gemini


from oauth_state import _issue_oauth_state, _consume_oauth_state
from github_helpers import (
    fetch_github_repos_and_issues, github_post, github_get_paginated,
    _valid_repo, _allowed_issue_repos,
)
from github_oauth import router as github_oauth_router
from calendar_routes import router as calendar_router
from calendar_automation.routes import router as lunch_block_router

import orchestrator
import scheduler
from commit_scheduler.routes import router as commit_scheduler_router
from email_scheduler.routes import router as email_scheduler_router
from workflow_routes import router as workflow_router
from audit_logs.routes import router as audit_logs_router
from memory.routes import router as memory_router
from pull_requests.routes import router as pull_requests_router
from analytics.routes import router as analytics_router
from open_source.routes import router as open_source_router
from account.routes import router as account_router
from auth.routes import router as auth_router
from notifications.routes import router as notifications_router
from job_hunter.routes import router as job_hunter_router
from organization_settings.routes import router as organization_settings_router

app = FastAPI(title="WorkForge Backend")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration}ms)")
    return response

app.include_router(orchestrator.router)
app.include_router(scheduler.router)
app.include_router(commit_scheduler_router)
app.include_router(email_scheduler_router)
app.include_router(workflow_router)

from webhooks.routes import router as webhooks_router
app.include_router(webhooks_router)
app.include_router(audit_logs_router)
app.include_router(memory_router)
app.include_router(pull_requests_router)
app.include_router(open_source_router)
app.include_router(account_router)
app.include_router(auth_router)
app.include_router(notifications_router)
app.include_router(analytics_router)
app.include_router(job_hunter_router)
app.include_router(github_oauth_router)
app.include_router(calendar_router)
app.include_router(lunch_block_router)
app.include_router(organization_settings_router)


@app.on_event("startup")
async def on_startup():
    scheduler.start_scheduler()


@app.get("/health")
def health_check():
    return {"status": "ok"}





from auth.dependencies import get_current_user, get_current_org_id


@app.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return {"id": user.get("sub"), "email": user.get("email")}

from org_webhooks import register_github_webhook

from audit_logs.service import log_event

@app.post("/github/connect-repo")
async def connect_repo(repo_full_name: str, org_id: str = Depends(get_current_org_id)):
    _valid_repo(repo_full_name)
    base_url = (settings.RENDER_BASE_URL or settings.RENDER_EXTERNAL_URL).rstrip("/")
    if not base_url.startswith("https://"):
        raise HTTPException(status_code=503, detail="GitHub webhook URL is not configured")
    _rate_limit(org_id, "github_write", "GITHUB_WRITES_MAX_PER_ORG_PER_HOUR")
    from closeout import _resolve_access_token
    access_token = _resolve_access_token(org_id, "github")
    user_repos = await github_get_paginated("https://api.github.com/user/repos", access_token)
    canonical_repo = next(
        (str(repo.get("full_name")) for repo in user_repos
         if str(repo.get("full_name", "")).casefold() == repo_full_name.casefold()),
        None,
    )
    if not canonical_repo:
        raise HTTPException(status_code=404, detail="Repository is not available to the connected GitHub account")
    result = await register_github_webhook(
        access_token=access_token,
        repo_full_name=canonical_repo,
        org_id=org_id,
        base_url=base_url
    )
    if result is None:
        raise HTTPException(status_code=400, detail="Failed to register webhook on GitHub")

    supabase_admin.table("organizations").update({"github_repo": canonical_repo}).eq("id", org_id).execute()

    return {"status": "connected", "repo": canonical_repo, "webhook_id": result.get("id")}


@app.get("/github/repos")
async def github_repos(org_id: str = Depends(get_current_org_id)):
    from closeout import _resolve_access_token
    access_token = _resolve_access_token(org_id, "github")
    return await github_get_paginated("https://api.github.com/user/repos", access_token)


@app.get("/github/summary")
async def github_summary(org_id: str = Depends(get_current_org_id)):
    from closeout import _resolve_access_token
    org_res = supabase_admin.table("organizations").select("github_repo").eq("id", org_id).execute()
    repo_full_name = org_res.data[0].get("github_repo") if org_res.data else None
    if not repo_full_name:
        return {"summary": "Enable events for a repository to see its AI summary."}

    _rate_limit(org_id, "ai_call", "AI_CALLS_MAX_PER_ORG_PER_HOUR")
    access_token = _resolve_access_token(org_id, "github")
    issues = await github_get_paginated(
        f"https://api.github.com/repos/{repo_full_name}/issues",
        access_token,
        params={"state": "open"},
    )
    issues_data = [
        {"title": issue.get("title"), "created_at": issue.get("created_at"),
         "comments": issue.get("comments"), "labels": [label.get("name") for label in issue.get("labels", [])]}
        for issue in issues if not issue.get("pull_request")
    ]
    if not issues_data:
        return {"summary": f"{repo_full_name} has no open issues."}

    prompt = f"""You are an AI assistant summarizing the connected GitHub repository.
Repository: {repo_full_name}
Its open issues: {issues_data}

Give a short, clear summary of this repository's open issues and main areas needing attention.
Only discuss {repo_full_name}; do not mention other repositories.
Keep it under 150 words."""

    response = run_gemini(prompt)
    return {"summary": response.text}


@app.get("/planner/priorities")
async def planner_priorities(org_id: str = Depends(get_current_org_id)):
    from closeout import _resolve_access_token
    org_res = supabase_admin.table("organizations").select("github_repo").eq("id", org_id).execute()
    repo_full_name = org_res.data[0].get("github_repo") if org_res.data else None
    if not repo_full_name:
        return {"priorities": "Enable events for a repository to see its prioritized issues."}
    _rate_limit(org_id, "ai_call", "AI_CALLS_MAX_PER_ORG_PER_HOUR")
    access_token = _resolve_access_token(org_id, "github")
    issues = await github_get_paginated(
        f"https://api.github.com/repos/{repo_full_name}/issues",
        access_token,
        params={"state": "open"},
    )
    issues_data = [
        {"title": issue.get("title"), "created_at": issue.get("created_at"), "comments": issue.get("comments")}
        for issue in issues if not issue.get("pull_request")
    ]

    if not issues_data:
        return {"priorities": f"No open issues in {repo_full_name}."}

    prompt = f"""You are a Planner AI for a busy developer/founder.
Repository: {repo_full_name}
Here are its open GitHub issues: {issues_data}

Task: Create a prioritized action list (max 5 items) of what needs attention first.
Consider how old the issue is and how many comments it has. Only include issues from this repository.

Format your response as a numbered list like:
1. [Repo name] Issue title — brief reason why it's priority
2. ...

Keep each line under 20 words. If there are no issues, say so clearly."""

    response = run_gemini(prompt)
    return {"priorities": response.text}


@app.post("/tasks/create-from-priorities")
async def create_tasks_from_priorities(org_id: str = Depends(get_current_org_id)):
    from closeout import _resolve_access_token
    cooldown_cutoff = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    recent = supabase_admin.table("tasks").select("id").eq("organization_id", org_id).eq("source", "github_planner").gte("created_at", cooldown_cutoff).limit(1).execute()
    if recent.data:
        raise HTTPException(status_code=429, detail="Tasks were just generated; please wait a minute before trying again")
    _rate_limit(org_id, "ai_call", "AI_CALLS_MAX_PER_ORG_PER_HOUR")
    access_token = _resolve_access_token(org_id, "github")
    issues_data = await fetch_github_repos_and_issues(access_token)
    issues_data = [{"repo": i["repo"], "title": i["title"], "comments": i.get("comments")} for i in issues_data]

    if not issues_data:
        return {"message": "No open issues, no tasks created", "tasks_created": 0}

    prompt = f"""You are a Planner AI. Given this GitHub issues data: {issues_data}

Return ONLY a valid JSON array (no markdown, no explanation) of up to 5 tasks, each with:
- title (string, short)
- description (string, 1 sentence)
- priority ("high", "medium", or "low")

Example format: [{{"title": "...", "description": "...", "priority": "high"}}]"""

    response = run_gemini(prompt)

    import json
    raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        tasks = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("Planner returned unparseable AI response")
        raise HTTPException(status_code=502, detail="Failed to parse AI response")

    if not isinstance(tasks, list):
        raise HTTPException(status_code=502, detail="Failed to parse AI response")
    created = []
    for t in [x for x in tasks if isinstance(x, dict)][:5]:
        result = supabase_admin.table("tasks").insert({
            "organization_id": org_id, "title": t.get("title"), "description": t.get("description"),
            "priority": t.get("priority", "medium"), "source": "github_planner"
        }).execute()
        created.append(result.data[0])

    return {"tasks_created": len(created), "tasks": created}


@app.get("/tasks")
def get_tasks(org_id: str = Depends(get_current_org_id)):
    result = supabase_admin.table("tasks").select("*").eq("organization_id", org_id).execute()
    return result.data


@app.delete("/tasks/{task_id}")
def delete_task(task_id: str, user: dict = Depends(get_current_user), org_id: str = Depends(get_current_org_id)):
    task_res = supabase_admin.table("tasks").select("id,title").eq("id", task_id).eq("organization_id", org_id).execute()
    if not task_res.data:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_res.data[0]
    supabase_admin.table("tasks").delete().eq("id", task_id).eq("organization_id", org_id).execute()
    log_event(
        organization_id=org_id,
        module="tasks",
        action="task_deleted",
        summary=f"Task deleted: {task.get('title', 'Untitled')}",
        status="warning",
        user_id=user.get("sub"),
        actor_type="user",
        resource_type="task",
        resource_id=task_id,
        metadata={"title": task.get("title")},
        source="backend",
    )
    return {"status": "deleted", "task_id": task_id}


@app.get("/github/connected-repo")
def get_connected_repo(org_id: str = Depends(get_current_org_id)):
    result = supabase_admin.table("organizations").select("github_repo").eq("id", org_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"repo": result.data[0].get("github_repo")}


@app.post("/github/disconnect-repo")
def disconnect_repo(org_id: str = Depends(get_current_org_id)):
    org_res = supabase_admin.table("organizations").select("github_repo").eq("id", org_id).execute()
    if not org_res.data:
        raise HTTPException(status_code=404, detail="Organization not found")

    current_repo = org_res.data[0].get("github_repo")
    if not current_repo:
        raise HTTPException(status_code=400, detail="No repository is currently connected")

    try:
        supabase_admin.table("organizations").update({"github_repo": None}).eq("id", org_id).execute()
    except Exception as e:
        logger.error(f"Failed to disconnect repo for org {org_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect repository")

    logger.info(f"Disconnected repo {current_repo} for org {org_id}")
    log_event(
        organization_id=org_id,
        module="github",
        action="github_repo_disconnected",
        summary=f"GitHub repo disconnected: {current_repo}",
        status="warning",
        resource_type="integration",
        resource_id=current_repo,
        metadata={"repo": current_repo},
        source="backend",
    )

    return {"status": "disconnected", "repo": current_repo}


@app.post("/github/create-issue")
async def github_create_issue(repo_full_name: str, title: str, body: str = "", org_id: str = Depends(get_current_org_id)):
    from closeout import _resolve_access_token
    _valid_repo(repo_full_name)
    if not title.strip() or len(title) > 256 or len(body) > 20000:
        raise HTTPException(status_code=422, detail="Invalid issue fields")
    _rate_limit(org_id, "github_write", "GITHUB_WRITES_MAX_PER_ORG_PER_HOUR")
    access_token = _resolve_access_token(org_id, "github")
    res = await github_post(
        f"https://api.github.com/repos/{repo_full_name}/issues",
        access_token,
        json_body={"title": title, "body": body}
    )
    if res.status_code != 201:
        raise HTTPException(status_code=400, detail=f"GitHub request failed with status {res.status_code}")
    issue = res.json()
    return {"status": "created", "issue_number": issue["number"], "url": issue["html_url"]}


@app.post("/tasks/{task_id}/approve-and-create-issue")
async def approve_and_create_issue(task_id: str, repo_full_name: str | None = None, resolution: str = "resolved", user: dict = Depends(get_current_user), org_id: str = Depends(get_current_org_id)):
    from closeout import run_closeout, _resolve_access_token, parse_source_ref

    if len(resolution) > 50:
        raise HTTPException(status_code=422, detail="Invalid resolution")

    task_res = supabase_admin.table("tasks").select("*").eq("id", task_id).eq("organization_id", org_id).execute()
    if not task_res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = task_res.data[0]

    if task.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Task must be approved before creating a GitHub issue")

    allowed = _allowed_issue_repos(task, org_id)
    if repo_full_name:
        _valid_repo(repo_full_name)
        if repo_full_name.lower() not in {v.lower() for v in allowed.values()}:
            raise HTTPException(status_code=403, detail="Repository is not permitted for this task")
    else:
        repo_full_name = allowed.get("source") or allowed.get("connected")
        if not repo_full_name:
            raise HTTPException(status_code=400, detail="No repository available for this task; connect a repository first")
    _valid_repo(repo_full_name)

    access_token = _resolve_access_token(task["organization_id"], "github")

    if not _claim_task(task_id, org_id, "approved", "issue_created"):
        raise HTTPException(status_code=409, detail="Task is already being processed or completed")

    try:
        res = await github_post(
            f"https://api.github.com/repos/{repo_full_name}/issues",
            access_token,
            json_body={"title": task["title"], "body": task.get("description", "")}
        )
        if res.status_code != 201:
            raise HTTPException(status_code=400, detail=f"GitHub request failed with status {res.status_code}")
        issue = res.json()
    except Exception:
        _release_task(task_id, org_id, "issue_created", "approved")
        raise

    supabase_admin.table("tasks").update({"resolution": resolution}).eq("id", task_id).eq("organization_id", org_id).execute()
    log_event(
        organization_id=task["organization_id"],
        module="github",
        action="github_issue_created",
        summary=f"GitHub issue created for task: {task.get('title', 'Untitled')}",
        status="success",
        resource_type="task",
        resource_id=task_id,
        metadata={"issue_url": issue["html_url"]},
        source="backend",
    )

    if task.get("source_ref"):
        await run_closeout(task, approved=True, access_token=access_token, resolution=resolution, pr_url=issue.get("html_url"))

    return {"status": "issue_created", "issue_url": issue["html_url"], "task_id": task_id}


# ---------- Gmail OAuth ----------

@app.get("/gmail/login")
def gmail_login(org_id: str = Depends(get_current_org_id)):
    from oauth_redirect import google_callback_uri
    prompt_param = "&prompt=consent"
    state = _issue_oauth_state(org_id, "gmail")
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={google_callback_uri('gmail')}"
        f"&response_type=code"
        f"&scope=https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email"
        f"&access_type=offline{prompt_param}&state={state}"
    )
    return {"url": url}


@app.get("/gmail/callback")
async def gmail_callback(code: str | None = None, state: str | None = None, error: str | None = None, accept: str | None = Header(default=None)):
    from fastapi.responses import RedirectResponse
    from oauth_redirect import google_callback_uri, integration_return_url

    browser_navigation = isinstance(accept, str) and "text/html" in accept
    if not state:
        raise HTTPException(status_code=400, detail="Invalid or expired authentication request")
    org_id = _consume_oauth_state(state, "gmail")
    if error or not code:
        if browser_navigation:
            return RedirectResponse(integration_return_url("gmail", "cancelled" if error else "failed"), status_code=303)
        raise HTTPException(status_code=400, detail="Gmail authorization was cancelled" if error else "Gmail authorization failed")
    async with httpx.AsyncClient(timeout=20) as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID, "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code, "redirect_uri": google_callback_uri("gmail"), "grant_type": "authorization_code"
            }
        )
        token_data = token_res.json()

    access_token = token_data.get("access_token")
    if not access_token:
        logger.error(f"Gmail OAuth exchange failed: {token_data.get('error', 'unknown')}")
        if browser_navigation:
            return RedirectResponse(integration_return_url("gmail", "failed"), status_code=303)
        raise HTTPException(status_code=400, detail="Gmail authorization failed")

    granted_scopes = set(token_data.get("scope", "").split())
    if "https://www.googleapis.com/auth/gmail.send" not in granted_scopes:
        logger.warning("Gmail OAuth did not grant the required send scope for org %s", org_id)
        if browser_navigation:
            return RedirectResponse(integration_return_url("gmail", "missing-permission"), status_code=303)
        raise HTTPException(status_code=400, detail="Gmail send permission was not granted. Please reconnect Gmail and allow sending email.")

    integration = supabase_admin.table("integrations").insert({
        "organization_id": org_id, "provider": "gmail", "connected": True
    }).execute()
    integration_id = integration.data[0]["id"]

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3599))).isoformat()

    supabase_admin.table("oauth_tokens").insert({
        "integration_id": integration_id, "access_token": encrypt_token(access_token),
        "refresh_token": encrypt_token(token_data.get("refresh_token")), "expires_at": expires_at
    }).execute()

    if browser_navigation:
        return RedirectResponse(integration_return_url("gmail", "connected"), status_code=303)
    return {"status": "connected", "integration_id": integration_id}


# ---------- Discord Agent ----------

def _org_discord_webhook(org_id: str):
    from config import pick_discord_webhook
    org_res = supabase_admin.table("organizations").select("discord_webhook_url").eq("id", org_id).execute()
    if not org_res.data:
        raise HTTPException(status_code=404, detail="Organization not found")
    org_webhook = org_res.data[0].get("discord_webhook_url")
    webhook_url = pick_discord_webhook(org_id, org_webhook)
    if not webhook_url:
        raise HTTPException(status_code=400, detail="Discord webhook is not configured for this organization")
    return webhook_url


async def _post_discord(webhook_url: str, content: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(webhook_url, json={"content": content})
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not reach Discord")
    if res.status_code not in (200, 204):
        raise HTTPException(status_code=400, detail=f"Discord rejected the message (status {res.status_code})")


@app.post("/discord/notify")
async def discord_notify(
    message: str,
    user: dict = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    if not message.strip() or len(message) > 1900:
        raise HTTPException(status_code=422, detail="Message must be between 1 and 1900 characters")
    _rate_limit(org_id, "discord_post", "DISCORD_POSTS_MAX_PER_ORG_PER_HOUR")
    await _post_discord(_org_discord_webhook(org_id), message)
    log_event(
        organization_id=org_id,
        module="discord",
        action="discord_notify_sent",
        summary="Discord notification sent",
        status="success",
        user_id=user.get("sub"),
        actor_type="user",
        source="backend",
    )
    return {"status": "sent", "message": message}


@app.post("/discord/daily-report")
async def discord_daily_report(org_id: str = Depends(get_current_org_id)):
    _rate_limit(org_id, "discord_post", "DISCORD_POSTS_MAX_PER_ORG_PER_HOUR")
    tasks_res = supabase_admin.table("tasks").select("*").eq("organization_id", org_id).execute()
    tasks = tasks_res.data
    open_tasks = [t for t in tasks if t.get("status") == "open"]
    done_tasks = [t for t in tasks if t.get("status") == "issue_created"]

    report = f"**Daily WorkForge Report**\n\n**Open Tasks:** {len(open_tasks)}\n**Issues Created:** {len(done_tasks)}\n\n**Top Priorities:**\n"
    for t in open_tasks[:5]:
        report += f"- [{t.get('priority', 'medium').upper()}] {t.get('title')}\n"

    await _post_discord(_org_discord_webhook(org_id), report[:1900])

    return {"status": "sent", "report": report}

# ---------- Human Approval Layer ----------

def _rate_limit(org_id: str, action: str, setting_name: str):
    from config import reserve_org_action, ActionRateLimited
    try:
        reserve_org_action(org_id, action, getattr(settings, setting_name))
    except ActionRateLimited as e:
        raise HTTPException(status_code=429, detail=str(e))

def _claim_task(task_id: str, org_id: str, from_status: str, to_status: str):
    res = supabase_admin.table("tasks").update({"status": to_status}) \
        .eq("id", task_id).eq("organization_id", org_id).eq("status", from_status).execute()
    return res.data[0] if res.data else None


def _release_task(task_id: str, org_id: str, claimed_status: str, restore_status: str):
    try:
        supabase_admin.table("tasks").update({"status": restore_status}) \
            .eq("id", task_id).eq("organization_id", org_id).eq("status", claimed_status).execute()
    except Exception as e:
        logger.error(f"Failed to release task {task_id}: {e}")


def _task_conflict(task_id: str, org_id: str):
    res = supabase_admin.table("tasks").select("id").eq("id", task_id).eq("organization_id", org_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    raise HTTPException(status_code=409, detail="Task is not in a state that allows this action")


@app.post("/tasks/{task_id}/approve")
def approve_task(task_id: str, user: dict = Depends(get_current_user), org_id: str = Depends(get_current_org_id)):
    task = _claim_task(task_id, org_id, "open", "approved")
    if not task:
        _task_conflict(task_id, org_id)
    log_event(
        organization_id=task["organization_id"],
        module="tasks",
        action="task_approved",
        summary=f"Task approved: {task.get('title', 'Untitled')}",
        status="success",
        resource_type="task",
        resource_id=task_id,
        metadata={"title": task.get("title")},
        source="backend",
    )
    return {"status": "approved", "task": task}


@app.post("/tasks/{task_id}/reject")
async def reject_task(task_id: str, user: dict = Depends(get_current_user), org_id: str = Depends(get_current_org_id)):
    from closeout import run_closeout

    task = _claim_task(task_id, org_id, "open", "rejected") or _claim_task(task_id, org_id, "approved", "rejected")
    if not task:
        _task_conflict(task_id, org_id)
    log_event(
        organization_id=task["organization_id"],
        module="tasks",
        action="task_rejected",
        summary=f"Task rejected: {task.get('title', 'Untitled')}",
        status="warning",
        resource_type="task",
        resource_id=task_id,
        metadata={"title": task.get("title")},
        source="backend",
    )

    if task.get("source_ref"):
        await run_closeout(task, approved=False)

    return {"status": "rejected", "task": task}


@app.get("/tasks/pending-approval")
def get_pending_tasks(org_id: str = Depends(get_current_org_id)):
    result = supabase_admin.table("tasks").select("*").eq("organization_id", org_id).eq("status", "open").execute()
    return result.data

# ---------- Gmail Agent (Write Actions) ----------

@app.post("/tasks/{task_id}/approve-and-send-email")
async def approve_and_send_email(task_id: str, to_email: str | None = None, archive: bool = False, user: dict = Depends(get_current_user), org_id: str = Depends(get_current_org_id)):
    import base64
    from email.mime.text import MIMEText
    from closeout import run_closeout, _resolve_access_token
    from config import single_line, validate_recipient, reserve_gmail_send, GmailSendLimitExceeded

    task_res = supabase_admin.table("tasks").select("*").eq("id", task_id).eq("organization_id", org_id).execute()
    if not task_res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = task_res.data[0]

    if task.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Task must be approved before sending an email")

    access_token = _resolve_access_token(task["organization_id"], "gmail")

    if not to_email:
        profile_res = supabase_admin.table("user_profiles").select("email").eq("organization_id", task["organization_id"]).execute()
        if not profile_res.data or not profile_res.data[0].get("email"):
            raise HTTPException(status_code=400, detail="to_email required — no email on file for this organization")
        to_email = profile_res.data[0]["email"]

    try:
        to_email = validate_recipient(to_email)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recipient email")

    if not _claim_task(task_id, org_id, "approved", "email_sent"):
        raise HTTPException(status_code=409, detail="Task is already being processed or completed")

    try:
        reserve_gmail_send(org_id, "task_approval")
        message = MIMEText(task.get("description", ""))
        message["to"] = to_email
        message["subject"] = single_line(task["title"])
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"raw": raw}
            )
        if res.status_code != 200:
            if res.status_code == 401:
                raise HTTPException(status_code=401, detail="Gmail authorization expired or was revoked — please reconnect Gmail in Settings")
            raise HTTPException(status_code=400, detail=f"Gmail send failed with status {res.status_code}")
    except GmailSendLimitExceeded as e:
        _release_task(task_id, org_id, "email_sent", "approved")
        raise HTTPException(status_code=429, detail=str(e))
    except httpx.HTTPError:
        _release_task(task_id, org_id, "email_sent", "approved")
        raise HTTPException(status_code=502, detail="Could not reach Gmail")
    except Exception:
        _release_task(task_id, org_id, "email_sent", "approved")
        raise

    if task.get("source_ref"):
        await run_closeout(task, approved=True, access_token=access_token, archive=archive)

    return {"status": "email_sent", "task_id": task_id, "to": to_email}

# ---------- Scheduled Commits ----------

@app.post("/commits/schedule")
def schedule_commit(target_date: str, folder_path: str,
                     file_name: str = None, content: str = None, branch_target: str = "main",
                     org_id: str = Depends(get_current_org_id)):
    import re
    from datetime import date as _date
    try:
        _date.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="target_date must be YYYY-MM-DD")
    if not re.fullmatch(r"[A-Za-z0-9_\-./]{1,200}", folder_path) or ".." in folder_path.split("/"):
        raise HTTPException(status_code=422, detail="Invalid folder_path")
    if file_name is not None and (not re.fullmatch(r"[A-Za-z0-9_\-.]{1,100}", file_name) or file_name in (".", "..")):
        raise HTTPException(status_code=422, detail="Invalid file_name")
    if content is not None and len(content) > 20000:
        raise HTTPException(status_code=422, detail="content is too large")
    if not re.fullmatch(r"[A-Za-z0-9_\-./]{1,100}", branch_target) or ".." in branch_target:
        raise HTTPException(status_code=422, detail="Invalid branch_target")
    result = supabase_admin.table("scheduled_commits").insert({
        "organization_id": org_id,
        "target_date": target_date,
        "folder_path": folder_path,
        "file_name": file_name,
        "content": content,
        "branch_target": branch_target
    }).execute()
    return {"status": "scheduled", "entry": result.data[0]}

@app.post("/commits/run-now")
async def commits_run_now(org_id: str = Depends(get_current_org_id)):
    if org_id != settings.SCHEDULER_ORG_ID or not scheduler.scheduler_target():
        raise HTTPException(status_code=403, detail="Not permitted")
    await scheduler.check_and_commit_job()
    return {"status": "triggered"}

# ---------- Integrations Status (frontend) ----------

@app.get("/integrations")
def get_integrations_status(org_id: str = Depends(get_current_org_id)):
    result = supabase_admin.table("integrations") \
        .select("*") \
        .eq("organization_id", org_id) \
        .order("created_at", desc=True) \
        .execute()

    latest_by_provider = {}
    for row in result.data:
        provider = row["provider"]
        if provider in {"github", "gmail", "calendar"} and provider not in latest_by_provider:
            latest_by_provider[provider] = row

    return [
        {k: v for k, v in row.items() if "token" not in k.lower() and "secret" not in k.lower()}
        for row in latest_by_provider.values()
    ]

# ---------- Integration Disconnect ----------

VALID_PROVIDERS = {"github", "gmail", "calendar"}


@app.post("/{provider}/disconnect")
def disconnect_integration(provider: str, org_id: str = Depends(get_current_org_id)):
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    integration_res = supabase_admin.table("integrations") \
        .select("*") \
        .eq("organization_id", org_id) \
        .eq("provider", provider) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()

    if not integration_res.data:
        raise HTTPException(status_code=404, detail=f"No {provider} integration found for this organization")

    integration = integration_res.data[0]

    if not integration.get("connected"):
        raise HTTPException(status_code=400, detail=f"{provider} integration is already disconnected")

    try:
        supabase_admin.table("oauth_tokens").delete().eq("integration_id", integration["id"]).execute()
        supabase_admin.table("integrations").update({"connected": False}).eq("id", integration["id"]).execute()
    except Exception as e:
        logger.error(f"Failed to disconnect {provider} for org {org_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to disconnect {provider}")

    logger.info(f"Disconnected {provider} integration for org {org_id} (integration_id={integration['id']})")
    log_event(
        organization_id=org_id,
        module="integrations",
        action=f"{provider}_disconnected",
        summary=f"{provider.capitalize()} integration disconnected",
        status="warning",
        resource_type="integration",
        resource_id=integration["id"],
        metadata={"provider": provider},
        source="backend",
    )

    return {"status": "disconnected", "provider": provider}
