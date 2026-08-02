from typing import Optional, Literal
from pydantic import BaseModel, field_validator

TriggerType = Literal["issue_created", "pr_opened", "push"]
ActionName = Literal["create_task", "send_email", "notify_discord", "create_calendar_event", "save_audit_log"]

class WorkflowCreate(BaseModel):
    organization_id: str
    name: str
    trigger_type: TriggerType
    conditions: dict = {}
    actions: list[ActionName]

    @field_validator("actions")
    @classmethod
    def actions_not_empty(cls, v):
        if not v:
            raise ValueError("actions must contain at least one action")
        return v

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    conditions: Optional[dict] = None
    actions: Optional[list[ActionName]] = None
    status: Optional[Literal["active", "paused"]] = None
