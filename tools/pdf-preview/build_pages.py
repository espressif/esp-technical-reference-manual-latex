#!/usr/bin/env python3
"""Publish CI-built TRM PDFs on GitLab Pages under public/.

Pages serves PDFs with `Content-Type: application/pdf` and no attachment
header, so the browser's built-in viewer opens them in place: reviewers who
cannot download files can still read (and search) the document.
"""

from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "public"
MANIFEST = PUBLIC / "preview-manifest.json"


def find_pdfs() -> list[Path]:
    """Return CI-built TRM PDFs under ``*/out/``, skipping temp-label files."""
    pdfs: list[Path] = []
    for path in sorted(ROOT.glob("*/out/*.pdf")):
        if path.name.startswith("temp-labels"):
            continue
        pdfs.append(path)
    return pdfs


def write_index(entries: list[dict]) -> None:
    """Write ``public/index.html`` with a link for each published PDF.

    Each *entry* must include ``chip``, ``name``, ``pdf`` (relative href),
    and ``size_mb``. If *entries* is empty, the page states that no PDFs
    were built.
    """
    items = []
    for entry in entries:
        label = html.escape(f"{entry['chip']} / {entry['name']}")
        href = html.escape(entry["pdf"])
        items.append(f'<li><a href="{href}">{label}</a> ({entry["size_mb"]:.1f} MB)</li>')
    if not items:
        items.append("<li>No PDFs were built in this pipeline.</li>")
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "index.html").write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>TRM preview</title>"
        "<style>body{font:16px/1.5 sans-serif;margin:24px auto;max-width:820px}"
        "li{margin:8px 0}</style></head>"
        "<body><h1>TRM preview</h1>"
        "<p>Documents open in the browser's PDF viewer. No download required.</p>"
        f"<ul>{''.join(items)}</ul></body></html>",
        encoding="utf-8",
    )


def main() -> int:
    """Copy built PDFs into ``public/``, write the index and manifest, then exit."""
    entries: list[dict] = []
    for pdf in find_pdfs():
        chip = pdf.parts[-3]  # CHIP/out/file.pdf
        dest = PUBLIC / chip
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf, dest / pdf.name)
        size_mb = pdf.stat().st_size / 1024 / 1024
        print(f"published {chip}/{pdf.name}  {size_mb:.1f} MB")
        entries.append(
            {
                "chip": chip,
                "name": pdf.stem,
                "pdf": f"{chip}/{pdf.name}",
                "size_mb": round(size_mb, 1),
            }
        )

    write_index(entries)
    MANIFEST.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    total = sum(entry["size_mb"] for entry in entries)
    print(f"wrote {PUBLIC / 'index.html'} ({len(entries)} documents, {total:.1f} MB)")
    if not entries:
        print("no PDFs found under */out/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
