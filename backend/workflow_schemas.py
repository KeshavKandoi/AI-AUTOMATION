import json
from typing import Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, field_validator, model_validator

TriggerType = Literal["issue_created", "push", "pull_request_opened"]
ActionName = Literal["create_task", "send_email", "notify_discord", "create_calendar_event", "save_audit_log"]
LifetimeMode = Literal["continuous", "run_once", "until_date"]

MAX_WORKFLOW_ACTIONS = 10
MAX_WORKFLOW_NAME_LENGTH = 200
MAX_CONDITIONS_JSON_CHARS = 10000
MAX_CONDITION_RULES = 20


def _check_name(v):
    if v is None:
        return v
    v = v.strip()
    if not v or len(v) > MAX_WORKFLOW_NAME_LENGTH:
        raise ValueError(f"name must be 1-{MAX_WORKFLOW_NAME_LENGTH} characters")
    return v


def _check_conditions(v):
    if v is None:
        return v
    if len(json.dumps(v, default=str)) > MAX_CONDITIONS_JSON_CHARS:
        raise ValueError("conditions are too large")
    rules = v.get("rules")
    if isinstance(rules, list) and len(rules) > MAX_CONDITION_RULES:
        raise ValueError(f"conditions may contain at most {MAX_CONDITION_RULES} rules")
    return v


def _check_actions_size(v):
    if v is not None and len(v) > MAX_WORKFLOW_ACTIONS:
        raise ValueError(f"a workflow may contain at most {MAX_WORKFLOW_ACTIONS} actions")
    return v

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
        return _check_actions_size(v)

    @field_validator("name")
    @classmethod
    def name_valid(cls, v):
        return _check_name(v)

    @field_validator("conditions")
    @classmethod
    def conditions_valid(cls, v):
        return _check_conditions(v)

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

    @field_validator("name")
    @classmethod
    def name_valid(cls, v):
        return _check_name(v)

    @field_validator("conditions")
    @classmethod
    def conditions_valid(cls, v):
        return _check_conditions(v)

    @field_validator("actions")
    @classmethod
    def actions_valid(cls, v):
        return _check_actions_size(v)
