from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, field_validator

MemoryImportance = Literal["low", "medium", "high", "critical"]

TITLE_MAX = 200
CONTENT_MAX = 20000


def _clean_title(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("title must not be empty")
    if len(v) > TITLE_MAX:
        raise ValueError(f"title must be at most {TITLE_MAX} characters")
    return v


def _clean_content(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("content must not be empty")
    if len(v) > CONTENT_MAX:
        raise ValueError(f"content must be at most {CONTENT_MAX} characters")
    return v


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

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        return _clean_title(v)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        return _clean_content(v)


class MemoryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    importance: Optional[MemoryImportance] = None
    metadata: Optional[dict] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        return _clean_title(v) if v is not None else v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        return _clean_content(v) if v is not None else v


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
