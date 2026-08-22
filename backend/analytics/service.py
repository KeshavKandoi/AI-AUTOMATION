"""
Business logic for Analytics: pulls raw rows via repository.py and buckets/
aggregates them in Python — there is no SQL/RPC aggregation function anywhere
else in this codebase (confirmed by searching for .sql files and rpc() calls),
so this follows the same in-Python aggregation style already used by
audit_logs.repository.distinct_modules / distinct_actions.
"""
from datetime import datetime, timedelta
from collections import defaultdict

from analytics import repository
from analytics.schemas import (
    AnalyticsSummary, DateRangeOut, DailyActivityPoint, BreakdownItem,
    TaskMetrics, WorkflowMetrics, CommitSchedulerMetrics,
)

RESOLVED_TASK_STATUSES = {"issue_created", "email_sent", "event_created", "resolved"}
VALID_AUDIT_STATUSES = {"success", "failed", "warning", "info"}


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _day_key(iso_str: str) -> str:
    return _parse_date(iso_str).date().isoformat()


def _daterange_days(start: datetime, end: datetime) -> list[str]:
    days = []
    cur = start.date()
    last = end.date()
    while cur <= last:
        days.append(cur.isoformat())
        cur += timedelta(days=1)
    return days


def _breakdown(counter: dict) -> list[BreakdownItem]:
    return [BreakdownItem(label=k, count=v) for k, v in sorted(counter.items(), key=lambda kv: -kv[1])]


def get_summary(organization_id: str, start_date: str, end_date: str) -> AnalyticsSummary:
    start_dt = _parse_date(start_date)
    end_dt = _parse_date(end_date)

    # ---- Audit logs: activity trend, module breakdown, totals ----
    logs = repository.get_audit_logs_in_range(organization_id, start_date, end_date)
    day_buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "failed": 0, "warning": 0, "info": 0})
    module_counts: dict[str, int] = defaultdict(int)
    failed_events = 0
    for row in logs:
        created_at = row.get("created_at")
        status = (row.get("status") or "info").lower()
        if status not in VALID_AUDIT_STATUSES:
            status = "info"
        module = row.get("module") or "unknown"
        if created_at:
            day_buckets[_day_key(created_at)][status] += 1
        if status == "failed":
            failed_events += 1
        module_counts[module] += 1

    activity_trend = [
        DailyActivityPoint(date=d, **day_buckets.get(d, {"success": 0, "failed": 0, "warning": 0, "info": 0}))
        for d in _daterange_days(start_dt, end_dt)
    ]

    # ---- Tasks ----
    tasks = repository.get_tasks_in_range(organization_id, start_date, end_date)
    priority_counts: dict[str, int] = defaultdict(int)
    status_counts: dict[str, int] = defaultdict(int)
    open_count = 0
    resolved_count = 0
    for t in tasks:
        priority_counts[t.get("priority") or "unknown"] += 1
        status_counts[t.get("status") or "unknown"] += 1
        if t.get("status") == "open":
            open_count += 1
        if t.get("status") in RESOLVED_TASK_STATUSES:
            resolved_count += 1

    task_metrics = TaskMetrics(
        total=len(tasks), open=open_count, resolved=resolved_count,
        by_priority=_breakdown(priority_counts), by_status=_breakdown(status_counts),
    )

    # ---- Workflows ----
    workflows = repository.get_workflows_for_org(organization_id)
    workflow_ids = [w["id"] for w in workflows]
    active_workflows = sum(1 for w in workflows if w.get("status") == "active")
    workflow_runs = repository.get_workflow_runs_in_range(workflow_ids, start_date, end_date)
    wf_status_counts: dict[str, int] = defaultdict(int)
    wf_success = 0
    for r in workflow_runs:
        s = r.get("status") or "unknown"
        wf_status_counts[s] += 1
        if s == "success":
            wf_success += 1
    wf_success_rate = round((wf_success / len(workflow_runs)) * 100, 1) if workflow_runs else None

    workflow_metrics = WorkflowMetrics(
        total_workflows=len(workflows), active_workflows=active_workflows,
        total_runs=len(workflow_runs), success_rate=wf_success_rate,
        by_status=_breakdown(wf_status_counts),
    )

    # ---- Commit Scheduler ----
    commit_jobs = repository.get_commit_jobs_for_org(organization_id)
    job_ids = [j["id"] for j in commit_jobs]
    active_jobs = sum(1 for j in commit_jobs if j.get("status") == "active")
    commit_runs = repository.get_commit_job_runs_in_range(job_ids, start_date, end_date)
    cs_status_counts: dict[str, int] = defaultdict(int)
    cs_success = 0
    for r in commit_runs:
        s = r.get("status") or "unknown"
        cs_status_counts[s] += 1
        if s == "success":
            cs_success += 1
    cs_success_rate = round((cs_success / len(commit_runs)) * 100, 1) if commit_runs else None

    commit_metrics = CommitSchedulerMetrics(
        total_jobs=len(commit_jobs), active_jobs=active_jobs,
        total_runs=len(commit_runs), success_rate=cs_success_rate,
        by_status=_breakdown(cs_status_counts),
    )

    return AnalyticsSummary(
        date_range=DateRangeOut(start_date=start_date, end_date=end_date),
        total_events=len(logs),
        failed_events=failed_events,
        activity_trend=activity_trend,
        module_breakdown=_breakdown(module_counts),
        tasks=task_metrics,
        workflows=workflow_metrics,
        commit_scheduler=commit_metrics,
    )
