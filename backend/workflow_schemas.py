from typing import Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, field_validator, model_validator

TriggerType = Literal["issue_created", "push", "pull_request_opened"]
ActionName = Literal["create_task", "send_email", "notify_discord", "create_calendar_event", "save_audit_log"]
LifetimeMode = Literal["continuous", "run_once", "until_date"]

class WorkflowCreate(BaseModel):
    organization_id: str
    name: str
    trigger_type: TriggerType
    conditions: dict = {}
    actions: list[ActionName]
    lifetime_mode: LifetimeMode = "continuous"
    expires_at: Optional[datetime] = None

    @field_validator("actions")
    @classmethod
    def actions_not_empty(cls, v):
        if not v:
            raise ValueError("actions must contain at least one action")
        return v

    @model_validator(mode="after")
    def validate_lifetime(self):
        if self.lifetime_mode == "until_date":
            if not self.expires_at:
                raise ValueError("expires_at is required when lifetime_mode is 'until_date'")
            expires_at = self.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= datetime.now(timezone.utc):
                raise ValueError("expires_at must be in the future")
            self.expires_at = expires_at
        else:
            # Don't let a stale date linger for continuous/run_once workflows.
            self.expires_at = None
        return self

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    conditions: Optional[dict] = None
    actions: Optional[list[ActionName]] = None
    status: Optional[Literal["active", "paused", "completed", "expired"]] = None
    lifetime_mode: Optional[LifetimeMode] = None
    expires_at: Optional[datetime] = None
