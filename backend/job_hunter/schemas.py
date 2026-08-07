from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, field_validator

ExperienceLevel = Literal["student", "fresher", "experienced"]
ApplicationStatus = Literal[
    "saved", "applied", "assessment", "interview",
    "hr_round", "technical_round", "final_round",
    "offer", "rejected", "archived",
]
AttachmentType = Literal[
    "resume", "cover_letter", "assignment", "interview_notes", "offer_letter", "other",
]
ActivitySource = Literal["user", "gmail", "system"]
ReminderStatus = Literal["pending", "notified", "dismissed"]


# ---------------------------------------------------------------------------
# Preferences (onboarding)
# ---------------------------------------------------------------------------

class ProjectHighlight(BaseModel):
    title: str
    description: str


class JobHunterPreferencesCreate(BaseModel):
    full_name: str
    email: str

    experience_level: ExperienceLevel
    years_of_experience: Optional[float] = None
    current_designation: Optional[str] = None
    current_company: Optional[str] = None

    employment_types: list[str] = []   # Internship, Full-time, Part-time, Contract, Freelance
    work_modes: list[str] = []         # Remote, Hybrid, Onsite

    desired_roles: list[str] = []
    skills: list[str] = []
    project_highlights: list[ProjectHighlight] = []

    preferred_locations: list[str] = []

    expected_salary_min: Optional[float] = None
    expected_salary_max: Optional[float] = None
    salary_currency: Optional[str] = "INR"

    @field_validator("desired_roles", "skills", "preferred_locations")
    @classmethod
    def must_have_at_least_one(cls, v, info):
        if not v:
            raise ValueError(f"{info.field_name} must have at least one entry")
        return v

    @field_validator("employment_types", "work_modes")
    @classmethod
    def must_pick_at_least_one(cls, v, info):
        if not v:
            raise ValueError(f"{info.field_name} must have at least one selection")
        return v


class JobHunterPreferencesUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    experience_level: Optional[ExperienceLevel] = None
    years_of_experience: Optional[float] = None
    current_designation: Optional[str] = None
    current_company: Optional[str] = None
    employment_types: Optional[list[str]] = None
    work_modes: Optional[list[str]] = None
    desired_roles: Optional[list[str]] = None
    skills: Optional[list[str]] = None
    project_highlights: Optional[list[ProjectHighlight]] = None
    preferred_locations: Optional[list[str]] = None
    expected_salary_min: Optional[float] = None
    expected_salary_max: Optional[float] = None
    salary_currency: Optional[str] = None


class JobHunterPreferencesOut(BaseModel):
    id: str
    organization_id: str
    full_name: str
    email: str
    experience_level: str
    years_of_experience: Optional[float] = None
    current_designation: Optional[str] = None
    current_company: Optional[str] = None
    employment_types: list[str]
    work_modes: list[str]
    desired_roles: list[str]
    skills: list[str]
    project_highlights: list[dict]
    preferred_locations: list[str]
    expected_salary_min: Optional[float] = None
    expected_salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    onboarding_completed: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Jobs (discovered listings)
# ---------------------------------------------------------------------------

class JobSourceOut(BaseModel):
    id: str
    job_id: str
    platform: str
    platform_job_id: Optional[str] = None
    platform_url: str
    discovered_at: datetime


class JobOut(BaseModel):
    id: str
    organization_id: str
    company_name: str
    job_title: str
    location: Optional[str] = None
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    experience_required: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    required_skills: list[str] = []
    qualifications: Optional[str] = None
    benefits: Optional[str] = None
    company_info: Optional[str] = None
    original_apply_url: str
    posted_at: Optional[datetime] = None
    first_discovered_at: datetime
    last_seen_at: datetime
    sources: list[JobSourceOut] = []


# ---------------------------------------------------------------------------
# Applications (tracking)
# ---------------------------------------------------------------------------

class ApplicationCreate(BaseModel):
    job_id: str
    status: ApplicationStatus = "saved"


class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None


class ActivityCreate(BaseModel):
    event_type: str
    summary: str
    metadata: dict = {}
    source: ActivitySource = "user"


class ActivityOut(BaseModel):
    id: str
    application_id: str
    event_type: str
    summary: str
    metadata: dict
    source: str
    created_at: datetime


class NoteCreate(BaseModel):
    content: str


class NoteOut(BaseModel):
    id: str
    application_id: str
    content: str
    created_at: datetime
    updated_at: datetime


class AttachmentCreate(BaseModel):
    file_name: str
    storage_path: str
    file_type: AttachmentType
    size_bytes: Optional[int] = None


class AttachmentOut(BaseModel):
    id: str
    application_id: str
    file_name: str
    storage_path: str
    file_type: str
    size_bytes: Optional[int] = None
    created_at: datetime


class ReminderCreate(BaseModel):
    remind_at: datetime
    note: Optional[str] = None


class ReminderOut(BaseModel):
    id: str
    application_id: str
    organization_id: str
    remind_at: datetime
    note: Optional[str] = None
    status: str
    created_at: datetime


class ApplicationOut(BaseModel):
    id: str
    organization_id: str
    job_id: str
    status: str
    applied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    job: Optional[JobOut] = None
    activity: list[ActivityOut] = []
    notes: list[NoteOut] = []
    attachments: list[AttachmentOut] = []
    reminders: list[ReminderOut] = []
