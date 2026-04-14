"""Mode 1 (no-changes chapter) workflow."""

from __future__ import annotations

import tempfile
from pathlib import Path

from tools.trm_automation_tools.common.git_ops import (
    checkout_or_create_branch,
    get_or_create_mr,
    run_pre_commit,
)
from tools.trm_automation_tools.common.text_ops import (
    remove_temp_label_block,
    uncomment_part_if_first_chapter,
    update_glance_status,
)
from tools.trm_automation_tools.common.repo_ops import (
    fetch_gitlab_current_user_id,
    gitlab_api_root_url,
    gitlab_private_token_kwargs,
)
from tools.trm_automation_tools.common.trm_env import get_trm_env_values, require_trm_env
from tools.trm_automation_tools.setup import core as wf


def apply_no_changes_chapter(
    repo_path: Path,
    base_project: str,
    target_project: str,
    module: str,
) -> list[str]:
    """Apply all file modifications for a no-changes chapter (mode 1)."""
    module_lower = module.lower()
    base_dir = repo_path / base_project
    target_dir = repo_path / target_project
    modified: list[str] = []

    if not base_dir.exists():
        raise SystemExit(f"❌ Base project directory not found: {base_project}/")
    if not target_dir.exists():
        raise SystemExit(f"❌ Target project directory not found: {target_project}/")

    skip_modulefiles = False
    base_id_module = wf.find_base_id_module(base_dir, module)

    if base_id_module:
        source_project, source_id_module = base_project, base_id_module
        print(f"✅ Found base chapter: {base_project}/{base_id_module}")
    else:
        upstream = wf.find_upstream_reference(base_dir, module)
        if upstream:
            source_project, source_id_module = upstream
            skip_modulefiles = True
            print(
                f"ℹ️  {base_project} reuses {module} from "
                f"{source_project}/{source_id_module}",
            )
        else:
            raise SystemExit(
                f"❌ Chapter folder for module {module!r} not found in {base_project}/, "
                "and no upstream \\subfile reference found in main files",
            )

    source_dir = repo_path / source_project
    for lang in ("EN", "CN"):
        f = source_dir / f"{source_id_module}__{lang}.tex"
        if not f.exists():
            raise SystemExit(
                f"❌ Source chapter file not found: "
                f"{source_project}/{source_id_module}__{lang}.tex",
            )

    main_en, main_cn = wf.find_main_files(target_dir)
    if not main_en or not main_cn:
        raise SystemExit(f"❌ Target project main .tex files not found in {target_project}/")
    print(f"✅ Found target main files: {main_en.name}, {main_cn.name}")

    chip_spec = wf.find_chip_spec_dir(target_dir)

    print("\n📝 Step 1: Updating base chapter \\modulefiles paths..." if not skip_modulefiles else
          "\n📝 Step 1: Updating source chapter \\modulefiles paths...")
    if skip_modulefiles:
        print(
            f"   ℹ️  Skipped — {source_project}/{source_id_module} "
            "is already set up for sharing",
        )
    else:
        for lang in ("EN", "CN"):
            tex = source_dir / f"{source_id_module}__{lang}.tex"
            try:
                if wf.update_modulefiles(tex, source_project, source_id_module):
                    modified.append(str(tex.relative_to(repo_path)))
                    print(f"   ✅ Updated {tex.relative_to(repo_path)}")
                else:
                    print(f"   ℹ️  {tex.name} already uses ../{source_project}/ path")
            except ValueError as e:
                print(f"   ⚠️  {e}")

    print("\n📝 Step 2: Updating target main files...")
    for lang, mf in [("EN", main_en), ("CN", main_cn)]:
        try:
            if wf.update_main_file(mf, module, source_project, source_id_module, lang):
                modified.append(str(mf.relative_to(repo_path)))
                print(f"   ✅ Updated {mf.name}")
            else:
                print(f"   ℹ️  {mf.name} already set up")
        except ValueError as e:
            print(f"   ⚠️  {e}")

    print("\n📝 Step 2b: Uncommenting \\part headers if needed...")
    for mf in (main_en, main_cn):
        if uncomment_part_if_first_chapter(mf, module):
            modified.append(str(mf.relative_to(repo_path)))
            print(f"   ✅ Uncommented \\part header in {mf.name}")

    print("\n📝 Step 3: Removing temporary labels...")
    if chip_spec:
        for fn in ("temp-labels-en.tex", "temp-labels-cn.tex"):
            p = chip_spec / fn
            if remove_temp_label_block(p, module_lower):
                modified.append(str(p.relative_to(repo_path)))
                print(f"   ✅ Removed label from {fn}")
            else:
                print(f"   ℹ️  No label for mod:{module_lower} found in {fn}")
    else:
        print(f"   ⚠️  Chip-spec-content directory not found in {target_project}/")

    print("\n📝 Step 4: Updating glance files...")
    if chip_spec:
        for lang, fn in [("EN", "glance__EN.tex"), ("CN", "glance__CN.tex")]:
            p = chip_spec / fn
            if update_glance_status(p, module_lower, lang):
                modified.append(str(p.relative_to(repo_path)))
                print(f"   ✅ Updated {fn}")
            else:
                latest_fn = fn.replace("glance__", "glance-latest__")
                lp = chip_spec / latest_fn
                if update_glance_status(lp, module_lower, lang):
                    modified.append(str(lp.relative_to(repo_path)))
                    print(f"   ✅ Updated {latest_fn}")
                else:
                    print(f"   ℹ️  No percentage status found in {fn}")
    else:
        print(f"   ⚠️  Chip-spec-content directory not found in {target_project}/")

    return modified


def run_no_changes_full(
    base_project: str,
    target_project: str,
    module: str,
    *,
    jira_ticket: str | None = None,
):
    """Clone latex-trm, apply no-changes setup, push, and create MR."""
    import git as gitpython

    wf._load_env()
    require_trm_env("GITLAB_TOKEN")

    module_upper = module.upper()
    slug = target_project.replace("-", "").lower()
    branch = f"docs/publish_{slug}_{module_upper.lower()}_chapter"
    commit_msg = f"{target_project}/{module_upper}: Publish chapter"

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        trm_path = tmp / "trm"
        wf.clone_latex_trm(trm_path)

        repo = gitpython.Repo(trm_path)
        checkout_or_create_branch(repo, branch)

        modified = apply_no_changes_chapter(trm_path, base_project, target_project, module_upper)

        if repo.is_dirty(untracked_files=True):
            repo.git.add(A=True)
            repo.index.commit(commit_msg)
            print(f"✅ Committed: {commit_msg}")

            if modified:
                ok = run_pre_commit(trm_path, modified)
                if repo.is_dirty(untracked_files=True):
                    repo.git.add(A=True)
                    repo.index.commit(f"{target_project}/{module_upper}: Run pre-commit auto-fixes")
                    print("✅ Committed: pre-commit auto-fixes")
                if not ok:
                    print("   ⚠️  Some pre-commit checks failed. Continuing anyway...")

            repo.git.push("--set-upstream", "origin", branch)
            print(f"✅ Pushed to branch: {branch}")
        else:
            print("\nℹ️  No changes to commit — will check MR description.")

        env = get_trm_env_values()
        if env.get("GITLAB_URL") and env.get("LATEX_TRM_REPO_ID"):
            import gitlab as gl_lib

            api_root = gitlab_api_root_url(env["GITLAB_URL"])
            token = env["GITLAB_TOKEN"] or ""
            gl = gl_lib.Gitlab(api_root, **gitlab_private_token_kwargs(token))
            assignee_id = fetch_gitlab_current_user_id(api_root, token)
            trm_proj = gl.projects.get(env["LATEX_TRM_REPO_ID"])
            desc = (
                f"Set up no-changes {module_upper} chapter for {target_project} "
                f"(based on {base_project}).\n"
            )
            if jira_ticket and jira_ticket.strip():
                key = jira_ticket.strip()
                desc += f"\n# Related\n\n* Closes {key}\n"
            desc += (
                "\n---\n"
                "### ⚠️ Before merging:\n"
                "- [ ] Add or remove any custom temporary labels as needed\n"
                "- [ ] Build the document locally to ensure no build errors\n"
            )
            mr, _ = get_or_create_mr(
                gl,
                trm_proj,
                branch,
                "master",
                commit_msg,
                desc,
                labels=[target_project],
                assignee_id=assignee_id,
            )
            print(f"\n📚 MR: {mr.web_url}")
        else:
            print("\nℹ️  GitLab API not configured — skipping MR creation.")

        print(f"\n{'=' * 60}")
        print("🎉 DONE")
        print(f"{'=' * 60}")


def run_no_changes_local(base_project: str, target_project: str, module: str):
    """Apply no-changes modifications in the local working copy only."""
    module_upper = module.upper()
    modified = apply_no_changes_chapter(wf.REPO_ROOT, base_project, target_project, module_upper)

    print(f"\n{'=' * 60}")
    print("✅ DONE (local mode)")
    print(f"{'=' * 60}")
    if modified:
        print("\nModified files:")
        for f in modified:
            print(f"   {f}")
    print("\n⚠️  Next steps:")
    print("   1. Review and commit the changes")
    print("   2. Push the branch and create a merge request")

