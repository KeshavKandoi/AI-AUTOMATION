"""
Business logic for Open Source discovery. Same design as pull_requests:
GitHub is the sole source of truth, nothing is persisted locally. Curation
comes from query construction, not from a database.
"""
from typing import Optional
from fastapi import HTTPException

import github_client as gh
from closeout import _resolve_access_token
from audit_logs.service import log_event

MODULE = "open_source"


def _get_token(organization_id: str) -> str:
    try:
        return _resolve_access_token(organization_id, "github")
    except RuntimeError:
        raise HTTPException(status_code=400, detail="No connected GitHub integration for this organization")


def _author(user: Optional[dict]) -> dict:
    if not user:
        return {"login": "unknown", "avatar_url": None}
    return {"login": user.get("login", "unknown"), "avatar_url": user.get("avatar_url")}


def _issue_summary(item: dict) -> dict:
    # Search API items carry repository_url like https://api.github.com/repos/{owner}/{repo}
    repo_full_name = item["repository_url"].split("/repos/")[-1]
    return {
        "repo_full_name": repo_full_name,
        "number": item["number"],
        "title": item["title"],
        "html_url": item["html_url"],
        "state": item["state"],
        "labels": [l.get("name") for l in item.get("labels", [])],
        "comments_count": item.get("comments", 0),
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
        "author": _author(item.get("user")),
    }


def _build_issue_query(
    language: Optional[str],
    label: Optional[str],
    unassigned_only: bool,
    search: Optional[str],
) -> str:
    parts = ["is:issue", "is:open"]
    if unassigned_only:
        parts.append("no:assignee")
    if language:
        parts.append(f"language:{language}")
    if label:
        # Quote multi-word labels like "good first issue"
        parts.append(f'label:"{label}"' if " " in label else f"label:{label}")
    if search:
        parts.append(search)
    return " ".join(parts)


async def list_issues(
    organization_id: str,
    language: Optional[str] = None,
    label: Optional[str] = None,
    unassigned_only: bool = True,
    search: Optional[str] = None,
    sort: str = "updated",
    page: int = 1,
    per_page: int = 30,
) -> dict:
    access_token = _get_token(organization_id)
    query = _build_issue_query(language, label, unassigned_only, search)

    try:
        result = await gh.search_issues(access_token, query, sort=sort, per_page=per_page, page=page)
    except gh.GitHubRateLimitError as e:
        raise HTTPException(status_code=429, detail=e.message)
    except gh.GitHubAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    # Search API's is:issue still returns items with a `pull_request` key for
    # actual PRs in rare edge cases — filter those out defensively so this
    # stays issue-only, distinct from the Pull Requests module.
    items = [_issue_summary(item) for item in result.get("items", []) if "pull_request" not in item]
    return {"items": items, "total_count": result.get("total_count", 0), "page": page, "per_page": per_page}


def _repo_summary(repo: dict) -> dict:
    return {
        "full_name": repo["full_name"],
        "name": repo["name"],
        "description": repo.get("description"),
        "html_url": repo["html_url"],
        "language": repo.get("language"),
        "topics": repo.get("topics", []),
        "stargazers_count": repo.get("stargazers_count", 0),
        "open_issues_count": repo.get("open_issues_count", 0),
        "default_branch": repo.get("default_branch", "main"),
        "updated_at": repo["updated_at"],
    }


def _build_repo_query(language: Optional[str], topic: Optional[str], search: Optional[str]) -> str:
    parts = []
    if language:
        parts.append(f"language:{language}")
    if topic:
        parts.append(f"topic:{topic}")
    if search:
        parts.append(search)
    if not parts:
        # Search API requires a non-empty query — fall back to a broad,
        # reasonable default rather than erroring on an empty discovery load.
        parts.append("stars:>100")
    return " ".join(parts)


async def list_repositories(
    organization_id: str,
    language: Optional[str] = None,
    topic: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = "stars",
    page: int = 1,
    per_page: int = 30,
) -> dict:
    access_token = _get_token(organization_id)
    query = _build_repo_query(language, topic, search)

    try:
        result = await gh.search_repositories(access_token, query, sort=sort, per_page=per_page, page=page)
    except gh.GitHubRateLimitError as e:
        raise HTTPException(status_code=429, detail=e.message)
    except gh.GitHubAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    items = [_repo_summary(r) for r in result.get("items", [])]
    return {"items": items, "total_count": result.get("total_count", 0), "page": page, "per_page": per_page}


async def get_repository_detail(organization_id: str, repo_full_name: str) -> dict:
    access_token = _get_token(organization_id)
    try:
        repo = await gh.get_repository(access_token, repo_full_name)
    except gh.GitHubRateLimitError as e:
        raise HTTPException(status_code=429, detail=e.message)
    except gh.GitHubAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    base = _repo_summary(repo)
    return {
        **base,
        "forks_count": repo.get("forks_count", 0),
        "license_name": (repo.get("license") or {}).get("name"),
        "homepage": repo.get("homepage"),
    }


async def get_issue_detail(organization_id: str, repo_full_name: str, issue_number: int) -> dict:
    access_token = _get_token(organization_id)
    try:
        issue = await gh.get_issue(access_token, repo_full_name, issue_number)
        comments = await gh.list_issue_comments(access_token, repo_full_name, issue_number)
    except gh.GitHubRateLimitError as e:
        raise HTTPException(status_code=429, detail=e.message)
    except gh.GitHubAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    if "pull_request" in issue:
        raise HTTPException(status_code=400, detail="This number refers to a pull request, not an issue. Use the Pull Requests workspace instead.")

    return {
        "repo_full_name": repo_full_name,
        "number": issue["number"],
        "title": issue["title"],
        "body": issue.get("body"),
        "html_url": issue["html_url"],
        "state": issue["state"],
        "labels": [l.get("name") for l in issue.get("labels", [])],
        "author": _author(issue.get("user")),
        "assignee": _author(issue["assignee"]) if issue.get("assignee") else None,
        "comments_count": issue.get("comments", 0),
        "created_at": issue["created_at"],
        "updated_at": issue["updated_at"],
        "comments": [
            {
                "id": c["id"],
                "author": _author(c.get("user")),
                "body": c.get("body", ""),
                "created_at": c["created_at"],
            }
            for c in comments
        ],
    }


def record_opportunity_selected(
    organization_id: str,
    resource_type: str,
    repo_full_name: str,
    issue_number: Optional[int],
    title: Optional[str],
) -> None:
    """Called when the user clicks 'Work on this' and is handed off to the
    Commit Scheduler form — the one meaningful Open Source action worth an
    audit entry, per the same restraint the PR module uses (no logging on
    passive search/list requests)."""
    resource_id = f"{repo_full_name}#{issue_number}" if issue_number else repo_full_name
    log_event(
        organization_id=organization_id,
        module=MODULE,
        action="opportunity_selected",
        summary=f"Selected {resource_type} for contribution: {title or repo_full_name}",
        status="info",
        resource_type=resource_type,
        resource_id=resource_id,
        metadata={"repo_full_name": repo_full_name, "issue_number": issue_number},
        source="backend",
    )
