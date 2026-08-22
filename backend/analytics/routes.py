from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query
from analytics import service
from analytics.schemas import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary(
    org_id: str,
    start_date: str | None = Query(None, description="ISO date (YYYY-MM-DD). Defaults to 30 days ago."),
    end_date: str | None = Query(None, description="ISO date (YYYY-MM-DD). Defaults to today."),
):
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=30)
    resolved_start = start_date or start_dt.date().isoformat()
    resolved_end = end_date or end_dt.date().isoformat()
    return service.get_summary(org_id, resolved_start, resolved_end)
