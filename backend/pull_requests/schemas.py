from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel

PRView = Literal[
    "all", "mine", "in_my_repos", "needs_review",
    "waiting_review", "changes_requested", "approved", "merged", "closed",
]


class PRAuthor(BaseModel):
    login: str
    avatar_url: Optional[str] = None


class PRSummary(BaseModel):
    repo_full_name: str
    number: int
    title: str
    author: PRAuthor
    state: str            # "open" | "closed"
    is_draft: bool
    is_merged: bool
    html_url: str
    base_branch: Optional[str] = None
    head_branch: Optional[str] = None
    labels: list[str] = []
    comments_count: int = 0
    created_at: datetime
    updated_at: datetime


class PRListResponse(BaseModel):
    items: list[PRSummary]
    total_count: int
    page: int
    per_page: int


class PRReview(BaseModel):
    id: int
    author: PRAuthor
    state: str   # "APPROVED" | "CHANGES_REQUESTED" | "COMMENTED" | "DISMISSED" | "PENDING"
    body: Optional[str] = None
    submitted_at: Optional[datetime] = None


class PRComment(BaseModel):
    id: int
    author: PRAuthor
    body: str
    created_at: datetime
    path: Optional[str] = None   # set for inline review comments, None for general issue comments


class PRCommit(BaseModel):
    sha: str
    message: str
    author_name: Optional[str] = None
    authored_at: Optional[datetime] = None


class PRFile(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int


class PRCheckRun(BaseModel):
    name: str
    status: str          # "queued" | "in_progress" | "completed"
    conclusion: Optional[str] = None   # "success" | "failure" | "neutral" | ... (only when completed)
    html_url: Optional[str] = None


class PRDetail(BaseModel):
    repo_full_name: str
    number: int
    title: str
    body: Optional[str] = None
    author: PRAuthor
    state: str
    is_draft: bool
    is_merged: bool
    mergeable: Optional[bool] = None
    mergeable_state: Optional[str] = None
    html_url: str
    base_branch: str
    head_branch: str
    additions: int
    deletions: int
    changed_files: int
    commits_count: int
    labels: list[str] = []
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime] = None
    reviews: list[PRReview] = []
    comments: list[PRComment] = []
    commits: list[PRCommit] = []
    files: list[PRFile] = []
    checks: list[PRCheckRun] = []
    review_decision: str   # "approved" | "changes_requested" | "review_required" | "none"


class PRActionRequest(BaseModel):
    body: Optional[str] = None


class PRMergeRequest(BaseModel):
    merge_method: Literal["merge", "squash", "rebase"] = "merge"


class PRSummarizeResponse(BaseModel):
    summary: str
