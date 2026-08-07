from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel

# Kept as plain str (not a strict Literal) so future categories can be added
# without a backend schema change — mirrors the audit_logs module/action
# fields. The values below are the ones the frontend currently renders with
# a dedicated icon/label; any other string still works, it just falls back
# to a generic display.
MemoryCategory = Literal[
    "user_preference", "project", "repository", "workflow",
    "conversation", "integration", "knowledge", "custom",
]
MemoryImportance = Literal["low", "medium", "high", "critical"]
MemoryStatus = Literal["active", "archived", "deleted"]


class MemoryCreate(BaseModel):
    organization_id: str
    title: str
    content: str
    category: str = "custom"
    tags: list[str] = []
    source: str = "user"
    importance: MemoryImportance = "medium"
    user_id: Optional[str] = None
    metadata: dict = {}


class MemoryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    importance: Optional[MemoryImportance] = None
    metadata: Optional[dict] = None


class MemoryOut(BaseModel):
    id: str
    organization_id: str
    title: Optional[str] = None
    content: str
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    source: Optional[str] = None
    importance: Optional[str] = None
    status: Optional[str] = None
    pinned: Optional[bool] = None
    favorited: Optional[bool] = None
    user_id: Optional[str] = None
    metadata: Optional[dict] = None
    access_count: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class MemoryListResponse(BaseModel):
    items: list[MemoryOut]
    total: int
    limit: int
    offset: int
