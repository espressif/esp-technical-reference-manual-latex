"""Publish flow: Overleaf discovery, archive step, orchestration.

CLI and argument parsing live in ``publish_trm_chapters.py``.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

import git
import gitlab

from tools.trm_automation_tools.common.fs_ops import has_real_files
from tools.trm_automation_tools.common.id_ops import module_from_id_module
from tools.trm_automation_tools.common.repo_ops import (
    clone_overleaf_repo as _clone_overleaf_repo_common,
    fetch_gitlab_current_user_id,
    gitlab_api_root_url,
    gitlab_private_token_kwargs,
)
from tools.trm_automation_tools.common.trm_env import get_trm_env_values, require_trm_env

from tools.trm_automation_tools.publish.repos import (
    publish_to_figures_repo,
    publish_to_trm_repo,
)

NO_EDITS_WARNING_TEMPLATE = """!NO EDITS IN PROJECT!
THIS CHAPTER IS MAINTAINED IN GitLab esp-technical-reference-manual-latex repository.

！请不要在此项目中编辑！
该章节已移至 GitLab esp-technical-reference-manual-latex 仓库中。

esp-technical-reference-manual-latex:
{trm_link}
"""


def get_chip_name(ol_path: Path) -> str:
    """Extract chip name from 00-shared/chip-spec-settings.sty or preamble-trm-module.sty."""
    sty_file = ol_path / "00-shared" / "chip-spec-settings.sty"

    if not sty_file.exists():
        sty_file = ol_path / "00-shared" / "preamble-trm-module.sty"

    if not sty_file.exists():
        raise FileNotFoundError(
            f"Required file not found: chip-spec-settings.sty or preamble-trm-module.sty "
            f"in {ol_path / '00-shared'}",
        )

    content = sty_file.read_text(encoding="utf-8")

    if match := re.search(r"\\newcommand\\chipname\{([^}]+)\}", content):
        chip_name = match.group(1)
        print(f"✅ Found chip name: {chip_name} (from {sty_file.name})")
        return chip_name

    raise ValueError(f"Could not find \\newcommand\\chipname in {sty_file}")


def find_module(ol_path: Path) -> tuple[Path, str]:
    """Find chapter folder whose name is an ID–Module token: digit(s)-UPPERCASE (e.g. 25-ECDSA).

    Returns (module_dir, id_module).
    """
    pattern = re.compile(r"^\d+-[A-Z]+$")

    for item in ol_path.iterdir():
        if item.is_dir() and item.name != "00-shared" and pattern.match(item.name):
            return item, item.name

    raise FileNotFoundError("No module folder found (expected pattern: digit(s)-UPPERCASE)")


def archive_overleaf_project(ol_repo: git.Repo, ol_path: Path) -> bool:
    """Archive Overleaf project by marking it as archived and adding warning file."""
    print(f"\n{'=' * 60}")
    print("📦 Archiving Overleaf project")
    print(f"{'=' * 60}\n")

    sty_file = ol_path / "00-shared" / "chip-spec-settings.sty"
    if not sty_file.exists():
        sty_file = ol_path / "00-shared" / "preamble-trm-module.sty"

    if sty_file.exists():
        content = sty_file.read_text(encoding="utf-8")
        new_content = re.sub(r"%\s*\\archivedtrue", r"\\archivedtrue", content)
        if new_content != content:
            sty_file.write_text(new_content, encoding="utf-8")
            print(f"✅ Uncommented \\archivedtrue in {sty_file.name}")
        else:
            print(f"ℹ️  No \\archivedtrue line to uncomment in {sty_file.name}")

    warning_file = ol_path / "!NO-EDITS-IN-PROJECT!.txt"
    gitlab_url = get_trm_env_values()["GITLAB_URL"] or ""
    warning_content = NO_EDITS_WARNING_TEMPLATE.format(
        trm_link=f"{gitlab_url}/documentation/esp-technical-reference-manual-latex",
    )
    warning_file.write_text(warning_content, encoding="utf-8")
    print(f"✅ Created {warning_file.name}")

    if not ol_repo.is_dirty(untracked_files=True):
        print("ℹ️  No changes to commit. Project might already be archived.")
        return False

    ol_repo.git.add(A=True)
    ol_repo.index.commit("Archive project: Mark as archived and add no-edits warning")

    try:
        ol_repo.git.push("origin", "master")
        print("✅ Pushed archive changes to Overleaf")
        return True
    except Exception as e:
        print(f"⚠️  Failed to push: {e}")
        return False


def publish_trm_chapters(overleaf_id: str, jira_ticket_id: str) -> None:
    """Publish sources and chapters from Overleaf to GitLab."""
    require_trm_env(
        "OVERLEAF_TOKEN",
        "GITLAB_TOKEN",
        "GITLAB_URL",
    )
    ev = get_trm_env_values()
    overleaf_token = ev["OVERLEAF_TOKEN"]
    gitlab_url = ev["GITLAB_URL"]
    gitlab_token = ev["GITLAB_TOKEN"]
    figures_repo_id = ev["FIGURES_REPO_ID"]
    trm_repo_id = ev["TRM_REPO_ID"]

    print(f"{'=' * 60}")
    print("Overleaf → GitLab Publisher")
    print(f"{'=' * 60}")

    api_root = gitlab_api_root_url(gitlab_url)
    gl = gitlab.Gitlab(api_root, **gitlab_private_token_kwargs(gitlab_token))
    assignee_id = fetch_gitlab_current_user_id(api_root, gitlab_token)
    print("✅ Connected to GitLab")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        ol_path = tmp / "ol"
        ol_repo = _clone_overleaf_repo_common(overleaf_id, overleaf_token, ol_path, depth=1)

        try:
            chip_name = get_chip_name(ol_path)
        except (FileNotFoundError, ValueError) as e:
            sys.exit(f"❌ Error: {e}")

        try:
            module_dir, id_module = find_module(ol_path)
            print(f"✅ Found module: {id_module}")
        except FileNotFoundError:
            print("ℹ️  No module folder found. Skipping.")
            return

        project = chip_name
        module = module_from_id_module(id_module)

        print("\n📋 Summary:")
        print(f"   Project: {project}")
        print(f"   ID–Module: {id_module}")
        print(f"   Module: {module}")

        sources_dir = module_dir / "sources"
        has_sources = has_real_files(sources_dir)

        figures_mr = None
        trm_mr = None

        if has_sources:
            figures_mr = publish_to_figures_repo(
                gl,
                sources_dir,
                project,
                id_module,
                overleaf_id,
                jira_ticket_id,
                tmp,
                figures_repo_id=figures_repo_id or "",
                gitlab_token=gitlab_token or "",
                assignee_id=assignee_id,
            )
        else:
            print("\nℹ️  No sources folder - skipping figures repo")

        trm_mr = publish_to_trm_repo(
            gl,
            ol_path,
            module_dir,
            id_module,
            project,
            overleaf_id,
            jira_ticket_id,
            tmp,
            trm_repo_id=trm_repo_id or "",
            gitlab_token=gitlab_token or "",
            assignee_id=assignee_id,
        )

        archive_success = archive_overleaf_project(ol_repo, ol_path)

        if archive_success:
            print("\n✅ Overleaf project archived (automated steps completed)")

        print(f"\n{'=' * 60}")
        print("🎉 COMPLETE")
        print(f"{'=' * 60}")

        if figures_mr:
            print(f"\n📦 figures MR: {figures_mr.web_url}")
        if trm_mr:
            print(f"📚 esp-technical-reference-manual-latex MR: {trm_mr.web_url}")

        print("\n⚠️  TODO:")
        if trm_mr:
            print("Before merging esp-technical-reference-manual-latex MR:")
            print("   1. Review the pre-commit auto-fixes")
            print("   2. Add or remove any custom temporary labels as needed")
            print("   3. Update revision history if needed")
            print("   4. Build the document locally to ensure no build errors")
            print("   5. Run tools/check_latex_links/check_latex_links.py to ensure no broken links")
        print("\nManually archive the Overleaf project:")
        print("   1. Remove Overleaf collaborators (keep the CI account)")
        print(f"   2. Archive project: https://www.overleaf.com/project/{overleaf_id}")
