"""GitHub OAuth endpoints. OAuth state is issued and consumed by oauth_state."""

from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from auth.dependencies import get_current_org_id
from config import encrypt_token, settings, supabase_admin
from oauth_state import _consume_oauth_state, _issue_oauth_state

router = APIRouter()


def _frontend_callback_url(result: str) -> str:
    allowed_origins = [
        origin.strip().rstrip("/")
        for origin in settings.ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ]
    frontend_url = settings.FRONTEND_URL.strip().rstrip("/") or (
        allowed_origins[0] if allowed_origins else ""
    )
    if frontend_url not in allowed_origins:
        raise HTTPException(status_code=503, detail="Frontend redirect URL is not configured")
    return f"{frontend_url}/integrations/github?{urlencode({'github': result})}"


@router.get("/github/login")
def github_login(org_id: str = Depends(get_current_org_id)):
    state = _issue_oauth_state(org_id, "github")
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=repo,read:user"
        f"&state={state}"
    )
    return {"url": url}


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    browser_navigation = "text/html" in request.headers.get("accept", "")
    if not state:
        raise HTTPException(status_code=400, detail="Invalid or expired authentication request")
    org_id = _consume_oauth_state(state, "github")
    if error:
        if not browser_navigation:
            raise HTTPException(status_code=400, detail="GitHub authorization was cancelled")
        return RedirectResponse(_frontend_callback_url("cancelled"), status_code=303)
    if not code:
        if not browser_navigation:
            raise HTTPException(status_code=400, detail="GitHub authorization failed")
        return RedirectResponse(_frontend_callback_url("failed"), status_code=303)

    async with httpx.AsyncClient(timeout=20) as client:
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
        if not browser_navigation:
            raise HTTPException(status_code=400, detail="GitHub auth failed")
        return RedirectResponse(_frontend_callback_url("failed"), status_code=303)

    integration = supabase_admin.table("integrations").insert({
        "organization_id": org_id, "provider": "github", "connected": True
    }).execute()
    integration_id = integration.data[0]["id"]

    supabase_admin.table("oauth_tokens").insert({
        "integration_id": integration_id, "access_token": encrypt_token(access_token)
    }).execute()

    if browser_navigation:
        return RedirectResponse(_frontend_callback_url("connected"), status_code=303)
    return {"status": "connected", "integration_id": integration_id}
