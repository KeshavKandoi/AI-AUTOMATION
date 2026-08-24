from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from config import supabase_admin
from workflow_schemas import WorkflowCreate, WorkflowUpdate
from workflow_engine import execute_workflow, sample_context_for_trigger, _is_past_expiry
from auth.dependencies import get_current_org_id

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("")
def create_workflow(payload: WorkflowCreate, org_id: str = Depends(get_current_org_id)):
    data = payload.model_dump()
    data["organization_id"] = org_id
    if data.get("expires_at"):
        data["expires_at"] = data["expires_at"].isoformat()
    result = supabase_admin.table("workflows").insert(data).execute()
    return {"status": "created", "workflow": result.data[0]}


@router.get("")
def list_workflows(org_id: str = Depends(get_current_org_id)):
    result = supabase_admin.table("workflows").select("*").eq("organization_id", org_id).execute()
    return result.data


@router.get("/{workflow_id}")
def get_workflow(workflow_id: str, org_id: str = Depends(get_current_org_id)):
    result = supabase_admin.table("workflows").select("*").eq("id", workflow_id).execute()
    if not result.data or result.data[0]["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    runs = supabase_admin.table("workflow_runs") \
        .select("*").eq("workflow_id", workflow_id) \
        .order("executed_at", desc=True).limit(20).execute()

    return {**result.data[0], "recent_runs": runs.data}


@router.patch("/{workflow_id}")
def update_workflow(workflow_id: str, payload: WorkflowUpdate, org_id: str = Depends(get_current_org_id)):
    existing = supabase_admin.table("workflows").select("*").eq("id", workflow_id).execute()
    if not existing.data or existing.data[0]["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    current = existing.data[0]

    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    # Validate the *merged* lifetime configuration, since a PATCH may only
    # touch one of lifetime_mode / expires_at while the other stays as-is.
    merged_mode = updates.get("lifetime_mode", current.get("lifetime_mode", "continuous"))
    merged_expires_raw = updates.get("expires_at", current.get("expires_at"))
    if merged_mode == "until_date":
        if not merged_expires_raw:
            raise HTTPException(status_code=400, detail="expires_at is required when lifetime_mode is 'until_date'")
        merged_expires = merged_expires_raw if isinstance(merged_expires_raw, datetime) else datetime.fromisoformat(str(merged_expires_raw).replace("Z", "+00:00"))
        if merged_expires.tzinfo is None:
            merged_expires = merged_expires.replace(tzinfo=timezone.utc)
        if merged_expires <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="expires_at must be in the future")
    elif "lifetime_mode" in updates:
        # Switching away from until_date clears any stale expiry date.
        updates["expires_at"] = None

    if "expires_at" in updates and updates["expires_at"] is not None:
        updates["expires_at"] = updates["expires_at"].isoformat()

    result = supabase_admin.table("workflows").update(updates).eq("id", workflow_id).execute()
    return {"status": "updated", "workflow": result.data[0]}


@router.delete("/{workflow_id}")
def delete_workflow(workflow_id: str, org_id: str = Depends(get_current_org_id)):
    existing = supabase_admin.table("workflows").select("*").eq("id", workflow_id).execute()
    if not existing.data or existing.data[0]["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    supabase_admin.table("workflows").delete().eq("id", workflow_id).execute()
    return {"status": "deleted", "workflow_id": workflow_id}


@router.post("/{workflow_id}/run-now")
async def run_workflow_now(workflow_id: str, context_override: dict | None = None, org_id: str = Depends(get_current_org_id)):
    existing = supabase_admin.table("workflows").select("*").eq("id", workflow_id).execute()
    if not existing.data or existing.data[0]["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow = existing.data[0]

    if workflow["status"] in ("completed", "expired"):
        raise HTTPException(status_code=409, detail=f"Workflow is {workflow['status']} and can no longer run")

    if _is_past_expiry(workflow):
        supabase_admin.table("workflows").update({"status": "expired"}).eq("id", workflow_id).execute()
        raise HTTPException(status_code=409, detail="Workflow has expired and can no longer run")

    context = sample_context_for_trigger(workflow["trigger_type"])
    if context_override:
        context.update(context_override)
    run = await execute_workflow(workflow, context, record_skipped=True)
    return {"status": "triggered", "run": run}
