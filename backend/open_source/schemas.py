from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel

IssueSort = Literal["updated", "created", "comments"]
RepoSort = Literal["stars", "updated", "forks"]


class OSAuthor(BaseModel):
    login: str
    avatar_url: Optional[str] = None


class OSIssueSummary(BaseModel):
    repo_full_name: str
    number: int
    title: str
    html_url: str
    state: str
    labels: list[str] = []
    comments_count: int = 0
    created_at: datetime
    updated_at: datetime
    author: OSAuthor


class OSIssueListResponse(BaseModel):
    items: list[OSIssueSummary]
    total_count: int
    page: int
    per_page: int


class OSIssueDetail(BaseModel):
    repo_full_name: str
    number: int
    title: str
    body: Optional[str] = None
    html_url: str
    state: str
    labels: list[str] = []
    author: OSAuthor
    assignee: Optional[OSAuthor] = None
    comments_count: int = 0
    created_at: datetime
    updated_at: datetime
    comments: list[dict] = []


class OSRepoSummary(BaseModel):
    full_name: str
    name: str
    description: Optional[str] = None
    html_url: str
    language: Optional[str] = None
    topics: list[str] = []
    stargazers_count: int = 0
    open_issues_count: int = 0
    default_branch: str
    updated_at: datetime


class OSRepoListResponse(BaseModel):
    items: list[OSRepoSummary]
    total_count: int
    page: int
    per_page: int


class OSRepoDetail(OSRepoSummary):
    forks_count: int = 0
    license_name: Optional[str] = None
    homepage: Optional[str] = None


class OpportunitySelectedRequest(BaseModel):
    organization_id: str
    resource_type: Literal["issue", "repository"]
    repo_full_name: str
    issue_number: Optional[int] = None
    title: Optional[str] = None
