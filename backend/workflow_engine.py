import base64
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
import httpx
from config import supabase_admin, logger, decrypt_token, get_valid_access_token
from audit import log_action


def _get_org_token(organization_id: str, provider: str):
    integration_res = supabase_admin.table("integrations") \
        .select("id").eq("organization_id", organization_id) \
        .eq("provider", provider).eq("connected", True) \
        .order("created_at", desc=True).execute()
    if not integration_res.data:
        return None
    integration_id = integration_res.data[0]["id"]
    try:
        return get_valid_access_token(integration_id)
    except ValueError as e:
        logger.error(f"Token unavailable for org {organization_id} provider {provider}: {e}")
        return None


def _get_org_email(organization_id: str):
    result = supabase_admin.table("organizations").select("notification_email").eq("id", organization_id).execute()
    return result.data[0].get("notification_email") if result.data else None


def _match_conditions(conditions: dict, context: dict) -> bool:
    for key, expected in conditions.items():
        actual = context.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        else:
            if actual != expected:
                return False
    return True


async def _action_create_task(organization_id: str, context: dict) -> dict:
    result = supabase_admin.table("tasks").insert({
        "organization_id": organization_id,
        "title": context.get("title", "Untitled task"),
        "description": context.get("description", ""),
        "priority": context.get("priority", "medium"),
        "source": "workflow_engine"
    }).execute()
    task = result.data[0]
    context["task_id"] = task["id"]
    return {"task_id": task["id"]}


async def _action_send_email(organization_id: str, context: dict) -> dict:
    access_token = _get_org_token(organization_id, "gmail")
    to_email = _get_org_email(organization_id)
    if not access_token or not to_email:
        raise RuntimeError("Missing Gmail token or org email")

    body = f"{context.get('title', 'Automation triggered')}\n\n{context.get('description', '')}"
    mime_msg = MIMEText(body)
    mime_msg["to"] = to_email
    mime_msg["subject"] = context.get("title", "Workflow notification")
    raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"raw": raw}
        )
    if res.status_code != 200:
        raise RuntimeError(f"Gmail send failed: {res.text}")
    return {"message_id": res.json().get("id")}


async def _action_notify_discord(organization_id: str, context: dict) -> dict:
    org_res = supabase_admin.table("organizations").select("discord_webhook_url").eq("id", organization_id).execute()
    webhook_url = org_res.data[0].get("discord_webhook_url") if org_res.data else None
    if not webhook_url:
        from config import settings
        webhook_url = settings.DISCORD_WEBHOOK_URL

    message = f"**Workflow triggered**\n{context.get('title', '')}"
    async with httpx.AsyncClient() as client:
        res = await client.post(webhook_url, json={"content": message})
    if res.status_code not in (200, 204):
        raise RuntimeError(f"Discord notify failed: {res.text}")
    return {"status": "sent"}


async def _action_create_calendar_event(organization_id: str, context: dict) -> dict:
    access_token = _get_org_token(organization_id, "calendar")
    if not access_token:
        raise RuntimeError("Missing Calendar token")

    start = datetime.now(timezone.utc) + timedelta(hours=1)
    end = start + timedelta(minutes=30)

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "summary": context.get("title", "Workflow event"),
                "description": context.get("description", ""),
                "start": {"dateTime": start.isoformat()},
                "end": {"dateTime": end.isoformat()},
            }
        )
    if res.status_code != 200:
        raise RuntimeError(f"Calendar event failed: {res.text}")
    return {"event_link": res.json().get("htmlLink")}


async def _action_save_audit_log(organization_id: str, context: dict) -> dict:
    log_action(organization_id, "workflow_audit", context)
    return {"status": "logged"}


ACTION_REGISTRY = {
    "create_task": _action_create_task,
    "send_email": _action_send_email,
    "notify_discord": _action_notify_discord,
    "create_calendar_event": _action_create_calendar_event,
    "save_audit_log": _action_save_audit_log,
}


def sample_context_for_trigger(trigger_type: str) -> dict:
    if trigger_type == "issue_created":
        return {
            "title": "Sample issue (manual test run)",
            "description": "This is a manually triggered test run.",
            "priority": "medium",
            "issue_number": 0,
            "issue_url": "",
            "repo": "manual-test",
        }
    return {}


async def execute_workflow(workflow: dict, context: dict, record_skipped: bool = False):
    """
    Runs condition match + all actions for a single workflow, records the run.
    - record_skipped=False (webhook path): no row written on non-match, returns None.
    - record_skipped=True (manual Run Now): writes a 'skipped_conditions' row on non-match.
    """
    organization_id = workflow["organization_id"]

    if not _match_conditions(workflow.get("conditions", {}), context):
        if not record_skipped:
            return None
        run = supabase_admin.table("workflow_runs").insert({
            "workflow_id": workflow["id"],
            "trigger_context": context,
            "actions_executed": [],
            "status": "skipped_conditions",
            "error_message": None
        }).execute()
        return run.data[0]

    executed = []
    run_status = "success"
    error_message = None
    for action_name in workflow.get("actions", []):
        handler = ACTION_REGISTRY.get(action_name)
        if not handler:
            logger.error(f"Unknown workflow action '{action_name}' in workflow {workflow['id']}")
            continue
        try:
            action_result = await handler(organization_id, context)
            executed.append({"action": action_name, "result": action_result})
        except Exception as e:
            logger.error(f"Workflow action '{action_name}' failed for workflow {workflow['id']}: {e}")
            executed.append({"action": action_name, "error": str(e)})
            run_status = "partial_failure"
            error_message = str(e)

    run = supabase_admin.table("workflow_runs").insert({
        "workflow_id": workflow["id"],
        "trigger_context": context,
        "actions_executed": executed,
        "status": run_status,
        "error_message": error_message
    }).execute()
    logger.info(f"Workflow '{workflow.get('name')}' ({workflow['id']}) executed: {executed}")
    return run.data[0]


async def run_workflows(organization_id: str, trigger_type: str, context: dict):
    result = supabase_admin.table("workflows") \
        .select("*").eq("organization_id", organization_id) \
        .eq("trigger_type", trigger_type).eq("status", "active").execute()
    workflows = result.data
    if not workflows:
        return
    for workflow in workflows:
        await execute_workflow(workflow, context, record_skipped=False)
