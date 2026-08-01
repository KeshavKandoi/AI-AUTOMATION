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
    """Looks up the org's connected GitHub integration and returns a decrypted access token.
    Handles multiple integration rows (from repeated OAuth connects) by finding
    the most recent one that actually has a token attached."""
    integration_res = supabase_admin.table("integrations") \
        .select("id") \
        .eq("organization_id", organization_id) \
        .eq("provider", "github") \
        .eq("connected", True) \
        .order("created_at", desc=True) \
        .execute()

    if not integration_res.data:
        raise HTTPException(status_code=400, detail="No connected GitHub integration for this organization")

    integration_ids = [row["id"] for row in integration_res.data]

    token_res = supabase_admin.table("oauth_tokens") \
        .select("access_token, integration_id, created_at") \
        .in_("integration_id", integration_ids) \
        .order("created_at", desc=True) \
        .execute()

    if not token_res.data:
        raise HTTPException(status_code=400, detail="No GitHub token found for this organization")

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

    if payload.folder_path and payload.file_name:
        duplicate = repository.find_duplicate_job(
            payload.organization_id, payload.repo_full_name, payload.branch,
            payload.folder_path, payload.file_name
        )
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail=f"An active schedule already targets {payload.folder_path}/{payload.file_name} on {payload.branch}"
            )

    job_data = payload.model_dump(mode="json", exclude={"files"})
    job = repository.create_job(job_data)

    if payload.files:
        files_data = [f.model_dump(mode="json") for f in payload.files]
        repository.create_job_files(job["id"], files_data)
        job["files"] = repository.get_files_for_job(job["id"])

    return job


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


async def _has_real_commit_today(access_token: str, repo_full_name: str) -> bool:
    """Used by guard mode: checks if any commit already landed on the repo today."""
    today = date.today().isoformat()
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/commits",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"since": f"{today}T00:00:00Z"}
        )
    if res.status_code != 200:
        return False
    return len(res.json()) > 0


async def _resolve_files_for_run(job: dict, run_date: str) -> list[dict]:
    """Returns the list of {folder_path, file_name, content} to commit today.
    Falls back to the job's single folder_path/file_name/file_content if no
    commit_job_files rows exist (backward compatible with single-file jobs)."""
    files = repository.get_files_for_date(job["id"], run_date)
    if files:
        return files
    if job.get("folder_path") and job.get("file_name"):
        return [{
            "folder_path": job["folder_path"],
            "file_name": job["file_name"],
            "content": job.get("file_content")
        }]
    return []


async def execute_job(job: dict) -> dict:
    """Performs the actual Git commit(s) for a due job. Returns the run record."""
    run_date = date.today().isoformat()

    if repository.has_run_for_date(job["id"], run_date):
        return repository.create_run({
            "job_id": job["id"], "run_date": run_date, "status": "skipped",
            "error_message": "Already ran for this date"
        })

    try:
        access_token = _get_github_token_for_org(job["organization_id"])
        provider = git_ops.get_provider(job["provider"])

        if job.get("mode") == "guard":
            if await _has_real_commit_today(access_token, job["repo_full_name"]):
                return repository.create_run({
                    "job_id": job["id"], "run_date": run_date, "status": "skipped",
                    "error_message": "Real commit already found today — guard mode skipped"
                })

        files_to_commit = await _resolve_files_for_run(job, run_date)
        if not files_to_commit:
            return repository.create_run({
                "job_id": job["id"], "run_date": run_date, "status": "skipped",
                "error_message": "No files staged for this date"
            })

        target_branch = job["branch"]
        if job.get("use_pr"):
            target_branch = f"auto/{run_date}"
            await provider.create_branch(access_token, job["repo_full_name"], job["branch"], target_branch)

        last_result = None
        for f in files_to_commit:
            path = f"{f['folder_path']}/{f['file_name']}"
            existing = await provider.get_file(access_token, job["repo_full_name"], path, target_branch)
            sha = existing["sha"] if existing else None
            content = f.get("content") or f"Auto-commit — {run_date}"

            last_result = await provider.commit_file(
                access_token, job["repo_full_name"], path, content,
                target_branch, job["commit_message"], sha
            )

        if job.get("use_pr"):
            pr = await provider.create_pull_request(
                access_token, job["repo_full_name"], target_branch, job["branch"],
                title=job["commit_message"], body=f"Automated commit for {run_date}"
            )
            return repository.create_run({
                "job_id": job["id"], "run_date": run_date, "status": "success",
                "commit_sha": last_result["sha"] if last_result else None,
                "commit_url": pr.get("html_url")
            })

        return repository.create_run({
            "job_id": job["id"], "run_date": run_date, "status": "success",
            "commit_sha": last_result["sha"] if last_result else None,
            "commit_url": last_result["commit_url"] if last_result else None
        })

    except Exception as e:
        return repository.create_run({
            "job_id": job["id"], "run_date": run_date, "status": "failed",
            "error_message": str(e)
        })
