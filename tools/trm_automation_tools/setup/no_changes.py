"""Mode 1 (no-changes chapter) workflow."""

from __future__ import annotations

import tempfile
from pathlib import Path

from tools.trm_automation_tools.common.chapter_inclusion import (
    chapter_included_via_subfiles,
    uncomment_chapter_includes,
)
from tools.trm_automation_tools.common.git_ops import (
    checkout_or_create_branch,
    get_or_create_mr,
    run_pre_commit,
)
from tools.trm_automation_tools.common.reused_chapter_sync import (
    REUSED_CHAPTER_LIST_REL,
    checkout_paths_from_ref,
    git_paths_for_reused_chapter,
    merge_reused_paths_into_list_file,
    paths_listed_in_file,
    read_git_blob,
    reused_chapter_path_lines,
)
from tools.trm_automation_tools.common.target_branch import (
    TRM_BRANCH_INTERNAL,
    TRM_BRANCH_PUBLISHED,
    resolve_target_branch,
)
from tools.trm_automation_tools.common.text_ops import (
    extend_tags_in_file,
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


def _remote_branch_exists(repo, branch_name: str) -> bool:
    """Check if branch exists on remote."""
    try:
        result = repo.git.ls_remote("--heads", "origin", branch_name)
        return len(result.strip()) > 0
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def _extract_project_labels(modified_files: list[str], target_project: str) -> list[str]:
    """Extract unique project labels from modified file paths.
    
    Always includes target_project. Adds any other projects that have modified files.
    """
    labels = {target_project}
    
    for file_path in modified_files:
        parts = file_path.replace("\\", "/").split("/")
        if parts and parts[0].startswith("ESP"):
            labels.add(parts[0])
    
    return sorted(labels)


def _project_exists_on_ref(repo, ref: str, project_name: str) -> bool:
    """Check if a project directory exists on a specific git ref."""
    try:
        result = repo.git.ls_tree("-d", "--name-only", ref, project_name)
        return bool(result.strip())
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def _prepare_chapter_sync_info(repo_path: Path, repo, base_project: str, module_upper: str):
    """Resolve chapter source and determine sync needs."""
    source_project, source_id_module, base_reuses_upstream = resolve_no_changes_source(
        repo_path, base_project, module_upper,
    )
    path_lines = reused_chapter_path_lines(source_project, source_id_module)
    git_paths = git_paths_for_reused_chapter(source_project, source_id_module)

    master_list_blob = read_git_blob(repo, "origin/master", REUSED_CHAPTER_LIST_REL) or ""
    listed_on_master = paths_listed_in_file(master_list_blob, path_lines)

    return source_project, source_id_module, base_reuses_upstream, path_lines, git_paths, listed_on_master


def _create_master_sync_mr(
    repo,
    trm_path: Path,
    gl_instance,
    trm_proj,
    module_upper: str,
    module_alias_lower: str,
    source_project: str,
    listed_on_master: bool,
    modified: list[str],
    git_paths: list[str],
    path_lines: list[str],
    work_branch: str,
    release_mr_url: str | None,
    jira_ticket: str | None,
    assignee_id: int | None,
) -> str | None:
    """Create a follow-up MR to master for internal TRM changes. Returns MR URL or None."""
    need_master_mr = (not listed_on_master) or _touches_chapter_paths(modified, git_paths)
    if not need_master_mr:
        print(
            "\nℹ️  Skipping master MR — chapter already listed on master and "
            "no chapter-path edits in this run.",
        )
        return None

    source_project_slug = source_project.replace("-", "").lower()
    master_branch = f"docs/update_reused_chapter_{source_project_slug}_{module_alias_lower}"
    checkout_or_create_branch(repo, master_branch, base_branch=TRM_BRANCH_PUBLISHED)

    had_list_change = False
    if not listed_on_master:
        lp = trm_path / REUSED_CHAPTER_LIST_REL
        had_list_change = merge_reused_paths_into_list_file(lp, path_lines)
        if had_list_change:
            print(f"✅ Master MR: updated {REUSED_CHAPTER_LIST_REL}")

    source_on_master = _project_exists_on_ref(repo, "origin/master", source_project)
    
    chapter_diff = False
    if source_on_master:
        try:
            checkout_paths_from_ref(repo, work_branch, git_paths)
            print(f"✅ Master MR: synced chapter files from {work_branch}")
            chapter_diff = _chapter_paths_changed_vs_ref(repo, "origin/master", git_paths)
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"   ⚠️  Failed to sync chapter files from {work_branch}: {e}")
            print("   ℹ️  Skipping master MR creation.")
            return None
    else:
        print(
            f"ℹ️  Master MR: {source_project} is unpublished (not on master); "
            "skipping chapter file sync, only updating list"
        )

    if source_on_master:
        master_title = f"{source_project}/{module_upper}: Update chapter"
    else:
        master_title = f"{source_project}/{module_upper}: Add to reused chapter list"

    if not listed_on_master:
        if source_on_master:
            desc_master = (
                "Registers the reused chapter in `tools/auto_backport/reused_chapter_list.txt` "
                "and syncs chapter sources from the internal no-changes setup.\n\n"
            )
        else:
            desc_master = (
                "Registers the reused chapter in `tools/auto_backport/reused_chapter_list.txt`.\n\n"
            )
    else:
        desc_master = (
            "Syncs chapter sources from the internal no-changes setup.\n\n"
        )
    related_items = []
    if release_mr_url:
        related_items.append(f"- No-changes (release) MR: {release_mr_url}")
    if jira_ticket and jira_ticket.strip():
        related_items.append(f"- Mentions {jira_ticket.strip()}")
    if related_items:
        desc_master += "\n---\n## Related\n\n" + "\n".join(related_items) + "\n"

    master_branch_pushed = False
    if repo.is_dirty(untracked_files=True):
        repo.git.add(A=True)
        repo.index.commit(master_title)
        print(f"✅ Committed (master sync): {master_title}")

        sync_files = [REUSED_CHAPTER_LIST_REL, *git_paths] if source_on_master else [REUSED_CHAPTER_LIST_REL]
        ok_m = run_pre_commit(trm_path, sync_files)
        if repo.is_dirty(untracked_files=True):
            repo.git.add(A=True)
            repo.index.commit(f"{master_title}: pre-commit auto-fixes")
        if not ok_m:
            print("   ⚠️  pre-commit reported issues on master-sync branch.")

        repo.git.push("--set-upstream", "origin", master_branch)
        print(f"✅ Pushed master-sync branch: {master_branch}")
        master_branch_pushed = True

    # Check if master branch exists remotely (from previous run)
    if not master_branch_pushed:
        master_branch_pushed = _remote_branch_exists(repo, master_branch)

    if master_branch_pushed:
        mr_m, _ = get_or_create_mr(
            gl_instance,
            trm_proj,
            master_branch,
            TRM_BRANCH_PUBLISHED,
            master_title,
            desc_master,
            labels=[source_project],
            assignee_id=assignee_id,
        )
        print(f"\n📚 Master MR (merge after release): {mr_m.web_url}")
        return mr_m.web_url

    return None


def resolve_no_changes_source(
    repo_path: Path,
    base_project: str,
    module: str,
) -> tuple[str, str, bool]:
    """Return ``(source_project, source_id_module, base_reuses_upstream)``."""
    base_dir = repo_path / base_project
    if not base_dir.exists():
        raise SystemExit(f"❌ Base project directory not found: {base_project}/")

    base_id_module = wf.find_base_id_module(base_dir, module)
    if base_id_module:
        return base_project, base_id_module, False

    upstream = wf.find_upstream_reference(base_dir, module)
    if upstream:
        source_project, source_id_module = upstream
        return source_project, source_id_module, True

    raise SystemExit(
        f"❌ Chapter folder for module {module!r} not found in {base_project}/, "
        "and no upstream \\subfile reference found in main files",
    )


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

    source_project, source_id_module, base_reuses_upstream = resolve_no_changes_source(
        repo_path, base_project, module,
    )

    if not base_reuses_upstream:
        print(f"✅ Found base chapter: {base_project}/{source_id_module}")
    else:
        print(
            f"ℹ️  {base_project} reuses {module} from "
            f"{source_project}/{source_id_module}",
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

    print("\n📝 Step 1: Updating base chapter \\modulefiles paths..." if not base_reuses_upstream else
          "\n📝 Step 1: Updating source chapter \\modulefiles paths...")
    if base_reuses_upstream:
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

    print(f"\n📝 Step 5: Extending tag macros in source chapter for {target_project}...")
    tag_count = 0
    module_dir = source_dir / source_id_module
    if module_dir.is_dir():
        for tex_file in sorted(module_dir.rglob("*.tex")):
            if extend_tags_in_file(tex_file, base_project, target_project):
                tag_count += 1
                modified.append(str(tex_file.relative_to(repo_path)))
                print(f"   ✅ Extended tags in {tex_file.relative_to(repo_path)}")
    for lang in ("EN", "CN"):
        main_f = source_dir / f"{source_id_module}__{lang}.tex"
        if extend_tags_in_file(main_f, base_project, target_project):
            tag_count += 1
            modified.append(str(main_f.relative_to(repo_path)))
            print(f"   ✅ Extended tags in {main_f.relative_to(repo_path)}")
    if tag_count == 0:
        print(f"   ℹ️  No tag macros matching {base_project} found")

    return modified


def _chapter_paths_changed_vs_ref(repo, ref: str, git_paths: list[str]) -> bool:
    """True if *git_paths* differ from *ref* in the index/worktree."""
    if not git_paths:
        return False
    try:
        diff = repo.git.diff(ref, "--", *git_paths)
    except Exception:  # pylint: disable=broad-exception-caught
        return True
    return bool(diff and diff.strip())


def _touches_chapter_paths(modified: list[str], git_paths: list[str]) -> bool:
    gnorm = {g.replace("\\", "/") for g in git_paths}
    for m in modified:
        m = m.replace("\\", "/").lstrip("./")
        if m in gnorm or any(m.startswith(g + "/") for g in gnorm):
            return True
    return False


def run_no_changes_full(
    base_project: str,
    target_project: str,
    module: str,
    *,
    jira_ticket: str | None = None,
):
    """Clone esp-technical-reference-manual-latex, apply no-changes setup, push, and create MR(s)."""
    import git as gitpython

    wf._load_env()
    require_trm_env("GITLAB_TOKEN")

    module_upper = module.upper()
    module_alias_lower = module_upper.lower()
    slug = target_project.replace("-", "").lower()
    work_branch = f"docs/publish_{slug}_{module_alias_lower}_chapter"
    release_commit_msg = f"{target_project}/{module_upper}: Publish chapter"

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        trm_path = tmp / "trm"
        wf.clone_trm(trm_path)

        repo = gitpython.Repo(trm_path)
        repo.git.fetch("origin")

        cfg = trm_path / ".lbcf.yml"
        mr_target, _pub, branch_note = resolve_target_branch(cfg, target_project)
        print(f"📌 TRM branch: {branch_note}")

        # Check out to target branch before resolving source chapter location
        checkout_or_create_branch(repo, work_branch, base_branch=mr_target)

        source_project, source_id_module, base_reuses_upstream, path_lines, git_paths, listed_on_master = (
            _prepare_chapter_sync_info(trm_path, repo, base_project, module_upper)
        )

        prep_modified: list[str] = []

        if mr_target == TRM_BRANCH_INTERNAL:
            included = chapter_included_via_subfiles(
                trm_path,
                base_project,
                source_project,
                source_id_module,
                base_reuses_upstream=base_reuses_upstream,
            )
            if not included:
                print(
                    f"\n📥 Base chapter not included (\\subfile lines) on {mr_target}; "
                    "copying from origin/master …",
                )
                try:
                    checkout_paths_from_ref(repo, "origin/master", git_paths)
                    prep_modified.extend(git_paths)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    print(f"   ⚠️  Failed to checkout chapter files: {e}")
                    raise SystemExit(
                        "❌ Cannot sync chapter files from origin/master. "
                        "Ensure the chapter exists in the master branch."
                    ) from e
                um = uncomment_chapter_includes(
                    trm_path,
                    base_project,
                    source_project,
                    source_id_module,
                    base_reuses_upstream=base_reuses_upstream,
                )
                prep_modified.extend(um)
                if not um and not prep_modified:
                    print(
                        "   ℹ️  No commented \\subfile / \\subfileinclude lines to uncomment.",
                    )
            else:
                print(f"ℹ️  Chapter already included via active \\subfile lines on {mr_target}.")

            if listed_on_master:
                print(
                    f"ℹ️  Reused chapter already listed in origin/master:{REUSED_CHAPTER_LIST_REL}",
                )
            else:
                print(
                    f"ℹ️  Reused chapter not in origin/master:{REUSED_CHAPTER_LIST_REL} "
                    "(a follow-up MR to `master` will register it).",
                )

        else:
            list_path = trm_path / REUSED_CHAPTER_LIST_REL
            if not listed_on_master:
                if merge_reused_paths_into_list_file(list_path, path_lines):
                    prep_modified.append(REUSED_CHAPTER_LIST_REL)
                    print(
                        f"✅ Registered reused chapter in {REUSED_CHAPTER_LIST_REL} "
                        "(alphabetical order)",
                    )
                else:
                    print(f"ℹ️  Paths already present in {REUSED_CHAPTER_LIST_REL}")
            else:
                print(
                    f"ℹ️  Reused chapter already listed in origin/master:{REUSED_CHAPTER_LIST_REL}",
                )

        modified = apply_no_changes_chapter(trm_path, base_project, target_project, module_upper)
        all_modified = prep_modified + modified

        release_mr_url: str | None = None
        pushed_work = False

        if repo.is_dirty(untracked_files=True):
            repo.git.add(A=True)
            repo.index.commit(release_commit_msg)
            print(f"✅ Committed: {release_commit_msg}")

            if all_modified:
                ok = run_pre_commit(trm_path, all_modified)
                if repo.is_dirty(untracked_files=True):
                    repo.git.add(A=True)
                    repo.index.commit(f"{target_project}/{module_upper}: Run pre-commit auto-fixes")
                    print("✅ Committed: pre-commit auto-fixes")
                if not ok:
                    print("   ⚠️  Some pre-commit checks failed. Continuing anyway...")

            repo.git.push("--set-upstream", "origin", work_branch)
            pushed_work = True
            print(f"✅ Pushed to branch: {work_branch}")
        else:
            print("\nℹ️  No changes to commit — no push needed.")

        # Check if branch exists remotely (from previous run)
        branch_exists = _remote_branch_exists(repo, work_branch)

        env = get_trm_env_values()
        if (pushed_work or branch_exists) and env.get("GITLAB_URL") and env.get("TRM_REPO_ID"):
            import gitlab as gl_lib

            api_root = gitlab_api_root_url(env["GITLAB_URL"])
            token = env["GITLAB_TOKEN"] or ""
            gl = gl_lib.Gitlab(api_root, **gitlab_private_token_kwargs(token))
            assignee_id = fetch_gitlab_current_user_id(api_root, token)
            trm_proj = gl.projects.get(env["TRM_REPO_ID"])

            desc_release = (
                f"Set up no-changes {module_upper} chapter for {target_project} "
                f"(based on {base_project}).\n"
            )
            desc_release += (
                "\n---\n"
                "### ⚠️ Before merging:\n"
                "- [ ] Add or remove any custom temporary labels as needed\n"
                "- [ ] Build the document locally to ensure no build errors\n"
            )
            if mr_target == TRM_BRANCH_INTERNAL:
                desc_release += (
                    "\n---\n"
                    "### ⚠️ After merging:\n"
                    "- [ ] Merge the follow-up MR to `master` if any (required when `reused_chapter_list.txt` "
                    "or/and the base chapter is updated)\n"
                )
            if jira_ticket and jira_ticket.strip():
                desc_release += f"\n---\n## Related\n\n* Closes {jira_ticket.strip()}\n"

            # Collect labels from all modified projects
            mr_labels = _extract_project_labels(all_modified, target_project)
            
            mr_r, _ = get_or_create_mr(
                gl,
                trm_proj,
                work_branch,
                mr_target,
                release_commit_msg,
                desc_release,
                labels=mr_labels,
                assignee_id=assignee_id,
            )
            release_mr_url = mr_r.web_url
            print(f"\n📚 Release/target MR: {release_mr_url}")

            if mr_target == TRM_BRANCH_INTERNAL:
                master_mr_url = _create_master_sync_mr(
                    repo,
                    trm_path,
                    gl,
                    trm_proj,
                    module_upper,
                    module_alias_lower,
                    source_project,
                    listed_on_master,
                    modified,
                    git_paths,
                    path_lines,
                    work_branch,
                    release_mr_url,
                    jira_ticket,
                    assignee_id,
                )
                
                if master_mr_url:
                    if jira_ticket and jira_ticket.strip():
                        desc_release += f"* Master sync MR: {master_mr_url}\n"
                    else:
                        desc_release += f"\n---\n## Related\n\n* Master sync MR: {master_mr_url}\n"
                    
                    mr_r.description = desc_release
                    mr_r.save()
                    print(f"✅ Updated release MR with master sync MR link")
            else:
                print("\nℹ️  Single MR workflow (published TRM → master).")

            if not pushed_work and branch_exists:
                print("\nℹ️  No file changes, but MR description(s) updated.")
        else:
            print("\nℹ️  GitLab API not configured — skipping MR operations.")

        print(f"\n{'=' * 60}")
        print("🎉 DONE")
        print(f"{'=' * 60}")


def run_no_changes_local(base_project: str, target_project: str, module: str):
    """Apply no-changes modifications in the local working copy only."""
    import git as gitpython

    module_upper = module.upper()
    repo_path = wf.REPO_ROOT

    # Initialize git repo to access remote refs
    try:
        repo = gitpython.Repo(repo_path)
    except gitpython.InvalidGitRepositoryError:
        print("⚠️  Not a git repository — skipping remote sync checks")
        modified = apply_no_changes_chapter(repo_path, base_project, target_project, module_upper)
        _print_local_completion(modified, needs_master_mr_note=False)
        return

    print("📡 Fetching latest refs from origin...")
    try:
        repo.git.fetch("origin")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"⚠️  Could not fetch from origin: {e}")
        print("   Continuing with local repository state...")

    # Resolve source chapter location
    source_project, source_id_module, base_reuses_upstream, _path_lines, git_paths, listed_on_master = (
        _prepare_chapter_sync_info(repo_path, repo, base_project, module_upper)
    )

    # Check if base chapter is included on current branch
    included = chapter_included_via_subfiles(
        repo_path,
        base_project,
        source_project,
        source_id_module,
        base_reuses_upstream=base_reuses_upstream,
    )

    # Determine if we need to pull chapter from master
    need_pull = not included or not listed_on_master

    prep_modified: list[str] = []

    if need_pull:
        if not included:
            print(
                "\n📥 Base chapter not included (\\subfile lines) on current branch; "
                "copying from origin/master…",
            )
        elif not listed_on_master:
            print(
                f"\n📥 Chapter not in origin/master:{REUSED_CHAPTER_LIST_REL}; "
                "pulling latest version from origin/master to ensure consistency…",
            )

        try:
            checkout_paths_from_ref(repo, "origin/master", git_paths)
            prep_modified.extend(git_paths)
            print("   ✅ Checked out chapter files from origin/master")

            if not included:
                um = uncomment_chapter_includes(
                    repo_path,
                    base_project,
                    source_project,
                    source_id_module,
                    base_reuses_upstream=base_reuses_upstream,
                )
                prep_modified.extend(um)
                if um:
                    print(f"   ✅ Uncommented {len(um)} \\subfile line(s) in {base_project}/")
                else:
                    print(
                        "   ℹ️  No commented \\subfile / \\subfileinclude lines to uncomment.",
                    )
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"   ⚠️  Failed to checkout from origin/master: {e}")
            print("   Continuing with current working copy...")
    else:
        print("ℹ️  Chapter already included and listed on master — using current working copy")

    modified = apply_no_changes_chapter(repo_path, base_project, target_project, module_upper)
    all_modified = prep_modified + modified

    # Determine if follow-up MR note is needed
    needs_master_mr_note = bool(prep_modified) and not listed_on_master
    _print_local_completion(all_modified, needs_master_mr_note=needs_master_mr_note)


def _print_local_completion(
    modified: list[str],
    *,
    needs_master_mr_note: bool = False,
):
    """Print completion message for local mode."""
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
    if needs_master_mr_note:
        print(
            "   3. Create a follow-up MR to master to register the reused chapter in\n"
            f"      {REUSED_CHAPTER_LIST_REL} and/or sync the base chapter files",
        )
