"""Shared environment.py loading helpers."""

from __future__ import annotations

import sys


def load_environment_module(import_error_message: str = "environment.py not found in repo root"):
    """Import ``environment.py`` from repo root path context or exit."""
    try:
        import environment as env  # type: ignore
        return env
    except ImportError:
        sys.exit(import_error_message)


def get_env_values(env_module, names: list[str]) -> dict[str, str | None]:
    """Read a list of attributes from imported environment module."""
    return {name: getattr(env_module, name, None) for name in names}


def require_env_values(values: dict[str, str | None], names: list[str], *, source: str = "environment.py"):
    """Exit if any required names are missing or falsy."""
    missing = [n for n in names if not values.get(n)]
    if missing:
        sys.exit(f"❌ Missing in {source}: {', '.join(missing)}")
