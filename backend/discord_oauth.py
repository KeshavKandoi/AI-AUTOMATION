"""Discord OAuth2 webhook authorization for organization notifications."""

from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from auth.dependencies import get_current_org_id
from config import is_valid_discord_webhook, logger, settings, supabase_admin
from oauth_redirect import integration_return_url, is_browser_navigation
from oauth_state import _consume_oauth_state, _issue_oauth_state

router = APIRouter(prefix="/discord", tags=["discord"])


def _redirect_uri() -> str:
    configured = settings.DISCORD_REDIRECT_URI.strip()
    service_url = settings.RENDER_EXTERNAL_URL.strip().rstrip("/")
    uri = configured or (f"{service_url}/discord/callback" if service_url else "")
    if not uri or not uri.startswith("https://") and not uri.startswith("http://127.0.0.1:"):
        raise HTTPException(status_code=503, detail="Discord callback URL is not configured")
    return uri


@router.get("/login")
def discord_login(org_id: str = Depends(get_current_org_id)):
    if not settings.DISCORD_CLIENT_ID or not settings.DISCORD_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Discord connection is not configured yet")
    state = _issue_oauth_state(org_id, "discord")
    url = "https://discord.com/oauth2/authorize?" + urlencode({
        "response_type": "code",
        "client_id": settings.DISCORD_CLIENT_ID,
        "scope": "webhook.incoming",
        "state": state,
        "redirect_uri": _redirect_uri(),
    })
    return {"url": url}


@router.get("/callback")
async def discord_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    browser = is_browser_navigation(request.headers.get("accept"), request.headers.get("sec-fetch-mode"))
    if not state:
        raise HTTPException(status_code=400, detail="Invalid or expired authentication request")
    org_id = _consume_oauth_state(state, "discord")
    if error or not code:
        result = "cancelled" if error == "access_denied" else "failed"
        if browser:
            return RedirectResponse(integration_return_url("discord", result), status_code=303)
        raise HTTPException(status_code=400, detail="Discord authorization was cancelled or failed")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://discord.com/api/oauth2/token", data={
                "client_id": settings.DISCORD_CLIENT_ID,
                "client_secret": settings.DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": _redirect_uri(),
            }, headers={"Content-Type": "application/x-www-form-urlencoded"})
            response.raise_for_status()
            webhook_url = response.json().get("webhook", {}).get("url")
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        logger.warning("Discord OAuth token exchange failed for organization %s", org_id)
        webhook_url = None

    if not is_valid_discord_webhook(webhook_url):
        if browser:
            return RedirectResponse(integration_return_url("discord", "failed"), status_code=303)
        raise HTTPException(status_code=400, detail="Discord did not return a usable webhook")

    saved = supabase_admin.table("organizations").update({"discord_webhook_url": webhook_url}).eq("id", org_id).select("id").execute()
    if not saved.data:
        raise HTTPException(status_code=404, detail="Organization settings were not found")
    if browser:
        return RedirectResponse(integration_return_url("discord", "connected"), status_code=303)
    return {"status": "connected"}
