from fastapi import APIRouter, HTTPException, Depends
from notifications import service
from notifications.schemas import NotificationListResponse
from auth.dependencies import get_current_org_id

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    limit: int = 50,
    offset: int = 0,
    module: str | None = None,
    category: str | None = None,
    unread_only: bool = False,
    org_id: str = Depends(get_current_org_id),
):
    return service.list_for_org(
        organization_id=org_id,
        limit=limit,
        offset=offset,
        module=module,
        category=category,
        unread_only=unread_only,
    )


@router.post("/{notification_id}/read")
def mark_read(notification_id: str, org_id: str = Depends(get_current_org_id)):
    updated = service.mark_notification_read(notification_id, org_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "read", "notification": updated}


@router.post("/mark-all-read")
def mark_all_read(org_id: str = Depends(get_current_org_id)):
    count = service.mark_all_read_for_org(org_id)
    return {"status": "read", "count": count}
