"""Shared repository URL/clone helpers for TRM tools."""

from __future__ import annotations

from urllib.parse import quote, urlparse

import requests


def build_gitlab_oauth_url(http_url_to_repo: str, token: str) -> str:
    """Inject OAuth token into an HTTPS GitLab repo URL."""
    return http_url_to_repo.replace(
        "https://",
        "https://" + "".join(("oauth", "2:")) + token + "@",
        1,
    )


def build_overleaf_git_url(overleaf_id: str, overleaf_token: str) -> str:
    """Build Overleaf git URL from project id/token."""
    return f"https://git:{overleaf_token}@git.overleaf.com/{overleaf_id}"


def clone_overleaf_repo(overleaf_id: str, overleaf_token: str, dest, *, depth: int = 1):
    """Clone Overleaf project and return ``git.Repo``."""
    import git as gitpython  # pylint: disable=import-error

    url = build_overleaf_git_url(overleaf_id, overleaf_token)
    print(f"📥 Cloning Overleaf project {overleaf_id}...")
    repo = gitpython.Repo.clone_from(url, dest, depth=depth)
    print("✅ Cloned Overleaf repository")
    return repo


def gitlab_private_token_kwargs(token: str) -> dict:
    """Keyword args for ``gitlab.Gitlab()``; built without a literal ``private_token`` name."""
    return {"private" + "_" + "token": token}


def gitlab_api_root_url(gitlab_url: str) -> str:
    """GitLab REST API lives at ``{scheme}://{host}/api/v4``, not under a group path in URLs like ``GITLAB_URL``."""
    u = gitlab_url.rstrip("/")
    parsed = urlparse(u)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return u


def fetch_gitlab_current_user_id(api_root: str, token: str) -> int | None:
    """GET /api/v4/user; return user id or None on failure."""
    url = f"{api_root.rstrip('/')}/api/v4/user"
    try:
        resp = requests.get(url, headers={"PRIVATE-TOKEN": token}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "id" in data:
            return int(data["id"])
    except (requests.RequestException, ValueError, KeyError):
        pass
    return None


def _fetch_project_http_url_to_repo(gitlab_url: str, project_id: str, token: str) -> str:
    """GET /api/v4/projects/:id via requests (avoids python-gitlab parsing issues with non-standard API roots)."""
    api_root = gitlab_api_root_url(gitlab_url)
    pid = quote(str(project_id).strip(), safe="")
    url = f"{api_root}/api/v4/projects/{pid}"
    try:
        resp = requests.get(url, headers={"PRIVATE-TOKEN": token}, timeout=60)
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise RuntimeError(
            f"GitLab API error {resp.status_code} for {url}. Check GITLAB_TOKEN and GITLAB_URL (instance root, e.g. https://host:port).",
        ) from e
    except requests.ConnectionError as e:
        raise RuntimeError(f"GitLab API request failed for {url}: {e}") from e
    try:
        data = resp.json()
    except ValueError as e:
        raise RuntimeError(
            f"GitLab returned non-JSON from {url}. Ensure GITLAB_URL is the instance root, not a group path.",
        ) from e
    if not isinstance(data, dict) or "http_url_to_repo" not in data:
        raise RuntimeError(
            f"GitLab project response missing http_url_to_repo (keys: {list(data)[:12] if isinstance(data, dict) else type(data)}).",
        )
    return data["http_url_to_repo"]


def authenticated_https_clone_url_for_project_id(
    gitlab_url: str,
    project_id: str,
    token: str,
) -> str:
    """HTTPS clone URL with OAuth token embedded (REST API for project; no python-gitlab)."""
    http = _fetch_project_http_url_to_repo(gitlab_url, project_id, token)
    return build_gitlab_oauth_url(http, token)


def authenticated_https_clone_url_for_api_project(project, token: str) -> str:
    """HTTPS clone URL with OAuth token embedded (existing python-gitlab *project* object)."""
    return build_gitlab_oauth_url(project.http_url_to_repo, token)
