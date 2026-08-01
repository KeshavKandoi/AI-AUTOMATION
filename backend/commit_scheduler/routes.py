from fastapi import APIRouter, HTTPException
from commit_scheduler import service, git_ops
from commit_scheduler.schemas import CommitJobCreate, CommitJobUpdate, CommitJobOut, CommitJobRunOut, CommitJobFile
from commit_scheduler import repository

router = APIRouter(prefix="/commit-jobs", tags=["commit-scheduler"])


@router.post("")
async def create_job(payload: CommitJobCreate):
    job = await service.create_scheduled_job(payload)
    return {"status": "scheduled", "job": job}


@router.get("")
def list_jobs(org_id: str):
    return service.list_jobs_for_org(org_id)


@router.get("/{job_id}")
def get_job(job_id: str, org_id: str):
    return service.get_job_with_runs(job_id, org_id)


@router.patch("/{job_id}")
def update_job(job_id: str, org_id: str, payload: CommitJobUpdate):
    job = service.update_job(job_id, org_id, payload)
    return {"status": "updated", "job": job}


@router.delete("/{job_id}")
def delete_job(job_id: str, org_id: str):
    service.delete_job(job_id, org_id)
    return {"status": "deleted", "job_id": job_id}


@router.post("/{job_id}/run-now")
async def run_job_now(job_id: str, org_id: str):
    job = service.get_job_or_404(job_id, org_id)
    run = await service.execute_job(job)
    return {"status": "triggered", "run": run}


@router.get("/meta/repos")
async def list_repos_for_org(org_id: str, provider: str = "github"):
    access_token = service._get_github_token_for_org(org_id)
    vcs = git_ops.get_provider(provider)
    return await vcs.list_repos(access_token)


@router.get("/meta/branches")
async def list_branches_for_repo(org_id: str, repo_full_name: str, provider: str = "github"):
    access_token = service._get_github_token_for_org(org_id)
    vcs = git_ops.get_provider(provider)
    return await vcs.list_branches(access_token, repo_full_name)


@router.post("/{job_id}/files")
def add_files(job_id: str, org_id: str, files: list[CommitJobFile]):
    service.get_job_or_404(job_id, org_id)
    files_data = [f.model_dump(mode="json") for f in files]
    created = repository.create_job_files(job_id, files_data)
    return {"status": "added", "files": created}


@router.get("/{job_id}/files")
def list_files(job_id: str, org_id: str):
    service.get_job_or_404(job_id, org_id)
    return repository.get_files_for_job(job_id)


@router.delete("/{job_id}/files/{file_id}")
def delete_file(job_id: str, file_id: str, org_id: str):
    service.get_job_or_404(job_id, org_id)
    repository.delete_job_file(file_id)
    return {"status": "deleted", "file_id": file_id}
