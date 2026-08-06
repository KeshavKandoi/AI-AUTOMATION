"""
Backward-compatible shim. All existing call sites use log_action(org_id, action, details).
New code should call audit_logs.service.log_event(...) directly for richer fields
(module, status, resource_type, resource_id, summary). This wrapper infers a
best-effort module from the action name and keeps everything else working
unchanged during the migration.
"""
from typing import Optional
from audit_logs.service import log_event

# Maps legacy action prefixes to a module name, so old call sites still land
# in a sensible module bucket on the Audit Logs page without being touched.
_MODULE_HINTS = {
    "task_": "tasks",
    "github_": "github",
    "email_": "gmail",
    "calendar_": "calendar",
    "workflow_": "workflows",
    "closeout_": "tasks",
    "missed_event_": "calendar",
    "gmail_": "gmail",
}


def _infer_module(action: str) -> str:
    for prefix, module in _MODULE_HINTS.items():
        if action.startswith(prefix):
            return module
    return "system"


def _infer_status(action: str) -> str:
    if "fail" in action:
        return "failed"
    if "reject" in action:
        return "warning"
    return "info"


def log_action(organization_id: str, action: str, details: Optional[dict] = None):
    log_event(
        organization_id=organization_id,
        module=_infer_module(action),
        action=action,
        summary=action.replace("_", " ").capitalize(),
        status=_infer_status(action),
        metadata=details or {},
        source="backend",
    )
