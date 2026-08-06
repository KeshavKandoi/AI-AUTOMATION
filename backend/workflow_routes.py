from fastapi import APIRouter, HTTPException
from config import supabase_admin
from workflow_schemas import WorkflowCreate, WorkflowUpdate
from workflow_engine import execute_workflow, sample_context_for_trigger

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("")
def create_workflow(payload: WorkflowCreate):
    result = supabase_admin.table("workflows").insert(payload.model_dump()).execute()
    return {"status": "created", "workflow": result.data[0]}


@router.get("")
def list_workflows(org_id: str):
    result = supabase_admin.table("workflows").select("*").eq("organization_id", org_id).execute()
    return result.data


@router.get("/{workflow_id}")
def get_workflow(workflow_id: str, org_id: str):
    result = supabase_admin.table("workflows").select("*").eq("id", workflow_id).execute()
    if not result.data or result.data[0]["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    runs = supabase_admin.table("workflow_runs") \
        .select("*").eq("workflow_id", workflow_id) \
        .order("executed_at", desc=True).limit(20).execute()

    return {**result.data[0], "recent_runs": runs.data}


@router.patch("/{workflow_id}")
def update_workflow(workflow_id: str, org_id: str, payload: WorkflowUpdate):
    existing = supabase_admin.table("workflows").select("*").eq("id", workflow_id).execute()
    if not existing.data or existing.data[0]["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    result = supabase_admin.table("workflows").update(updates).eq("id", workflow_id).execute()
    return {"status": "updated", "workflow": result.data[0]}


@router.delete("/{workflow_id}")
def delete_workflow(workflow_id: str, org_id: str):
    existing = supabase_admin.table("workflows").select("*").eq("id", workflow_id).execute()
    if not existing.data or existing.data[0]["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    supabase_admin.table("workflows").delete().eq("id", workflow_id).execute()
    return {"status": "deleted", "workflow_id": workflow_id}


@router.post("/{workflow_id}/run-now")
async def run_workflow_now(workflow_id: str, org_id: str, context_override: dict | None = None):
    existing = supabase_admin.table("workflows").select("*").eq("id", workflow_id).execute()
    if not existing.data or existing.data[0]["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow = existing.data[0]
    context = sample_context_for_trigger(workflow["trigger_type"])
    if context_override:
        context.update(context_override)
    run = await execute_workflow(workflow, context, record_skipped=True)
    return {"status": "triggered", "run": run}
