"""
Provider-agnostic Git operations interface.
Add new providers (GitLab, Bitbucket, Azure DevOps) by implementing VCSProvider
without touching routes/service/scheduler layers.
"""
from abc import ABC, abstractmethod
from typing import Optional
import base64
import httpx


class VCSProvider(ABC):
    @abstractmethod
    async def list_repos(self, access_token: str) -> list[dict]:
        ...

    @abstractmethod
    async def list_branches(self, access_token: str, repo_full_name: str) -> list[dict]:
        ...

    @abstractmethod
    async def get_file(self, access_token: str, repo_full_name: str, path: str, branch: str) -> Optional[dict]:
        """Returns {'sha': ..., 'content': ...} or None if file doesn't exist."""
        ...

    @abstractmethod
    async def commit_file(
        self, access_token: str, repo_full_name: str, path: str,
        content: str, branch: str, message: str, sha: Optional[str] = None
    ) -> dict:
        """Creates or updates a file. Returns {'sha': ..., 'html_url': ..., 'commit_url': ...}."""
        ...


class GitHubProvider(VCSProvider):
    BASE_URL = "https://api.github.com"

    def _headers(self, access_token: str) -> dict:
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }

    async def list_repos(self, access_token: str) -> list[dict]:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{self.BASE_URL}/user/repos",
                headers=self._headers(access_token),
                params={"per_page": 100, "sort": "updated"}
            )
        res.raise_for_status()
        repos = res.json()
        return [
            {"full_name": r["full_name"], "name": r["name"], "default_branch": r["default_branch"]}
            for r in repos
        ]

    async def list_branches(self, access_token: str, repo_full_name: str) -> list[dict]:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{self.BASE_URL}/repos/{repo_full_name}/branches",
                headers=self._headers(access_token),
                params={"per_page": 100}
            )
        res.raise_for_status()
        branches = res.json()
        return [{"name": b["name"]} for b in branches]

    async def get_file(self, access_token: str, repo_full_name: str, path: str, branch: str) -> Optional[dict]:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{self.BASE_URL}/repos/{repo_full_name}/contents/{path}",
                headers=self._headers(access_token),
                params={"ref": branch}
            )
        if res.status_code == 404:
            return None
        res.raise_for_status()
        data = res.json()
        return {"sha": data.get("sha")}

    async def commit_file(
        self, access_token: str, repo_full_name: str, path: str,
        content: str, branch: str, message: str, sha: Optional[str] = None
    ) -> dict:
        encoded = base64.b64encode(content.encode()).decode()
        payload = {"message": message, "content": encoded, "branch": branch}
        if sha:
            payload["sha"] = sha

        async with httpx.AsyncClient() as client:
            res = await client.put(
                f"{self.BASE_URL}/repos/{repo_full_name}/contents/{path}",
                headers=self._headers(access_token),
                json=payload
            )
        if res.status_code not in (200, 201):
            raise RuntimeError(f"GitHub commit failed ({res.status_code}): {res.text}")
        data = res.json()
        return {
            "sha": data["content"]["sha"],
            "html_url": data["content"]["html_url"],
            "commit_url": data["commit"]["html_url"],
        }


def get_provider(provider_name: str) -> VCSProvider:
    if provider_name == "github":
        return GitHubProvider()
    raise ValueError(f"Unsupported provider: {provider_name}")
