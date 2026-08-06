from datetime import date, datetime, time
from typing import Optional, Literal
from zoneinfo import ZoneInfo
from pydantic import BaseModel, field_validator, model_validator

IST = ZoneInfo("Asia/Kolkata")

Frequency = Literal["daily", "every_2_days", "weekdays", "custom"]
JobStatus = Literal["active", "paused", "completed", "cancelled"]
RunStatus = Literal["pending", "success", "failed", "skipped"]
JobMode = Literal["scheduled", "recurring", "guard"]


class CommitJobFile(BaseModel):
    target_date: Optional[date] = None
    folder_path: str
    file_name: str
    content: Optional[str] = None

    @field_validator("folder_path")
    @classmethod
    def no_path_traversal_file(cls, v):
        if ".." in v or v.startswith("/"):
            raise ValueError("folder_path must not contain '..' or start with '/'")
        return v.strip("/")

    @field_validator("file_name")
    @classmethod
    def no_slashes_file(cls, v):
        if "/" in v or ".." in v:
            raise ValueError("file_name must not contain '/' or '..'")
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

    # Recurring / guard only — required when mode is "recurring" or "guard"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    frequency: Frequency = "daily"
    custom_dates: Optional[list[date]] = None

    # Scheduled (one-time) only — required when mode is "scheduled"
    execution_at: Optional[datetime] = None

    mode: JobMode = "scheduled"
    guard_cutoff_time: time = time(23, 30, 0)
    use_pr: bool = False
    files: Optional[list[CommitJobFile]] = None

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        start = info.data.get("start_date")
        if start and v and v < start:
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
        if v is None:
            return v
        if ".." in v or v.startswith("/"):
            raise ValueError("folder_path must not contain '..' or start with '/'")
        return v.strip("/")

    @field_validator("file_name")
    @classmethod
    def no_slashes_in_filename(cls, v):
        if v is None:
            return v
        if "/" in v or ".." in v:
            raise ValueError("file_name must not contain '/' or '..'")
        return v

    @field_validator("execution_at")
    @classmethod
    def execution_at_must_be_future(cls, v):
        if v is None:
            return v
        exec_at = v if v.tzinfo else v.replace(tzinfo=IST)
        if exec_at <= datetime.now(IST):
            raise ValueError("execution_at must be in the future")
        return v

    @model_validator(mode="after")
    def validate_mode_requirements(self):
        if self.mode == "scheduled":
            if not self.execution_at:
                raise ValueError("execution_at is required when mode is 'scheduled'")
        else:
            if not self.start_date or not self.end_date:
                raise ValueError("start_date and end_date are required when mode is 'recurring' or 'guard'")
        return self


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
    execution_at: Optional[datetime] = None
    status: Optional[JobStatus] = None

    @field_validator("execution_at")
    @classmethod
    def execution_at_must_be_future(cls, v):
        if v is None:
            return v
        exec_at = v if v.tzinfo else v.replace(tzinfo=IST)
        if exec_at <= datetime.now(IST):
            raise ValueError("execution_at must be in the future")
        return v


class CommitJobOut(BaseModel):
    id: str
    organization_id: str
    provider: str
    repo_full_name: str
    branch: str
    folder_path: Optional[str] = None
    file_name: Optional[str] = None
    commit_message: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    frequency: str
    mode: str
    execution_at: Optional[datetime] = None
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
