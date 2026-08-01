import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter

from config import settings
from orchestrator import coo_graph

router = APIRouter()
scheduler = AsyncIOScheduler()

TEST_GITHUB_TOKEN = settings.TEST_GITHUB_ACCESS_TOKEN
TEST_ORG_ID = settings.TEST_ORG_ID


async def scheduled_orchestrator_run():
    print("Running scheduled AI COO orchestrator...")
    initial_state = {
        "github_token": TEST_GITHUB_TOKEN,
        "gmail_token": None,
        "calendar_token": None,
        "org_id": TEST_ORG_ID,
        "issues_data": [],
        "emails_data": [],
        "events_data": [],
        "tasks": [],
        "report": ""
    }
    final_state = await coo_graph.ainvoke(initial_state)
    print(f"Scheduled run complete: {final_state['report']}")


def start_scheduler():
    scheduler.add_job(scheduled_orchestrator_run, "interval", hours=1, id="orchestrator_job")
    scheduler.add_job(check_and_commit_job, "cron", hour=23, minute=0, timezone="Asia/Kolkata", id="check_and_commit_job")
    scheduler.start()
    scheduler.pause_job("orchestrator_job")
    print("Scheduler started — orchestrator PAUSED, check_and_commit_job ACTIVE at 11pm IST")


@router.get("/scheduler/status")
def scheduler_status():
    jobs = scheduler.get_jobs()
    return {
        "running": scheduler.running,
        "jobs": [{"id": j.id, "next_run": str(j.next_run_time)} for j in jobs]
    }


@router.post("/scheduler/pause")
def pause_scheduler():
    scheduler.pause_job("orchestrator_job")
    return {"status": "paused"}


@router.post("/scheduler/resume")
def resume_scheduler():
    scheduler.resume_job("orchestrator_job")
    return {"status": "resumed"}

import base64
from datetime import date

REPO = "KeshavKandoi/Smart-Inventory-Management-System"
GITHUB_TOKEN = settings.TEST_GITHUB_ACCESS_TOKEN


async def has_committed_today() -> bool:
    today = date.today().isoformat()
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://api.github.com/repos/{REPO}/commits",
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
            params={"since": f"{today}T00:00:00Z"}
        )
    if res.status_code != 200:
        return False
    commits = res.json()
    return len(commits) > 0


async def check_and_commit_job():
    today = date.today().isoformat()
    print(f"Running 11pm check-and-commit job for {today}")

    if await has_committed_today():
        print("Real commit already found today — skipping auto-commit")
        return

    result = supabase_admin.table("scheduled_commits") \
        .select("*") \
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
            f"https://api.github.com/repos/{REPO}/contents/{full_path}",
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
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
            f"https://api.github.com/repos/{REPO}/contents/{full_path}",
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
            json=payload
        )

    if put_res.status_code not in (200, 201):
        print(f"Scheduled commit failed: {put_res.text}")
        return

    supabase_admin.table("scheduled_commits") \
        .update({"status": "committed"}) \
        .eq("id", entry["id"]) \
        .execute()

    print(f"Scheduled commit succeeded for {today}: {full_path} on {branch}")
