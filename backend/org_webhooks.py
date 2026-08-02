import secrets
import httpx
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

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api.github.com/repos/{repo_full_name}/hooks",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            json={
                "name": "web",
                "active": True,
                "events": ["push", "issues", "pull_request"],
                "config": {
                    "url": f"{base_url}/webhooks/github",
                    "content_type": "json",
                    "secret": webhook_secret,
                }
            }
        )

    if res.status_code not in (200, 201):
        logger.error(f"Failed to auto-register webhook for {repo_full_name}: {res.text}")
        return None

    logger.info(f"Auto-registered GitHub webhook for {repo_full_name} (org {org_id})")
    return res.json()
