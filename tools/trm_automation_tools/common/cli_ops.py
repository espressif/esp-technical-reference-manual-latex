"""Shared interactive CLI helpers for TRM tooling."""

from __future__ import annotations

import sys
from collections.abc import Callable


def prompt_choice(prompt: str, options: list[str]) -> int:
    """Prompt the user to pick from numbered *options*. Returns 0-based index."""
    print(prompt)
    for i, opt in enumerate(options, 1):
        print(f"   {i}. {opt}")
    while True:
        try:
            val = int(input("\nYour choice: ").strip())
            if 1 <= val <= len(options):
                return val - 1
            print(f"   Please enter 1–{len(options)}")
        except ValueError:
            print("   Please enter a valid number")
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(0)


def prompt_input(prompt: str, default: str | None = None) -> str:
    """Prompt user for a text value. Empty input returns *default* if given."""
    try:
        suffix = f" [{default}]" if default else ""
        while True:
            val = input(f"{prompt}{suffix}: ").strip()
            if val:
                return val
            if default:
                return default
            print("   Please enter a value")
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)


def prompt_input_optional(prompt: str) -> str:
    """Prompt for optional text; empty input means skip."""
    try:
        return input(f"{prompt} (optional, press Enter to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)


def prompt_member_of(
    prompt: str,
    allowed: frozenset[str],
    *,
    default: str | None = None,
    case_insensitive: bool = True,
) -> str:
    """Prompt until input is in *allowed* (after strip; optional case fold)."""
    allowed_norm = frozenset(a.upper() for a in allowed) if case_insensitive else allowed
    display = ", ".join(sorted(allowed))
    suffix = f" [{default}]" if default else ""
    try:
        while True:
            raw = input(f"{prompt}{suffix}: ").strip()
            if not raw:
                if default is not None:
                    d = default.upper() if case_insensitive else default
                    if d in allowed_norm:
                        return d
                print("   Please enter a value")
                continue
            val = raw.upper() if case_insensitive else raw
            if val in allowed_norm:
                return val
            print(f"   ❌ Must be one of: {display}. Please try again.")
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)


def prompt_validated(
    prompt: str,
    validator: Callable[[str], bool],
    invalid_hint: str,
    *,
    default: str | None = None,
) -> str:
    """Prompt until *validator* returns True for the entered string."""
    suffix = f" [{default}]" if default else ""
    try:
        while True:
            raw = input(f"{prompt}{suffix}: ").strip()
            if not raw:
                if default is not None:
                    if validator(default):
                        return default
                    print(f"   {invalid_hint}")
                    continue
                print("   Please enter a value")
                continue
            if validator(raw):
                return raw
            print(f"   {invalid_hint}")
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)
