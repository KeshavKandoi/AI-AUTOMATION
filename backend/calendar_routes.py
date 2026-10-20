"""Google Calendar OAuth and organization-scoped calendar actions."""

import asyncio
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import RedirectResponse

from auth.dependencies import get_current_org_id, get_current_user
from audit_logs.service import log_event
from calendar_automation.service import _get_calendar_token_for_org
from config import encrypt_token, logger, reserve_org_action, settings, supabase_admin
from oauth_state import _consume_oauth_state, _issue_oauth_state
from oauth_redirect import google_callback_uri, integration_return_url

router = APIRouter()
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def _parse_event_time(value: str) -> datetime:
    if not value or len(value) > 64:
        raise HTTPException(status_code=422, detail="Invalid event time")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid event time") from exc


def _rate_limit(org_id: str, action: str, setting_name: str):
    from config import ActionRateLimited
    try:
        reserve_org_action(org_id, action, getattr(settings, setting_name))
    except ActionRateLimited as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


@router.get("/calendar/login")
def calendar_login(org_id: str = Depends(get_current_org_id)):
    state = _issue_oauth_state(org_id, "calendar")
    params = urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": google_callback_uri("calendar"),
        "response_type": "code",
        "scope": CALENDAR_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })
    return {"url": f"https://accounts.google.com/o/oauth2/v2/auth?{params}"}


@router.get("/calendar/callback")
async def calendar_callback(code: str | None = None, state: str | None = None, error: str | None = None, accept: str | None = Header(default=None)):
    browser_navigation = isinstance(accept, str) and "text/html" in accept
    if not state:
        raise HTTPException(status_code=400, detail="Invalid or expired authentication request")
    org_id = _consume_oauth_state(state, "calendar")
    if error or not code:
        if browser_navigation:
            return RedirectResponse(integration_return_url("calendar", "cancelled" if error else "failed"), status_code=303)
        raise HTTPException(status_code=400, detail="Calendar authorization was cancelled" if error else "Calendar authorization failed")
    async with httpx.AsyncClient(timeout=20) as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": google_callback_uri("calendar"),
                "grant_type": "authorization_code",
            },
        )
    token_data = token_res.json()
    access_token = token_data.get("access_token")
    if not access_token:
        logger.error("Calendar OAuth exchange failed: %s", token_data.get("error", "unknown"))
        if browser_navigation:
            return RedirectResponse(integration_return_url("calendar", "failed"), status_code=303)
        raise HTTPException(status_code=400, detail="Calendar authorization failed")

    integration = supabase_admin.table("integrations").insert({
        "organization_id": org_id, "provider": "calendar", "connected": True,
    }).execute()
    integration_id = integration.data[0]["id"]
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3599))).isoformat()
    supabase_admin.table("oauth_tokens").insert({
        "integration_id": integration_id,
        "access_token": encrypt_token(access_token),
        "refresh_token": encrypt_token(token_data.get("refresh_token")),
        "expires_at": expires_at,
    }).execute()
    if browser_navigation:
        return RedirectResponse(integration_return_url("calendar", "connected"), status_code=303)
    return {"status": "connected", "integration_id": integration_id}


@router.get("/calendar/events")
async def calendar_events(org_id: str = Depends(get_current_org_id)):
    access_token = await asyncio.to_thread(_get_calendar_token_for_org, org_id)
    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.get(
            CALENDAR_EVENTS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "timeMin": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "maxResults": 10,
                "singleEvents": "true",
                "orderBy": "startTime",
            },
        )
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not load calendar events")
    events = res.json().get("items", [])
    formatted = [
        {
            "summary": event.get("summary"),
            "start": event.get("start", {}).get("dateTime") or event.get("start", {}).get("date"),
            "end": event.get("end", {}).get("dateTime") or event.get("end", {}).get("date"),
        }
        for event in events
    ]
    return {"event_count": len(formatted), "events": formatted}


@router.post("/calendar/create-event")
async def calendar_create_event(
    summary: str,
    start_time: str,
    end_time: str,
    org_id: str = Depends(get_current_org_id),
):
    if not summary.strip() or len(summary) > 500 or len(start_time) > 64 or len(end_time) > 64:
        raise HTTPException(status_code=422, detail="Invalid event fields")
    _parse_event_time(start_time)
    _parse_event_time(end_time)
    _rate_limit(org_id, "calendar_create", "CALENDAR_CREATES_MAX_PER_ORG_PER_HOUR")
    access_token = _get_calendar_token_for_org(org_id)
    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.post(
            CALENDAR_EVENTS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"summary": summary, "start": {"dateTime": start_time}, "end": {"dateTime": end_time}},
        )
    if res.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Calendar request failed with status {res.status_code}")
    return {"status": "created", "event_link": res.json().get("htmlLink")}


@router.post("/tasks/{task_id}/approve-and-create-event")
async def approve_and_create_event(
    task_id: str,
    start_time: str,
    end_time: str,
    user: dict = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    _parse_event_time(start_time)
    _parse_event_time(end_time)
    task_res = supabase_admin.table("tasks").select("*").eq("id", task_id).eq("organization_id", org_id).execute()
    if not task_res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = task_res.data[0]
    if task.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Task must be approved before creating a calendar event")
    access_token = _get_calendar_token_for_org(task["organization_id"])
    claim = supabase_admin.table("tasks").update({"status": "event_created"}).eq("id", task_id).eq("organization_id", org_id).eq("status", "approved").execute()
    if not claim.data:
        raise HTTPException(status_code=409, detail="Task is already being processed or completed")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                CALENDAR_EVENTS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "summary": task["title"],
                    "description": task.get("description", ""),
                    "start": {"dateTime": start_time},
                    "end": {"dateTime": end_time},
                },
            )
        if res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Calendar request failed with status {res.status_code}")
        event = res.json()
    except httpx.HTTPError as exc:
        supabase_admin.table("tasks").update({"status": "approved"}).eq("id", task_id).eq("organization_id", org_id).eq("status", "event_created").execute()
        raise HTTPException(status_code=502, detail="Could not reach Google Calendar") from exc
    except Exception:
        supabase_admin.table("tasks").update({"status": "approved"}).eq("id", task_id).eq("organization_id", org_id).eq("status", "event_created").execute()
        raise
    log_event(
        organization_id=task["organization_id"], module="calendar", action="calendar_event_created",
        summary=f"Calendar event created for task: {task.get('title', 'Untitled')}", status="success",
        resource_type="task", resource_id=task_id, metadata={"event_link": event.get("htmlLink")}, source="backend",
    )
    if task.get("source_ref"):
        from closeout import run_closeout
        await run_closeout(
            task,
            approved=True,
            notes=f"Follow-up event created: {event.get('htmlLink')}",
        )
    return {"status": "event_created", "task_id": task_id, "event_link": event.get("htmlLink")}
