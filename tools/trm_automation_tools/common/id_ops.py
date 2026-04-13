"""Shared ID-Module helpers (chapter folder token ``NN-Alias``, e.g. ``45-I2S``)."""

from __future__ import annotations

import re
import sys

# Chapter id (digits), hyphen, module alias (e.g. ``45-I2S``, ``08-2DDMA``).
_ID_MODULE_UI_PATTERN = re.compile(r"^\d+-[A-Za-z0-9][A-Za-z0-9]*$")


def is_valid_id_module_format(s: str) -> bool:
    """True if *s* matches the interactive ID–Module shape ``NN-Alias`` (e.g. ``45-I2S``)."""
    return bool(_ID_MODULE_UI_PATTERN.fullmatch(s.strip()))


def parse_id_module(id_module: str) -> tuple[str, str]:
    """Parse ``NN-Alias`` into ``(chapter_id, module)``."""
    m = re.match(r"^(\d+)-(.+)$", id_module)
    if not m:
        sys.exit(
            f"❌ Invalid ID–Module format: '{id_module}'. "
            "Expected 'NN-Alias' (e.g., '45-I2S').",
        )
    return m.group(1), m.group(2)


def module_from_id_module(id_module: str) -> str:
    """Return the module alias, e.g. ``25-ECDSA`` → ``ECDSA``."""
    if "-" in id_module:
        return id_module.split("-", 1)[1]
    return id_module
