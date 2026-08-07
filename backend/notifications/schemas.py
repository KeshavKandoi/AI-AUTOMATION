from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel

Priority = Literal["low", "normal", "high", "urgent"]


class NotificationCreate(BaseModel):
    organization_id: str
    module: str                       # e.g. "job_hunter", "commit_scheduler", "chat"
    category: Optional[str] = None    # e.g. "new_job_match", "interview_invite", "offer"
    priority: Priority = "normal"
    title: str
    body: str
    resource_type: Optional[str] = None   # e.g. "job_hunter_job", "job_hunter_application"
    resource_id: Optional[str] = None
    action_url: Optional[str] = None      # deep link the future bell/drawer UI opens
    action_label: Optional[str] = None    # e.g. "View Job"
    metadata: dict = {}
    dedup_key: Optional[str] = None       # e.g. "job_hunter:job_match:{job_id}" — enforces
                                           # "never show duplicate notifications for the
                                           # same event" generically, at the DB level


class NotificationOut(BaseModel):
    id: str
    organization_id: str
    module: str
    category: Optional[str] = None
    priority: str
    title: str
    body: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    metadata: Optional[dict] = None
    delivered_channels: Optional[dict] = None
    read: bool
    read_at: Optional[datetime] = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationOut]
    total: int
    unread_count: int
    limit: int
    offset: int
