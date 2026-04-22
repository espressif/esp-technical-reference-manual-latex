"""``tools/auto_backport/reused_chapter_list.txt`` helpers and git path sync."""

from __future__ import annotations

from pathlib import Path

REUSED_CHAPTER_LIST_REL = "tools/auto_backport/reused_chapter_list.txt"


def reused_chapter_path_lines(source_project: str, source_id_module: str) -> list[str]:
    """Three list-file lines for a reused chapter (folder + two mains)."""
    base = f"./{source_project}/{source_id_module}"
    return [
        base,
        f"{base}__CN.tex",
        f"{base}__EN.tex",
    ]


def git_paths_for_reused_chapter(source_project: str, source_id_module: str) -> list[str]:
    """Repo-relative paths (no ``./``) for ``git checkout <ref> -- …``."""
    return [
        f"{source_project}/{source_id_module}",
        f"{source_project}/{source_id_module}__CN.tex",
        f"{source_project}/{source_id_module}__EN.tex",
    ]


def paths_listed_in_file(content: str, path_lines: list[str]) -> bool:
    """True if every expected line appears as a line in *content*."""
    lines = {ln.strip() for ln in content.splitlines() if ln.strip()}
    return all(pl.strip() in lines for pl in path_lines)


def merge_reused_paths_into_list_file(list_path: Path, path_lines: list[str]) -> bool:
    """Insert missing *path_lines*, sort all lines alphabetically. Returns True if changed."""
    if not list_path.is_file():
        raise FileNotFoundError(f"Missing reused chapter list: {list_path}")

    raw = list_path.read_text(encoding="utf-8")
    lines = [ln.rstrip("\n") for ln in raw.splitlines() if ln.strip()]
    before = "\n".join(lines) + ("\n" if lines else "")
    merged = sorted(frozenset(lines) | {pl.strip() for pl in path_lines})
    after = "\n".join(merged) + "\n" if merged else ""
    if before == after:
        return False
    list_path.write_text(after, encoding="utf-8")
    return True


def read_git_blob(repo, ref: str, rel_path: str) -> str | None:
    """Return file text at ``ref:rel_path``, or None if missing."""
    try:
        return repo.git.show(f"{ref}:{rel_path}")
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def checkout_paths_from_ref(repo, ref: str, rel_paths: list[str]) -> None:
    """Populate working tree paths from *ref* (e.g. ``origin/master``)."""
    if not rel_paths:
        return
    repo.git.checkout(ref, "--", *rel_paths)
