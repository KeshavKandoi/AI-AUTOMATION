from config import supabase_admin, logger
from audit import log_action
from orchestrator import coo_graph
from missed_event_recovery.service import (
    _get_org_github_token, find_missed_issue_events,
    mark_event_processed, _update_last_polled_at
)


async def run_missed_event_recovery():
    logger.info("Running missed-event recovery check")

    orgs_res = supabase_admin.table("organizations") \
        .select("id, github_repo").not_.is_("github_repo", "null").execute()
    orgs = orgs_res.data

    for org in orgs:
        org_id = org["id"]
        repo = org["github_repo"]

        access_token = _get_org_github_token(org_id)
        if not access_token:
            continue

        missed = await find_missed_issue_events(org_id, repo, access_token)

        if not missed:
            _update_last_polled_at(org_id)
            continue

        logger.info(f"Recovered {len(missed)} missed GitHub event(s) for org {org_id} ({repo})")
        log_action(org_id, "missed_event_recovered", {"repo": repo, "count": len(missed)})

        initial_state = {
            "github_token": access_token, "gmail_token": "", "calendar_token": "",
            "org_id": org_id, "issues_data": [], "emails_data": [],
            "events_data": [], "tasks": [], "report": ""
        }
        try:
            final_state = await coo_graph.ainvoke(initial_state)
            logger.info(f"Recovery run complete for org {org_id}: {final_state['report']}")
        except Exception as e:
            logger.error(f"Recovery orchestrator run failed for org {org_id}: {e}")
            continue

        for item in missed:
            mark_event_processed(org_id, item["event_key"], source="poll_recovery")

        _update_last_polled_at(org_id)
