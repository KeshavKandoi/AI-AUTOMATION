import secrets
import httpx
from fastapi import HTTPException
from config import supabase_admin, logger


def get_or_create_org_webhook_secret(org_id: str) -> str:
    org_res = supabase_admin.table("organizations").select("webhook_secret").eq("id", org_id).execute()
    if org_res.data and org_res.data[0].get("webhook_secret"):
        return org_res.data[0]["webhook_secret"]
    new_secret = secrets.token_hex(32)
    supabase_admin.table("organizations").update({"webhook_secret": new_secret}).eq("id", org_id).execute()
    return new_secret


def get_org_by_webhook_secret(secret: str):
    result = supabase_admin.table("organizations").select("*").eq("webhook_secret", secret).execute()
    return result.data[0] if result.data else None


async def register_github_webhook(access_token: str, repo_full_name: str, org_id: str, base_url: str):
    webhook_secret = get_or_create_org_webhook_secret(org_id)
    target_url = f"{base_url}/webhooks/github"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                f"https://api.github.com/repos/{repo_full_name}/hooks",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
                json={
                    "name": "web",
                    "active": True,
                    "events": ["push", "issues", "pull_request"],
                    "config": {
                        "url": target_url,
                        "content_type": "json",
                        "secret": webhook_secret,
                    }
                }
            )
    except httpx.HTTPError as e:
        logger.error(f"GitHub webhook registration network error for {repo_full_name}: {e}")
        raise HTTPException(status_code=502, detail="Couldn't reach GitHub. Please try again shortly.")

    if res.status_code in (200, 201):
        logger.info(f"Auto-registered GitHub webhook for {repo_full_name} (org {org_id})")
        return res.json()

    already_exists = res.status_code == 422 and "already exists" in res.text.lower()
    if not already_exists:
        logger.error(f"Failed to auto-register webhook for {repo_full_name}: {res.text}")
        return None

    try:
        async with httpx.AsyncClient(timeout=20) as client2:
            list_res = await client2.get(
                f"https://api.github.com/repos/{repo_full_name}/hooks",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            )
    except httpx.HTTPError as e:
        logger.error(f"GitHub webhook list network error for {repo_full_name}: {e}")
        raise HTTPException(status_code=502, detail="Couldn't reach GitHub. Please try again shortly.")

    if list_res.status_code == 200:
        for hook in list_res.json():
            if hook.get("config", {}).get("url") == target_url:
                logger.info(f"Webhook already registered for {repo_full_name} (org {org_id}) - reusing existing hook {hook.get('id')}")
                return hook

    logger.info(f"Webhook already registered for {repo_full_name} (org {org_id}) - treating as connected")
    return {"id": None, "already_existed": True}
