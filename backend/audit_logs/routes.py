from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from audit_logs import service
from audit_logs.schemas import AuditLogListResponse, AuditLogOut
from auth.dependencies import get_current_org_id

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    org_id: str = Depends(get_current_org_id),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    module: Optional[str] = None,
    action: Optional[str] = None,
    status: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
):
    items, total = service.list_events(
        organization_id=org_id,
        limit=limit,
        offset=offset,
        module=module,
        action=action,
        status=status,
        resource_type=resource_type,
        resource_id=resource_id,
        search=search,
        start_date=start_date,
        end_date=end_date,
        sort_dir=sort_dir,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/filters")
def get_filter_options(org_id: str = Depends(get_current_org_id)):
    return service.list_filter_options(org_id)


@router.get("/{log_id}", response_model=AuditLogOut)
def get_audit_log(log_id: str, org_id: str = Depends(get_current_org_id)):
    log = service.get_event(log_id)
    if not log or log.get("organization_id") != org_id:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log
