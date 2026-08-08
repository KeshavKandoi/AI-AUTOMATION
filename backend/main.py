from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
import httpx
from datetime import datetime, timedelta, timezone

import time
from config import settings, supabase_admin, gemini_client, logger, encrypt_token, decrypt_token, get_valid_access_token

def run_gemini(prompt: str):
    """Wraps a Gemini generate_content call. Raises a clean 503 on transient
    provider errors (overload, unavailable) instead of letting them surface
    as unhandled 500s. Logs the real exception for debugging."""
    from google.genai import errors as genai_errors
    try:
        return gemini_client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    except genai_errors.ServerError as e:
        logger.error(f"Gemini ServerError (transient): {e}")
        raise HTTPException(status_code=503, detail="AI service is temporarily unavailable. Please try again shortly.")
    except genai_errors.APIError as e:
        logger.error(f"Gemini APIError: {e}")
        raise HTTPException(status_code=503, detail="AI service is temporarily unavailable. Please try again shortly.")
    except Exception as e:
        logger.error(f"Unexpected error calling Gemini: {e}")
        raise HTTPException(status_code=503, detail="AI service is temporarily unavailable. Please try again shortly.")


async def fetch_github_repos_and_issues(access_token: str):
    """Fetches the user's repos and open issues for repos that have any.
    Wraps outbound GitHub calls so transient network failures (dropped
    connections, timeouts) return a clean error instead of an unhandled 500."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            repos_res = await client.get(
                "https://api.github.com/user/repos",
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as e:
        logger.error(f"GitHub repos fetch failed: {e}")
        raise HTTPException(status_code=502, detail="Couldn't reach GitHub. Please try again shortly.")

    repos = repos_res.json()
    if not isinstance(repos, list):
        raise HTTPException(status_code=400, detail=f"GitHub API error: {repos}")

    repos_with_issues = [r for r in repos if r.get("open_issues_count", 0) > 0]
    issues_data = []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            for r in repos_with_issues:
                issues_res = await client.get(
                    f"https://api.github.com/repos/{r['full_name']}/issues",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"state": "open"}
                )
                issues = issues_res.json()
                if isinstance(issues, list):
                    for issue in issues:
                        issues_data.append({
                            "repo": r["name"], "title": issue.get("title"),
                            "created_at": issue.get("created_at"), "comments": issue.get("comments"),
                        })
    except httpx.HTTPError as e:
        logger.error(f"GitHub issues fetch failed: {e}")
        raise HTTPException(status_code=502, detail="Couldn't reach GitHub. Please try again shortly.")

    return issues_data


async def github_get(url: str, access_token: str, params: dict = None):
    """GET a GitHub API URL with clean handling for network-level failures."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
        return res
    except httpx.HTTPError as e:
        logger.error(f"GitHub GET {url} failed: {e}")
        raise HTTPException(status_code=502, detail="Couldn't reach GitHub. Please try again shortly.")


async def github_post(url: str, access_token: str, json_body: dict = None):
    """POST to a GitHub API URL with clean handling for network-level failures."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                json=json_body,
            )
        return res
    except httpx.HTTPError as e:
        logger.error(f"GitHub POST {url} failed: {e}")
        raise HTTPException(status_code=502, detail="Couldn't reach GitHub. Please try again shortly.")
import orchestrator
import scheduler
from commit_scheduler.routes import router as commit_scheduler_router
from email_scheduler.routes import router as email_scheduler_router
from workflow_routes import router as workflow_router
from calendar_automation.routes import router as lunch_block_router
from audit_logs.routes import router as audit_logs_router
from memory.routes import router as memory_router
from auth.routes import router as auth_router
from notifications.routes import router as notifications_router
from job_hunter.routes import router as job_hunter_router

app = FastAPI(title="AI COO Backend")

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
app.include_router(lunch_block_router)
app.include_router(audit_logs_router)
app.include_router(memory_router)
app.include_router(auth_router)
app.include_router(notifications_router)
app.include_router(job_hunter_router)


@app.on_event("startup")
async def on_startup():
    scheduler.start_scheduler()


@app.get("/tokens/{integration_id}/valid")
def get_valid_token(integration_id: str):
    try:
        token = get_valid_access_token(integration_id)
        return {"status": "ok", "access_token": token}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/debug/probe-error-check")
def debug_probe_error_check(email: str):
    """TEMPORARY — shows the exact error message Supabase returns for a
    sign_in_with_password probe, to fix the forgot_password existence check."""
    from config import supabase_admin
    try:
        supabase_admin.auth.sign_in_with_password({"email": email, "password": "__nonexistent_probe__"})
        return {"result": "unexpected success"}
    except Exception as e:
        return {"error_str": str(e), "error_type": str(type(e))}




def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return {"id": user.get("sub"), "email": user.get("email")}

# ---------- GitHub OAuth ----------

@app.get("/github/login")
def github_login(org_id: str):
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=repo,read:user"
        f"&state={org_id}"
    )
    return RedirectResponse(url)


@app.get("/github/callback")
async def github_callback(code: str, state: str):
    org_id = state
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
        )
        token_data = token_res.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub auth failed")

    integration = supabase_admin.table("integrations").insert({
        "organization_id": org_id, "provider": "github", "connected": True
    }).execute()
    integration_id = integration.data[0]["id"]

    supabase_admin.table("oauth_tokens").insert({
        "integration_id": integration_id, "access_token": encrypt_token(access_token)
    }).execute()

    return {"status": "connected", "integration_id": integration_id, "access_token": access_token}


from org_webhooks import register_github_webhook

RENDER_BASE_URL = "https://ai-automation-d2s2.onrender.com"

from missed_event_recovery.scheduler_jobs import run_missed_event_recovery
from audit_logs.service import log_event

@app.post("/missed-events/run-now")
async def trigger_missed_event_recovery():
    await run_missed_event_recovery()
    return {"status": "triggered"}


@app.post("/github/connect-repo")
async def connect_repo(org_id: str, repo_full_name: str):
    from closeout import _resolve_access_token
    access_token = _resolve_access_token(org_id, "github")
    result = await register_github_webhook(
        access_token=access_token,
        repo_full_name=repo_full_name,
        org_id=org_id,
        base_url=RENDER_BASE_URL
    )
    if result is None:
        raise HTTPException(status_code=400, detail="Failed to register webhook on GitHub")

    supabase_admin.table("organizations").update({"github_repo": repo_full_name}).eq("id", org_id).execute()

    return {"status": "connected", "repo": repo_full_name, "webhook_id": result.get("id")}


@app.get("/github/repos")
async def github_repos(org_id: str):
    from closeout import _resolve_access_token
    access_token = _resolve_access_token(org_id, "github")
    res = await github_get("https://api.github.com/user/repos", access_token)
    return res.json()


@app.get("/github/summary")
async def github_summary(org_id: str):
    from closeout import _resolve_access_token
    access_token = _resolve_access_token(org_id, "github")
    repos_res = await github_get("https://api.github.com/user/repos", access_token)
    repos = repos_res.json()
    if not isinstance(repos, list):
        raise HTTPException(status_code=400, detail=f"GitHub API error: {repos}")

    repo_info = [
        {"name": r["name"], "language": r.get("language"),
         "open_issues": r.get("open_issues_count"), "description": r.get("description")}
        for r in repos
    ]

    prompt = f"""You are an AI assistant summarizing a developer's GitHub activity.
Here is their repo data: {repo_info}

Give a short, clear summary covering:
- Total repos
- Which repos have open issues that need attention
- What kind of projects they're working on (languages/themes)
Keep it under 150 words."""

    response = run_gemini(prompt)
    return {"summary": response.text}


@app.get("/planner/priorities")
async def planner_priorities(org_id: str):
    from closeout import _resolve_access_token
    access_token = _resolve_access_token(org_id, "github")
    issues_data = await fetch_github_repos_and_issues(access_token)

    prompt = f"""You are a Planner AI for a busy developer/founder.
Here is their open GitHub issues data: {issues_data}

Task: Create a prioritized action list (max 5 items) of what needs attention first.
Consider: how old the issue is, how many comments (engagement), and which repo it's in.

Format your response as a numbered list like:
1. [Repo name] Issue title — brief reason why it's priority
2. ...

Keep each line under 20 words. If there are no issues, say so clearly."""

    response = run_gemini(prompt)
    return {"priorities": response.text}


@app.get("/tasks/create-from-priorities")
async def create_tasks_from_priorities(org_id: str):
    from closeout import _resolve_access_token
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
        raise HTTPException(status_code=500, detail=f"Failed to parse AI response: {raw_text}")

    created = []
    for t in tasks:
        result = supabase_admin.table("tasks").insert({
            "organization_id": org_id, "title": t.get("title"), "description": t.get("description"),
            "priority": t.get("priority", "medium"), "source": "github_planner"
        }).execute()
        created.append(result.data[0])

    return {"tasks_created": len(created), "tasks": created}


@app.get("/tasks")
def get_tasks(org_id: str):
    result = supabase_admin.table("tasks").select("*").eq("organization_id", org_id).execute()
    return result.data


@app.get("/github/connected-repo")
def get_connected_repo(org_id: str):
    result = supabase_admin.table("organizations").select("github_repo").eq("id", org_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"repo": result.data[0].get("github_repo")}


@app.post("/github/disconnect-repo")
def disconnect_repo(org_id: str):
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
        raise HTTPException(status_code=500, detail=f"Failed to disconnect repository: {e}")

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
async def github_create_issue(org_id: str, repo_full_name: str, title: str, body: str = ""):
    from closeout import _resolve_access_token
    access_token = _resolve_access_token(org_id, "github")
    res = await github_post(
        f"https://api.github.com/repos/{repo_full_name}/issues",
        access_token,
        json_body={"title": title, "body": body}
    )
    if res.status_code != 201:
        raise HTTPException(status_code=400, detail=f"GitHub error: {res.json()}")
    issue = res.json()
    return {"status": "created", "issue_number": issue["number"], "url": issue["html_url"]}


@app.post("/tasks/{task_id}/approve-and-create-issue")
async def approve_and_create_issue(task_id: str, access_token: str | None = None, repo_full_name: str | None = None, resolution: str = "resolved"):
    from closeout import run_closeout, _resolve_access_token, parse_source_ref

    task_res = supabase_admin.table("tasks").select("*").eq("id", task_id).execute()
    if not task_res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = task_res.data[0]

    if task.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Task must be approved before creating a GitHub issue")

    if not access_token:
        access_token = _resolve_access_token(task["organization_id"], "github")

    if not repo_full_name:
        source_type, identifier = parse_source_ref(task.get("source_ref") or "")
        if source_type != "github" or not identifier or "#" not in identifier:
            raise HTTPException(status_code=400, detail="repo_full_name required — task has no GitHub source_ref to infer it from")
        repo_full_name = identifier.rsplit("#", 1)[0]

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api.github.com/repos/{repo_full_name}/issues",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"title": task["title"], "body": task.get("description", "")}
        )
    if res.status_code != 201:
        raise HTTPException(status_code=400, detail=f"GitHub error: {res.json()}")
    issue = res.json()

    supabase_admin.table("tasks").update({"status": "issue_created", "resolution": resolution}).eq("id", task_id).execute()
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
def gmail_login(org_id: str):
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_GMAIL_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send"
        f"&access_type=offline&prompt=consent&state={org_id}"
    )
    return RedirectResponse(url)


@app.get("/gmail/callback")
async def gmail_callback(code: str, state: str):
    org_id = state
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID, "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code, "redirect_uri": settings.GOOGLE_GMAIL_REDIRECT_URI, "grant_type": "authorization_code"
            }
        )
        token_data = token_res.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail=f"Gmail auth failed: {token_data}")

    integration = supabase_admin.table("integrations").insert({
        "organization_id": org_id, "provider": "gmail", "connected": True
    }).execute()
    integration_id = integration.data[0]["id"]

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3599))).isoformat()

    supabase_admin.table("oauth_tokens").insert({
        "integration_id": integration_id, "access_token": encrypt_token(access_token),
        "refresh_token": encrypt_token(token_data.get("refresh_token")), "expires_at": expires_at
    }).execute()

    return {"status": "connected", "integration_id": integration_id, "access_token": access_token}


@app.get("/gmail/unread")
async def gmail_unread(org_id: str):
    from closeout import _resolve_access_token
    access_token = _resolve_access_token(org_id, "gmail")
    async with httpx.AsyncClient() as client:
        list_res = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"q": "is:unread", "maxResults": 10}
        )
    messages = list_res.json().get("messages", [])

    emails = []
    async with httpx.AsyncClient() as client:
        for m in messages:
            msg_res = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "metadata", "metadataHeaders": ["From", "Subject"]}
            )
            msg = msg_res.json()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            emails.append({"from": headers.get("From"), "subject": headers.get("Subject"), "snippet": msg.get("snippet")})

    return {"unread_count": len(emails), "emails": emails}


@app.get("/gmail/summary")
async def gmail_summary(org_id: str):
    from closeout import _resolve_access_token
    access_token = _resolve_access_token(org_id, "gmail")
    async with httpx.AsyncClient() as client:
        list_res = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"q": "is:unread", "maxResults": 10}
        )
    messages = list_res.json().get("messages", [])

    emails = []
    async with httpx.AsyncClient() as client:
        for m in messages:
            msg_res = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "metadata", "metadataHeaders": ["From", "Subject"]}
            )
            msg = msg_res.json()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            emails.append({"from": headers.get("From"), "subject": headers.get("Subject"), "snippet": msg.get("snippet")})

    if not emails:
        return {"summary": "No unread emails. Inbox is clear."}

    prompt = f"""You are an AI assistant summarizing unread emails for a busy founder.
Here is the email data: {emails}

Give a short summary covering:
- How many unread emails
- Which ones seem urgent or need a reply
- Any patterns (spam, newsletters, real messages)
Keep it under 150 words."""

    response = run_gemini(prompt)
    return {"summary": response.text}

# ---------- Calendar OAuth ----------

@app.get("/calendar/login")
def calendar_login(org_id: str):
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_CALENDAR_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=https://www.googleapis.com/auth/calendar"
        f"&access_type=offline&prompt=consent&state={org_id}"
    )
    return RedirectResponse(url)


@app.get("/calendar/callback")
async def calendar_callback(code: str, state: str):
    org_id = state
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID, "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code, "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI, "grant_type": "authorization_code"
            }
        )
        token_data = token_res.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail=f"Calendar auth failed: {token_data}")

    integration = supabase_admin.table("integrations").insert({
        "organization_id": org_id, "provider": "calendar", "connected": True
    }).execute()
    integration_id = integration.data[0]["id"]

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3599))).isoformat()

    supabase_admin.table("oauth_tokens").insert({
        "integration_id": integration_id, "access_token": encrypt_token(access_token),
        "refresh_token": encrypt_token(token_data.get("refresh_token")), "expires_at": expires_at
    }).execute()

    return {"status": "connected", "integration_id": integration_id, "access_token": access_token}


@app.get("/calendar/events")
async def calendar_events(org_id: str):
    from closeout import _resolve_access_token
    access_token = _resolve_access_token(org_id, "calendar")
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"timeMin": "2026-08-01T00:00:00Z", "maxResults": 10, "singleEvents": "true", "orderBy": "startTime"}
        )
    data = res.json()
    events = data.get("items", [])
    formatted = [
        {"summary": e.get("summary"),
         "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
         "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date")}
        for e in events
    ]
    return {"event_count": len(formatted), "events": formatted}


@app.get("/calendar/summary")
async def calendar_summary(org_id: str):
    from closeout import _resolve_access_token
    access_token = _resolve_access_token(org_id, "calendar")
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"timeMin": "2026-08-01T00:00:00Z", "maxResults": 10, "singleEvents": "true", "orderBy": "startTime"}
        )
    data = res.json()
    events = data.get("items", [])
    if not events:
        return {"summary": "No upcoming events. Calendar is clear."}

    formatted = [
        {"summary": e.get("summary"),
         "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
         "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date")}
        for e in events
    ]

    prompt = f"""You are an AI assistant summarizing a founder's upcoming calendar.
Here is the event data: {formatted}

Give a short summary covering:
- How many upcoming events
- Any potential scheduling conflicts (overlapping times)
- What's coming up soonest
Keep it under 150 words."""

    response = run_gemini(prompt)
    return {"summary": response.text}


@app.post("/calendar/create-event")
async def calendar_create_event(org_id: str, summary: str, start_time: str, end_time: str):
    from closeout import _resolve_access_token
    access_token = _resolve_access_token(org_id, "calendar")
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"summary": summary, "start": {"dateTime": start_time}, "end": {"dateTime": end_time}}
        )
    if res.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Calendar error: {res.json()}")
    event = res.json()
    return {"status": "created", "event_link": event.get("htmlLink")}

# ---------- Discord Agent ----------

@app.post("/discord/notify")
async def discord_notify(message: str):
    async with httpx.AsyncClient() as client:
        res = await client.post(settings.DISCORD_WEBHOOK_URL, json={"content": message})
    if res.status_code not in [200, 204]:
        raise HTTPException(status_code=400, detail=f"Discord error: {res.text}")
    return {"status": "sent", "message": message}


@app.post("/discord/daily-report")
async def discord_daily_report(github_access_token: str, org_id: str):
    tasks_res = supabase_admin.table("tasks").select("*").eq("organization_id", org_id).execute()
    tasks = tasks_res.data
    open_tasks = [t for t in tasks if t.get("status") == "open"]
    done_tasks = [t for t in tasks if t.get("status") == "issue_created"]

    report = f"**📊 Daily AI COO Report**\n\n**Open Tasks:** {len(open_tasks)}\n**Issues Created:** {len(done_tasks)}\n\n**Top Priorities:**\n"
    for t in open_tasks[:5]:
        report += f"- [{t.get('priority', 'medium').upper()}] {t.get('title')}\n"

    async with httpx.AsyncClient() as client:
        res = await client.post(settings.DISCORD_WEBHOOK_URL, json={"content": report})
    if res.status_code not in [200, 204]:
        raise HTTPException(status_code=400, detail=f"Discord error: {res.text}")

    return {"status": "sent", "report": report}

# ---------- Memory System moved to memory/routes.py ----------

# ---------- Human Approval Layer ----------

@app.post("/tasks/{task_id}/approve")
def approve_task(task_id: str):
    result = supabase_admin.table("tasks").update({"status": "approved"}).eq("id", task_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = result.data[0]
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
async def reject_task(task_id: str):
    from closeout import run_closeout

    result = supabase_admin.table("tasks").update({"status": "rejected"}).eq("id", task_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = result.data[0]
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
def get_pending_tasks(org_id: str):
    result = supabase_admin.table("tasks").select("*").eq("organization_id", org_id).eq("status", "open").execute()
    return result.data

# ---------- Gmail Agent (Write Actions) ----------

@app.post("/tasks/{task_id}/approve-and-send-email")
async def approve_and_send_email(task_id: str, access_token: str | None = None, to_email: str | None = None, archive: bool = False):
    import base64
    from email.mime.text import MIMEText
    from closeout import run_closeout, _resolve_access_token

    task_res = supabase_admin.table("tasks").select("*").eq("id", task_id).execute()
    if not task_res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = task_res.data[0]

    if task.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Task must be approved before sending an email")

    if not access_token:
        access_token = _resolve_access_token(task["organization_id"], "gmail")

    if not to_email:
        profile_res = supabase_admin.table("user_profiles").select("email").eq("organization_id", task["organization_id"]).execute()
        if not profile_res.data or not profile_res.data[0].get("email"):
            raise HTTPException(status_code=400, detail="to_email required — no email on file for this organization")
        to_email = profile_res.data[0]["email"]

    message = MIMEText(task.get("description", ""))
    message["to"] = to_email
    message["subject"] = task["title"]
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"raw": raw}
        )

    if res.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Gmail send error: {res.json()}")

    supabase_admin.table("tasks").update({"status": "email_sent"}).eq("id", task_id).execute()

    if task.get("source_ref"):
        await run_closeout(task, approved=True, access_token=access_token, archive=archive)

    return {"status": "email_sent", "task_id": task_id, "to": to_email}

# ---------- Calendar Agent (Write Action, Approval-Gated) ----------

@app.post("/tasks/{task_id}/approve-and-create-event")
async def approve_and_create_event(task_id: str, start_time: str, end_time: str, access_token: str | None = None):
    from closeout import run_closeout, _resolve_access_token

    task_res = supabase_admin.table("tasks").select("*").eq("id", task_id).execute()
    if not task_res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = task_res.data[0]

    if task.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Task must be approved before creating a calendar event")

    if not access_token:
        access_token = _resolve_access_token(task["organization_id"], "calendar")

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "summary": task["title"],
                "description": task.get("description", ""),
                "start": {"dateTime": start_time},
                "end": {"dateTime": end_time},
            }
        )

    if res.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Calendar error: {res.json()}")

    event = res.json()
    supabase_admin.table("tasks").update({"status": "event_created"}).eq("id", task_id).execute()
    log_event(
        organization_id=task["organization_id"],
        module="calendar",
        action="calendar_event_created",
        summary=f"Calendar event created for task: {task.get('title', 'Untitled')}",
        status="success",
        resource_type="task",
        resource_id=task_id,
        metadata={"event_link": event.get("htmlLink")},
        source="backend",
    )

    if task.get("source_ref"):
        await run_closeout(task, approved=True, access_token=access_token, notes=f"Follow-up event created: {event.get('htmlLink')}")

    return {"status": "event_created", "event_link": event.get("htmlLink"), "task_id": task_id}

# ---------- Scheduled Commits ----------

@app.post("/commits/schedule")
def schedule_commit(org_id: str, target_date: str, folder_path: str,
                     file_name: str = None, content: str = None, branch_target: str = "main"):
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
async def commits_run_now():
    await scheduler.check_and_commit_job()
    return {"status": "triggered"}

# ---------- Integrations Status (frontend) ----------

@app.get("/integrations")
def get_integrations_status(org_id: str):
    result = supabase_admin.table("integrations") \
        .select("*") \
        .eq("organization_id", org_id) \
        .order("created_at", desc=True) \
        .execute()

    latest_by_provider = {}
    for row in result.data:
        provider = row["provider"]
        if provider not in latest_by_provider:
            latest_by_provider[provider] = row

    return list(latest_by_provider.values())

# ---------- Audit Logs moved to audit_logs/routes.py ----------

# ---------- Integration Disconnect ----------

VALID_PROVIDERS = {"github", "gmail", "calendar"}


@app.post("/{provider}/disconnect")
def disconnect_integration(provider: str, org_id: str):
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
        raise HTTPException(status_code=500, detail=f"Failed to disconnect {provider}: {e}")

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
