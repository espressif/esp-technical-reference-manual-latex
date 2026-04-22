r"""Detect whether a reused chapter is *included* via active ``\subfile`` / ``\subfileinclude`` lines."""

from __future__ import annotations

import re
from pathlib import Path


def _line_is_active(line: str) -> bool:
    """False if the line is a full-line TeX comment."""
    return not line.lstrip().startswith("%")


def _iter_main_tex(project_dir: Path):
    if not project_dir.is_dir():
        return
    for p in sorted(project_dir.glob("*-main__*.tex")):
        if p.is_file():
            yield p


def _active_subfileinclude_in_file(path: Path, source_id_module: str) -> bool:
    pat = re.compile(
        rf"\\subfileinclude\s*\{{\s*{re.escape(source_id_module)}(?:-latest)?__(EN|CN)\s*\}}",
    )
    for line in path.read_text(encoding="utf-8").splitlines():
        if not _line_is_active(line):
            continue
        if pat.search(line):
            return True
    return False


def _active_subfile_upstream_in_file(
    path: Path,
    source_project: str,
    source_id_module: str,
) -> bool:
    pat = re.compile(
        rf"\\subfile\s*\{{\s*\.\./\s*{re.escape(source_project)}\s*/\s*"
        rf"{re.escape(source_id_module)}(?:-latest)?__(EN|CN)\s*\}}",
    )
    for line in path.read_text(encoding="utf-8").splitlines():
        if not _line_is_active(line):
            continue
        if pat.search(line):
            return True
    return False


def chapter_included_via_subfiles(
    repo_root: Path,
    base_project: str,
    source_project: str,
    source_id_module: str,
    *,
    base_reuses_upstream: bool,
) -> bool:
    r"""True if the chapter is included via uncommented ``\subfile`` / ``\subfileinclude`` lines."""
    base_dir = repo_root / base_project
    if not base_reuses_upstream:
        for p in _iter_main_tex(base_dir):
            if _active_subfileinclude_in_file(p, source_id_module):
                return True
        return False

    for p in _iter_main_tex(base_dir):
        if _active_subfile_upstream_in_file(p, source_project, source_id_module):
            break
    else:
        return False

    src_dir = repo_root / source_project
    for p in _iter_main_tex(src_dir):
        if _active_subfileinclude_in_file(p, source_id_module):
            return True
    return False


def _uncomment_subfileinclude_content(content: str, source_id_module: str) -> str:
    inner = re.escape(source_id_module) + r"(?:-latest)?__(?:CN|EN)"
    pattern = rf"%\s*\\subfileinclude\{{({inner})\}}"
    return re.sub(pattern, r"\\subfileinclude{\1}", content)


def _uncomment_subfile_upstream_content(
    content: str,
    source_project: str,
    source_id_module: str,
) -> str:
    pattern = (
        rf"%\s*\\subfile\s*\{{\s*(\.\./\s*{re.escape(source_project)}\s*/\s*"
        rf"{re.escape(source_id_module)}(?:-latest)?__(?:CN|EN))\s*\}}"
    )
    return re.sub(
        pattern,
        rf"\\subfile{{\1}}",
        content,
    )


def uncomment_chapter_includes(
    repo_root: Path,
    base_project: str,
    source_project: str,
    source_id_module: str,
    *,
    base_reuses_upstream: bool,
) -> list[str]:
    """Uncomment ``% \\subfileinclude`` / ``% \\subfile`` so the chapter is included. Returns modified rel paths."""
    modified: list[str] = []
    base_dir = repo_root / base_project
    if not base_reuses_upstream:
        for p in _iter_main_tex(base_dir):
            text = p.read_text(encoding="utf-8")
            new = _uncomment_subfileinclude_content(text, source_id_module)
            if new != text:
                p.write_text(new, encoding="utf-8")
                modified.append(str(p.relative_to(repo_root)))
        return modified

    for p in _iter_main_tex(base_dir):
        text = p.read_text(encoding="utf-8")
        new = _uncomment_subfile_upstream_content(text, source_project, source_id_module)
        if new != text:
            p.write_text(new, encoding="utf-8")
            modified.append(str(p.relative_to(repo_root)))

    src_dir = repo_root / source_project
    for p in _iter_main_tex(src_dir):
        text = p.read_text(encoding="utf-8")
        new = _uncomment_subfileinclude_content(text, source_id_module)
        if new != text:
            p.write_text(new, encoding="utf-8")
            modified.append(str(p.relative_to(repo_root)))
    return modified
