#!/usr/bin/env python3
r"""
Scan the repository for occurrences of \subfile{../...} and generate
reused_chapter_list.txt: each referenced .tex path plus the module folder path
(e.g. ./ESP32-C5/02-RISCVTRACENC__CN.tex, ./ESP32-C5/02-RISCVTRACENC).

Example usage:
    python3 tools/auto_backport/collect_reused_chapters.py

Output example:
    ./ESP32-C5/02-RISCVTRACENC
    ./ESP32-C5/02-RISCVTRACENC__CN.tex
    ./ESP32-C5/02-RISCVTRACENC__EN.tex
    ./ESP32-H2/03-DMA
    ./ESP32-H2/03-DMA__CN.tex
    ./ESP32-H2/03-DMA__EN.tex
"""

import os
import re

script_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(script_dir, "reused_chapter_list.txt")

# Match \subfile{../xxxx}
PATTERN = re.compile(r"\\subfile\{(\.\./[^}]+)\}")

# Basename like 02-RISCVTRACENC__CN.tex -> module folder name without __CN/__EN
MODULE_FROM_SUBFILE_TEX = re.compile(r"^(.+)/([^/]+)__(CN|EN)\.tex$")
MODULE_FROM_SUBFILE_TEX_ROOT = re.compile(r"^\./(.+)__(CN|EN)\.tex$")

# Root directory of the repository
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
results = set()


def normalize_repo_relative(path: str) -> str:
    # Make paths repo-relative and comparable to MR diffs: forward slashes, ``./`` prefix
    path = os.path.normpath(path).replace("\\", "/")
    return path if path.startswith("./") else "./" + path


def add_module_dir_for_subfile_tex(tex_path: str) -> None:
    # If path is .../__CN.tex or .../__EN.tex, also add .../basename-without-lang
    m = MODULE_FROM_SUBFILE_TEX.match(tex_path)
    if m:
        results.add(f"{m.group(1)}/{m.group(2)}")
        return
    m = MODULE_FROM_SUBFILE_TEX_ROOT.match(tex_path)
    if m:
        results.add(f"./{m.group(1)}")


for root, _, files in os.walk(repo_root):
    for name in files:
        # Only scan .tex files
        if not name.endswith(".tex"):
            continue

        path = os.path.join(root, name)

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue

        matches = PATTERN.findall(content)
        for m in matches:
            # Remove leading "../"
            cleaned = m[3:] if m.startswith("../") else m

            # Append .tex extension if missing
            if not cleaned.endswith(".tex"):
                cleaned += ".tex"

            # Normalize path and ensure it starts with "./"
            cleaned = normalize_repo_relative(cleaned)

            results.add(cleaned)
            add_module_dir_for_subfile_tex(cleaned)

# Output sorted results
with open(output_file, "w", encoding="utf-8") as f:
    for r in sorted(results):
        f.write(r + "\n")

print(f"Output written to: {output_file}")
