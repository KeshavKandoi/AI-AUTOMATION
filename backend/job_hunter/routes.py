from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from job_hunter import service
from job_hunter.schemas import (
    JobHunterPreferencesCreate, JobHunterPreferencesUpdate,
    ApplicationCreate, ApplicationUpdate,
    NoteCreate, ReminderCreate,
)

router = APIRouter(prefix="/job-hunter", tags=["job-hunter"])


# ---------------------------------------------------------------------------
# Preferences / onboarding
# ---------------------------------------------------------------------------

@router.get("/preferences")
def get_preferences(org_id: str):
    prefs = service.get_preferences(org_id)
    if not prefs:
        return {"onboarding_completed": False, "preferences": None}
    return {"onboarding_completed": True, "preferences": prefs}


@router.post("/preferences")
def save_preferences(org_id: str, payload: JobHunterPreferencesCreate):
    saved = service.save_preferences(org_id, payload)
    return {"status": "saved", "preferences": saved}


@router.patch("/preferences")
def update_preferences(org_id: str, payload: JobHunterPreferencesUpdate):
    saved = service.update_preferences(org_id, payload)
    return {"status": "updated", "preferences": saved}


# ---------------------------------------------------------------------------
# Jobs (discovered listings)
# ---------------------------------------------------------------------------

@router.get("/jobs")
def list_jobs(
    org_id: str,
    limit: int = 50,
    offset: int = 0,
    employment_type: str | None = None,
    work_mode: str | None = None,
    search: str | None = None,
):
    return service.list_jobs(
        org_id, limit=limit, offset=offset,
        employment_type=employment_type, work_mode=work_mode, search=search,
    )


@router.get("/jobs/{job_id}")
def get_job(job_id: str, org_id: str):
    return service.get_job_with_sources(job_id, org_id)


# ---------------------------------------------------------------------------
# Applications (tracking)
# ---------------------------------------------------------------------------

@router.get("/applications")
def list_applications(org_id: str, status: str | None = None):
    return service.list_applications(org_id, status=status)


@router.post("/applications")
def create_application(org_id: str, payload: ApplicationCreate):
    application = service.get_or_create_application(org_id, payload.job_id, initial_status=payload.status)
    return {"status": "created", "application": application}


@router.get("/applications/{application_id}")
def get_application(application_id: str, org_id: str):
    return service.get_application_detail(org_id, application_id)


@router.patch("/applications/{application_id}")
def update_application(application_id: str, org_id: str, payload: ApplicationUpdate):
    if payload.status is None:
        raise HTTPException(status_code=400, detail="status is required")
    updated = service.update_application_status(org_id, application_id, payload.status)
    return {"status": "updated", "application": updated}


@router.post("/applications/{application_id}/notes")
def add_note(application_id: str, org_id: str, payload: NoteCreate):
    note = service.add_note(org_id, application_id, payload.content)
    return {"status": "added", "note": note}


@router.post("/applications/{application_id}/attachments")
async def add_attachment(
    application_id: str,
    org_id: str,
    file_type: str = Form(...),
    file: UploadFile = File(...),
):
    file_bytes = await file.read()
    attachment = service.add_attachment(
        org_id, application_id,
        file_name=file.filename or "upload",
        file_bytes=file_bytes,
        content_type=file.content_type or "application/octet-stream",
        file_type=file_type,
    )
    return {"status": "added", "attachment": attachment}


@router.get("/applications/{application_id}/attachments/{attachment_id}/download")
def download_attachment(application_id: str, attachment_id: str, org_id: str):
    url = service.get_attachment_download_url(org_id, application_id, attachment_id)
    return {"download_url": url}


@router.delete("/applications/{application_id}/attachments/{attachment_id}")
def delete_attachment(application_id: str, attachment_id: str, org_id: str):
    service.delete_attachment(org_id, application_id, attachment_id)
    return {"status": "deleted", "attachment_id": attachment_id}


@router.post("/applications/{application_id}/reminders")
def create_reminder(application_id: str, org_id: str, payload: ReminderCreate):
    reminder = service.create_reminder(
        org_id, application_id,
        remind_at=payload.remind_at.isoformat(), note=payload.note,
    )
    return {"status": "created", "reminder": reminder}


# ---------------------------------------------------------------------------
# Manual trigger (mirrors commit_scheduler's /run-now pattern)
# ---------------------------------------------------------------------------

@router.post("/search/run-now")
async def run_search_now(org_id: str):
    from job_hunter.scheduler_jobs import run_search_for_org
    result = await run_search_for_org(org_id)
    return {"status": "triggered", "result": result}
