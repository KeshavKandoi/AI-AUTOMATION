from typing import Optional
from fastapi import APIRouter, Query
from memory import service
from memory.schemas import MemoryCreate, MemoryUpdate, MemoryListResponse, MemoryOut

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("")
def create_memory(payload: MemoryCreate):
    memory = service.create_memory(payload)
    return {"status": "created", "memory": memory}


@router.get("", response_model=MemoryListResponse)
def list_memories(
    org_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    status: Optional[str] = None,
    importance: Optional[str] = None,
    pinned: Optional[bool] = None,
    favorited: Optional[bool] = None,
    tags: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    items, total = service.list_memories_for_org(
        organization_id=org_id,
        limit=limit,
        offset=offset,
        category=category,
        status=status,
        importance=importance,
        pinned=pinned,
        favorited=favorited,
        tags=tag_list,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/filters")
def get_filter_options(org_id: str):
    return service.list_filter_options(org_id)


@router.get("/recent")
def get_recent_memories(org_id: str, limit: int = Query(5, ge=1, le=20)):
    return service.recent_memories_for_org(org_id, limit)


@router.get("/{memory_id}", response_model=MemoryOut)
def get_memory(memory_id: str, org_id: str):
    return service.get_memory_or_404(memory_id, org_id)


@router.patch("/{memory_id}")
def update_memory(memory_id: str, org_id: str, payload: MemoryUpdate):
    memory = service.update_memory(memory_id, org_id, payload)
    return {"status": "updated", "memory": memory}


@router.post("/{memory_id}/access")
def access_memory(memory_id: str, org_id: str):
    memory = service.access_memory(memory_id, org_id)
    return {"status": "accessed", "memory": memory}


@router.post("/{memory_id}/pin")
def pin_memory(memory_id: str, org_id: str):
    memory = service.set_pinned(memory_id, org_id, True)
    return {"status": "pinned", "memory": memory}


@router.post("/{memory_id}/unpin")
def unpin_memory(memory_id: str, org_id: str):
    memory = service.set_pinned(memory_id, org_id, False)
    return {"status": "unpinned", "memory": memory}


@router.post("/{memory_id}/favorite")
def favorite_memory(memory_id: str, org_id: str):
    memory = service.set_favorited(memory_id, org_id, True)
    return {"status": "favorited", "memory": memory}


@router.post("/{memory_id}/unfavorite")
def unfavorite_memory(memory_id: str, org_id: str):
    memory = service.set_favorited(memory_id, org_id, False)
    return {"status": "unfavorited", "memory": memory}


@router.post("/{memory_id}/archive")
def archive_memory(memory_id: str, org_id: str):
    memory = service.archive_memory(memory_id, org_id)
    return {"status": "archived", "memory": memory}


@router.post("/{memory_id}/restore")
def restore_memory(memory_id: str, org_id: str):
    memory = service.restore_memory(memory_id, org_id)
    return {"status": "restored", "memory": memory}


@router.delete("/{memory_id}")
def delete_memory(memory_id: str, org_id: str):
    service.delete_memory(memory_id, org_id)
    return {"status": "deleted", "memory_id": memory_id}
