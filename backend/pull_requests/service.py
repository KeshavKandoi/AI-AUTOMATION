"""
Business logic for the Pull Requests module. GitHub is the sole source of
truth — there is no local pull_requests table. Every read hits the GitHub
API live via github_client.py; nothing is cached or persisted here.

Org isolation: every function takes organization_id and resolves that org's
own GitHub token via closeout._resolve_access_token — the same mechanism
every other GitHub-touching module in this app already uses. There is no
path by which one org's request can read or act on another org's token.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException

import github_client as gh
from closeout import _resolve_access_token
from config import run_gemini, logger
from audit_logs.service import log_event
from notifications.service import notify

MODULE = "pull_requests"


def _get_token(organization_id: str) -> str:
    try:
        return _resolve_access_token(organization_id, "github")
    except RuntimeError:
        raise HTTPException(status_code=400, detail="No connected GitHub integration for this organization")


async def _get_login(access_token: str) -> str:
    user = await gh.get_current_user(access_token)
    return user["login"]


def _repo_from_search_item(item: dict) -> str:
    # repository_url looks like https://api.github.com/repos/{owner}/{repo}
    return item["repository_url"].split("/repos/")[-1]


def _author(item_user: Optional[dict]) -> dict:
    if not item_user:
        return {"login": "unknown", "avatar_url": None}
    return {"login": item_user.get("login", "unknown"), "avatar_url": item_user.get("avatar_url")}


def _summary_from_search_item(item: dict) -> dict:
    pr_info = item.get("pull_request") or {}
    return {
        "repo_full_name": _repo_from_search_item(item),
        "number": item["number"],
        "title": item["title"],
        "author": _author(item.get("user")),
        "state": item["state"],
        "is_draft": item.get("draft", False),
        "is_merged": pr_info.get("merged_at") is not None,
        "html_url": item["html_url"],
        "base_branch": None,   # not present on search items — only on the full PR object
        "head_branch": None,
        "labels": [l.get("name") for l in item.get("labels", [])],
        "comments_count": item.get("comments", 0),
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
    }


def _build_query(view: str, login: str, repo: Optional[str], author: Optional[str], search: Optional[str]) -> str:
    parts = ["is:pr"]

    view_qualifiers = {
        "all": [f"involves:{login}"],
        "mine": [f"author:{login}"],
        "in_my_repos": [f"user:{login}"],
        "needs_review": [f"review-requested:{login}"],
        "waiting_review": [f"author:{login}", "is:open", "review:none"],
        "changes_requested": [f"involves:{login}", "review:changes_requested"],
        "approved": [f"involves:{login}", "review:approved"],
        "merged": [f"involves:{login}", "is:merged"],
        "closed": [f"involves:{login}", "is:closed", "is:unmerged"],
    }
    parts.extend(view_qualifiers.get(view, [f"involves:{login}"]))

    if repo:
        parts.append(f"repo:{repo}")
    if author:
        parts.append(f"author:{author}")
    if search:
        parts.append(search)

    return " ".join(parts)


async def list_pull_requests(
    organization_id: str,
    view: str = "all",
    repo: Optional[str] = None,
    author: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 30,
) -> dict:
    access_token = _get_token(organization_id)
    login = await _get_login(access_token)
    query = _build_query(view, login, repo, author, search)

    try:
        result = await gh.search_issues(access_token, query, sort="updated", per_page=per_page, page=page)
    except gh.GitHubRateLimitError as e:
        raise HTTPException(status_code=429, detail=e.message)
    except gh.GitHubAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    items = [_summary_from_search_item(item) for item in result.get("items", [])]
    return {"items": items, "total_count": result.get("total_count", 0), "page": page, "per_page": per_page}


def _review_decision(reviews: list[dict]) -> str:
    """Latest review state per reviewer wins (matches GitHub's own decision
    logic) — a reviewer who approves after previously requesting changes
    should count as approved, not stuck on their earlier state."""
    latest_by_reviewer: dict[str, str] = {}
    for r in reviews:
        reviewer = (r.get("user") or {}).get("login")
        state = r.get("state")
        if reviewer and state in ("APPROVED", "CHANGES_REQUESTED", "COMMENTED"):
            latest_by_reviewer[reviewer] = state

    states = list(latest_by_reviewer.values())
    if not states:
        return "none"
    if "CHANGES_REQUESTED" in states:
        return "changes_requested"
    if "APPROVED" in states:
        return "approved"
    return "review_required"


async def get_pull_request_detail(organization_id: str, repo_full_name: str, pr_number: int) -> dict:
    access_token = _get_token(organization_id)

    try:
        pr, reviews, review_comments, issue_comments, commits, files = await asyncio.gather(
            gh.get_pull_request(access_token, repo_full_name, pr_number),
            gh.list_pr_reviews(access_token, repo_full_name, pr_number),
            gh.list_pr_review_comments(access_token, repo_full_name, pr_number),
            gh.list_issue_comments(access_token, repo_full_name, pr_number),
            gh.list_pr_commits(access_token, repo_full_name, pr_number),
            gh.list_pr_files(access_token, repo_full_name, pr_number),
        )
    except gh.GitHubRateLimitError as e:
        raise HTTPException(status_code=429, detail=e.message)
    except gh.GitHubAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    head_sha = pr["head"]["sha"]
    checks: list[dict] = []
    try:
        check_data = await gh.list_check_runs(access_token, repo_full_name, head_sha)
        checks = [
            {
                "name": c["name"],
                "status": c["status"],
                "conclusion": c.get("conclusion"),
                "html_url": c.get("html_url"),
            }
            for c in check_data.get("check_runs", [])
        ]
    except gh.GitHubAPIError:
        # Checks API can 404/403 on repos without Actions/CI configured — not fatal.
        pass

    all_comments = [
        {
            "id": c["id"],
            "author": _author(c.get("user")),
            "body": c.get("body", ""),
            "created_at": c["created_at"],
            "path": c.get("path"),
        }
        for c in (review_comments + issue_comments)
    ]
    all_comments.sort(key=lambda c: c["created_at"])

    return {
        "repo_full_name": repo_full_name,
        "number": pr["number"],
        "title": pr["title"],
        "body": pr.get("body"),
        "author": _author(pr.get("user")),
        "state": pr["state"],
        "is_draft": pr.get("draft", False),
        "is_merged": pr.get("merged", False),
        "mergeable": pr.get("mergeable"),
        "mergeable_state": pr.get("mergeable_state"),
        "html_url": pr["html_url"],
        "base_branch": pr["base"]["ref"],
        "head_branch": pr["head"]["ref"],
        "additions": pr.get("additions", 0),
        "deletions": pr.get("deletions", 0),
        "changed_files": pr.get("changed_files", 0),
        "commits_count": pr.get("commits", 0),
        "labels": [l.get("name") for l in pr.get("labels", [])],
        "created_at": pr["created_at"],
        "updated_at": pr["updated_at"],
        "merged_at": pr.get("merged_at"),
        "reviews": [
            {
                "id": r["id"],
                "author": _author(r.get("user")),
                "state": r["state"],
                "body": r.get("body"),
                "submitted_at": r.get("submitted_at"),
            }
            for r in reviews
        ],
        "comments": all_comments,
        "commits": [
            {
                "sha": c["sha"],
                "message": c["commit"]["message"],
                "author_name": (c["commit"].get("author") or {}).get("name"),
                "authored_at": (c["commit"].get("author") or {}).get("date"),
            }
            for c in commits
        ],
        "files": [
            {
                "filename": f["filename"],
                "status": f["status"],
                "additions": f["additions"],
                "deletions": f["deletions"],
                "changes": f["changes"],
            }
            for f in files
        ],
        "checks": checks,
        "review_decision": _review_decision(reviews),
    }


async def _action_common(organization_id: str, repo_full_name: str, pr_number: int, action: str, status: str, summary: str, error: Optional[str] = None):
    log_event(
        organization_id=organization_id,
        module=MODULE,
        action=action,
        summary=summary,
        status=status,
        resource_type="pull_request",
        resource_id=f"{repo_full_name}#{pr_number}",
        metadata={"repo_full_name": repo_full_name, "pr_number": pr_number},
        error_message=error,
        source="backend",
    )


async def approve_pull_request(organization_id: str, repo_full_name: str, pr_number: int, body: Optional[str]) -> dict:
    access_token = _get_token(organization_id)
    try:
        result = await gh.approve_pull_request(access_token, repo_full_name, pr_number, body)
    except gh.GitHubAPIError as e:
        await _action_common(organization_id, repo_full_name, pr_number, "pr_approve_failed", "failed", f"Failed to approve PR #{pr_number} in {repo_full_name}", error=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)

    await _action_common(organization_id, repo_full_name, pr_number, "pr_approved", "success", f"Approved PR #{pr_number} in {repo_full_name}")
    notify(
        organization_id=organization_id, module=MODULE, category="pr_approved", priority="normal",
        title=f"PR approved: #{pr_number}", body=f"You approved a pull request in {repo_full_name}.",
        resource_type="pull_request", resource_id=f"{repo_full_name}#{pr_number}",
        action_url=f"/pull-requests/{repo_full_name}/{pr_number}", action_label="View PR",
    )
    return result


async def request_changes_on_pull_request(organization_id: str, repo_full_name: str, pr_number: int, body: str) -> dict:
    if not body or not body.strip():
        raise HTTPException(status_code=400, detail="A comment body is required when requesting changes")
    access_token = _get_token(organization_id)
    try:
        result = await gh.request_changes_on_pull_request(access_token, repo_full_name, pr_number, body)
    except gh.GitHubAPIError as e:
        await _action_common(organization_id, repo_full_name, pr_number, "pr_request_changes_failed", "failed", f"Failed to request changes on PR #{pr_number} in {repo_full_name}", error=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)

    await _action_common(organization_id, repo_full_name, pr_number, "pr_changes_requested", "warning", f"Requested changes on PR #{pr_number} in {repo_full_name}")
    return result


async def comment_on_pull_request(organization_id: str, repo_full_name: str, pr_number: int, body: str) -> dict:
    if not body or not body.strip():
        raise HTTPException(status_code=400, detail="Comment body is required")
    access_token = _get_token(organization_id)
    try:
        result = await gh.comment_on_pull_request(access_token, repo_full_name, pr_number, body)
    except gh.GitHubAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    await _action_common(organization_id, repo_full_name, pr_number, "pr_commented", "success", f"Commented on PR #{pr_number} in {repo_full_name}")
    return result


async def merge_pull_request(organization_id: str, repo_full_name: str, pr_number: int, merge_method: str) -> dict:
    access_token = _get_token(organization_id)
    try:
        result = await gh.merge_pull_request(access_token, repo_full_name, pr_number, merge_method)
    except gh.GitHubAPIError as e:
        await _action_common(organization_id, repo_full_name, pr_number, "pr_merge_failed", "failed", f"Failed to merge PR #{pr_number} in {repo_full_name}", error=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)

    await _action_common(organization_id, repo_full_name, pr_number, "pr_merged", "success", f"Merged PR #{pr_number} in {repo_full_name}")
    notify(
        organization_id=organization_id, module=MODULE, category="pr_merged", priority="normal",
        title=f"PR merged: #{pr_number}", body=f"Pull request #{pr_number} in {repo_full_name} was merged.",
        resource_type="pull_request", resource_id=f"{repo_full_name}#{pr_number}",
        action_url=f"/pull-requests/{repo_full_name}/{pr_number}", action_label="View PR",
        dedup_key=f"pull_requests:merged:{repo_full_name}:{pr_number}",
    )
    return result


async def close_pull_request(organization_id: str, repo_full_name: str, pr_number: int) -> dict:
    access_token = _get_token(organization_id)
    try:
        result = await gh.close_pull_request(access_token, repo_full_name, pr_number)
    except gh.GitHubAPIError as e:
        await _action_common(organization_id, repo_full_name, pr_number, "pr_close_failed", "failed", f"Failed to close PR #{pr_number} in {repo_full_name}", error=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)

    await _action_common(organization_id, repo_full_name, pr_number, "pr_closed", "warning", f"Closed PR #{pr_number} in {repo_full_name}")
    return result


async def summarize_pull_request(organization_id: str, repo_full_name: str, pr_number: int) -> str:
    """On-demand only — never called automatically. Uses the existing shared
    run_gemini() from config.py, same infra as GitHub/Gmail/Calendar summaries."""
    detail = await get_pull_request_detail(organization_id, repo_full_name, pr_number)

    files_summary = "\n".join(f"- {f['filename']} (+{f['additions']}/-{f['deletions']})" for f in detail["files"][:30])
    reviews_summary = "\n".join(f"- {r['author']['login']}: {r['state']}" + (f" — {r['body'][:200]}" if r.get("body") else "") for r in detail["reviews"])
    checks_summary = "\n".join(f"- {c['name']}: {c['status']} ({c.get('conclusion') or 'pending'})" for c in detail["checks"])

    prompt = f"""You are summarizing a GitHub pull request for a developer.

Title: {detail['title']}
Repo: {repo_full_name} #{pr_number}
State: {detail['state']} (draft={detail['is_draft']}, merged={detail['is_merged']})
Description: {(detail.get('body') or '')[:1000]}

Files changed ({detail['changed_files']} files, +{detail['additions']}/-{detail['deletions']}):
{files_summary or 'none'}

Reviews:
{reviews_summary or 'no reviews yet'}

CI checks:
{checks_summary or 'no checks reported'}

Task: Write a concise summary (under 180 words) covering:
1. What this PR changes, in plain language
2. Any risks worth flagging (e.g. large diff, no reviews, failing checks)
3. What needs attention right now (if anything)
"""
    response = run_gemini(prompt)
    return response.text
