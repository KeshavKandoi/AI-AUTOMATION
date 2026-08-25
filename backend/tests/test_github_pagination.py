"""
Regression tests: GitHub repo/issue fetches must follow pagination and
return the full result set across multiple pages, not just page 1 (GitHub's
default page size is 30). These tests mock 3 pages of data and assert every
item across all pages is present in the final result -- import success is
not proof pagination actually works.
"""
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


def _override_org(app, org_id="org-1"):
    from auth.dependencies import get_current_org_id
    app.dependency_overrides[get_current_org_id] = lambda: org_id


def _clear(app):
    app.dependency_overrides.clear()


def _make_repo(i):
    return {"id": i, "name": f"repo-{i}", "full_name": f"acme/repo-{i}", "open_issues_count": 0}


def test_github_get_paginated_follows_multiple_pages():
    """Direct unit test of the pagination helper: 3 pages of 100 items each,
    a final short page of 20 -- must return all 320 items in one list."""
    import asyncio
    from main import github_get_paginated

    page1 = [_make_repo(i) for i in range(100)]
    page2 = [_make_repo(i) for i in range(100, 200)]
    page3 = [_make_repo(i) for i in range(200, 220)]  # short page -> stop here

    responses = [
        MagicMock(json=lambda: page1),
        MagicMock(json=lambda: page2),
        MagicMock(json=lambda: page3),
    ]

    with patch("main.github_get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = responses

        result = asyncio.run(
            github_get_paginated("https://api.github.com/user/repos", "tok")
        )

        assert len(result) == 220
        assert mock_get.call_count == 3

        call_pages = [c.kwargs["params"]["page"] for c in mock_get.call_args_list]
        assert call_pages == [1, 2, 3]
        for c in mock_get.call_args_list:
            assert c.kwargs["params"]["per_page"] == 100


def test_github_get_paginated_stops_on_exact_full_page_then_empty():
    """Edge case: if page 1 returns exactly per_page items (100), the loop
    must fetch page 2 to check for more, and stop only when a page comes
    back empty."""
    import asyncio
    from main import github_get_paginated

    page1 = [_make_repo(i) for i in range(100)]
    page2 = []

    with patch("main.github_get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [MagicMock(json=lambda: page1), MagicMock(json=lambda: page2)]

        result = asyncio.run(
            github_get_paginated("https://api.github.com/user/repos", "tok")
        )

        assert len(result) == 100
        assert mock_get.call_count == 2


def test_github_get_paginated_raises_on_error_response_first_page():
    import asyncio
    from main import github_get_paginated
    from fastapi import HTTPException

    with patch("main.github_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = MagicMock(json=lambda: {"message": "Bad credentials"})

        try:
            asyncio.run(
                github_get_paginated("https://api.github.com/user/repos", "tok")
            )
            assert False, "expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 400


def test_github_repos_endpoint_returns_all_pages():
    """End-to-end: /github/repos must return repos from every page, not just
    the first 100."""
    from main import app
    _override_org(app, org_id="org-1")
    try:
        page1 = [_make_repo(i) for i in range(100)]
        page2 = [_make_repo(i) for i in range(100, 145)]  # short page -> last

        with patch("closeout._resolve_access_token", return_value="tok"), \
             patch("main.github_get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [MagicMock(json=lambda: page1), MagicMock(json=lambda: page2)]

            client = TestClient(app)
            res = client.get("/github/repos")

            assert res.status_code == 200
            body = res.json()
            assert isinstance(body, list)
            assert len(body) == 145
            assert body[0]["name"] == "repo-0"
            assert body[-1]["name"] == "repo-144"
    finally:
        _clear(app)


def test_fetch_github_repos_and_issues_paginates_both_repos_and_issues():
    """A repo with >100 open issues must have all of them included, not
    just the first page of issues."""
    import asyncio
    from main import fetch_github_repos_and_issues

    repo = {"id": 1, "name": "big-repo", "full_name": "acme/big-repo", "open_issues_count": 150}
    repos_page1 = [repo]

    def _issue(i):
        return {"title": f"issue-{i}", "created_at": "2026-01-01T00:00:00Z", "comments": 0}

    issues_page1 = [_issue(i) for i in range(100)]
    issues_page2 = [_issue(i) for i in range(100, 150)]

    with patch("main.github_get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [
            MagicMock(json=lambda: repos_page1),        # repos page 1 (short -> stop)
            MagicMock(json=lambda: issues_page1),        # issues page 1 (full -> continue)
            MagicMock(json=lambda: issues_page2),        # issues page 2 (short -> stop)
        ]

        result = asyncio.run(
            fetch_github_repos_and_issues("tok")
        )

        assert len(result) == 150
        titles = {i["title"] for i in result}
        assert "issue-0" in titles
        assert "issue-149" in titles
