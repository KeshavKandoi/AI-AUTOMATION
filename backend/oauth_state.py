import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from config import supabase_admin

OAUTH_STATE_TTL_MINUTES = 10


def _issue_oauth_state(org_id: str, provider: str) -> str:
    state = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=OAUTH_STATE_TTL_MINUTES)).isoformat()
    supabase_admin.table("oauth_states").insert({
        "state": state,
        "organization_id": org_id,
        "provider": provider,
        "expires_at": expires_at,
    }).execute()
    return state


def _consume_oauth_state(state: str, provider: str) -> str:
    """Validates and single-use-consumes an OAuth state token. Returns the
    organization_id it was issued for. Raises HTTPException(400) on any
    invalid, expired, wrong-provider, or already-used state -- the error
    message is intentionally generic so it does not reveal which specific
    check failed (avoids leaking timing/enumeration signal to an attacker
    probing the callback endpoint)."""
    row_res = supabase_admin.table("oauth_states").select("*").eq("state", state).execute()
    if not row_res.data:
        raise HTTPException(status_code=400, detail="Invalid or expired authentication request")
    row = row_res.data[0]

    if row["provider"] != provider:
        raise HTTPException(status_code=400, detail="Invalid or expired authentication request")
    if row.get("consumed_at") is not None:
        raise HTTPException(status_code=400, detail="Invalid or expired authentication request")
    expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) >= expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired authentication request")

    # Atomically claim this state: only succeeds if consumed_at is still
    # null at the moment of the update, closing the replay race window
    # between the check above and this write.
    claim_res = supabase_admin.table("oauth_states") \
        .update({"consumed_at": datetime.now(timezone.utc).isoformat()}) \
        .eq("id", row["id"]) \
        .is_("consumed_at", "null") \
        .execute()
    if not claim_res.data:
        raise HTTPException(status_code=400, detail="Invalid or expired authentication request")

    return row["organization_id"]

