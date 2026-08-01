from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import RedirectResponse
from pydantic_settings import BaseSettings
from jose import jwt, JWTError
from supabase import create_client
from google import genai
import httpx

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_REDIRECT_URI: str
    GEMINI_API_KEY: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    DISCORD_WEBHOOK_URL: str

    class Config:
        env_file = ".env"

settings = Settings()

supabase_admin = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

app = FastAPI(title="AI COO Backend")

@app.get("/health")
def health_check():
    return {"status": "ok"}

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
        "organization_id": org_id,
        "provider": "github",
        "connected": True
    }).execute()

    integration_id = integration.data[0]["id"]

    supabase_admin.table("oauth_tokens").insert({
        "integration_id": integration_id,
        "access_token": access_token
    }).execute()

    return {"status": "connected", "integration_id": integration_id, "access_token": access_token}

# ---------- GitHub Data ----------

@app.get("/github/repos")
async def github_repos(access_token: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    return res.json()

# ---------- GitHub Agent (AI Summary) ----------

@app.get("/github/summary")
async def github_summary(access_token: str):
    async with httpx.AsyncClient() as client:
        repos_res = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    repos = repos_res.json()

    if not isinstance(repos, list):
        raise HTTPException(status_code=400, detail=f"GitHub API error: {repos}")

    repo_info = [
        {
            "name": r["name"],
            "language": r.get("language"),
            "open_issues": r.get("open_issues_count"),
            "description": r.get("description"),
        }
        for r in repos
    ]

    prompt = f"""You are an AI assistant summarizing a developer's GitHub activity.
Here is their repo data: {repo_info}

Give a short, clear summary covering:
- Total repos
- Which repos have open issues that need attention
- What kind of projects they're working on (languages/themes)
Keep it under 150 words."""

    response = gemini_client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return {"summary": response.text}

# ---------- Planner Agent ----------

@app.get("/planner/priorities")
async def planner_priorities(access_token: str):
    async with httpx.AsyncClient() as client:
        repos_res = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    repos = repos_res.json()

    if not isinstance(repos, list):
        raise HTTPException(status_code=400, detail=f"GitHub API error: {repos}")

    # Only pull issues for repos that actually have open issues (avoids wasted calls)
    repos_with_issues = [r for r in repos if r.get("open_issues_count", 0) > 0]

    issues_data = []
    async with httpx.AsyncClient() as client:
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
                        "repo": r["name"],
                        "title": issue.get("title"),
                        "created_at": issue.get("created_at"),
                        "comments": issue.get("comments"),
                    })

    prompt = f"""You are a Planner AI for a busy developer/founder.
Here is their open GitHub issues data: {issues_data}

Task: Create a prioritized action list (max 5 items) of what needs attention first.
Consider: how old the issue is, how many comments (engagement), and which repo it's in.

Format your response as a numbered list like:
1. [Repo name] Issue title — brief reason why it's priority
2. ...

Keep each line under 20 words. If there are no issues, say so clearly."""

    response = gemini_client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return {"priorities": response.text}

# ---------- Task Manager ----------

@app.get("/tasks/create-from-priorities")
async def create_tasks_from_priorities(access_token: str, org_id: str):
    async with httpx.AsyncClient() as client:
        repos_res = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    repos = repos_res.json()

    if not isinstance(repos, list):
        raise HTTPException(status_code=400, detail=f"GitHub API error: {repos}")

    repos_with_issues = [r for r in repos if r.get("open_issues_count", 0) > 0]

    issues_data = []
    async with httpx.AsyncClient() as client:
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
                        "repo": r["name"],
                        "title": issue.get("title"),
                        "comments": issue.get("comments"),
                    })

    if not issues_data:
        return {"message": "No open issues, no tasks created", "tasks_created": 0}

    prompt = f"""You are a Planner AI. Given this GitHub issues data: {issues_data}

Return ONLY a valid JSON array (no markdown, no explanation) of up to 5 tasks, each with:
- title (string, short)
- description (string, 1 sentence)
- priority ("high", "medium", or "low")

Example format: [{{"title": "...", "description": "...", "priority": "high"}}]"""

    response = gemini_client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    import json
    raw_text = response.text.strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        tasks = json.loads(raw_text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Failed to parse AI response: {raw_text}")

    created = []
    for t in tasks:
        result = supabase_admin.table("tasks").insert({
            "organization_id": org_id,
            "title": t.get("title"),
            "description": t.get("description"),
            "priority": t.get("priority", "medium"),
            "source": "github_planner"
        }).execute()
        created.append(result.data[0])

    return {"tasks_created": len(created), "tasks": created}

@app.get("/tasks")
def get_tasks(org_id: str):
    result = supabase_admin.table("tasks").select("*").eq("organization_id", org_id).execute()
    return result.data

# ---------- GitHub Agent (Write Actions) ----------

@app.post("/github/create-issue")
async def github_create_issue(access_token: str, repo_full_name: str, title: str, body: str = ""):
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api.github.com/repos/{repo_full_name}/issues",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"title": title, "body": body}
        )

    if res.status_code != 201:
        raise HTTPException(status_code=400, detail=f"GitHub error: {res.json()}")

    issue = res.json()
    return {
        "status": "created",
        "issue_number": issue["number"],
        "url": issue["html_url"]
    }

@app.post("/tasks/{task_id}/approve-and-create-issue")
async def approve_and_create_issue(task_id: str, access_token: str, repo_full_name: str):
    task_res = supabase_admin.table("tasks").select("*").eq("id", task_id).execute()
    if not task_res.data:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_res.data[0]

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api.github.com/repos/{repo_full_name}/issues",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"title": task["title"], "body": task.get("description", "")}
        )

    if res.status_code != 201:
        raise HTTPException(status_code=400, detail=f"GitHub error: {res.json()}")

    issue = res.json()

    supabase_admin.table("tasks").update({
        "status": "issue_created"
    }).eq("id", task_id).execute()

    return {
        "status": "issue_created",
        "issue_url": issue["html_url"],
        "task_id": task_id
    }

# ---------- Gmail OAuth ----------

@app.get("/gmail/login")
def gmail_login(org_id: str):
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=https://www.googleapis.com/auth/gmail.readonly"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={org_id}"
    )
    return RedirectResponse(url)

@app.get("/gmail/callback")
async def gmail_callback(code: str, state: str):
    org_id = state

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )
        token_data = token_res.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail=f"Gmail auth failed: {token_data}")

    integration = supabase_admin.table("integrations").insert({
        "organization_id": org_id,
        "provider": "gmail",
        "connected": True
    }).execute()

    integration_id = integration.data[0]["id"]

    supabase_admin.table("oauth_tokens").insert({
        "integration_id": integration_id,
        "access_token": access_token,
        "refresh_token": token_data.get("refresh_token")
    }).execute()

    return {"status": "connected", "integration_id": integration_id, "access_token": access_token}

# ---------- Gmail Data ----------

@app.get("/gmail/unread")
async def gmail_unread(access_token: str):
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
            emails.append({
                "from": headers.get("From"),
                "subject": headers.get("Subject"),
                "snippet": msg.get("snippet")
            })

    return {"unread_count": len(emails), "emails": emails}

# ---------- Gmail Agent (AI Summary) ----------

@app.get("/gmail/summary")
async def gmail_summary(access_token: str):
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
            emails.append({
                "from": headers.get("From"),
                "subject": headers.get("Subject"),
                "snippet": msg.get("snippet")
            })

    if not emails:
        return {"summary": "No unread emails. Inbox is clear."}

    prompt = f"""You are an AI assistant summarizing unread emails for a busy founder.
Here is the email data: {emails}

Give a short summary covering:
- How many unread emails
- Which ones seem urgent or need a reply
- Any patterns (spam, newsletters, real messages)
Keep it under 150 words."""

    response = gemini_client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return {"summary": response.text}

# ---------- Calendar OAuth ----------

@app.get("/calendar/login")
def calendar_login(org_id: str):
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=https://www.googleapis.com/auth/calendar"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={org_id}"
    )
    return RedirectResponse(url)

@app.get("/calendar/callback")
async def calendar_callback(code: str, state: str):
    org_id = state

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )
        token_data = token_res.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail=f"Calendar auth failed: {token_data}")

    integration = supabase_admin.table("integrations").insert({
        "organization_id": org_id,
        "provider": "calendar",
        "connected": True
    }).execute()

    integration_id = integration.data[0]["id"]

    supabase_admin.table("oauth_tokens").insert({
        "integration_id": integration_id,
        "access_token": access_token,
        "refresh_token": token_data.get("refresh_token")
    }).execute()

    return {"status": "connected", "integration_id": integration_id, "access_token": access_token}

# ---------- Calendar Data ----------

@app.get("/calendar/events")
async def calendar_events(access_token: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "timeMin": "2026-08-01T00:00:00Z",
                "maxResults": 10,
                "singleEvents": "true",
                "orderBy": "startTime"
            }
        )
    data = res.json()
    events = data.get("items", [])

    formatted = [
        {
            "summary": e.get("summary"),
            "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
            "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
        }
        for e in events
    ]

    return {"event_count": len(formatted), "events": formatted}

# ---------- Calendar Agent (AI Summary) ----------

@app.get("/calendar/summary")
async def calendar_summary(access_token: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "timeMin": "2026-08-01T00:00:00Z",
                "maxResults": 10,
                "singleEvents": "true",
                "orderBy": "startTime"
            }
        )
    data = res.json()
    events = data.get("items", [])

    if not events:
        return {"summary": "No upcoming events. Calendar is clear."}

    formatted = [
        {
            "summary": e.get("summary"),
            "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
            "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
        }
        for e in events
    ]

    prompt = f"""You are an AI assistant summarizing a founder's upcoming calendar.
Here is the event data: {formatted}

Give a short summary covering:
- How many upcoming events
- Any potential scheduling conflicts (overlapping times)
- What's coming up soonest
Keep it under 150 words."""

    response = gemini_client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return {"summary": response.text}

# ---------- Calendar Agent (Create Event) ----------

@app.post("/calendar/create-event")
async def calendar_create_event(access_token: str, summary: str, start_time: str, end_time: str):
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "summary": summary,
                "start": {"dateTime": start_time},
                "end": {"dateTime": end_time},
            }
        )

    if res.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Calendar error: {res.json()}")

    event = res.json()
    return {"status": "created", "event_link": event.get("htmlLink")}

# ---------- Discord Agent ----------

@app.post("/discord/notify")
async def discord_notify(message: str):
    async with httpx.AsyncClient() as client:
        res = await client.post(
            settings.DISCORD_WEBHOOK_URL,
            json={"content": message}
        )

    if res.status_code not in [200, 204]:
        raise HTTPException(status_code=400, detail=f"Discord error: {res.text}")

    return {"status": "sent", "message": message}

@app.post("/discord/daily-report")
async def discord_daily_report(github_access_token: str, org_id: str):
    tasks_res = supabase_admin.table("tasks").select("*").eq("organization_id", org_id).execute()
    tasks = tasks_res.data

    open_tasks = [t for t in tasks if t.get("status") == "open"]
    done_tasks = [t for t in tasks if t.get("status") == "issue_created"]

    report = f"""**📊 Daily AI COO Report**

**Open Tasks:** {len(open_tasks)}
**Issues Created:** {len(done_tasks)}

**Top Priorities:**
"""
    for t in open_tasks[:5]:
        report += f"- [{t.get('priority', 'medium').upper()}] {t.get('title')}\n"

    async with httpx.AsyncClient() as client:
        res = await client.post(
            settings.DISCORD_WEBHOOK_URL,
            json={"content": report}
        )

    if res.status_code not in [200, 204]:
        raise HTTPException(status_code=400, detail=f"Discord error: {res.text}")

    return {"status": "sent", "report": report}
