from datetime import date, datetime, time
from typing import Optional, Literal
from zoneinfo import ZoneInfo
from pydantic import BaseModel, field_validator, model_validator

IST = ZoneInfo("Asia/Kolkata")

import re as _re

_BAD_PATH_CHARS = _re.compile(r"[\x00-\x1f\x7f\\?#%]")
MAX_COMMIT_MESSAGE = 2000
MAX_FILE_CONTENT = 500_000
MAX_JOB_FILES = 50
MAX_CUSTOM_DATES = 400


def validate_folder_path(v):
    if v is None:
        return v
    if v.startswith("/") or ".." in v or len(v) > 300 or _BAD_PATH_CHARS.search(v):
        raise ValueError("folder_path is invalid")
    v = v.strip("/")
    if v and any(seg in ("", ".") for seg in v.split("/")):
        raise ValueError("folder_path is invalid")
    return v


def validate_file_name(v):
    if v is None or v == "":
        return v
    if v == "." or ".." in v or "/" in v or len(v) > 255 or _BAD_PATH_CHARS.search(v):
        raise ValueError("file_name is invalid")
    return v


def validate_branch(v):
    if v is None:
        return v
    if not v or v.startswith("/") or v.endswith("/") or ".." in v or "//" in v or " " in v or len(v) > 255 or _BAD_PATH_CHARS.search(v):
        raise ValueError("branch is invalid")
    return v


def validate_commit_message(v):
    if v is not None and (len(v) > MAX_COMMIT_MESSAGE or "\x00" in v):
        raise ValueError("commit_message is invalid")
    return v


def validate_content(v):
    if v is not None and len(v) > MAX_FILE_CONTENT:
        raise ValueError("content is too large")
    return v


def validate_custom_dates(v):
    if v is not None and len(v) > MAX_CUSTOM_DATES:
        raise ValueError("too many custom_dates")
    return v


def validate_files(v):
    if v is not None and len(v) > MAX_JOB_FILES:
        raise ValueError("too many files")
    return v

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
        return validate_folder_path(v)

    @field_validator("file_name")
    @classmethod
    def no_slashes_file(cls, v):
        return validate_file_name(v)

    @field_validator("content")
    @classmethod
    def content_size(cls, v):
        return validate_content(v)


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
        return validate_folder_path(v)

    @field_validator("file_name")
    @classmethod
    def no_slashes_in_filename(cls, v):
        return validate_file_name(v)

    @field_validator("execution_at")
    @classmethod
    def execution_at_must_be_future(cls, v):
        if v is None:
            return v
        exec_at = v if v.tzinfo else v.replace(tzinfo=IST)
        if exec_at <= datetime.now(IST):
            raise ValueError("execution_at must be in the future")
        return v

    @field_validator("commit_message")
    @classmethod
    def create_commit_message_ok(cls, v):
        return validate_commit_message(v)

    @field_validator("file_content")
    @classmethod
    def create_file_content_ok(cls, v):
        return validate_content(v)

    @field_validator("files")
    @classmethod
    def create_files_ok(cls, v):
        return validate_files(v)

    @field_validator("custom_dates")
    @classmethod
    def create_custom_dates_ok(cls, v):
        return validate_custom_dates(v)

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

    @field_validator("folder_path")
    @classmethod
    def update_folder_path_ok(cls, v):
        return validate_folder_path(v)

    @field_validator("file_name")
    @classmethod
    def update_file_name_ok(cls, v):
        return validate_file_name(v)

    @field_validator("branch")
    @classmethod
    def update_branch_ok(cls, v):
        return validate_branch(v)

    @field_validator("commit_message")
    @classmethod
    def update_commit_message_ok(cls, v):
        return validate_commit_message(v)

    @field_validator("file_content")
    @classmethod
    def update_file_content_ok(cls, v):
        return validate_content(v)

    @field_validator("custom_dates")
    @classmethod
    def update_custom_dates_ok(cls, v):
        return validate_custom_dates(v)


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
