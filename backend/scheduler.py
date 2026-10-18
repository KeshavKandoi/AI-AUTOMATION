import httpx
import re
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, Depends
from auth.dependencies import get_current_user

from config import settings, supabase_admin, logger, get_valid_access_token
from commit_scheduler.scheduler_jobs import run_due_commit_jobs
from email_scheduler.scheduler_jobs import run_due_email_jobs
from missed_event_recovery.scheduler_jobs import run_missed_event_recovery
from job_hunter.scheduler_jobs import run_search_for_all_orgs_background, run_due_reminders, run_stale_job_cleanup
from job_hunter import repository as job_hunter_repository
from workflow_engine import sweep_expired_workflows
from orchestrator import coo_graph

router = APIRouter()
scheduler = AsyncIOScheduler()

def scheduler_target() -> tuple[str, str] | None:
    org_id = settings.SCHEDULER_ORG_ID.strip()
    repo = settings.SCHEDULER_REPOSITORY.strip()
    if not org_id or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or (settings.ENVIRONMENT == "production" and (not settings.SCHEDULER_ENABLE_PRODUCTION or org_id == settings.TEST_ORG_ID)):
        logger.warning("Dedicated scheduler target is not configured; legacy scheduler jobs are disabled")
        return None
    return org_id, repo


def _get_org_integration_token(organization_id: str, provider: str):
    integration_res = supabase_admin.table("integrations") \
        .select("id").eq("organization_id", organization_id) \
        .eq("provider", provider).eq("connected", True) \
        .order("created_at", desc=True).execute()
    if not integration_res.data:
        logger.info(f"No connected '{provider}' integration for org {organization_id} — skipping in scheduled run")
        return None
    integration_id = integration_res.data[0]["id"]
    try:
        return get_valid_access_token(integration_id)
    except ValueError as e:
        logger.error(f"Could not get valid '{provider}' token for org {organization_id}: {e}")
        return None


async def scheduled_orchestrator_run():
    target = scheduler_target()
    if not target:
        return
    org_id, _ = target
    github_token = _get_org_integration_token(org_id, "github")
    if not github_token:
        return

    initial_state = {
        "github_token": github_token,
        "org_id": org_id,
        "issues_data": [],
        "tasks": [],
        "report": ""
    }
    final_state = await coo_graph.ainvoke(initial_state)
    print(f"Scheduled run complete: {final_state['report']}")


async def keep_alive_ping():
    if not settings.SCHEDULER_SELF_URL:
        return
    if settings.ENVIRONMENT == "production" and not settings.SCHEDULER_SELF_URL.startswith("https://"):
        logger.error("Production scheduler self URL must use HTTPS")
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(settings.SCHEDULER_SELF_URL)
        logger.info(f"Keep-alive ping -> {res.status_code}")
    except Exception as e:
        logger.error(f"Keep-alive ping failed: {e}")


def start_scheduler():
    try:
        interrupted_runs = job_hunter_repository.fail_interrupted_search_runs()
        if interrupted_runs:
            logger.warning(f"Marked {interrupted_runs} interrupted Job Hunter run(s) failed after backend restart")
    except Exception:
        logger.exception("Could not reconcile interrupted Job Hunter runs during startup")

    scheduler.add_job(scheduled_orchestrator_run, "interval", hours=1, id="orchestrator_job")
    scheduler.add_job(check_and_commit_job, "cron", hour=23, minute=0, timezone="Asia/Kolkata", id="check_and_commit_job")
    scheduler.add_job(run_due_commit_jobs, "interval", minutes=1, id="commit_scheduler_job")
    scheduler.add_job(run_due_email_jobs, "interval", minutes=1, id="email_scheduler_job")
    scheduler.add_job(keep_alive_ping, "interval", minutes=10, id="keep_alive_job")
    scheduler.add_job(run_missed_event_recovery, "interval", minutes=15, id="missed_event_recovery_job")
    scheduler.add_job(sweep_expired_workflows, "interval", minutes=1, id="workflow_expiry_sweep_job")
    scheduler.add_job(
        run_search_for_all_orgs_background,
        "interval",
        hours=24,
        id="job_hunter_search_job",
        next_run_time=datetime.now(timezone.utc),
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    scheduler.add_job(run_due_reminders, "interval", minutes=15, id="job_hunter_reminders_job")
    # Purge listings older than five days on the discovery cadence; only
    # organizations with a recent successful sweep are eligible.
    scheduler.add_job(run_stale_job_cleanup, "interval", hours=6, id="job_hunter_stale_cleanup_job")
    scheduler.start()
    scheduler.pause_job("orchestrator_job")
    print("Scheduler started — orchestrator PAUSED, check_and_commit_job + commit_scheduler_job ACTIVE")


@router.get("/scheduler/status")
def scheduler_status(user: dict = Depends(get_current_user)):
    jobs = scheduler.get_jobs()
    return {
        "running": scheduler.running,
        "jobs": [{"id": j.id, "next_run": str(j.next_run_time)} for j in jobs]
    }



import base64
from datetime import date

async def has_committed_today() -> bool:
    target = scheduler_target()
    if not target:
        return False
    org_id, repo = target
    token = _get_org_integration_token(org_id, "github")
    if not token:
        return False
    today = date.today().isoformat()
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://api.github.com/repos/{repo}/commits",
            headers={"Authorization": f"Bearer {token}"},
            params={"since": f"{today}T00:00:00Z"}
        )
    if res.status_code != 200:
        raise RuntimeError(f"Could not verify repository commits (HTTP {res.status_code})")
    commits = res.json()
    return len(commits) > 0


async def check_and_commit_job():
    target = scheduler_target()
    if not target:
        return
    org_id, repo = target
    token = _get_org_integration_token(org_id, "github")
    if not token:
        return
    today = date.today().isoformat()
    print(f"Running 11pm check-and-commit job for {today}")

    if await has_committed_today():
        print("Real commit already found today — skipping auto-commit")
        return

    result = supabase_admin.table("scheduled_commits") \
        .select("*") \
        .eq("organization_id", org_id) \
        .eq("target_date", today) \
        .eq("status", "pending") \
        .execute()

    if not result.data:
        print("No pending scheduled_commits entry for today — nothing to do")
        return

    entry = result.data[0]
    folder_path = entry["folder_path"].strip("/")
    file_name = entry.get("file_name") or f"{today}.txt"
    content = entry.get("content") or f"Auto-commit placeholder — {today}"
    branch = entry.get("branch_target") or "main"
    full_path = f"{folder_path}/{file_name}"

    encoded_content = base64.b64encode(content.encode()).decode()

    async with httpx.AsyncClient() as client:
        get_res = await client.get(
            f"https://api.github.com/repos/{repo}/contents/{full_path}",
            headers={"Authorization": f"Bearer {token}"},
            params={"ref": branch}
        )
        sha = get_res.json().get("sha") if get_res.status_code == 200 else None

        payload = {
            "message": f"scheduled commit: {today}",
            "content": encoded_content,
            "branch": branch
        }
        if sha:
            payload["sha"] = sha

        put_res = await client.put(
            f"https://api.github.com/repos/{repo}/contents/{full_path}",
            headers={"Authorization": f"Bearer {token}"},
            json=payload
        )

    if put_res.status_code not in (200, 201):
        print(f"Scheduled commit failed with status {put_res.status_code}")
        return

    supabase_admin.table("scheduled_commits") \
        .update({"status": "committed"}) \
        .eq("id", entry["id"]) \
        .execute()

    print(f"Scheduled commit succeeded for {today}: {full_path} on {branch}")
