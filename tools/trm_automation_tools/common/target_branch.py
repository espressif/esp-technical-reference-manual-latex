"""Resolve TRM merge-request target branch from the repo document config file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

TRM_BRANCH_PUBLISHED = "master"
TRM_BRANCH_INTERNAL = "release/v0.1"


def _normalize_language(doc: dict[str, Any]) -> str | None:
    raw = doc.get("language")
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw.split("#", 1)[0].strip().lower()
    return None


def _normalize_visibility(raw: Any) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw.split("#", 1)[0].strip().lower()
    return None


def _primary_main_en_path(chip: str) -> str:
    c = chip.strip()
    return f"{c}/{c}-main__EN.tex"


def resolve_target_branch(
    config_path: Path,
    chip_series_wanted: str,
) -> tuple[str, bool, str]:
    """Return GitLab merge target branch for a chip TRM.

    Reads the project ``documents`` list (English TRM row for ``chip_series``).
    ``visibility_on_website: show`` → ``master``; ``hide`` → ``release/v0.1``.

    If the chip has no English document entry, defaults to ``release/v0.1``.

    Returns:
        ``(merge_target_branch, is_public_on_website, summary_for_logging)``.
    """
    if not config_path.is_file():
        raise FileNotFoundError(f"Document config not found: {config_path}")

    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML syntax in {config_path}: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to read config {config_path}: {e}") from e

    documents = data.get("documents") if isinstance(data, dict) else None
    if not isinstance(documents, list):
        raise ValueError(f"Invalid document config: missing documents list in {config_path}")

    want = chip_series_wanted.strip()
    want_cf = want.casefold()

    en_docs: list[dict[str, Any]] = []
    for doc in documents:
        if not isinstance(doc, dict):
            continue
        cs = doc.get("chip_series")
        if not isinstance(cs, str) or cs.strip().casefold() != want_cf:
            continue
        if _normalize_language(doc) != "en":
            continue
        en_docs.append(doc)

    if not en_docs:
        summary = (
            f"chip {want!r} has no EN document entry — default MR target {TRM_BRANCH_INTERNAL!r}"
        )
        return TRM_BRANCH_INTERNAL, False, summary

    canonical_chip = str(en_docs[0].get("chip_series", "")).strip()
    primary = _primary_main_en_path(canonical_chip)
    chosen: dict[str, Any] | None = None
    for doc in en_docs:
        dp = doc.get("document_path")
        if isinstance(dp, str) and dp.replace("\\", "/") == primary:
            chosen = doc
            break
    if chosen is None:
        for doc in en_docs:
            dp = doc.get("document_path")
            if isinstance(dp, str) and dp.endswith("-main__EN.tex"):
                chosen = doc
                break
    if chosen is None:
        chosen = en_docs[0]

    vis = _normalize_visibility(chosen.get("visibility_on_website"))
    if vis == "show":
        branch = TRM_BRANCH_PUBLISHED
        is_public = True
    elif vis == "hide":
        branch = TRM_BRANCH_INTERNAL
        is_public = False
    else:
        raise ValueError(
            f"Unsupported visibility_on_website for chip_series {canonical_chip!r} "
            f"({chosen.get('document_name')!r}): {chosen.get('visibility_on_website')!r}. "
            "Expected 'show' or 'hide'.",
        )

    doc_name = chosen.get("document_name", "?")
    summary = (
        f"chip {canonical_chip} — EN {doc_name!r}: visibility_on_website={vis!r} "
        f"→ MR target {branch!r}"
    )
    return branch, is_public, summary
