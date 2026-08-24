from typing import Optional
from fastapi import APIRouter, Query, Depends
from pull_requests import service
from pull_requests.schemas import (
    PRListResponse, PRDetail, PRActionRequest, PRMergeRequest, PRSummarizeResponse, PRView,
)
from auth.dependencies import get_current_org_id

router = APIRouter(prefix="/pull-requests", tags=["pull-requests"])


@router.get("", response_model=PRListResponse)
async def list_pull_requests(
    org_id: str = Depends(get_current_org_id),
    view: PRView = "all",
    repo: Optional[str] = None,
    author: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
):
    return await service.list_pull_requests(org_id, view, repo, author, search, page, per_page)


@router.get("/{owner}/{repo}/{pr_number}", response_model=PRDetail)
async def get_pull_request(owner: str, repo: str, pr_number: int, org_id: str = Depends(get_current_org_id)):
    return await service.get_pull_request_detail(org_id, f"{owner}/{repo}", pr_number)


@router.get("/{owner}/{repo}/{pr_number}/summary", response_model=PRSummarizeResponse)
async def summarize_pull_request(owner: str, repo: str, pr_number: int, org_id: str = Depends(get_current_org_id)):
    summary = await service.summarize_pull_request(org_id, f"{owner}/{repo}", pr_number)
    return {"summary": summary}


@router.post("/{owner}/{repo}/{pr_number}/approve")
async def approve_pull_request(owner: str, repo: str, pr_number: int, payload: PRActionRequest, org_id: str = Depends(get_current_org_id)):
    result = await service.approve_pull_request(org_id, f"{owner}/{repo}", pr_number, payload.body)
    return {"status": "approved", "result": result}


@router.post("/{owner}/{repo}/{pr_number}/request-changes")
async def request_changes(owner: str, repo: str, pr_number: int, payload: PRActionRequest, org_id: str = Depends(get_current_org_id)):
    result = await service.request_changes_on_pull_request(org_id, f"{owner}/{repo}", pr_number, payload.body or "")
    return {"status": "changes_requested", "result": result}


@router.post("/{owner}/{repo}/{pr_number}/comment")
async def comment_on_pull_request(owner: str, repo: str, pr_number: int, payload: PRActionRequest, org_id: str = Depends(get_current_org_id)):
    result = await service.comment_on_pull_request(org_id, f"{owner}/{repo}", pr_number, payload.body or "")
    return {"status": "commented", "result": result}


@router.post("/{owner}/{repo}/{pr_number}/merge")
async def merge_pull_request(owner: str, repo: str, pr_number: int, payload: PRMergeRequest, org_id: str = Depends(get_current_org_id)):
    result = await service.merge_pull_request(org_id, f"{owner}/{repo}", pr_number, payload.merge_method)
    return {"status": "merged", "result": result}


@router.post("/{owner}/{repo}/{pr_number}/close")
async def close_pull_request(owner: str, repo: str, pr_number: int, org_id: str = Depends(get_current_org_id)):
    result = await service.close_pull_request(org_id, f"{owner}/{repo}", pr_number)
    return {"status": "closed", "result": result}
