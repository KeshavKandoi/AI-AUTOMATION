"""
Business logic for commit scheduling: validation, org access control,
and orchestration between repository.py (DB) and git_ops.py (Git provider).
"""
from datetime import date
from typing import Optional
from fastapi import HTTPException

from commit_scheduler import repository, git_ops
from commit_scheduler.schemas import CommitJobCreate, CommitJobUpdate
from config import supabase_admin, decrypt_token


def _get_github_token_for_org(organization_id: str) -> str:
    """Looks up the org's connected GitHub integration and returns a decrypted access token."""
    integration_res = supabase_admin.table("integrations") \
        .select("id") \
        .eq("organization_id", organization_id) \
        .eq("provider", "github") \
        .eq("connected", True) \
        .execute()

    if not integration_res.data:
        raise HTTPException(status_code=400, detail="No connected GitHub integration for this organization")

    integration_id = integration_res.data[0]["id"]

    token_res = supabase_admin.table("oauth_tokens") \
        .select("access_token") \
        .eq("integration_id", integration_id) \
        .execute()

    if not token_res.data:
        raise HTTPException(status_code=400, detail="No GitHub token found for this integration")

    return decrypt_token(token_res.data[0]["access_token"])


async def validate_repo_and_branch(organization_id: str, repo_full_name: str, branch: str, provider_name: str = "github"):
    access_token = _get_github_token_for_org(organization_id)
    provider = git_ops.get_provider(provider_name)

    repos = await provider.list_repos(access_token)
    repo_names = {r["full_name"] for r in repos}
    if repo_full_name not in repo_names:
        raise HTTPException(status_code=400, detail=f"Repository '{repo_full_name}' not found or not accessible")

    branches = await provider.list_branches(access_token, repo_full_name)
    branch_names = {b["name"] for b in branches}
    if branch not in branch_names:
        raise HTTPException(status_code=400, detail=f"Branch '{branch}' not found in '{repo_full_name}'")


async def create_scheduled_job(payload: CommitJobCreate) -> dict:
    await validate_repo_and_branch(payload.organization_id, payload.repo_full_name, payload.branch, payload.provider)

    duplicate = repository.find_duplicate_job(
        payload.organization_id, payload.repo_full_name, payload.branch,
        payload.folder_path, payload.file_name
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail=f"An active schedule already targets {payload.folder_path}/{payload.file_name} on {payload.branch}"
        )

    job_data = payload.model_dump(mode="json")
    return repository.create_job(job_data)


def get_job_or_404(job_id: str, organization_id: Optional[str] = None) -> dict:
    job = repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled commit job not found")
    if organization_id and job["organization_id"] != organization_id:
        raise HTTPException(status_code=403, detail="You do not have access to this job")
    return job


def list_jobs_for_org(organization_id: str) -> list[dict]:
    return repository.list_jobs(organization_id)


def update_job(job_id: str, organization_id: str, payload: CommitJobUpdate) -> dict:
    get_job_or_404(job_id, organization_id)
    updates = payload.model_dump(mode="json", exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")
    updates["updated_at"] = "now()"
    return repository.update_job(job_id, updates)


def delete_job(job_id: str, organization_id: str) -> None:
    get_job_or_404(job_id, organization_id)
    repository.delete_job(job_id)


def get_job_with_runs(job_id: str, organization_id: str) -> dict:
    job = get_job_or_404(job_id, organization_id)
    runs = repository.get_runs_for_job(job_id)
    return {**job, "runs": runs}


async def execute_job(job: dict) -> dict:
    """Performs the actual Git commit for a due job. Returns the run record."""
    run_date = date.today().isoformat()

    if repository.has_run_for_date(job["id"], run_date):
        run = repository.create_run({
            "job_id": job["id"], "run_date": run_date, "status": "skipped",
            "error_message": "Already ran for this date"
        })
        return run

    try:
        access_token = _get_github_token_for_org(job["organization_id"])
        provider = git_ops.get_provider(job["provider"])
        path = f"{job['folder_path']}/{job['file_name']}"

        existing = await provider.get_file(access_token, job["repo_full_name"], path, job["branch"])
        sha = existing["sha"] if existing else None

        content = job.get("file_content") or f"Auto-commit — {run_date}"

        result = await provider.commit_file(
            access_token, job["repo_full_name"], path, content,
            job["branch"], job["commit_message"], sha
        )

        return repository.create_run({
            "job_id": job["id"], "run_date": run_date, "status": "success",
            "commit_sha": result["sha"], "commit_url": result["commit_url"]
        })

    except Exception as e:
        return repository.create_run({
            "job_id": job["id"], "run_date": run_date, "status": "failed",
            "error_message": str(e)
        })
