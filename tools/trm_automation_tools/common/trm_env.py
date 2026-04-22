"""Cached ``environment.py`` values shared by setup and publish scripts."""

from __future__ import annotations

from tools.trm_automation_tools.common import gitlab_repo_ids
from tools.trm_automation_tools.common.env_ops import (
    get_env_values,
    load_environment_module,
    require_env_values,
)

# All attributes read from ``environment.py`` (subset may be unset / unused per script).
TRM_ENV_KEYS = [
    "OVERLEAF_TOKEN",
    "GITLAB_TOKEN",
    "GITLAB_URL",
    "TRM_REPO_ID",
    "FIGURES_REPO_ID",
]

_ENV_IMPORT_MESSAGE = (
    "❌ environment.py not found in repo root. "
    "See tools/trm_automation_tools/README.md for setup."
)

_cached: dict[str, str | None] | None = None


def _apply_gitlab_repo_id_defaults(values: dict[str, str | None]) -> dict[str, str | None]:
    """Fill missing GitLab project IDs from ``gitlab_repo_ids`` (``environment.py`` may omit them)."""
    out = dict(values)
    if not (out.get("TRM_REPO_ID") or "").strip():
        out["TRM_REPO_ID"] = gitlab_repo_ids.TRM_REPO_ID
    if not (out.get("FIGURES_REPO_ID") or "").strip():
        out["FIGURES_REPO_ID"] = gitlab_repo_ids.FIGURES_REPO_ID
    return out


def get_trm_env_values() -> dict[str, str | None]:
    """Load ``environment.py`` once and return all TRM env keys (values may be ``None``)."""
    global _cached
    if _cached is None:
        env = load_environment_module(_ENV_IMPORT_MESSAGE)
        _cached = _apply_gitlab_repo_id_defaults(get_env_values(env, TRM_ENV_KEYS))
    return _cached


def require_trm_env(*names: str) -> None:
    """Exit if any of *names* are missing or empty in ``environment.py``."""
    require_env_values(get_trm_env_values(), list(names))
