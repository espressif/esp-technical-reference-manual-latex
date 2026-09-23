#!/usr/bin/env python3
"""Post GitLab Pages preview URLs as an MR note."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("authkey")
    parser.add_argument("project")
    parser.add_argument("mr_iid")
    parser.add_argument("--url", required=True, help="GitLab origin, e.g. https://host:port")
    parser.add_argument(
        "--pages-url",
        default="",
        help="GitLab Pages base URL (defaults to public/pages-url.txt or $CI_PAGES_URL)",
    )
    parser.add_argument(
        "--public-dir",
        type=Path,
        default=Path("public"),
    )
    return parser.parse_args()


def resolve_pages_url(args: argparse.Namespace) -> str:
    url_file = args.public_dir / "pages-url.txt"
    if url_file.is_file():
        from_file = url_file.read_text(encoding="utf-8").strip()
        if from_file:
            return from_file
    return args.pages_url or os.environ.get("CI_PAGES_URL", "")


def load_entries(public: Path) -> list[dict]:
    manifest = public / "preview-manifest.json"
    if manifest.is_file():
        return json.loads(manifest.read_text(encoding="utf-8"))
    return []


def build_note(pages_url: str, entries: list[dict]) -> str:
    base = pages_url.rstrip("/")
    lines = [
        "Browser preview (opens in the browser's PDF viewer):",
        "",
        f"- Index: [{base}/]({base}/)",
    ]
    for entry in entries:
        label = f"{entry['chip']} / {entry['name']}"
        size = entry.get("size_mb")
        suffix = f" ({size} MB)" if size else ""
        lines.append(f"- [{label}]({base}/{entry['pdf']}){suffix}")
    if not entries:
        lines.append("- No documents were built in this pipeline.")
    lines.append("")
    lines.append(
        "Published by GitLab Pages for this merge request; the deployment "
        "expires in two weeks."
    )
    return "\n".join(lines)


def post_note(origin: str, token: str, project: str, mr_iid: str, body: str) -> None:
    quoted = urllib.parse.quote(project, safe="")
    api = f"{origin.rstrip('/')}/api/v4/projects/{quoted}/merge_requests/{mr_iid}/notes"
    data = json.dumps({"body": body}).encode()
    req = urllib.request.Request(
        api,
        data=data,
        method="POST",
        headers={
            "PRIVATE-TOKEN": token,
            "Content-Type": "application/json",
        },
    )
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            if resp.status not in (200, 201):
                raise SystemExit(f"GitLab notes API returned {resp.status}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise SystemExit(f"GitLab notes API failed: {exc.code} {detail}") from exc


def main() -> int:
    args = parse_args()
    pages_url = resolve_pages_url(args)
    if not pages_url:
        print("No Pages URL (CI_PAGES_URL empty). Skip MR note.", file=sys.stderr)
        return 0
    body = build_note(pages_url, load_entries(args.public_dir))
    post_note(args.url, args.authkey, args.project, args.mr_iid, body)
    print("Posted preview note")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
