from typing import Optional
from fastapi import APIRouter, Query
from open_source import service
from open_source.schemas import (
    OSIssueListResponse, OSIssueDetail, OSRepoListResponse, OSRepoDetail,
    OpportunitySelectedRequest,
)

router = APIRouter(prefix="/open-source", tags=["open-source"])


@router.get("/issues", response_model=OSIssueListResponse)
async def list_issues(
    org_id: str,
    language: Optional[str] = None,
    label: Optional[str] = None,
    unassigned_only: bool = True,
    search: Optional[str] = None,
    sort: str = "updated",
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
):
    return await service.list_issues(org_id, language, label, unassigned_only, search, sort, page, per_page)


@router.get("/issues/{owner}/{repo}/{issue_number}", response_model=OSIssueDetail)
async def get_issue(owner: str, repo: str, issue_number: int, org_id: str):
    return await service.get_issue_detail(org_id, f"{owner}/{repo}", issue_number)


@router.get("/repositories", response_model=OSRepoListResponse)
async def list_repositories(
    org_id: str,
    language: Optional[str] = None,
    topic: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = "stars",
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
):
    return await service.list_repositories(org_id, language, topic, search, sort, page, per_page)


@router.get("/repositories/{owner}/{repo}", response_model=OSRepoDetail)
async def get_repository(owner: str, repo: str, org_id: str):
    return await service.get_repository_detail(org_id, f"{owner}/{repo}")


@router.post("/opportunity-selected")
def opportunity_selected(payload: OpportunitySelectedRequest):
    service.record_opportunity_selected(
        payload.organization_id, payload.resource_type, payload.repo_full_name,
        payload.issue_number, payload.title,
    )
    return {"status": "recorded"}
