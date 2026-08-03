import httpx
from config import supabase_admin, logger
from audit import log_action


def parse_source_ref(source_ref: str):
    if not source_ref or ":" not in source_ref:
        return None, None
    source_type, identifier = source_ref.split(":", 1)
    return source_type, identifier


async def _github_comment(access_token: str, owner_repo: str, issue_number: str, body: str):
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api.github.com/repos/{owner_repo}/issues/{issue_number}/comments",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"body": body}
        )
    if res.status_code not in (200, 201):
        raise RuntimeError(f"GitHub comment failed: {res.text}")


async def _github_close(access_token: str, owner_repo: str, issue_number: str):
    async with httpx.AsyncClient() as client:
        res = await client.patch(
            f"https://api.github.com/repos/{owner_repo}/issues/{issue_number}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"state": "closed"}
        )
    if res.status_code != 200:
        raise RuntimeError(f"GitHub close failed: {res.text}")


async def close_github_loop(task: dict, access_token: str, approved: bool, resolution: str = None, pr_url: str = None):
    source_type, identifier = parse_source_ref(task.get("source_ref", ""))
    if source_type != "github" or not identifier or "#" not in identifier:
        raise RuntimeError(f"Cannot close GitHub loop — invalid source_ref: {task.get('source_ref')}")

    owner_repo, issue_number = identifier.rsplit("#", 1)

    if approved:
        body = f"Task completed: {task.get('title')}\n\n{task.get('description', '')}"
        if pr_url:
            body += f"\n\nRelated PR: {pr_url}"
        await _github_comment(access_token, owner_repo, issue_number, body)
        if resolution == "resolved":
            await _github_close(access_token, owner_repo, issue_number)
    else:
        body = f"Task rejected/cancelled: {task.get('title')}"
        await _github_comment(access_token, owner_repo, issue_number, body)


async def _gmail_modify(access_token: str, message_id: str, add_labels=None, remove_labels=None):
    payload = {}
    if add_labels:
        payload["addLabelIds"] = add_labels
    if remove_labels:
        payload["removeLabelIds"] = remove_labels
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload
        )
    if res.status_code != 200:
        raise RuntimeError(f"Gmail modify failed: {res.text}")


async def close_gmail_loop(task: dict, access_token: str, approved: bool, archive: bool = False):
    source_type, message_id = parse_source_ref(task.get("source_ref", ""))
    if source_type != "gmail" or not message_id:
        raise RuntimeError(f"Cannot close Gmail loop — invalid source_ref: {task.get('source_ref')}")

    remove_labels = ["UNREAD"]
    if approved and archive:
        remove_labels.append("INBOX")

    await _gmail_modify(access_token, message_id, remove_labels=remove_labels)


async def _calendar_patch(access_token: str, event_id: str, payload: dict):
    async with httpx.AsyncClient() as client:
        res = await client.patch(
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload
        )
    if res.status_code != 200:
        raise RuntimeError(f"Calendar update failed: {res.text}")


async def _calendar_delete(access_token: str, event_id: str):
    async with httpx.AsyncClient() as client:
        res = await client.delete(
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
    if res.status_code not in (200, 204):
        raise RuntimeError(f"Calendar delete failed: {res.text}")


async def close_calendar_loop(task: dict, access_token: str, approved: bool, decline: bool = False, notes: str = None):
    source_type, event_id = parse_source_ref(task.get("source_ref", ""))
    if source_type != "calendar" or not event_id:
        raise RuntimeError(f"Cannot close Calendar loop — invalid source_ref: {task.get('source_ref')}")

    if approved:
        if notes:
            await _calendar_patch(access_token, event_id, {"description": notes})
    else:
        if decline:
            await _calendar_delete(access_token, event_id)


CLOSEOUT_HANDLERS = {
    "github": close_github_loop,
    "gmail": close_gmail_loop,
    "calendar": close_calendar_loop,
}


async def run_closeout(task: dict, access_token: str, approved: bool, **kwargs):
    source_type, _ = parse_source_ref(task.get("source_ref", ""))
    handler = CLOSEOUT_HANDLERS.get(source_type)

    if not handler:
        logger.info(f"No closeout handler for source_type={source_type} on task {task.get('id')} — skipping")
        return

    try:
        await handler(task, access_token, approved, **kwargs)
        supabase_admin.table("tasks").update({
            "closeout_status": "completed",
            "closeout_error": None
        }).eq("id", task["id"]).execute()
        log_action(task["organization_id"], "closeout_completed", {
            "task_id": task["id"], "source_ref": task.get("source_ref"), "approved": approved
        })
    except Exception as e:
        logger.error(f"Closeout failed for task {task.get('id')}: {e}")
        supabase_admin.table("tasks").update({
            "closeout_status": "failed",
            "closeout_error": str(e)
        }).eq("id", task["id"]).execute()
        log_action(task["organization_id"], "closeout_failed", {
            "task_id": task["id"], "source_ref": task.get("source_ref"), "error": str(e)
        })
