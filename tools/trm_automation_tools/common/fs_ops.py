"""Shared filesystem helpers."""

from __future__ import annotations

from pathlib import Path


def find_chip_spec_dir(project_dir: Path) -> Path | None:
    """Find ``00-chip-spec-content`` or ``00-chip-spec-settings`` under *project_dir*."""
    for name in ("00-chip-spec-content", "00-chip-spec-settings"):
        d = project_dir / name
        if d.exists():
            return d
    return None


def has_real_files(dir_path: Path) -> bool:
    """Return True if directory contains files other than placeholder.temp."""
    return any(
        p.is_file() and p.name != "placeholder.temp"
        for p in dir_path.rglob("*")
    )
