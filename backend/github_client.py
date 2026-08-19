"""
Shared low-level GitHub REST + Search API client used by pull_requests and
open_source (and available to any future module that needs GitHub reads).

Design notes:
- Read-only helpers only. Write operations (commit/branch/PR-create) already
  live in commit_scheduler/git_ops.py and are left there — this module does
  not duplicate them.
- Uses GitHub's Search API for "PRs involving me" / "PRs needing my review"
  queries (one call instead of iterating every repo's /pulls endpoint),
  which is both faster and far friendlier to GitHub's rate limits.
- Every call surfaces GitHub's rate-limit headers via GitHubRateLimitError
  so callers (routes/service layers) can return a clean 429 instead of an
  opaque 500, and surfaces 403/404 permission failures as GitHubAPIError
  rather than raising raw httpx exceptions.
"""
import httpx
from typing import Optional

BASE_URL = "https://api.github.com"


class GitHubAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class GitHubRateLimitError(GitHubAPIError):
    def __init__(self, reset_at: Optional[str] = None):
        self.reset_at = reset_at
        message = "GitHub API rate limit exceeded."
        if reset_at:
            message += f" Resets at {reset_at}."
        super().__init__(status_code=429, message=message)


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _check_rate_limit(res: httpx.Response):
    if res.status_code == 403 and res.headers.get("X-RateLimit-Remaining") == "0":
        raise GitHubRateLimitError(reset_at=res.headers.get("X-RateLimit-Reset"))
    if res.status_code == 429:
        raise GitHubRateLimitError()


async def _request(method: str, url: str, access_token: str, **kwargs) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            res = await client.request(method, url, headers=_headers(access_token), **kwargs)
    except httpx.HTTPError as e:
        raise GitHubAPIError(status_code=502, message=f"Couldn't reach GitHub: {e}")

    _check_rate_limit(res)

    if res.status_code == 404:
        raise GitHubAPIError(status_code=404, message="Not found, or you don't have access.")
    if res.status_code == 403:
        raise GitHubAPIError(status_code=403, message="GitHub denied this action — check repository permissions.")
    if res.status_code >= 400:
        raise GitHubAPIError(status_code=res.status_code, message=res.text)

    return res


async def get(access_token: str, path: str, params: Optional[dict] = None) -> httpx.Response:
    return await _request("GET", f"{BASE_URL}{path}", access_token, params=params)


async def post(access_token: str, path: str, json: Optional[dict] = None) -> httpx.Response:
    return await _request("POST", f"{BASE_URL}{path}", access_token, json=json)


async def put(access_token: str, path: str, json: Optional[dict] = None) -> httpx.Response:
    return await _request("PUT", f"{BASE_URL}{path}", access_token, json=json)


async def get_current_user(access_token: str) -> dict:
    """Returns the authenticated GitHub user (used to resolve `login` for
    Search API queries like involves:{login} and review-requested:{login})."""
    res = await get(access_token, "/user")
    return res.json()


async def search_issues(access_token: str, query: str, sort: Optional[str] = None, per_page: int = 30, page: int = 1) -> dict:
    """Wraps GET /search/issues (which also covers PRs — GitHub's Search API
    treats PRs as a kind of issue). Returns the raw {total_count, items}
    payload; callers filter/shape as needed."""
    params = {"q": query, "per_page": per_page, "page": page}
    if sort:
        params["sort"] = sort
        params["order"] = "desc"
    res = await get(access_token, "/search/issues", params=params)
    return res.json()


async def search_repositories(access_token: str, query: str, sort: Optional[str] = None, per_page: int = 30, page: int = 1) -> dict:
    params = {"q": query, "per_page": per_page, "page": page}
    if sort:
        params["sort"] = sort
        params["order"] = "desc"
    res = await get(access_token, "/search/repositories", params=params)
    return res.json()


async def get_pull_request(access_token: str, repo_full_name: str, pr_number: int) -> dict:
    res = await get(access_token, f"/repos/{repo_full_name}/pulls/{pr_number}")
    return res.json()


async def list_pr_reviews(access_token: str, repo_full_name: str, pr_number: int) -> list[dict]:
    res = await get(access_token, f"/repos/{repo_full_name}/pulls/{pr_number}/reviews", params={"per_page": 100})
    return res.json()


async def list_pr_review_comments(access_token: str, repo_full_name: str, pr_number: int) -> list[dict]:
    res = await get(access_token, f"/repos/{repo_full_name}/pulls/{pr_number}/comments", params={"per_page": 100})
    return res.json()


async def list_issue_comments(access_token: str, repo_full_name: str, issue_number: int) -> list[dict]:
    """PRs are issues under the hood — general (non-review) comments live
    under the issue-comments endpoint even for a PR number."""
    res = await get(access_token, f"/repos/{repo_full_name}/issues/{issue_number}/comments", params={"per_page": 100})
    return res.json()


async def list_pr_commits(access_token: str, repo_full_name: str, pr_number: int) -> list[dict]:
    res = await get(access_token, f"/repos/{repo_full_name}/pulls/{pr_number}/commits", params={"per_page": 100})
    return res.json()


async def list_pr_files(access_token: str, repo_full_name: str, pr_number: int) -> list[dict]:
    res = await get(access_token, f"/repos/{repo_full_name}/pulls/{pr_number}/files", params={"per_page": 100})
    return res.json()


async def get_combined_status(access_token: str, repo_full_name: str, ref: str) -> dict:
    """Legacy commit-status API (older CI integrations)."""
    res = await get(access_token, f"/repos/{repo_full_name}/commits/{ref}/status")
    return res.json()


async def list_check_runs(access_token: str, repo_full_name: str, ref: str) -> dict:
    """Modern Checks API (GitHub Actions and most current CI providers)."""
    res = await get(access_token, f"/repos/{repo_full_name}/commits/{ref}/check-runs", params={"per_page": 100})
    return res.json()


async def approve_pull_request(access_token: str, repo_full_name: str, pr_number: int, body: Optional[str] = None) -> dict:
    res = await post(access_token, f"/repos/{repo_full_name}/pulls/{pr_number}/reviews", json={"event": "APPROVE", "body": body or ""})
    return res.json()


async def request_changes_on_pull_request(access_token: str, repo_full_name: str, pr_number: int, body: str) -> dict:
    res = await post(access_token, f"/repos/{repo_full_name}/pulls/{pr_number}/reviews", json={"event": "REQUEST_CHANGES", "body": body})
    return res.json()


async def comment_on_pull_request(access_token: str, repo_full_name: str, pr_number: int, body: str) -> dict:
    res = await post(access_token, f"/repos/{repo_full_name}/issues/{pr_number}/comments", json={"body": body})
    return res.json()


async def merge_pull_request(access_token: str, repo_full_name: str, pr_number: int, merge_method: str = "merge") -> dict:
    res = await put(access_token, f"/repos/{repo_full_name}/pulls/{pr_number}/merge", json={"merge_method": merge_method})
    return res.json()


async def close_pull_request(access_token: str, repo_full_name: str, pr_number: int) -> dict:
    res = await _request("PATCH", f"{BASE_URL}/repos/{repo_full_name}/pulls/{pr_number}", access_token, json={"state": "closed"})
    return res.json()


async def get_repository(access_token: str, repo_full_name: str) -> dict:
    res = await get(access_token, f"/repos/{repo_full_name}")
    return res.json()


async def get_issue(access_token: str, repo_full_name: str, issue_number: int) -> dict:
    res = await get(access_token, f"/repos/{repo_full_name}/issues/{issue_number}")
    return res.json()
