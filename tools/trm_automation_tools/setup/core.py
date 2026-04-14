#!/usr/bin/env python3
"""Shared helpers for TRM chapter setup (env, discovery, copy, transforms, Git/GitLab).

CLI and interactive flow live in ``set_up_trm_chapters.py``. Mode implementations
import this module as ``core``.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import git as gitpython

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
from tools.trm_automation_tools.common.repo_ops import (
    authenticated_https_clone_url_for_project_id as _auth_clone_url_for_project_id,
    clone_overleaf_repo as _clone_overleaf_repo_common,
)
from tools.trm_automation_tools.common.trm_env import get_trm_env_values as _get_trm_env_values
from tools.trm_automation_tools.common.fs_ops import find_chip_spec_dir
import tools.trm_automation_tools.common.tex_sections as _tex_sections_common
from tools.trm_automation_tools.common.text_ops import (
    extend_indented_block as _extend_indented_block,
    remove_temp_label_block as _remove_temp_label_block_common,
)

# Environment variables (populated by _load_env)
_env_loaded = False
_OVERLEAF_TOKEN: str | None = None
_GITLAB_TOKEN: str | None = None
_GITLAB_URL: str | None = None
_LATEX_TRM_REPO_ID: str | None = None


# ============================================================
# Environment & Auth
# ============================================================

def _load_env():
    global _env_loaded, _OVERLEAF_TOKEN, _GITLAB_TOKEN
    global _GITLAB_URL, _LATEX_TRM_REPO_ID
    if _env_loaded:
        return
    values = _get_trm_env_values()
    _OVERLEAF_TOKEN = values["OVERLEAF_TOKEN"]
    _GITLAB_TOKEN = values["GITLAB_TOKEN"]
    _GITLAB_URL = values["GITLAB_URL"]
    _LATEX_TRM_REPO_ID = values["LATEX_TRM_REPO_ID"]
    _env_loaded = True


# ============================================================
# Cloning Helpers
# ============================================================

def _get_trm_clone_url() -> str:
    """Build an authenticated latex-trm clone URL from GitLab API (project HTTP URL + token)."""
    _load_env()
    if not (_GITLAB_URL and _LATEX_TRM_REPO_ID and _GITLAB_TOKEN):
        sys.exit(
            "❌ Cannot determine latex-trm clone URL. "
            "Set GITLAB_URL and GITLAB_TOKEN in environment.py.",
        )
    return _auth_clone_url_for_project_id(_GITLAB_URL, _LATEX_TRM_REPO_ID, _GITLAB_TOKEN)


def clone_latex_trm(dest: Path):
    """Clone the latex-trm repository. Returns ``git.Repo``."""
    url = _get_trm_clone_url()
    print("📥 Cloning latex-trm repository...")
    repo = gitpython.Repo.clone_from(url, dest)
    print("✅ Cloned latex-trm")
    return repo


def clone_overleaf(overleaf_id: str, dest: Path):
    """Clone an Overleaf project. Returns ``git.Repo``."""
    return _clone_overleaf_repo_common(overleaf_id, _OVERLEAF_TOKEN, dest, depth=1)


# ============================================================
# Chapter folder discovery (ID–Module tokens in latex-trm)
# ============================================================


def find_base_id_module(base_dir: Path, module: str) -> str | None:
    """Find a folder named ``NN-Alias`` (ID–Module, e.g. ``25-ECDSA``) in *base_dir* matching *module*."""
    pattern = re.compile(rf"^\d+-{re.escape(module)}$", re.IGNORECASE)
    for item in sorted(base_dir.iterdir()):
        if item.is_dir() and pattern.match(item.name):
            return item.name
    return None


def _resolve_modulefiles_folder(en_main: Path, tex_content: str) -> tuple[Path, str] | None:
    r"""Parse ``\def \\modulefiles {PATH}`` and resolve *PATH* relative to *en_main*'s parent.

    Chapters may use ``./NN-Alias`` or a repo-relative form like ``../ESP32-C5/26-SHA``.
    Returns ``(resolved_module_folder, id_module)`` where *id_module* is the
    resolved folder's name (e.g. ``26-SHA``).
    """
    m = re.search(r"\\def\s*\\modulefiles\s*\{([^}]+)\}", tex_content)
    if not m:
        return None
    spec = m.group(1).strip()
    try:
        module_folder = (en_main.parent / spec).resolve()
    except OSError:
        return None
    if not module_folder.is_dir():
        return None
    return module_folder, module_folder.name


def _try_find_base_module_in_dir(base_dir: Path, module: str) -> tuple[Path, Path, Path, str] | None:
    r"""Locate chapter folder + main ``.tex`` files in *base_dir*, preferring ``-latest``.

    Returns ``None`` if mains or ``\modulefiles`` / module folder are missing.
    """
    mu = module.upper()

    pat_regular = re.compile(rf"^\d+-{re.escape(mu)}__(?:EN|CN)\.tex$", re.IGNORECASE)
    pat_latest = re.compile(rf"^\d+-{re.escape(mu)}-latest__(?:EN|CN)\.tex$", re.IGNORECASE)

    regular: dict[str, Path | None] = {"EN": None, "CN": None}
    latest: dict[str, Path | None] = {"EN": None, "CN": None}

    for item in base_dir.iterdir():
        if not item.is_file():
            continue
        lang = "EN" if "__EN" in item.name else "CN" if "__CN" in item.name else None
        if lang is None:
            continue
        if pat_latest.match(item.name):
            latest[lang] = item
        elif pat_regular.match(item.name):
            regular[lang] = item

    en_main = latest["EN"] or regular["EN"]
    cn_main = latest["CN"] or regular["CN"]
    if not en_main or not cn_main:
        return None

    content = en_main.read_text(encoding="utf-8")
    if content.startswith("\ufeff"):
        content = content[1:]
    resolved = _resolve_modulefiles_folder(en_main, content)
    if resolved is None:
        return None
    module_folder, folder_name = resolved

    print(f"✅ Found base chapter (ID–Module): {base_dir.name}/{folder_name}")
    print(f"   Main files: {en_main.name}, {cn_main.name}")
    return module_folder, en_main, cn_main, folder_name


def find_base_module(base_dir: Path, module: str) -> tuple[Path, Path, Path, str]:
    """Locate chapter folder + main ``.tex`` files in *base_dir*, preferring ``-latest``."""
    mu = module.upper()
    r = _try_find_base_module_in_dir(base_dir, module)
    if r is None:
        sys.exit(f"❌ Main .tex files for {mu} not found in {base_dir.name}/")
    return r


def find_subfile_upstream_to_chapter(project_dir: Path, module: str) -> tuple[str, str] | None:
    r"""If *project_dir* reuses a chapter via ``\subfile{../OTHER/NN-Alias__EN}``, return ``(OTHER, NN-Alias)``.

    Scans ``*-main__EN.tex`` for a ``\subfile`` that points to another project folder
    (``../ProjectName/``) and a main file whose module alias matches *module*
    (e.g. ``SHA`` matches ``26-SHA__EN``). Allows optional whitespace inside the braced path.
    """
    main_en, _ = find_main_files(project_dir)
    if not main_en:
        return None
    content = main_en.read_text(encoding="utf-8")
    np = re.escape(module)
    pat = re.compile(
        rf"\\subfile\s*\{{\s*\.\./\s*([^/]+?)\s*/\s*(\d+-{np})__EN\s*\}}",
        re.IGNORECASE,
    )
    m = pat.search(content)
    return (m.group(1), m.group(2)) if m else None


def find_base_module_with_upstream(
    trm_path: Path,
    base_project: str,
    module: str,
) -> tuple[Path, Path, Path, str]:
    r"""Like ``find_base_module`` but if *base_project* has no local mains for *module*,
    follow ``\subfile{{../UPSTREAM/NN-Alias__EN}}`` in that project's ``*-main__EN.tex``
    and load the chapter from *UPSTREAM*.
    """
    mu = module.upper()
    base_dir = trm_path / base_project
    if not base_dir.is_dir():
        sys.exit(f"❌ Base project '{base_project}' not found in latex-trm")

    r = _try_find_base_module_in_dir(base_dir, module)
    if r is not None:
        return r

    upstream = find_subfile_upstream_to_chapter(base_dir, module)
    if upstream is None:
        sys.exit(
            f"❌ Main .tex files for {mu} not found in {base_project}/, "
            f"and no \\subfile{{../.../NN-{mu}__EN}} reference in *-main__EN.tex",
        )

    up_project, up_id_module = upstream
    up_dir = trm_path / up_project
    if not up_dir.is_dir():
        sys.exit(
            f"❌ Upstream project '{up_project}' (from \\subfile) not found under latex-trm",
        )
    print(
        f"ℹ️  {base_project} reuses {mu} via \\subfile → {up_project}/{up_id_module} "
        f"— using chapter from {up_project}/",
    )
    r = _try_find_base_module_in_dir(up_dir, module)
    if r is None:
        sys.exit(
            f"❌ Could not locate chapter {mu} under upstream project {up_project}/ "
            f"(expected {up_id_module}__EN/CN.tex and folder)",
        )
    return r


# ============================================================
# Overleaf Placeholder Detection
# ============================================================

# Top-level dirs that are not the module placeholder (sorted before ``NN-Alias``).
_OVERLEAF_NON_MODULE_DIRS = frozenset({
    "00-shared",
    "00-chip-spec-content",
    "00-chip-spec-settings",
})


def find_module_placeholder(ol_path: Path) -> str | None:
    """Return the placeholder folder name (e.g. ``NN-Alias``) in *ol_path*."""
    for item in sorted(ol_path.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            if item.name in _OVERLEAF_NON_MODULE_DIRS:
                continue
            return item.name
    return None


def infer_root_main_id_module(ol_path: Path) -> str | None:
    """Infer ID–Module prefix from root-level ``*__EN.tex`` / ``*__CN.tex`` files.

    Used when there is no module placeholder directory but root mains still use a
    placeholder prefix (e.g. ``NN-Alias__EN.tex``) or already match the target
    (e.g. ``12-ECC__EN.tex``).
    """
    def _prefixes(lang: str) -> list[str]:
        suf = f"__{lang}.tex"
        out: list[str] = []
        for p in sorted(ol_path.glob(f"*{suf}")):
            if p.is_file() and p.parent == ol_path and p.name.endswith(suf):
                out.append(p.name[: -len(suf)])
        return out

    en = _prefixes("EN")
    cn = _prefixes("CN")
    if not en and not cn:
        return None
    if en and cn and en[0] != cn[0]:
        print(
            "   ⚠️  Root main prefixes differ between __EN and __CN; using EN",
        )
    return en[0] if en else cn[0]


def resolve_overleaf_source_id(ol_path: Path, target_id_module: str) -> tuple[str | None, str]:
    """Resolve the source module id used for root mains / renames in Overleaf trees.

    Returns ``(placeholder_folder, source_id)`` where:
    - ``placeholder_folder`` is the detected module folder (e.g. ``NN-Alias``), or ``None``.
    - ``source_id`` is the id to use for root-main lookups / rename source:
      placeholder folder name when present, else inferred root-main prefix, else target id.
    """
    placeholder_folder = find_module_placeholder(ol_path)
    if placeholder_folder:
        print(f"✅ Found Overleaf placeholder: {placeholder_folder}")
        return placeholder_folder, placeholder_folder

    print(
        "ℹ️  No module placeholder folder found; continuing — chapter copy goes to "
        f"./{target_id_module}/; root mains use inferred or target id.",
    )
    source_id = infer_root_main_id_module(ol_path) or target_id_module
    return None, source_id


def ensure_root_main_modulefiles(ol_path: Path, target_id_module: str):
    r"""Ensure root EN/CN mains use ``\def \\modulefiles {./<target_id_module>}``."""
    expected = f"\\def \\modulefiles {{./{target_id_module}}}"
    for lang in ("EN", "CN"):
        mf = ol_path / f"{target_id_module}__{lang}.tex"
        if not mf.exists():
            continue
        content = mf.read_text(encoding="utf-8")
        if expected in content:
            print(f"   ✅ {mf.name} correct")
            continue
        content = re.sub(
            r"\\def\s*\\modulefiles\s*\{[^}]*\}", expected, content,
        )
        mf.write_text(content, encoding="utf-8")
        print(f"   ✅ Fixed \\modulefiles in {mf.name}")


def move_non_source_main_to_module(ol_path: Path, target_id_module: str, source_lang: str):
    """Move non-source-language root main into the module folder, if both exist."""
    non_source = "CN" if source_lang.upper() == "EN" else "EN"
    ns_file = ol_path / f"{target_id_module}__{non_source}.tex"
    mod_dir = ol_path / target_id_module
    if ns_file.exists() and mod_dir.exists():
        dest = mod_dir / ns_file.name
        shutil.move(str(ns_file), str(dest))
        print(
            f"   ✅ Moved {ns_file.name} → "
            f"{target_id_module}/{ns_file.name}",
        )
    else:
        print(f"   ⚠️  File or folder not found for move operation")


# ============================================================
# Rename Utility
# ============================================================

def rename_in_repo(ol_path: Path, old_name: str, new_name: str):
    """Replace *old_name* with *new_name* in file/folder names and ``.tex``/``.sty`` contents."""
    if old_name == new_name:
        return

    for ext in ("*.tex", "*.sty"):
        for f in ol_path.rglob(ext):
            content = f.read_text(encoding="utf-8")
            if old_name in content:
                f.write_text(content.replace(old_name, new_name), encoding="utf-8")

    for item in sorted(ol_path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if old_name in item.name:
            new_path = item.parent / item.name.replace(old_name, new_name)
            item.rename(new_path)
            print(f"   Renamed: {item.name} → {new_path.name}")


# ============================================================
# Temp-Labels Helpers
# ============================================================

def comment_out_temp_label(file_path: Path, module_lower: str) -> tuple[bool, bool]:
    """Comment out the line containing ``mod:<module>`` and following block in temp-labels."""
    if not file_path.exists():
        return (False, False)

    content = file_path.read_text(encoding="utf-8")
    if content.startswith("\ufeff"):
        content = content[1:]

    lines = content.split("\n")
    needle = f"mod:{module_lower}".lower()

    start: int | None = None
    for i, line in enumerate(lines):
        if needle in line.lower():
            start = i
            break
    if start is None:
        return (False, False)

    end = _extend_indented_block(lines, start, include_blank_lines=True)

    changed = False
    for i in range(start, end):
        line = lines[i]
        if not line.strip():
            continue
        stripped = line.lstrip()
        if stripped.startswith("%"):
            continue
        lines[i] = "% " + line
        changed = True

    if changed:
        file_path.write_text("\n".join(lines), encoding="utf-8")
    return (True, changed)


def remove_temp_label(file_path: Path, module_lower: str) -> bool:
    """Delete the temp-label block for *module_lower* entirely."""
    return _remove_temp_label_block_common(file_path, module_lower)


# ============================================================
# Content Transfer
# ============================================================

def extract_outline_template(template_path: Path) -> str:
    r"""Extract chapter content (``\hypertarget`` through ``\end{document}``, inclusive)."""
    content = template_path.read_text(encoding="utf-8")
    return _tex_sections_common.extract_chapter_content(content, template_path.name)


def find_outline_template(shared_dir: Path, lang: str) -> Path | None:
    """Locate the outline-template file for *lang* inside *shared_dir*."""
    lang_lower = lang.lower()
    for name in (
        f"outline-template-{lang_lower}.tex",
        f"outline-template.{lang_lower}.tex",
        f"outline_template_{lang_lower}.tex",
        f"outline-template_{lang_lower}.tex",
    ):
        p = shared_dir / name
        if p.exists():
            return p
    for p in shared_dir.iterdir():
        if "outline-template" in p.name.lower() and lang_lower in p.name.lower():
            return p
    return None


# ============================================================
# Copy Module Folder
# ============================================================

def _resolve_latest_files(directory: Path) -> int:
    """Prefer ``-latest`` variants over their non-latest counterparts."""
    pat_tex = re.compile(r"^(.+)-latest(__(?:EN|CN)\.tex)$", re.IGNORECASE)
    pat_other = re.compile(r"^(.+)[_-]latest(\.\w+)$", re.IGNORECASE)

    resolved = 0
    for f in sorted(directory.rglob("*")):
        if not f.is_file():
            continue
        m = pat_tex.match(f.name) or pat_other.match(f.name)
        if not m:
            continue
        clean_name = m.group(1) + m.group(2)
        non_latest = f.parent / clean_name
        if non_latest.exists():
            non_latest.unlink()
        f.rename(f.parent / clean_name)
        resolved += 1
    return resolved


def remove_latest_suffix_in_subfile_refs(*paths: Path) -> list[str]:
    r"""Remove ``-latest`` from ``\subfile{}`` references in ``.tex`` files.

    *paths* can be directories (recursively scanned) or individual files.
    Returns a list of relative display names for files that were modified.
    """
    pat = re.compile(r"\\subfile\s*\{[^}]*\}")
    modified: list[str] = []
    tex_files: list[Path] = []
    for p in paths:
        if p.is_dir():
            tex_files.extend(sorted(p.rglob("*.tex")))
        elif p.is_file() and p.suffix == ".tex":
            tex_files.append(p)
    for f in tex_files:
        content = f.read_text(encoding="utf-8")
        new_content = pat.sub(lambda m: m.group(0).replace("-latest", ""), content)
        if new_content != content:
            f.write_text(new_content, encoding="utf-8")
            modified.append(f.name)
    return modified


def _snapshot_tex_under(folder: Path) -> dict[str, str]:
    """Map relative POSIX path → file text for every ``*.tex`` under *folder*."""
    if not folder.exists():
        return {}
    out: dict[str, str] = {}
    for f in folder.rglob("*.tex"):
        rel = f.relative_to(folder).as_posix()
        out[rel] = f.read_text(encoding="utf-8")
    return out


def _resolve_tex_template_snapshot(
    rel: str,
    tex_snapshots: dict[str, str],
    placeholder: str,
    dest_id_module: str,
) -> str | None:
    """Map post-copy relative path back to the pre-rmtree template key.

    Template files often use the placeholder ID–Module (e.g. ``NN-Alias-reg__EN.tex``) while
    the copy uses *dest_id_module* (e.g. ``45-I2S-reg__EN.tex``).
    """
    t = tex_snapshots.get(rel)
    if t is not None:
        return t
    if placeholder != dest_id_module:
        return tex_snapshots.get(rel.replace(dest_id_module, placeholder))
    return None


def _merge_copied_tex_with_templates(
    dest_dir: Path,
    tex_snapshots: dict[str, str],
    placeholder: str,
    dest_id_module: str,
) -> int:
    r"""For each copied ``.tex``, if the pre-copy template had chapter content, keep its preamble.

    Replaces only the chapter content region (``\hypertarget`` through ``\end{document}``) in
    the template with the matching region from the latex-trm copy (after ID–Module renames).

    Returns the number of files merged.
    """
    merged = 0
    for f in sorted(dest_dir.rglob("*.tex")):
        rel = f.relative_to(dest_dir).as_posix()
        template = _resolve_tex_template_snapshot(
            rel, tex_snapshots, placeholder, dest_id_module,
        )
        if not template:
            continue
        copied = f.read_text(encoding="utf-8")
        merged_text = _tex_sections_common.merge_template_chapter_content(template, copied)
        if merged_text is None:
            if _tex_sections_common.try_find_chapter_content_start(template.split("\n")) is not None:
                if _tex_sections_common.try_extract_chapter_content(copied) is None:
                    print(
                        f"   ⚠️  Template has \\hypertarget but could not extract matching "
                        f"chapter content from copied {rel}; keeping full copy",
                    )
            continue
        f.write_text(merged_text, encoding="utf-8")
        merged += 1
    if merged:
        print(
            f"   Merged chapter content from base into {merged} .tex file(s) "
            f"(Overleaf preamble kept)",
        )
    return merged


def copy_module_folder(
    src_dir: Path,
    dest_dir: Path,
    src_id_module: str,
    dest_id_module: str,
    *,
    merge_placeholder: str | None = None,
):
    r"""Copy *src_dir* into *dest_dir*, renaming *src_id_module* → *dest_id_module*.

    Both are full ID–Module strings (e.g. ``35-I2S`` → ``45-I2S``).

    If *dest_dir* already exists (Overleaf template), each ``*.tex`` whose pre-copy
    template contained ``\hypertarget`` keeps the template preamble; only the region from
    that first ``\hypertarget`` through ``\end{document}`` is taken from the latex-trm source.
    """
    tex_snapshots = _snapshot_tex_under(dest_dir) if dest_dir.exists() else {}

    # Preserve the sources/ folder
    saved_sources = None
    sources_dir = dest_dir / "sources"
    if sources_dir.is_dir():
        saved_sources = dest_dir.parent / f".{dest_dir.name}_sources_bak"
        shutil.copytree(sources_dir, saved_sources)

    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    if saved_sources and saved_sources.is_dir():
        shutil.copytree(saved_sources, sources_dir)
        shutil.rmtree(saved_sources)

    file_count = 0
    for item in src_dir.iterdir():
        if item.name in ("sources", "placeholder.temp"):
            continue
        dest_name = item.name.replace(src_id_module, dest_id_module)
        dst = dest_dir / dest_name

        if item.is_dir():
            shutil.copytree(
                item, dst,
                ignore=shutil.ignore_patterns("placeholder.temp", "sources"),
            )
            for f in sorted(dst.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if src_id_module in f.name:
                    f.rename(
                        f.parent / f.name.replace(src_id_module, dest_id_module),
                    )
            for f in dst.rglob("*.tex"):
                c = f.read_text(encoding="utf-8")
                if src_id_module in c:
                    f.write_text(
                        c.replace(src_id_module, dest_id_module),
                        encoding="utf-8",
                    )
            file_count += sum(1 for f in dst.rglob("*") if f.is_file())
        else:
            shutil.copy2(item, dst)
            if dst.suffix == ".tex":
                c = dst.read_text(encoding="utf-8")
                if src_id_module in c:
                    dst.write_text(
                        c.replace(src_id_module, dest_id_module),
                        encoding="utf-8",
                    )
            file_count += 1

    n_latest = _resolve_latest_files(dest_dir)
    if n_latest:
        print(f"   Resolved {n_latest} -latest file(s) (non-latest duplicates removed)")
        file_count -= n_latest

    if tex_snapshots:
        ph = merge_placeholder if merge_placeholder is not None else dest_dir.name
        _merge_copied_tex_with_templates(dest_dir, tex_snapshots, ph, dest_id_module)

    print(
        f"   Copied {file_count} files "
        f"(renamed {src_id_module} → {dest_id_module})",
    )


# ============================================================
# Overleaf readme (Module PM / Writer)
# ============================================================

def update_readme_module_contacts(readme_path: Path, module_pm: str, writer: str) -> bool:
    r"""Fill ``\item Module PM:`` and ``\item Writer:`` in readme.tex.
    """
    if not readme_path.exists():
        print(f"   ⚠️  readme not found: {readme_path}")
        return False
    text = readme_path.read_text(encoding="utf-8")
    if text.startswith("\ufeff"):
        text = text[1:]
    orig = text

    pm_name = " ".join(module_pm.strip().split())
    wr_name = " ".join(writer.strip().split())

    # Line-by-line: replace the *whole* body of each matching line; preserve line ending (\n or \r\n).
    pm_head = re.compile(r"^\s*\\item\s+Module\s+PM\s*[:：]", re.IGNORECASE)
    wr_head = re.compile(r"^\s*\\item\s+Writer\s*[:：]", re.IGNORECASE)
    pm_prefix = re.compile(r"^(\s*\\item\s+Module\s+PM)\s*[:：]\s*", re.IGNORECASE)
    wr_prefix = re.compile(r"^(\s*\\item\s+Writer)\s*[:：]\s*", re.IGNORECASE)

    lines = text.splitlines(True)
    out: list[str] = []
    pm_done = not pm_name
    wr_done = not wr_name
    n_pm = n_wr = 0

    for line in lines:
        body = line.rstrip("\r\n")
        eol = line[len(body) :]

        if not pm_done and pm_head.match(body):
            m = pm_prefix.match(body)
            if m:
                out.append(m.group(1) + ": " + pm_name + eol)
                pm_done = True
                n_pm = 1
                continue
        if not wr_done and wr_head.match(body):
            m = wr_prefix.match(body)
            if m:
                out.append(m.group(1) + ": " + wr_name + eol)
                wr_done = True
                n_wr = 1
                continue
        out.append(line)

    text = "".join(out)

    if pm_name and n_pm == 0:
        print(
            "   ⚠️  No line matching '\\item Module PM:' (with optional indent) — "
            "readme.tex not updated for PM",
        )
    if wr_name and n_wr == 0:
        print(
            "   ⚠️  No line matching '\\item Writer:' (with optional indent) — "
            "readme.tex not updated for Writer",
        )

    if text == orig:
        return False
    readme_path.write_text(text, encoding="utf-8")
    return True


# ============================================================
# Existing No-Changes Helpers (Mode 1)
# ============================================================

def find_main_files(project_dir: Path) -> tuple[Path | None, Path | None]:
    """Find ``*-main__EN.tex`` and ``*-main__CN.tex`` in *project_dir*."""
    en = list(project_dir.glob("*-main__EN.tex"))
    cn = list(project_dir.glob("*-main__CN.tex"))
    return (en[0] if en else None, cn[0] if cn else None)


def find_upstream_reference(project_dir: Path, module: str) -> tuple[str, str] | None:
    r"""Check whether *project_dir* already reuses a chapter via ``\subfile`` (same *module*)."""
    return find_subfile_upstream_to_chapter(project_dir, module)


def update_modulefiles(tex_file: Path, base_project: str, id_module: str) -> bool:
    r"""Rewrite ``\modulefiles`` from ``./NN-Alias`` to ``../BASE/NN-Alias``."""
    content = tex_file.read_text(encoding="utf-8")
    target = f"../{base_project}/{id_module}"
    if f"\\def \\modulefiles {{{target}}}" in content:
        return False

    old_literal = f"\\def \\modulefiles {{./{id_module}}}"
    if old_literal in content:
        content = content.replace(old_literal, f"\\def \\modulefiles {{{target}}}")
        tex_file.write_text(content, encoding="utf-8")
        return True

    old_regex = rf"\\def\s*\\modulefiles\s*\{{\./{re.escape(id_module)}\}}"
    if re.search(old_regex, content):
        content = re.sub(old_regex, f"\\def \\modulefiles {{{target}}}", content)
        tex_file.write_text(content, encoding="utf-8")
        return True

    raise ValueError(
        f"Cannot find \\modulefiles definition for {id_module} in {tex_file.name}."
    )


def update_main_file(
    main_file: Path,
    module: str,
    base_project: str,
    base_id_module: str,
    lang: str,
) -> bool:
    r"""Replace ``\subfileinclude`` with ``\subfile{{../BASE/...}}``."""
    content = main_file.read_text(encoding="utf-8")
    new_line = f"\\subfile{{../{base_project}/{base_id_module}__{lang}}}"
    if new_line in content:
        return False
    pat = re.compile(
        rf"^(%?\s*)(\\subfileinclude\{{\d+-{re.escape(module)}__{re.escape(lang)}\}})",
        re.MULTILINE | re.IGNORECASE,
    )
    new_content, count = pat.subn(lambda _: new_line, content)
    if count > 0:
        main_file.write_text(new_content, encoding="utf-8")
        return True
    raise ValueError(
        f"Cannot find {module} chapter reference in {main_file.name}."
    )

