import json
import httpx
from typing import TypedDict
from fastapi import APIRouter
from langgraph.graph import StateGraph, END

from config import settings, supabase_admin, gemini_client

router = APIRouter()


def get_memory_context(org_id: str) -> str:
    result = supabase_admin.table("memory").select("*").eq("organization_id", org_id).execute()
    memories = result.data
    if not memories:
        return "No prior context stored."
    return "\n".join([f"- [{m['category']}] {m['content']}" for m in memories])


class COOState(TypedDict):
    access_token: str
    org_id: str
    issues_data: list
    tasks: list
    report: str


async def node_fetch_issues(state: COOState) -> COOState:
    access_token = state["access_token"]
    async with httpx.AsyncClient() as client:
        repos_res = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    repos = repos_res.json()
    repos_with_issues = [r for r in repos if r.get("open_issues_count", 0) > 0]

    issues_data = []
    async with httpx.AsyncClient() as client:
        for r in repos_with_issues:
            issues_res = await client.get(
                f"https://api.github.com/repos/{r['full_name']}/issues",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"state": "open"}
            )
            issues = issues_res.json()
            if isinstance(issues, list):
                for issue in issues:
                    issues_data.append({
                        "repo": r["name"],
                        "title": issue.get("title"),
                        "comments": issue.get("comments"),
                    })

    state["issues_data"] = issues_data
    return state


async def node_create_tasks(state: COOState) -> COOState:
    issues_data = state["issues_data"]

    if not issues_data:
        state["tasks"] = []
        return state

    memory_context = get_memory_context(state["org_id"])

    prompt = f"""You are a Planner AI. Here is prior context about this company/project:
{memory_context}

Given this GitHub issues data: {issues_data}

Return ONLY a valid JSON array (no markdown) of up to 5 tasks, each with:
- title (string, short)
- description (string, 1 sentence)
- priority ("high", "medium", or "low")
Use the prior context to inform priority — e.g. if a repo/area was flagged important before, weigh it higher."""

    response = gemini_client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()

    try:
        tasks = json.loads(raw_text)
    except json.JSONDecodeError:
        tasks = []

    created = []
    for t in tasks:
        result = supabase_admin.table("tasks").insert({
            "organization_id": state["org_id"],
            "title": t.get("title"),
            "description": t.get("description"),
            "priority": t.get("priority", "medium"),
            "source": "langgraph_orchestrator"
        }).execute()
        created.append(result.data[0])

    state["tasks"] = created
    return state


async def node_notify_discord(state: COOState) -> COOState:
    tasks = state["tasks"]

    if not tasks:
        report = "**🤖 AI COO Run Complete**\n\nNo open issues found. Nothing to report."
    else:
        report = "**🤖 AI COO Run Complete**\n\n**New Tasks Created:**\n"
        for t in tasks:
            report += f"- [{t.get('priority', 'medium').upper()}] {t.get('title')}\n"

    async with httpx.AsyncClient() as client:
        await client.post(settings.DISCORD_WEBHOOK_URL, json={"content": report})

    state["report"] = report
    return state


workflow = StateGraph(COOState)
workflow.add_node("fetch_issues", node_fetch_issues)
workflow.add_node("create_tasks", node_create_tasks)
workflow.add_node("notify_discord", node_notify_discord)

workflow.set_entry_point("fetch_issues")
workflow.add_edge("fetch_issues", "create_tasks")
workflow.add_edge("create_tasks", "notify_discord")
workflow.add_edge("notify_discord", END)

coo_graph = workflow.compile()


@router.post("/orchestrator/run")
async def run_orchestrator(access_token: str, org_id: str):
    initial_state = {
        "access_token": access_token,
        "org_id": org_id,
        "issues_data": [],
        "tasks": [],
        "report": ""
    }

    final_state = await coo_graph.ainvoke(initial_state)

    return {
        "issues_found": len(final_state["issues_data"]),
        "tasks_created": len(final_state["tasks"]),
        "report": final_state["report"]
    }
