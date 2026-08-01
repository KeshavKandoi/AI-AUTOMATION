from fastapi import APIRouter
from calendar_automation import service
from calendar_automation.schemas import LunchBlockSettingsUpsert

router = APIRouter(prefix="/lunch-block", tags=["calendar-automation"])

@router.post("/settings")
def upsert_settings(payload: LunchBlockSettingsUpsert):
    settings = service.upsert_settings(payload)
    return {"status": "saved", "settings": settings}

@router.get("/settings")
def get_settings(org_id: str):
    return service.get_settings_with_runs(org_id)

@router.post("/run-now")
async def run_now(org_id: str):
    settings = service.get_settings_or_404(org_id)
    run = await service.check_and_block_lunch(settings)
    return {"status": "triggered", "run": run}
