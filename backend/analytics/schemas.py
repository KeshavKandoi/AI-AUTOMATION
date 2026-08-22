from typing import Optional
from pydantic import BaseModel


class DateRangeOut(BaseModel):
    start_date: str
    end_date: str


class DailyActivityPoint(BaseModel):
    date: str
    success: int = 0
    failed: int = 0
    warning: int = 0
    info: int = 0


class BreakdownItem(BaseModel):
    label: str
    count: int


class TaskMetrics(BaseModel):
    total: int
    open: int
    resolved: int
    by_priority: list[BreakdownItem]
    by_status: list[BreakdownItem]


class WorkflowMetrics(BaseModel):
    total_workflows: int
    active_workflows: int
    total_runs: int
    success_rate: Optional[float] = None
    by_status: list[BreakdownItem]


class CommitSchedulerMetrics(BaseModel):
    total_jobs: int
    active_jobs: int
    total_runs: int
    success_rate: Optional[float] = None
    by_status: list[BreakdownItem]


class AnalyticsSummary(BaseModel):
    date_range: DateRangeOut
    total_events: int
    failed_events: int
    activity_trend: list[DailyActivityPoint]
    module_breakdown: list[BreakdownItem]
    # False when the org has more audit log events in range than the row-fetch
    # cap allows us to pull for day/module bucketing -- total_events/failed_events
    # stay accurate regardless (see get_audit_log_counts), but activity_trend and
    # module_breakdown are computed only from the rows actually fetched when this
    # is False, and should be labeled as partial in the UI rather than presented
    # as complete.
    activity_data_complete: bool
    tasks: TaskMetrics
    workflows: WorkflowMetrics
    commit_scheduler: CommitSchedulerMetrics
