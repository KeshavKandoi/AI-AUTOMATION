from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel

# Kept loose (plain str, not Literal) on purpose: any current or future module
# should be able to log an action/module name without a backend schema change.
# status is the one field worth constraining for consistent badge coloring on
# the frontend, but we still accept any string and just fall back gracefully.
AuditStatus = Literal["success", "failed", "warning", "info"]
ActorType = Literal["user", "ai", "system"]


class AuditLogCreate(BaseModel):
    organization_id: str
    module: str
    action: str
    status: AuditStatus = "info"
    summary: str
    user_id: Optional[str] = None
    actor_type: ActorType = "system"
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    metadata: dict = {}
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    source: str = "backend"


class AuditLogOut(BaseModel):
    id: str
    organization_id: str
    module: Optional[str] = None
    action: str
    status: Optional[str] = None
    summary: Optional[str] = None
    user_id: Optional[str] = None
    actor_type: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    metadata: Optional[dict] = None
    details: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    source: Optional[str] = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogOut]
    total: int
    limit: int
    offset: int
