from datetime import date, datetime, time
from typing import Optional, Literal
from pydantic import BaseModel, field_validator


Frequency = Literal["daily", "every_2_days", "weekdays", "custom"]
JobStatus = Literal["active", "paused", "completed", "cancelled"]
RunStatus = Literal["pending", "success", "failed", "skipped"]
JobMode = Literal["scheduled", "guard"]


class CommitJobFile(BaseModel):
    target_date: Optional[date] = None
    folder_path: str
    file_name: str
    content: Optional[str] = None

    @field_validator("folder_path")
    @classmethod
    def no_path_traversal_file(cls, v):
        if ".." in v or v.startswith("/"):
            raise ValueError("folder_path must not contain '\''..'\'' or start with '\''/'\''")
        return v.strip("/")

    @field_validator("file_name")
    @classmethod
    def no_slashes_file(cls, v):
        if "/" in v or ".." in v:
            raise ValueError("file_name must not contain '\''/'\'' or '\''..'\''")
        return v


class CommitJobCreate(BaseModel):
    organization_id: str
    provider: str = "github"
    repo_full_name: str
    branch: str = "main"
    folder_path: Optional[str] = None
    file_name: Optional[str] = None
    file_content: Optional[str] = None
    commit_message: str
    start_date: date
    end_date: date
    frequency: Frequency = "daily"
    custom_dates: Optional[list[date]] = None
    mode: JobMode = "scheduled"
    guard_cutoff_time: time = time(23, 30, 0)
    use_pr: bool = False
    files: Optional[list[CommitJobFile]] = None

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must be on or after start_date")
        return v

    @field_validator("custom_dates")
    @classmethod
    def custom_dates_required_for_custom_frequency(cls, v, info):
        freq = info.data.get("frequency")
        if freq == "custom" and not v:
            raise ValueError("custom_dates is required when frequency is 'custom'")
        return v

    @field_validator("folder_path")
    @classmethod
    def no_path_traversal(cls, v):
        if ".." in v or v.startswith("/"):
            raise ValueError("folder_path must not contain '..' or start with '/'")
        return v.strip("/")

    @field_validator("file_name")
    @classmethod
    def no_slashes_in_filename(cls, v):
        if "/" in v or ".." in v:
            raise ValueError("file_name must not contain '/' or '..'")
        return v


class CommitJobUpdate(BaseModel):
    branch: Optional[str] = None
    folder_path: Optional[str] = None
    file_name: Optional[str] = None
    file_content: Optional[str] = None
    commit_message: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    frequency: Optional[Frequency] = None
    custom_dates: Optional[list[date]] = None
    status: Optional[JobStatus] = None


class CommitJobOut(BaseModel):
    id: str
    organization_id: str
    provider: str
    repo_full_name: str
    branch: str
    folder_path: str
    file_name: str
    commit_message: str
    start_date: date
    end_date: date
    frequency: str
    status: str
    created_at: datetime
    updated_at: datetime


class CommitJobRunOut(BaseModel):
    id: str
    job_id: str
    run_date: date
    status: str
    commit_sha: Optional[str] = None
    commit_url: Optional[str] = None
    error_message: Optional[str] = None
    executed_at: datetime
