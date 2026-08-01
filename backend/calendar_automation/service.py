from datetime import date, datetime, time as dtime
import httpx
from fastapi import HTTPException

from calendar_automation import repository
from calendar_automation.schemas import LunchBlockSettingsUpsert
from config import supabase_admin, decrypt_token, get_valid_access_token


def _get_calendar_token_for_org(organization_id: str) -> str:
    integration_res = supabase_admin.table("integrations") \
        .select("id") \
        .eq("organization_id", organization_id) \
        .eq("provider", "calendar") \
        .eq("connected", True) \
        .order("created_at", desc=True) \
        .execute()

    if not integration_res.data:
        raise HTTPException(status_code=400, detail="No connected Calendar integration for this organization")

    last_error = None
    for row in integration_res.data:
        try:
            return get_valid_access_token(row["id"])
        except Exception as e:
            last_error = e
            continue

    raise HTTPException(status_code=400, detail=f"No usable Calendar token found for this organization: {last_error}")


def upsert_settings(payload: LunchBlockSettingsUpsert) -> dict:
    return repository.upsert_settings(payload.model_dump(mode="json"))


def get_settings_or_404(organization_id: str) -> dict:
    settings = repository.get_settings(organization_id)
    if not settings:
        raise HTTPException(status_code=404, detail="No lunch block settings found for this organization")
    return settings


def get_settings_with_runs(organization_id: str) -> dict:
    settings = get_settings_or_404(organization_id)
    runs = repository.get_runs(organization_id)
    return {**settings, "runs": runs}


async def check_and_block_lunch(settings: dict) -> dict:
    org_id = settings["organization_id"]
    today = date.today()
    today_str = today.isoformat()

    if settings["weekdays_only"] and today.weekday() >= 5:
        return repository.create_run({
            "organization_id": org_id, "run_date": today_str, "status": "skipped_weekend"
        })

    if repository.has_run_for_date(org_id, today_str):
        return repository.create_run({
            "organization_id": org_id, "run_date": today_str, "status": "skipped_already_ran"
        })

    try:
        access_token = _get_calendar_token_for_org(org_id)

        from zoneinfo import ZoneInfo
        ist = ZoneInfo("Asia/Kolkata")
        start_dt = datetime.combine(today, dtime.fromisoformat(settings["start_time"]), tzinfo=ist)
        end_dt = datetime.combine(today, dtime.fromisoformat(settings["end_time"]), tzinfo=ist)

        async with httpx.AsyncClient() as client:
            events_res = await client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "timeMin": start_dt.isoformat() + "Z",
                    "timeMax": end_dt.isoformat() + "Z",
                    "singleEvents": "true",
                }
            )
        events = events_res.json().get("items", [])

        if events:
            return repository.create_run({
                "organization_id": org_id, "run_date": today_str, "status": "already_exists"
            })

        async with httpx.AsyncClient() as client:
            create_res = await client.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "summary": settings["title"],
                    "start": {"dateTime": start_dt.isoformat()},
                    "end": {"dateTime": end_dt.isoformat()},
                }
            )

        if create_res.status_code != 200:
            return repository.create_run({
                "organization_id": org_id, "run_date": today_str, "status": "failed",
                "error_message": f"Calendar API error {create_res.status_code}: {create_res.text}"
            })

        event = create_res.json()
        return repository.create_run({
            "organization_id": org_id, "run_date": today_str, "status": "created",
            "event_id": event.get("id")
        })

    except Exception as e:
        return repository.create_run({
            "organization_id": org_id, "run_date": today_str, "status": "failed",
            "error_message": str(e)
        })
