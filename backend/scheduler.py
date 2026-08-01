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
    scheduler.start()
    scheduler.pause_job("orchestrator_job")
    print("Scheduler started (PAUSED by default) — call /scheduler/resume to enable auto-runs")


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
