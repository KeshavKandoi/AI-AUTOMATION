from fastapi import APIRouter, Depends
from email_scheduler import service
from email_scheduler.schemas import EmailJobCreate, EmailJobUpdate
from auth.dependencies import get_current_org_id

router = APIRouter(prefix="/email-jobs", tags=["email-scheduler"])

@router.post("")
async def create_job(payload: EmailJobCreate, org_id: str = Depends(get_current_org_id)):
    job = await service.create_scheduled_job(payload, organization_id=org_id)
    return {"status": "scheduled", "job": job}

@router.get("")
def list_jobs(org_id: str = Depends(get_current_org_id)):
    return service.list_jobs_for_org(org_id)

@router.get("/{job_id}")
def get_job(job_id: str, org_id: str = Depends(get_current_org_id)):
    return service.get_job_with_runs(job_id, org_id)

@router.patch("/{job_id}")
def update_job(job_id: str, payload: EmailJobUpdate, org_id: str = Depends(get_current_org_id)):
    job = service.update_job(job_id, org_id, payload)
    return {"status": "updated", "job": job}

@router.delete("/{job_id}")
def delete_job(job_id: str, org_id: str = Depends(get_current_org_id)):
    service.delete_job(job_id, org_id)
    return {"status": "deleted", "job_id": job_id}

@router.post("/{job_id}/run-now")
async def run_job_now(job_id: str, org_id: str = Depends(get_current_org_id)):
    job = service.get_job_or_404(job_id, org_id)
    run = await service.execute_job(job)
    return {"status": "triggered", "run": run}
