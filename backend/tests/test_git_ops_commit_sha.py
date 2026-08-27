"""
Regression test for a real duplicate-execution bug: GitHubProvider.commit_file
was returning the file BLOB's sha (data["content"]["sha"]) instead of the
actual commit sha (data["commit"]["sha"]). Since the dispatch layer uses this
value as the idempotency event_key, and a real GitHub webhook for the same
commit reports the true commit sha, the mismatch caused a scheduler-dispatched
event and a real webhook event for the identical commit to be treated as two
different events -- firing every configured workflow action twice (observed:
duplicate emails, duplicate calendar events, duplicate audit log entries,
duplicate tasks).

This test uses a realistic GitHub Contents API PUT response where the blob
sha and commit sha are deliberately different values, so a future accidental
revert to data["content"]["sha"] fails immediately and obviously.
"""
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from commit_scheduler.git_ops import GitHubProvider


def run(coro):
    return asyncio.run(coro)


def test_commit_file_returns_the_commit_sha_not_the_blob_sha():
    provider = GitHubProvider()

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "content": {
            "sha": "blobsha0000000000000000000000000000000",
            "html_url": "https://github.com/acme/repo/blob/main/file.txt",
        },
        "commit": {
            "sha": "realcommitsha1111111111111111111111111",
            "html_url": "https://github.com/acme/repo/commit/realcommitsha1111111111111111111111111",
        },
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.put = AsyncMock(return_value=fake_response)

    with patch("commit_scheduler.git_ops.httpx.AsyncClient", return_value=mock_client):
        result = run(provider.commit_file(
            "gh-token", "acme/repo", "file.txt", "hello", "main", "a commit"
        ))

    assert result["sha"] == "realcommitsha1111111111111111111111111"
    assert result["sha"] != "blobsha0000000000000000000000000000000"
    assert result["commit_url"] == "https://github.com/acme/repo/commit/realcommitsha1111111111111111111111111"
