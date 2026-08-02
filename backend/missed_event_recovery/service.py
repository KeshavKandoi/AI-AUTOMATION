from datetime import datetime, timezone, timedelta
import httpx
from config import supabase_admin, logger, decrypt_token


def _get_org_github_token(organization_id: str) -> str | None:
    integration_res = supabase_admin.table("integrations") \
        .select("id").eq("organization_id", organization_id) \
        .eq("provider", "github").eq("connected", True) \
        .order("created_at", desc=True).execute()
    if not integration_res.data:
        return None
    integration_ids = [row["id"] for row in integration_res.data]

    token_res = supabase_admin.table("oauth_tokens") \
        .select("access_token").in_("integration_id", integration_ids) \
        .order("created_at", desc=True).execute()
    if not token_res.data:
        return None
    return decrypt_token(token_res.data[0]["access_token"])


def _get_last_polled_at(organization_id: str) -> str:
    result = supabase_admin.table("github_poll_state") \
        .select("last_polled_at").eq("organization_id", organization_id).execute()
    if result.data:
        return result.data[0]["last_polled_at"]
    default = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    supabase_admin.table("github_poll_state").upsert({
        "organization_id": organization_id, "last_polled_at": default
    }).execute()
    return default


def _update_last_polled_at(organization_id: str):
    supabase_admin.table("github_poll_state").upsert({
        "organization_id": organization_id,
        "last_polled_at": datetime.now(timezone.utc).isoformat()
    }).execute()


def is_event_processed(organization_id: str, event_key: str) -> bool:
    result = supabase_admin.table("github_processed_events") \
        .select("id").eq("organization_id", organization_id).eq("event_key", event_key).execute()
    return len(result.data) > 0


def mark_event_processed(organization_id: str, event_key: str, source: str):
    try:
        supabase_admin.table("github_processed_events").insert({
            "organization_id": organization_id, "event_key": event_key, "source": source
        }).execute()
    except Exception:
        pass  # unique constraint race — already marked, fine


async def find_missed_issue_events(organization_id: str, repo_full_name: str, access_token: str) -> list[dict]:
    since = _get_last_polled_at(organization_id)

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/issues",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"state": "all", "since": since, "sort": "updated"}
        )

    if res.status_code != 200:
        logger.error(f"Missed-event poll failed for {repo_full_name}: {res.text}")
        return []

    issues = res.json()
    missed = []
    for issue in issues:
        event_key = f"issue-{issue['id']}-{issue['updated_at']}"
        if not is_event_processed(organization_id, event_key):
            missed.append({"issue": issue, "event_key": event_key})

    return missed
