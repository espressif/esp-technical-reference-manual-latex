#!/usr/bin/env python3
"""Publish TRM chapters from Overleaf to GitLab. Interactive or positional CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from tools.trm_automation_tools.common.cli_ops import prompt_validated as _prompt_validated
from tools.trm_automation_tools.publish.core import publish_trm_chapters


def interactive_publish_main() -> None:
    """Prompt for Overleaf id and Jira ticket, then run the publish flow."""
    print(f"{'=' * 60}")
    print("Publish TRM Chapters (Overleaf → GitLab)")
    print(f"{'=' * 60}\n")

    def _overleaf_id_ok(s: str) -> bool:
        if not s or "/" in s or " " in s or len(s) < 4:
            return False
        return s.replace("-", "").replace("_", "").isalnum()

    overleaf_id = _prompt_validated(
        "Overleaf project ID (from the project URL)",
        _overleaf_id_ok,
        "Enter the project id only (no URL, no spaces), e.g. the hex string from "
        "https://www.overleaf.com/project/<id>.",
    )
    jira_ticket_id = _prompt_validated(
        "Jira ticket id for the MR description (e.g. TRMC5-12345)",
        lambda s: bool(s) and " " not in s and "/" not in s,
        "Enter a ticket key (e.g. TRMC5-12345), not a URL or sentence.",
    )
    print()
    publish_trm_chapters(overleaf_id, jira_ticket_id)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="publish_trm_chapters.py",
        description=(
            "Publish TRM chapter sources from Overleaf to GitLab (figures + latex-trm) and "
            "open merge requests. Run with no arguments for interactive mode."
        ),
    )
    parser.add_argument(
        "overleaf_id",
        nargs="?",
        help="Overleaf project id (from https://www.overleaf.com/project/<id>)",
    )
    parser.add_argument(
        "jira_ticket_id",
        nargs="?",
        help="Jira ticket id for MR text (e.g. TRMC5-12345)",
    )
    return parser


def main() -> None:
    if len(sys.argv) <= 1:
        interactive_publish_main()
        return

    first = sys.argv[1]
    if first in ("-i", "--interactive"):
        interactive_publish_main()
        return

    parser = _build_arg_parser()
    args = parser.parse_args()

    if not args.overleaf_id or not args.jira_ticket_id:
        parser.error("the following arguments are required: overleaf_id, jira_ticket_id")

    publish_trm_chapters(args.overleaf_id, args.jira_ticket_id)


if __name__ == "__main__":
    main()
