"""Clone figures / latex-trm repos, copy content, push branches, open MRs."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import git

from tools.trm_automation_tools.common.fs_ops import find_chip_spec_dir, has_real_files
from tools.trm_automation_tools.common.git_ops import (
    checkout_or_create_branch,
    get_or_create_mr,
    run_pre_commit,
)
from tools.trm_automation_tools.common.id_ops import module_from_id_module
from tools.trm_automation_tools.common.repo_ops import (
    authenticated_https_clone_url_for_api_project as _auth_clone_url_for_api_project,
)
from tools.trm_automation_tools.common.text_ops import (
    remove_temp_label_block,
    uncomment_part_if_first_chapter,
    update_glance_status,
)


def update_main_tex_include(file_path: Path, id_module: str) -> bool:
    r"""Uncomment ``\subfileinclude{<id_module>__…>}`` line."""
    if not file_path.exists():
        return False

    content = file_path.read_text(encoding="utf-8")
    pattern = rf"%\\subfileinclude\{{{re.escape(id_module)}(__CN|__EN)\}}"
    new_content = re.sub(pattern, rf"\\subfileinclude{{{id_module}\1}}", content)

    if new_content != content:
        file_path.write_text(new_content, encoding="utf-8")
        return True
    return False


def update_globaltrue(file_path: Path) -> bool:
    """Uncomment %\\globaltrue line."""
    if not file_path.exists():
        return False

    content = file_path.read_text(encoding="utf-8")
    new_content = content.replace("%\\globaltrue", "\\globaltrue")

    if new_content != content:
        file_path.write_text(new_content, encoding="utf-8")
        return True
    return False


def publish_to_figures_repo(
    gl_instance,
    sources_dir: Path,
    project: str,
    id_module: str,
    overleaf_id: str,
    jira_ticket_id: str,
    tmp: Path,
    *,
    figures_repo_id: str,
    gitlab_token: str,
    assignee_id: int | None = None,
):
    """Publish sources to figures repo."""
    print(f"\n{'=' * 60}")
    print("📦 Publishing to figures repo")
    print(f"{'=' * 60}")

    module = module_from_id_module(id_module)

    fig_proj = gl_instance.projects.get(figures_repo_id)
    fig_url = _auth_clone_url_for_api_project(fig_proj, gitlab_token)
    fig_path = tmp / "fig"

    print("📥 Cloning figures repository...")
    git.Repo.clone_from(fig_url, fig_path)
    print("✅ Cloned")

    r = git.Repo(fig_path)
    branch_name = f"docs/publish_{project}_{id_module}_sources"
    checkout_or_create_branch(r, branch_name)

    target = fig_path / project / id_module
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    file_count = 0
    for src in sources_dir.rglob("*"):
        if src.is_file() and src.name != "placeholder.temp":
            dst = target / src.relative_to(sources_dir)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            file_count += 1

    print(f"✅ Copied {file_count} files to {project}/{id_module}")

    if not r.is_dirty(untracked_files=True):
        print("ℹ️  No changes to commit.")
        return None

    r.git.add(A=True)
    r.index.commit(f"{project}/{module}: Publish graphics sources")
    r.git.push("--set-upstream", "origin", branch_name)
    print(f"✅ Pushed to branch: {branch_name}")

    description = (
        f"Publish {module} graphics sources for {project}.\n\n"
        f"## Related\n\n"
        f"- Overleaf project: https://www.overleaf.com/project/{overleaf_id}\n"
        f"- Mentions {jira_ticket_id}"
    )

    mr, _ = get_or_create_mr(
        gl_instance,
        fig_proj,
        branch_name,
        "master",
        f"{project}/{module}: Publish graphics sources",
        description,
        assignee_id=assignee_id,
    )
    return mr


def publish_to_latex_trm_repo(
    gl_instance,
    ol_path: Path,
    module_dir: Path,
    id_module: str,
    project: str,
    overleaf_id: str,
    jira_ticket_id: str,
    tmp: Path,
    *,
    latex_trm_repo_id: str,
    gitlab_token: str,
    assignee_id: int | None = None,
):
    """Publish chapter to latex-trm repo."""
    print(f"\n{'=' * 60}")
    print("📚 Publishing to latex-trm repo")
    print(f"{'=' * 60}")

    module = module_from_id_module(id_module)
    module_lower = module.lower()
    print(f"✅ Module: {module}")

    trm_proj = gl_instance.projects.get(latex_trm_repo_id)
    trm_url = _auth_clone_url_for_api_project(trm_proj, gitlab_token)
    trm_path = tmp / "trm"

    print("📥 Cloning latex-trm repository...")
    git.Repo.clone_from(trm_url, trm_path)
    print("✅ Cloned")

    r = git.Repo(trm_path)
    branch_name = f"docs/publish_{project}_{module}"
    checkout_or_create_branch(r, branch_name)

    project_dir = trm_path / project
    if not project_dir.exists():
        print(f"❌ Project folder '{project}' not found in latex-trm repo")
        return None
    print(f"✅ Found project folder: {project}")

    modified_files: list[str] = []

    module_target = project_dir / id_module
    print(f"\n📁 Copying module folder to {project}/{id_module}/...")

    if module_target.exists():
        shutil.rmtree(module_target)
    module_target.mkdir(parents=True, exist_ok=True)

    file_count = 0
    for item in module_dir.iterdir():
        if item.name == "sources":
            continue

        if item.is_dir() and not has_real_files(item):
            print(f"   ⏭ Skipped empty folder: {item.name}")
            continue

        dst = module_target / item.name

        if item.is_dir():
            shutil.copytree(item, dst, ignore=shutil.ignore_patterns("placeholder.temp"))
            for f in dst.rglob("*"):
                if f.is_file():
                    modified_files.append(str(f.relative_to(trm_path)))
                    file_count += 1
        else:
            if item.name == "placeholder.temp":
                continue
            shutil.copy2(item, dst)
            modified_files.append(str(dst.relative_to(trm_path)))
            file_count += 1
    print(f"   Copied {file_count} files to {project}/{id_module}/")

    print("📄 Copying main tex files...")
    for suffix in ["__CN.tex", "__EN.tex"]:
        main_file = ol_path / f"{id_module}{suffix}"
        if main_file.exists():
            dst = project_dir / main_file.name
            shutil.copy2(main_file, dst)
            modified_files.append(str(dst.relative_to(trm_path)))
            print(f"   Copied {main_file.name}")

    print("\n📝 Updating main tex files...")
    for suffix in ["__CN.tex", "__EN.tex"]:
        main_files = list(project_dir.glob(f"*main{suffix}"))
        for main_file in main_files:
            if update_main_tex_include(main_file, id_module):
                modified_files.append(str(main_file.relative_to(trm_path)))
                print(f"   ✅ Uncommented \\subfileinclude in {main_file.name}")

    print("📝 Uncommenting \\part headers if needed...")
    for suffix in ["__CN.tex", "__EN.tex"]:
        main_files = list(project_dir.glob(f"*main{suffix}"))
        for main_file in main_files:
            if uncomment_part_if_first_chapter(main_file, module):
                modified_files.append(str(main_file.relative_to(trm_path)))
                print(f"   ✅ Uncommented \\part header in {main_file.name}")

    print("📝 Updating module tex files...")
    for suffix in ["__CN.tex", "__EN.tex"]:
        module_tex = project_dir / f"{id_module}{suffix}"
        if update_globaltrue(module_tex):
            print(f"   ✅ Uncommented \\globaltrue in {id_module}{suffix}")

    print("📝 Updating glance files...")
    chip_spec_dir = find_chip_spec_dir(project_dir)

    if chip_spec_dir:
        for lang, filename in [("CN", "glance__CN.tex"), ("EN", "glance__EN.tex")]:
            glance_file = chip_spec_dir / filename
            if update_glance_status(glance_file, module_lower, lang):
                modified_files.append(str(glance_file.relative_to(trm_path)))
                print(f"   ✅ Updated {filename} with published status")
    else:
        print("   ⚠️  Could not find chip-spec-content/settings folder")

    print("📝 Removing temporary labels...")
    if chip_spec_dir:
        for filename in ("temp-labels-cn.tex", "temp-labels-en.tex"):
            temp_labels_file = chip_spec_dir / filename
            if remove_temp_label_block(temp_labels_file, module_lower):
                modified_files.append(str(temp_labels_file.relative_to(trm_path)))
                print(f"   ✅ Removed temporary labels from {filename}")

    if not r.is_dirty(untracked_files=True):
        print("ℹ️  No changes to commit.")
        return None

    r.git.add(A=True)
    commit_msg = f"{project}/{module}: Publish {module} chapter"
    r.index.commit(commit_msg)
    print(f"✅ Committed: {commit_msg}")

    if modified_files:
        pre_commit_passed = run_pre_commit(trm_path, modified_files)

        if r.is_dirty(untracked_files=True):
            r.git.add(A=True)
            r.index.commit(f"{project}/{module}: Run pre-commit auto-fixes")
            print(f"✅ Committed: {project}/{module}: Run pre-commit auto-fixes")

        if not pre_commit_passed:
            print("   ⚠️  Some pre-commit checks failed. Continuing anyway...")
            print("   💡 You may need to fix these issues manually before merging.")

    r.git.push("--set-upstream", "origin", branch_name)
    print(f"✅ Pushed to branch: {branch_name}")

    description = (
        f"Publish {module} chapter for {project}.\n\n"
        f"---\n"
        f"### ⚠️ Before merging, please:\n"
        f"- [ ] Review the pre-commit auto-fixes\n"
        f"- [ ] Add or remove any custom temporary labels as needed\n"
        f"- [ ] Update revision history if needed\n"
        f"- [ ] Build the document locally to ensure no build errors\n\n"
        f"## Related\n\n"
        f"- Overleaf project: https://www.overleaf.com/project/{overleaf_id}\n"
        f"- Closes {jira_ticket_id}"
    )

    mr, _ = get_or_create_mr(
        gl_instance,
        trm_proj,
        branch_name,
        "master",
        commit_msg,
        description,
        labels=[project],
        assignee_id=assignee_id,
    )
    return mr
