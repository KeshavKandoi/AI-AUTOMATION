from fastapi import APIRouter, Depends, HTTPException
from config import is_valid_discord_webhook, resolve_discord_webhook, supabase_admin
from auth.dependencies import get_current_org_id
from organization_settings.schemas import DiscordWebhookUpdate

router = APIRouter(prefix="/organization-settings", tags=["organization settings"])


def _discord_status(org_id: str, org_webhook: str | None):
    webhook_url, source = resolve_discord_webhook(org_id, org_webhook)
    return {
        "configured": webhook_url is not None,
        "masked_url": "Discord webhook ••••••••" if webhook_url else None,
        "source": source,
    }


@router.get("/discord-webhook")
def get_discord_webhook_settings(org_id: str = Depends(get_current_org_id)):
    result = supabase_admin.table("organizations").select("discord_webhook_url").eq("id", org_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Organization settings were not found")
    webhook = result.data[0].get("discord_webhook_url")
    return _discord_status(org_id, webhook)


@router.put("/discord-webhook")
def update_discord_webhook_settings(payload: DiscordWebhookUpdate, org_id: str = Depends(get_current_org_id)):
    webhook_url = payload.webhook_url
    if webhook_url is not None and not isinstance(webhook_url, str):
        raise HTTPException(status_code=422, detail="Webhook URL must be a string or null")

    normalized = webhook_url.strip() if isinstance(webhook_url, str) else None
    if normalized == "":
        normalized = None
    if normalized is not None and (len(normalized) > 500 or not is_valid_discord_webhook(normalized)):
        raise HTTPException(status_code=422, detail="Enter a valid Discord HTTPS webhook URL")

    result = supabase_admin.table("organizations").update({"discord_webhook_url": normalized}).eq("id", org_id).select("id").execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Organization settings were not found")
    return _discord_status(org_id, normalized)
