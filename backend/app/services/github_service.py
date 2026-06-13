"""
GitHub integration: fetch repo metadata via API and clone via git.
"""
import os
import shutil
import re
import httpx
import git

from app.core.config import get_settings

settings = get_settings()


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo_name) from various GitHub URL formats."""
    url = url.rstrip("/").removesuffix(".git")
    patterns = [
        r"github\.com[:/]([^/]+)/([^/]+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1), match.group(2)
    raise ValueError(f"Could not parse GitHub URL: {url}")


async def fetch_repo_metadata(owner: str, repo_name: str) -> dict:
    """Fetch repo info from GitHub API."""
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    url = f"https://api.github.com/repos/{owner}/{repo_name}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return {
        "description": data.get("description"),
        "language": data.get("language"),
        "star_count": data.get("stargazers_count", 0),
        "default_branch": data.get("default_branch", "main"),
    }


def clone_repo(github_url: str, owner: str, repo_name: str) -> str:
    """
    Clone the repo to REPOS_DIR/<owner>/<repo_name>.
    If already present, do a git pull instead.
    Returns the local repo path.
    """
    repos_dir = settings.repos_dir
    os.makedirs(repos_dir, exist_ok=True)

    local_path = os.path.join(repos_dir, owner, repo_name)

    clone_url = github_url
    if settings.github_token:
        # Inject token for private repos
        clone_url = clone_url.replace(
            "https://github.com",
            f"https://{settings.github_token}@github.com"
        )

    if os.path.exists(local_path):
        try:
            repo = git.Repo(local_path)
            repo.remotes.origin.pull()
            return local_path
        except Exception:
            shutil.rmtree(local_path, ignore_errors=True)

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    git.Repo.clone_from(clone_url, local_path, depth=1)  # shallow clone for speed
    return local_path
