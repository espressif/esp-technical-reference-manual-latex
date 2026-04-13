#!/usr/bin/env python3
"""Set up TRM chapters (no-changes, normal, new). Interactive or subcommand CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from tools.trm_automation_tools.common.cli_ops import (
    prompt_choice as _prompt_choice,
    prompt_input as _prompt_input,
    prompt_input_optional as _prompt_input_optional,
    prompt_member_of as _prompt_member_of,
    prompt_validated as _prompt_validated,
)
from tools.trm_automation_tools.common.id_ops import is_valid_id_module_format
from tools.trm_automation_tools.setup import new as setup_new
from tools.trm_automation_tools.setup import no_changes as setup_no_changes
from tools.trm_automation_tools.setup import normal as setup_normal


def interactive_main() -> None:
    """Interactive entry-point: ask user for mode, then collect inputs."""
    print(f"{'=' * 60}")
    print("TRM Chapter Setup")
    print(f"{'=' * 60}\n")

    mode = _prompt_choice(
        "Select setup mode:",
        [
            "No-changes chapter (reference base project's chapter in latex-trm)",
            "Normal chapter (copy base chapter from latex-trm to Overleaf)",
            "New chapter (set up from outline template in Overleaf)",
        ],
    )

    if mode == 0:
        print("\n--- No-Changes Chapter Setup ---\n")
        base = _prompt_input("Base project (e.g., ESP32-P4)")
        target = _prompt_input("Target project (e.g., ESP32-S31)")
        module = _prompt_input("Module alias, e.g., ECDSA)")
        local = _prompt_choice(
            "Run mode:",
            [
                "Full (clone → modify → push → create MR)",
                "Local (modify files in working copy only)",
            ],
        )
        jira_ticket = ""
        if local == 0:
            jira_ticket = _prompt_input_optional(
                "Jira issue key (for MR description, e.g. TRMC5-12345)",
            )
        print()
        if local == 0:
            setup_no_changes.run_no_changes_full(
                base, target, module, jira_ticket=jira_ticket or None,
            )
        else:
            setup_no_changes.run_no_changes_local(base, target, module)

    elif mode == 1:
        print("\n--- Normal Chapter Setup ---\n")
        ol_id = _prompt_input("Overleaf repo ID")
        base = _prompt_input("Base project in latex-trm (e.g., ESP32-P4)")
        target_mid = _prompt_validated(
            "Target ID–Module (e.g., 45-I2S)",
            is_valid_id_module_format,
            "Use digits, a hyphen, then the module alias (e.g. 45-I2S, 08-2DDMA).",
        ).strip().upper()
        lang = _prompt_member_of(
            "Source language (EN/CN)",
            frozenset({"EN", "CN"}),
            default="EN",
        )
        print("Contacts for 00-shared/config/readme.tex (Module PM / Writer):")
        module_pm = _prompt_input_optional("Module PM name")
        writer = _prompt_input_optional("Writer name")
        print()
        setup_normal.setup_normal_chapter(
            ol_id,
            base,
            target_mid,
            lang,
            module_pm=module_pm,
            writer=writer,
        )

    elif mode == 2:
        print("\n--- New Chapter Setup ---\n")
        ol_id = _prompt_input("Overleaf repo ID")
        target_mid = _prompt_validated(
            "Target ID–Module (e.g., 45-I2S)",
            is_valid_id_module_format,
            "Use digits, a hyphen, then the module alias (e.g. 45-I2S, 08-2DDMA).",
        ).strip().upper()
        lang = _prompt_member_of(
            "Source language (EN/CN)",
            frozenset({"EN", "CN"}),
            default="EN",
        )
        print("Contacts for 00-shared/config/readme.tex (Module PM / Writer):")
        module_pm = _prompt_input_optional("Module PM name")
        writer = _prompt_input_optional("Writer name")
        print()
        setup_new.setup_new_chapter(
            ol_id,
            target_mid,
            lang,
            module_pm=module_pm,
            writer=writer,
        )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="set_up_trm_chapters.py",
        description=(
            "Set up TRM chapters. Use subcommands no-changes, normal, or new. "
            "Run with no arguments for interactive mode."
        ),
    )
    sub = parser.add_subparsers(dest="mode")

    p1 = sub.add_parser("no-changes", help="Set up a no-changes chapter in latex-trm")
    p1.add_argument("base_project", help="Base project (e.g., ESP32-P4)")
    p1.add_argument("target_project", help="Target project (e.g., ESP32-S31)")
    p1.add_argument(
        "module",
        help="Module alias (e.g. ECDSA)",
    )
    p1.add_argument(
        "jira_ticket_id",
        nargs="?",
        default="",
        help=(
            "Optional Jira ticket id for the MR description (e.g. TRMC5-12345), "
            "same style as publish_trm_chapters.py; adds a # Related / Closes line. "
            "Ignored with --local. If you use both, put the ticket before --local."
        ),
    )
    p1.add_argument(
        "--local",
        action="store_true",
        help="Only modify local working copy (no clone/push/MR)",
    )

    p2 = sub.add_parser("normal", help="Set up a normal chapter in Overleaf from a base")
    p2.add_argument("overleaf_id", help="Overleaf project ID")
    p2.add_argument("base_project", help="Base project in latex-trm (e.g., ESP32-P4)")
    p2.add_argument(
        "target_id_module",
        metavar="target_id_module",
        help="Target ID–Module (e.g. 45-I2S)",
    )
    p2.add_argument("source_lang", choices=["EN", "CN"], help="Source language")
    p2.add_argument(
        "--module-pm",
        default="",
        metavar="NAME",
        help="Module PM (written to 00-shared/config/readme.tex)",
    )
    p2.add_argument(
        "--writer",
        default="",
        metavar="NAME",
        help="Writer (written to 00-shared/config/readme.tex)",
    )

    p3 = sub.add_parser("new", help="Set up a new chapter in Overleaf from template")
    p3.add_argument("overleaf_id", help="Overleaf project ID")
    p3.add_argument(
        "target_id_module",
        metavar="target_id_module",
        help="Target ID–Module (e.g. 45-I2S)",
    )
    p3.add_argument("source_lang", choices=["EN", "CN"], help="Source language")
    p3.add_argument(
        "--module-pm",
        default="",
        metavar="NAME",
        help="Module PM (written to 00-shared/config/readme.tex)",
    )
    p3.add_argument(
        "--writer",
        default="",
        metavar="NAME",
        help="Writer (written to 00-shared/config/readme.tex)",
    )

    return parser


def main() -> None:
    if len(sys.argv) <= 1:
        interactive_main()
        return

    first = sys.argv[1]
    if first in ("-i", "--interactive"):
        interactive_main()
        return

    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.mode == "no-changes":
        if args.local:
            setup_no_changes.run_no_changes_local(
                args.base_project,
                args.target_project,
                args.module,
            )
        else:
            setup_no_changes.run_no_changes_full(
                args.base_project,
                args.target_project,
                args.module,
                jira_ticket=args.jira_ticket_id or None,
            )
    elif args.mode == "normal":
        setup_normal.setup_normal_chapter(
            args.overleaf_id,
            args.base_project,
            args.target_id_module,
            args.source_lang,
            module_pm=args.module_pm,
            writer=args.writer,
        )
    elif args.mode == "new":
        setup_new.setup_new_chapter(
            args.overleaf_id,
            args.target_id_module,
            args.source_lang,
            module_pm=args.module_pm,
            writer=args.writer,
        )
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
