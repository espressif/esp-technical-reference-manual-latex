"""Shared text/file transforms for TRM tooling."""

from __future__ import annotations

import re
from pathlib import Path

_TAG_CMD_RE = re.compile(r"\\(iftagged|tagged|untagged)(?!\w)")

_PROJECT_TAG_VARIANTS: dict[str, frozenset[str]] = {
    "ESP32-P4": frozenset({"ESP32-P4-latest"}),
}


def _tag_matches_project(tag_list_str: str, base_project: str) -> bool:
    """Return True if *base_project* is listed in the comma-separated *tag_list_str*."""
    tags = {t.strip() for t in tag_list_str.split(",")}
    names = {base_project} | _PROJECT_TAG_VARIANTS.get(base_project, frozenset())
    return bool(tags & names)


def _find_brace_group(text: str, pos: int) -> tuple[int, int, str] | None:
    r"""Find the next ``{…}`` group starting from *pos*, skipping whitespace.

    Handles nested braces; treats ``\{`` / ``\}`` as literal (not delimiters).
    """
    i = pos
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    if i >= len(text) or text[i] != "{":
        return None
    start = i
    depth = 1
    i += 1
    while i < len(text) and depth > 0:
        ch = text[i]
        if ch == "\\" and i + 1 < len(text) and text[i + 1] in "{}":
            i += 2  # skip \{ or \}
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return (start, i, text[start + 1 : i - 1])


def _extract_tag_body(content: str) -> str:
    r"""Strip multi-line wrapper markers from a brace-group body.

    Handles ``{%\n…\n}`` and ``{\n…\n}`` patterns; inline bodies pass through.
    """
    multiline = False
    if content.startswith("%\n"):
        content = content[2:]
        multiline = True
    elif content.startswith("%\r\n"):
        content = content[3:]
        multiline = True
    elif content.startswith("\n"):
        content = content[1:]
        multiline = True
    elif content.startswith("\r\n"):
        content = content[2:]
        multiline = True
    if multiline and content.endswith("\n"):
        content = content[:-1]
    return content


def resolve_tags(text: str, base_project: str) -> str:
    r"""Resolve ``\tagged``, ``\untagged``, and ``\iftagged`` for *base_project*.

    Tagged content matching the base project is kept; non-matching content is
    removed.  ``\iftagged`` selects the appropriate branch.
    """
    result = text
    matches = list(_TAG_CMD_RE.finditer(result))

    for m in reversed(matches):
        cmd = m.group(1)
        cmd_start = m.start()

        # First brace group: tag list
        g1 = _find_brace_group(result, m.end())
        if g1 is None:
            continue
        tag_list = g1[2]

        # Second brace group: body (or true-branch for iftagged)
        g2 = _find_brace_group(result, g1[1])
        if g2 is None:
            continue
        body = g2[2]

        matches_tag = _tag_matches_project(tag_list, base_project)

        if cmd == "iftagged":
            # Third brace group: false-branch
            g3 = _find_brace_group(result, g2[1])
            if g3 is None:
                continue
            false_body = g3[2]
            end = g3[1]
            replacement = (
                _extract_tag_body(body) if matches_tag else _extract_tag_body(false_body)
            )
        elif cmd == "tagged":
            end = g2[1]
            replacement = _extract_tag_body(body) if matches_tag else ""
        else:  # untagged
            end = g2[1]
            replacement = "" if matches_tag else _extract_tag_body(body)

        if replacement == "":
            # Remove: extend to full line(s) when the match is the sole content
            line_start = result.rfind("\n", 0, cmd_start) + 1
            next_nl = result.find("\n", end)
            before = result[line_start:cmd_start]
            after = result[end:next_nl] if next_nl != -1 else result[end:]
            if before.strip() == "" and after.strip() == "":
                span_s = line_start
                span_e = next_nl + 1 if next_nl != -1 else len(result)
                result = result[:span_s] + result[span_e:]
            else:
                result = result[:cmd_start] + result[end:]
        else:
            result = result[:cmd_start] + replacement + result[end:]

    return result


def resolve_tags_in_file(file_path: Path, base_project: str) -> bool:
    """Resolve tag macros in *file_path* in place.  Returns True if changed."""
    if not file_path.exists():
        return False
    original = file_path.read_text(encoding="utf-8")
    resolved = resolve_tags(original, base_project)
    if resolved != original:
        file_path.write_text(resolved, encoding="utf-8")
        return True
    return False


def extend_indented_block(lines: list[str], start: int, *, include_blank_lines: bool = True) -> int:
    """Return the exclusive end index of the block beginning at *start*.

    The block extends forward while lines are blank or indented.  When
    *include_blank_lines* is false, a blank line terminates the block.
    """
    end = start + 1
    while end < len(lines):
        seg = lines[end]
        if not seg.strip():
            if include_blank_lines:
                end += 1
                continue
            break
        if seg.startswith((" ", "\t")):
            end += 1
            continue
        break
    return end


def update_glance_status(file_path: Path, module_lower: str, lang: str) -> bool:
    r"""Replace ``\textcolor{...}{...%}`` status with Published/已发布 for matching module lines."""
    if not file_path.exists():
        return False
    content = file_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    updated = False
    for i, line in enumerate(lines):
        if module_lower in line.lower():
            replacement = (
                rf"\\hyperref[mod:{module_lower}]{{已发布}}"
                if lang.upper() == "CN"
                else rf"\\hyperref[mod:{module_lower}]{{Published}}"
            )
            new_line = re.sub(r"\\textcolor\{[^}]*\}\{[^}]*%\}", replacement, line)
            if new_line != line:
                lines[i] = new_line
                updated = True
    if updated:
        file_path.write_text("\n".join(lines), encoding="utf-8")
    return updated


def remove_temp_label_block(file_path: Path, module_lower: str) -> bool:
    """Delete one temp-label block for ``mod:<module_lower>``.
    """
    if not file_path.exists():
        return False

    content = file_path.read_text(encoding="utf-8")
    if content.startswith("\ufeff"):
        content = content[1:]
    lines = content.split("\n")
    mod = re.escape(module_lower)
    label_re = re.compile(rf"\\label\s*\{{\s*mod:\s*{mod}\s*\}}", re.IGNORECASE)

    start = None
    for i, line in enumerate(lines):
        if label_re.search(line):
            start = i
            break
    if start is None:
        return False

    end = extend_indented_block(lines, start, include_blank_lines=True)

    new_lines = lines[:start] + lines[end:]
    new_content = "\n".join(new_lines)
    if new_content != content:
        file_path.write_text(new_content, encoding="utf-8")
        return True
    return False


_SUBFILE_RE = re.compile(r"\\subfile(?:include)?\{")


def _uncomment_tex_line(line: str) -> str:
    """Remove a single leading ``% `` or ``%`` from *line*, preserving indentation."""
    stripped = line.lstrip()
    indent = line[: len(line) - len(stripped)]
    if stripped.startswith("% "):
        return indent + stripped[2:]
    if stripped.startswith("%"):
        return indent + stripped[1:]
    return line


def _find_part_boundaries(lines: list[str]) -> list[int]:
    r"""Return indices of all ``\part{…}`` lines (commented or not)."""
    out: list[int] = []
    for i, line in enumerate(lines):
        clean = line.strip().lstrip("% ")
        if clean.startswith("\\part{"):
            out.append(i)
    return out


def uncomment_part_if_first_chapter(main_file: Path, module: str) -> bool:
    r"""Uncomment ``\part`` header and description if *module* is the first active chapter."""
    content = main_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    part_indices = _find_part_boundaries(lines)
    if not part_indices:
        return False

    module_upper = module.upper()
    target_pi: int | None = None
    for pi, part_idx in enumerate(part_indices):
        end = part_indices[pi + 1] if pi + 1 < len(part_indices) else len(lines)
        for j in range(part_idx, end):
            if re.search(
                rf"\\subfile(?:include)?\{{.*\b\d*-?{re.escape(module_upper)}",
                lines[j], re.IGNORECASE,
            ):
                target_pi = pi
                break
        if target_pi is not None:
            break

    if target_pi is None:
        return False

    part_line_idx = part_indices[target_pi]
    part_end = part_indices[target_pi + 1] if target_pi + 1 < len(part_indices) else len(lines)

    # Already uncommented → nothing to do
    if not lines[part_line_idx].strip().startswith("%"):
        return False

    # Count uncommented chapter lines in this part
    uncommented = 0
    for j in range(part_line_idx, part_end):
        s = lines[j].strip()
        if s.startswith("%"):
            continue
        if _SUBFILE_RE.match(s):
            uncommented += 1

    if uncommented != 1:
        return False

    # Uncomment \part line
    lines[part_line_idx] = _uncomment_tex_line(lines[part_line_idx])

    # Find description lines between \part and first \subfileinclude
    desc_candidates: list[int] = []
    for j in range(part_line_idx + 1, part_end):
        s = lines[j].strip()
        if not s:
            continue
        clean = s.lstrip("% ")
        if clean.startswith("\\subfile"):
            break
        if s.startswith("%"):
            desc_candidates.append(j)

    if len(desc_candidates) == 1:
        # Single line = description
        lines[desc_candidates[0]] = _uncomment_tex_line(lines[desc_candidates[0]])
    elif len(desc_candidates) >= 2:
        # First = internal note (keep), last = description (uncomment)
        lines[desc_candidates[-1]] = _uncomment_tex_line(lines[desc_candidates[-1]])

    new_content = "\n".join(lines)
    if new_content != content:
        main_file.write_text(new_content, encoding="utf-8")
        return True
    return False
