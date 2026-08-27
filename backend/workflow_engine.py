import base64
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
import httpx
from config import supabase_admin, logger, decrypt_token, get_valid_access_token
from audit_logs.service import log_event


def _get_org_token(organization_id: str, provider: str):
    """Returns (access_token, error_reason). access_token is None on any
    failure; error_reason is a short, specific string safe to surface in
    workflow_runs.error_message (never includes token material)."""
    integration_res = supabase_admin.table("integrations") \
        .select("id").eq("organization_id", organization_id) \
        .eq("provider", provider).eq("connected", True) \
        .order("created_at", desc=True).execute()
    if not integration_res.data:
        return None, f"No connected {provider} integration for this organization"
    integration_id = integration_res.data[0]["id"]
    try:
        return get_valid_access_token(integration_id), None
    except ValueError as e:
        logger.error(f"Token unavailable for org {organization_id} provider {provider}: {e}")
        reason = str(e)
        if "invalid_grant" in reason or "expired or revoked" in reason:
            return None, f"{provider.capitalize()} authorization expired or was revoked — please reconnect {provider} in Settings"
        if "No token found" in reason:
            return None, f"No {provider} token on record — please reconnect {provider} in Settings"
        return None, f"{provider.capitalize()} token error: {reason}"


def _get_org_email(organization_id: str):
    """Resolves the recipient for Gmail-based workflow notifications.

    Primary source: the actual email address of the connected Gmail account
    (fetched live via Google's userinfo endpoint using the org's own valid
    Gmail access token) -- this is the account the workflow is authorized to
    send *as*, so it's the correct default recipient with zero extra setup.

    organizations.notification_email remains a supported override for orgs
    that explicitly want notifications routed to a different address than
    the connected Gmail account; if set, it takes precedence. As of this
    change nothing in the product writes this column automatically -- it's
    purely an opt-in override a future settings UI could expose.
    """
    org_res = supabase_admin.table("organizations").select("notification_email").eq("id", organization_id).execute()
    override_email = org_res.data[0].get("notification_email") if org_res.data else None
    if override_email:
        return override_email

    access_token, _token_error = _get_org_token(organization_id, "gmail")
    if not access_token:
        return None

    try:
        res = httpx.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if res.status_code != 200:
            logger.error(f"Failed to resolve Gmail account email for org {organization_id}: {res.status_code} {res.text}")
            return None
        return res.json().get("email")
    except httpx.HTTPError as e:
        logger.error(f"Failed to resolve Gmail account email for org {organization_id}: {e}")
        return None


def _derive_context_label(context: dict) -> str:
    """Derives a meaningful, human-readable label for a triggering event,
    for actions (save_audit_log, create_calendar_event) that need a title
    but whose trigger type may not provide one directly.

    issue_created and pull_request_opened contexts already carry a real
    'title' field -- used as-is (still prefixed with the workflow name
    below), unchanged in substance from prior behavior. push contexts have
    no 'title' at all (they carry commit_message, repo, branch, commit_sha
    instead), so without this, every push-triggered audit log entry /
    calendar event silently fell back to a hardcoded generic label
    ("Untitled" / "Workflow event") regardless of what was actually pushed
    -- this fixes that by using the real commit message, falling back
    further to repo@branch if even that is missing.

    When execute_workflow has attached the triggering workflow's own name
    to the context (as "_workflow_name"), it's prefixed onto the label --
    e.g. "KK: fix typo in README" -- so the entry identifies both which
    workflow ran and what specifically triggered it."""
    title = context.get("title")
    if title:
        event_label = title
    else:
        commit_message = context.get("commit_message")
        if commit_message:
            event_label = commit_message
        else:
            repo = context.get("repo")
            branch = context.get("branch")
            if repo and branch:
                event_label = f"{repo}@{branch}"
            elif repo:
                event_label = repo
            else:
                event_label = "Untitled"

    workflow_name = context.get("_workflow_name")
    if workflow_name:
        return f"{workflow_name}: {event_label}"
    return event_label


def _match_conditions(conditions: dict, context: dict) -> bool:
    if not conditions:
        return True

    # New format: {"logic": "AND"|"OR", "rules": [{"field", "op", "value"}]}
    if "rules" in conditions and "logic" in conditions:
        rules = conditions.get("rules") or []
        if not rules:
            return True
        logic = conditions.get("logic", "AND")
        results = []
        for rule in rules:
            field = rule.get("field")
            op = rule.get("op", "eq")
            expected = rule.get("value")
            actual = context.get(field)
            if op == "in":
                candidates = expected if isinstance(expected, list) else [expected]
                results.append(actual in candidates)
            else:
                results.append(actual == expected)
        return all(results) if logic == "AND" else any(results)

    # Legacy flat-dict format: {"field": value, ...} — implicit AND. Preserved so
    # workflows created before AND/OR support (e.g. "High priority issue fan-out")
    # keep working unchanged.
    for key, expected in conditions.items():
        actual = context.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        else:
            if actual != expected:
                return False
    return True


def _is_past_expiry(workflow: dict) -> bool:
    """True if a 'until_date' workflow's expires_at has already passed.
    A lazy, per-call check as a backstop between scheduler sweeps, so an
    expired workflow can't slip through and fire between the minute-by-minute
    sweep and an incoming trigger event."""
    if workflow.get("lifetime_mode") != "until_date":
        return False
    expires_at = workflow.get("expires_at")
    if not expires_at:
        return False
    expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00")) if isinstance(expires_at, str) else expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= expiry


async def sweep_expired_workflows():
    """Marks any active 'until_date' workflow whose time has passed as expired.
    Runs on a schedule so expiry fires even without an incoming trigger event."""
    result = supabase_admin.table("workflows") \
        .select("*").eq("status", "active").eq("lifetime_mode", "until_date").execute()
    expired_count = 0
    for workflow in result.data:
        if _is_past_expiry(workflow):
            supabase_admin.table("workflows").update({"status": "expired"}).eq("id", workflow["id"]).execute()
            expired_count += 1
    if expired_count:
        logger.info(f"Swept {expired_count} expired workflow(s)")
    return expired_count


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
    access_token, token_error = _get_org_token(organization_id, "gmail")
    to_email = _get_org_email(organization_id)
    if not access_token or not to_email:
        problems = []
        if not access_token:
            problems.append(token_error or "Gmail is not connected for this organization")
        elif not to_email:
            problems.append("Could not determine a recipient email — please reconnect Gmail in Settings (new permission required)")
        raise RuntimeError("; ".join(problems))

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
    access_token, token_error = _get_org_token(organization_id, "calendar")
    if not access_token:
        raise RuntimeError(token_error or "Calendar is not connected for this organization")

    start = datetime.now(timezone.utc) + timedelta(hours=1)
    end = start + timedelta(minutes=30)

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "summary": _derive_context_label(context),
                "description": context.get("description", ""),
                "start": {"dateTime": start.isoformat()},
                "end": {"dateTime": end.isoformat()},
            }
        )
    if res.status_code != 200:
        raise RuntimeError(f"Calendar event failed: {res.text}")
    return {"event_link": res.json().get("htmlLink")}


async def _action_save_audit_log(organization_id: str, context: dict) -> dict:
    log_event(
        organization_id=organization_id,
        module="workflows",
        action="workflow_audit",
        summary=f"Workflow audit action: {_derive_context_label(context)}".strip(),
        status="info",
        metadata=context,
        source="backend",
    )
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
            "labels": [],
            "assignee": "",
            "author": "manual-test-user",
        }
    if trigger_type == "push":
        return {
            "repo": "manual-test",
            "branch": "main",
            "author": "manual-test-user",
            "commit_message": "Sample commit (manual test run)",
            "commit_sha": "0000000",
            "files_changed": [],
            "commit_count": 1,
            "timestamp": "",
        }
    if trigger_type == "pull_request_opened":
        return {
            "repo": "manual-test",
            "title": "Sample PR (manual test run)",
            "author": "manual-test-user",
            "source_branch": "feature/test",
            "target_branch": "main",
            "draft": False,
            "labels": [],
            "pr_number": 0,
            "pr_url": "",
        }
    return {}


async def execute_workflow(workflow: dict, context: dict, record_skipped: bool = False):
    """
    Runs condition match + all actions for a single workflow, records the run.
    - record_skipped=False (webhook path): no row written on non-match, returns None.
    - record_skipped=True (manual Run Now): writes a 'skipped_conditions' row on non-match.
    """
    import time
    organization_id = workflow["organization_id"]
    started = time.monotonic()
    # Attach the workflow's own name to the context so actions like
    # save_audit_log / create_calendar_event can show "<workflow name>: <event>"
    # instead of just the raw event details -- copy, never mutate the
    # caller's original context dict.
    context = {**context, "_workflow_name": workflow.get("name")}

    if not _match_conditions(workflow.get("conditions", {}), context):
        if not record_skipped:
            return None
        duration_ms = int((time.monotonic() - started) * 1000)
        run = supabase_admin.table("workflow_runs").insert({
            "workflow_id": workflow["id"],
            "trigger_context": context,
            "actions_executed": [],
            "status": "skipped_conditions",
            "error_message": None,
            "duration_ms": duration_ms,
        }).execute()
        log_event(
            organization_id=organization_id,
            module="workflows",
            action="workflow_run_skipped",
            summary=f"Workflow '{workflow.get('name', 'Untitled')}' skipped — conditions not met",
            status="warning",
            resource_type="workflow",
            resource_id=workflow["id"],
            metadata={"trigger_type": workflow.get("trigger_type")},
            duration_ms=duration_ms,
            source="backend",
        )
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

    duration_ms = int((time.monotonic() - started) * 1000)
    run = supabase_admin.table("workflow_runs").insert({
        "workflow_id": workflow["id"],
        "trigger_context": context,
        "actions_executed": executed,
        "status": run_status,
        "error_message": error_message,
        "duration_ms": duration_ms,
    }).execute()
    logger.info(f"Workflow '{workflow.get('name')}' ({workflow['id']}) executed in {duration_ms}ms: {executed}")
    log_event(
        organization_id=organization_id,
        module="workflows",
        action="workflow_execution_failed" if run_status == "partial_failure" else "workflow_executed",
        summary=(
            f"Workflow '{workflow.get('name', 'Untitled')}' failed"
            if run_status == "partial_failure"
            else f"Workflow '{workflow.get('name', 'Untitled')}' executed successfully"
        ),
        status="failed" if run_status == "partial_failure" else "success",
        resource_type="workflow",
        resource_id=workflow["id"],
        metadata={"trigger_type": workflow.get("trigger_type"), "actions_executed": executed},
        error_message=error_message,
        duration_ms=duration_ms,
        source="backend",
    )

    # A run_once workflow retires after its first clean success. A partial
    # failure does NOT retire it — it stays active so it can fire again on
    # the next matching event or a manual Run Now.
    if run_status == "success" and workflow.get("lifetime_mode") == "run_once":
        supabase_admin.table("workflows").update({"status": "completed"}).eq("id", workflow["id"]).execute()

    return run.data[0]


def _record_event_if_new(organization_id: str, repo_full_name: str, event_type: str, event_key: str) -> bool:
    """Atomically claims this (org, repo, event_type, event_key) combination via
    the database's own unique constraint on processed_github_events. Returns
    True if this call successfully claimed it (i.e. this is the first time
    this exact event has been seen -- proceed with execution). Returns False
    if it was already claimed by an earlier call (a real GitHub webhook and
    an internally-dispatched scheduler event for the same commit both resolve
    here, and only the first one through wins).

    This is a database-level uniqueness check, not an application-level
    check-then-insert -- the INSERT itself is what enforces atomicity; a
    conflict here means "someone already processed this," full stop."""
    try:
        supabase_admin.table("processed_github_events").insert({
            "organization_id": organization_id,
            "repo_full_name": repo_full_name,
            "event_type": event_type,
            "event_key": event_key,
        }).execute()
        return True
    except Exception as e:
        # A unique-constraint violation is the expected "already processed"
        # case, not an error -- Supabase/PostgREST surfaces this as an
        # APIError with code 23505. Any other exception is a real problem
        # and should not be silently swallowed as a dedup hit.
        if "23505" in str(e) or "duplicate key" in str(e).lower():
            return False
        logger.error(f"Unexpected error recording event dedup for org {organization_id}, repo {repo_full_name}, event {event_type}/{event_key}: {e}")
        raise


async def dispatch_workflow_event(organization_id: str, trigger_type: str, context: dict, event_key: str):
    """Single shared entry point for any GitHub-shaped event that should run
    through the workflow engine, regardless of whether it originated from a
    real, signature-verified GitHub webhook delivery or from this
    application's own internal actions (e.g. Commit Scheduler successfully
    pushing a commit).

    organization_id must already be trusted by the caller before this is
    invoked -- for real webhooks that means it was resolved via
    _resolve_org_for_webhook's signature verification; for internally
    generated events it means the organization_id the initiating job/action
    was created under. This function never re-derives or second-guesses
    organization identity -- that responsibility stays with the caller.

    event_key must uniquely identify this specific occurrence within its
    (organization, repo, trigger_type) scope -- e.g. a commit SHA for push,
    or "pr-<number>-<head_sha>" for a pull request -- so that the same real
    event arriving twice (once as a real webhook, once as an internally
    dispatched event, or via GitHub's own webhook redelivery) executes the
    matching workflow(s) at most once.
    """
    repo_full_name = context.get("repo", "")
    if not _record_event_if_new(organization_id, repo_full_name, trigger_type, event_key):
        logger.info(
            f"Skipping duplicate {trigger_type} event for org {organization_id}, "
            f"repo {repo_full_name}, event_key={event_key} -- already processed."
        )
        return
    await run_workflows(organization_id, trigger_type, context)


async def run_workflows(organization_id: str, trigger_type: str, context: dict):
    result = supabase_admin.table("workflows") \
        .select("*").eq("organization_id", organization_id) \
        .eq("trigger_type", trigger_type).eq("status", "active").execute()
    workflows = result.data
    if not workflows:
        return
    for workflow in workflows:
        if _is_past_expiry(workflow):
            supabase_admin.table("workflows").update({"status": "expired"}).eq("id", workflow["id"]).execute()
            continue
        await execute_workflow(workflow, context, record_skipped=False)
