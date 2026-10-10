import httpx
from fastapi import HTTPException
from config import logger

async def fetch_github_repos_and_issues(access_token: str):
    """Fetches the user's repos and open issues for repos that have any.
    Paginates both the repo list and each repo's issue list so orgs/repos
    with more than one GitHub API page of results aren't silently truncated.
    Wraps outbound GitHub calls so transient network failures (dropped
    connections, timeouts) return a clean error instead of an unhandled 500."""
    repos = await github_get_paginated("https://api.github.com/user/repos", access_token)

    repos_with_issues = [r for r in repos if r.get("open_issues_count", 0) > 0]
    issues_data = []
    for r in repos_with_issues:
        issues = await github_get_paginated(
            f"https://api.github.com/repos/{r['full_name']}/issues",
            access_token,
            params={"state": "open"},
        )
        for issue in issues:
            issues_data.append({
                "repo": r["name"], "title": issue.get("title"),
                "created_at": issue.get("created_at"), "comments": issue.get("comments"),
            })

    return issues_data


async def github_get(url: str, access_token: str, params: dict = None):
    """GET a GitHub API URL with clean handling for network-level failures."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
        return res
    except httpx.HTTPError as e:
        logger.error(f"GitHub GET {url} failed: {e}")
        raise HTTPException(status_code=502, detail="Couldn't reach GitHub. Please try again shortly.")


async def github_post(url: str, access_token: str, json_body: dict = None):
    """POST to a GitHub API URL with clean handling for network-level failures."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                json=json_body,
            )
        return res
    except httpx.HTTPError as e:
        logger.error(f"GitHub POST {url} failed: {e}")
        raise HTTPException(status_code=502, detail="Couldn't reach GitHub. Please try again shortly.")


GITHUB_MAX_PAGES = 20  # hard ceiling (up to 2000 items at per_page=100) -- safety bound, not expected to be hit


async def github_get_paginated(url: str, access_token: str, params: dict = None) -> list:
    """GETs every page of a GitHub list endpoint (repos, issues, etc.) and
    returns the concatenated results. Uses per_page=100 and increments page
    until a page comes back empty or short (fewer than per_page items,
    meaning it was the last page), or GITHUB_MAX_PAGES is hit as a safety
    bound. Raises the same clean errors as github_get on network failure or
    a non-list response (e.g. a GitHub error payload on page 1)."""
    all_items: list = []
    page = 1
    per_page = 100
    base_params = dict(params or {})
    base_params["per_page"] = per_page

    while page <= GITHUB_MAX_PAGES:
        page_params = dict(base_params)
        page_params["page"] = page
        res = await github_get(url, access_token, params=page_params)
        data = res.json()

        if not isinstance(data, list):
            if page == 1:
                raise HTTPException(status_code=400, detail="GitHub API error")
            break

        all_items.extend(data)

        if len(data) < per_page:
            break
        page += 1

    return all_items
