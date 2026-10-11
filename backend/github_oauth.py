"""GitHub OAuth endpoints. OAuth state is issued and consumed by oauth_state."""

import httpx
from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import get_current_org_id
from config import encrypt_token, settings, supabase_admin
from oauth_state import _consume_oauth_state, _issue_oauth_state

router = APIRouter()


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
async def github_callback(code: str, state: str):
    org_id = _consume_oauth_state(state, "github")
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
        raise HTTPException(status_code=400, detail="GitHub auth failed")

    integration = supabase_admin.table("integrations").insert({
        "organization_id": org_id, "provider": "github", "connected": True
    }).execute()
    integration_id = integration.data[0]["id"]

    supabase_admin.table("oauth_tokens").insert({
        "integration_id": integration_id, "access_token": encrypt_token(access_token)
    }).execute()

    return {"status": "connected", "integration_id": integration_id}
