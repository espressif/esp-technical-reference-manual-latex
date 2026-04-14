r"""Shared chapter-content extraction/splice helpers for TRM LaTeX files.

Chapter content starts at the earlier of:
- the first ``\chapter`` line after ``\begin{document}``, and
- the first ``\hypertarget{...}{}`` line after ``\begin{document}``

The ``\hypertarget`` marker is still required. Content ends at
``\end{document}`` (inclusive).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HYPERTARGET_LINE = re.compile(r"\\hypertarget\{[^}]*\}\{\}")
_CHAPTER_LINE = re.compile(r"\\chapter\*?\s*(?:\[[^\]]*\])?\s*\{")


def line_is_latex_end_document(line: str) -> bool:
    """True if *line* is a real ``\\end{document}`` command, not a substring."""
    code = line.split("%", 1)[0].strip()
    return bool(re.fullmatch(r"\\end\s*\{\s*document\s*\}", code, re.IGNORECASE))


def _line_without_comment(line: str) -> str:
    """Return code portion of a LaTeX line (drop trailing ``%`` comments)."""
    return line.split("%", 1)[0]


def _find_begin_document_start(lines: list[str]) -> int:
    r"""Return search start index at ``\begin{document}``, else 0."""
    for i, line in enumerate(lines):
        code = _line_without_comment(line).strip()
        if re.fullmatch(r"\\begin\s*\{\s*document\s*\}", code, re.IGNORECASE):
            return i
    return 0


def _find_first_hypertarget(lines: list[str], start: int) -> int | None:
    r"""First line index with ``\hypertarget{...}{}`` at/after *start*."""
    for i in range(start, len(lines)):
        if _HYPERTARGET_LINE.search(_line_without_comment(lines[i])):
            return i
    return None


def _find_first_chapter(lines: list[str], start: int) -> int | None:
    r"""First line index with ``\chapter`` at/after *start*."""
    for i in range(start, len(lines)):
        if _CHAPTER_LINE.search(_line_without_comment(lines[i])):
            return i
    return None


def _find_chapter_content_start(lines: list[str], source_label: str) -> int:
    r"""Return chapter content start index (earlier of ``\chapter``/``\hypertarget``)."""
    scan_start = _find_begin_document_start(lines)
    first_hypertarget = _find_first_hypertarget(lines, scan_start)
    if first_hypertarget is None:
        sys.exit(f"❌ No '\\hypertarget{{...}}{{}}' line found in {source_label}")
    first_chapter = _find_first_chapter(lines, scan_start)
    if first_chapter is None:
        return first_hypertarget
    return min(first_hypertarget, first_chapter)


def try_find_chapter_content_start(lines: list[str]) -> int | None:
    r"""Start index (earlier of ``\chapter``/``\hypertarget``), or ``None``."""
    scan_start = _find_begin_document_start(lines)
    first_hypertarget = _find_first_hypertarget(lines, scan_start)
    if first_hypertarget is None:
        return None
    first_chapter = _find_first_chapter(lines, scan_start)
    if first_chapter is None:
        return first_hypertarget
    return min(first_hypertarget, first_chapter)


def extract_chapter_content(content: str, source_label: str) -> str:
    r"""Extract chapter content (start marker through ``\end{document}`` inclusive)."""
    lines = content.split("\n")
    start = _find_chapter_content_start(lines, source_label)
    end = None
    for i in range(start, len(lines)):
        if line_is_latex_end_document(lines[i]):
            end = i + 1
            break
    if end is None:
        sys.exit(f"❌ No '\\end{{document}}' after chapter content start in {source_label}")
    return "\n".join(lines[start:end])


def try_extract_chapter_content(content: str) -> str | None:
    """Like ``extract_chapter_content`` but returns ``None`` if chapter content markers are missing."""
    lines = content.split("\n")
    start = try_find_chapter_content_start(lines)
    if start is None:
        return None
    end = None
    for i in range(start, len(lines)):
        if line_is_latex_end_document(lines[i]):
            end = i + 1
            break
    if end is None:
        return None
    return "\n".join(lines[start:end])


def replace_chapter_content(tex_path: Path, new_content: str):
    r"""Replace chapter content (start marker through ``\end{document}``) with *new_content*."""
    content = tex_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    start = _find_chapter_content_start(lines, tex_path.name)
    end_doc = None
    for i in range(start, len(lines)):
        if line_is_latex_end_document(lines[i]):
            end_doc = i
            break
    if end_doc is None:
        sys.exit(f"❌ '\\end{{document}}' not found in {tex_path.name}")
    new_lines = lines[:start] + new_content.split("\n")
    tex_path.write_text("\n".join(new_lines), encoding="utf-8")


def merge_template_chapter_content(template: str, copied: str) -> str | None:
    r"""Merge chapter content from *copied* into *template*.

    Keeps the template preamble (before chapter content start) and replaces the chapter
    content region with the one extracted from *copied*. Returns ``None`` when either
    file lacks the expected chapter content markers.
    """
    tlines = template.split("\n")
    tstart = try_find_chapter_content_start(tlines)
    if tstart is None:
        return None
    new_body = try_extract_chapter_content(copied)
    if new_body is None:
        return None
    return "\n".join(tlines[:tstart] + new_body.split("\n"))
