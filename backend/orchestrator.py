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
    github_token: str
    gmail_token: str
    calendar_token: str
    org_id: str
    issues_data: list
    emails_data: list
    events_data: list
    tasks: list
    report: str


async def node_fetch_issues(state: COOState) -> COOState:
    access_token = state["github_token"]
    async with httpx.AsyncClient() as client:
        repos_res = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    repos = repos_res.json()
    if not isinstance(repos, list):
        state["issues_data"] = []
        return state

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
                        "source": "github",
                        "repo": r["name"],
                        "title": issue.get("title"),
                        "comments": issue.get("comments"),
                    })

    state["issues_data"] = issues_data
    return state


async def node_fetch_emails(state: COOState) -> COOState:
    gmail_token = state.get("gmail_token")
    if not gmail_token:
        state["emails_data"] = []
        return state

    async with httpx.AsyncClient() as client:
        list_res = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {gmail_token}"},
            params={"q": "is:unread", "maxResults": 10}
        )
    messages = list_res.json().get("messages", [])

    emails = []
    async with httpx.AsyncClient() as client:
        for m in messages:
            msg_res = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}",
                headers={"Authorization": f"Bearer {gmail_token}"},
                params={"format": "metadata", "metadataHeaders": ["From", "Subject"]}
            )
            msg = msg_res.json()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            emails.append({
                "source": "gmail",
                "from": headers.get("From"),
                "subject": headers.get("Subject"),
                "snippet": msg.get("snippet")
            })

    state["emails_data"] = emails
    return state


async def node_fetch_events(state: COOState) -> COOState:
    calendar_token = state.get("calendar_token")
    if not calendar_token:
        state["events_data"] = []
        return state

    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {calendar_token}"},
            params={"maxResults": 10, "singleEvents": "true", "orderBy": "startTime"}
        )
    data = res.json()
    events = data.get("items", [])

    formatted = [
        {
            "source": "calendar",
            "summary": e.get("summary"),
            "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
        }
        for e in events
    ]
    state["events_data"] = formatted
    return state


async def node_create_tasks(state: COOState) -> COOState:
    issues_data = state.get("issues_data", [])
    emails_data = state.get("emails_data", [])
    events_data = state.get("events_data", [])

    if not issues_data and not emails_data and not events_data:
        state["tasks"] = []
        return state

    memory_context = get_memory_context(state["org_id"])

    prompt = f"""You are a Planner AI for a busy founder. Here is prior context:
{memory_context}

GitHub open issues: {issues_data}
Unread emails: {emails_data}
Upcoming calendar events: {events_data}

Return ONLY a valid JSON array (no markdown) of up to 5 tasks across ALL sources above, each with:
- title (string, short)
- description (string, 1 sentence)
- priority ("high", "medium", or "low")
- source ("github", "gmail", or "calendar")

Prioritize using prior context. Combine related items where sensible."""

    response = gemini_client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()

    try:
        tasks = json.loads(raw_text)
    except json.JSONDecodeError:
        tasks = []

    from audit import log_action

    created = []
    for t in tasks:
        result = supabase_admin.table("tasks").insert({
            "organization_id": state["org_id"],
            "title": t.get("title"),
            "description": t.get("description"),
            "priority": t.get("priority", "medium"),
            "source": f"orchestrator_{t.get('source', 'unknown')}"
        }).execute()
        created_task = result.data[0]
        created.append(created_task)
        log_action(state["org_id"], "task_created", {"task_id": created_task["id"], "title": created_task.get("title")})

    state["tasks"] = created
    return state


async def node_notify_discord(state: COOState) -> COOState:
    tasks = state.get("tasks", [])

    if not tasks:
        report = "**🤖 AI COO Run Complete**\n\nNothing found across GitHub, Gmail, or Calendar. All clear."
    else:
        report = "**🤖 AI COO Run Complete**\n\n**Tasks awaiting your approval:**\n"
        for t in tasks:
            report += f"- [{t.get('priority', 'medium').upper()}] {t.get('title')} (source: {t.get('source')}, id: {t.get('id')[:8]})\n"
        report += "\nApprove via /tasks/{id}/approve"

    async with httpx.AsyncClient() as client:
        await client.post(settings.DISCORD_WEBHOOK_URL, json={"content": report})

    state["report"] = report
    return state


workflow = StateGraph(COOState)
workflow.add_node("fetch_issues", node_fetch_issues)
workflow.add_node("fetch_emails", node_fetch_emails)
workflow.add_node("fetch_events", node_fetch_events)
workflow.add_node("create_tasks", node_create_tasks)
workflow.add_node("notify_discord", node_notify_discord)

workflow.set_entry_point("fetch_issues")
workflow.add_edge("fetch_issues", "fetch_emails")
workflow.add_edge("fetch_emails", "fetch_events")
workflow.add_edge("fetch_events", "create_tasks")
workflow.add_edge("create_tasks", "notify_discord")
workflow.add_edge("notify_discord", END)

coo_graph = workflow.compile()


@router.post("/orchestrator/run")
async def run_orchestrator(github_token: str, org_id: str, gmail_token: str = None, calendar_token: str = None):
    initial_state = {
        "github_token": github_token,
        "gmail_token": gmail_token,
        "calendar_token": calendar_token,
        "org_id": org_id,
        "issues_data": [],
        "emails_data": [],
        "events_data": [],
        "tasks": [],
        "report": ""
    }

    final_state = await coo_graph.ainvoke(initial_state)

    return {
        "issues_found": len(final_state["issues_data"]),
        "emails_found": len(final_state["emails_data"]),
        "events_found": len(final_state["events_data"]),
        "tasks_created": len(final_state["tasks"]),
        "report": final_state["report"]
    }
