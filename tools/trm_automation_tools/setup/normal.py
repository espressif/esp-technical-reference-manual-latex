"""Mode 2 (normal chapter from base) workflow."""

from __future__ import annotations

import tempfile
from pathlib import Path

from tools.trm_automation_tools.common.id_ops import parse_id_module
from tools.trm_automation_tools.common.tex_sections import (
    extract_chapter_content,
    replace_chapter_content,
)
from tools.trm_automation_tools.common.text_ops import resolve_tags_in_file
from tools.trm_automation_tools.common.trm_env import require_trm_env
from tools.trm_automation_tools.setup import core as wf


def apply_normal_chapter_to_workdirs(
    ol_path: Path,
    trm_path: Path,
    base_project: str,
    target_id_module: str,
    source_lang: str,
    *,
    fig_path: Path | None = None,
    module_pm: str = "",
    writer: str = "",
) -> tuple[str, str]:
    """Apply mode-2 file transforms on existing trees (no clone/push)."""
    _, module = parse_id_module(target_id_module)
    module_lower = module.lower()

    module_folder, en_main, cn_main, base_id_module = wf.find_base_module_with_upstream(
        trm_path, base_project, module,
    )

    placeholder_folder, source_id = wf.resolve_overleaf_source_id(ol_path, target_id_module)

    print("\n📝 Step 1: Commenting out temporary labels...")
    shared = ol_path / "00-shared"
    possible_locations = [shared, shared / "config", ol_path / "00-chip-spec-content"]
    for fn in ("temp-labels-en.tex", "temp-labels-cn.tex"):
        found = False
        for location in possible_locations:
            p = location / fn
            if p.exists():
                label_found, did_edit = wf.comment_out_temp_label(p, module_lower)
                rel = p.relative_to(ol_path)
                if not label_found:
                    print(
                        f"   ℹ️  No line with \\label{{mod:{module_lower}}} "
                        f"(or mod:{module_lower}) in {rel}",
                    )
                elif did_edit:
                    print(f"   ✅ Commented out temp-label block in {rel}")
                else:
                    print(f"   ℹ️  mod:{module_lower} block already commented in {rel}")
                found = True
                break
        if not found:
            print(f"   ⚠️  {fn} not found in any expected location")

    if module_pm.strip() or writer.strip():
        print("\n📝 Step 2: Updating 00-shared/config/readme.tex...")
        readme = ol_path / "00-shared" / "config" / "readme.tex"
        if wf.update_readme_module_contacts(readme, module_pm, writer):
            print("   ✅ Filled Module PM / Writer in readme.tex")
        else:
            print("   ℹ️  readme.tex unchanged or file missing")

    print(f"\n📝 Step 3: Copying chapter folder from {base_project}/{base_id_module}/...")
    copy_dest_name = placeholder_folder if placeholder_folder else target_id_module
    dest_folder = ol_path / copy_dest_name
    merge_ph = placeholder_folder if placeholder_folder else target_id_module
    wf.copy_module_folder(
        module_folder,
        dest_folder,
        base_id_module,
        target_id_module,
        merge_placeholder=merge_ph,
    )

    print(
        "\n📝 Step 4: Copying chapter content (EN and CN) from base chapter "
        "(\\hypertarget … \\end{document})…",
    )
    for lang, base_main in (("EN", en_main), ("CN", cn_main)):
        target_main = ol_path / f"{source_id}__{lang}.tex"
        if not target_main.exists():
            print(f"   ⚠️  {source_id}__{lang}.tex not found in Overleaf repo")
            continue
        section = extract_chapter_content(base_main.read_text(encoding="utf-8"), base_main.name)
        section = section.replace(base_id_module, target_id_module)
        replace_chapter_content(target_main, section)
        print(f"   ✅ Updated {target_main.name}")

    print(f"\n📝 Step 5: Renaming {source_id} → {target_id_module}...")
    wf.rename_in_repo(ol_path, source_id, target_id_module)

    print("\n📝 Step 6: Verifying \\modulefiles...")
    wf.ensure_root_main_modulefiles(ol_path, target_id_module)

    non_source = "CN" if source_lang.upper() == "EN" else "EN"
    print(f"\n📝 Step 7: Moving {non_source} main file into module folder...")
    wf.move_non_source_main_to_module(ol_path, target_id_module, source_lang)

    print(f"\n📝 Step 8: Resolving \\tagged / \\iftagged / \\untagged macros for {base_project}...")
    resolved_count = 0
    module_dir = ol_path / target_id_module
    if module_dir.is_dir():
        for tex_file in sorted(module_dir.rglob("*.tex")):
            if resolve_tags_in_file(tex_file, base_project):
                resolved_count += 1
                print(f"   ✅ Resolved tags in {tex_file.relative_to(ol_path)}")
    for lang in ("EN", "CN"):
        main_file = ol_path / f"{target_id_module}__{lang}.tex"
        if main_file.exists() and resolve_tags_in_file(main_file, base_project):
            resolved_count += 1
            print(f"   ✅ Resolved tags in {main_file.name}")
    if resolved_count == 0:
        print("   ℹ️  No tag macros found")

    print("\n📝 Step 9: Removing -latest suffix from \\subfile{} references...")
    scan_paths: list[Path] = []
    module_dir2 = ol_path / target_id_module
    if module_dir2.is_dir():
        scan_paths.append(module_dir2)
    for lang in ("EN", "CN"):
        main_f = ol_path / f"{target_id_module}__{lang}.tex"
        if main_f.exists():
            scan_paths.append(main_f)
    cleaned = wf.remove_latest_suffix_in_subfile_refs(*scan_paths)
    if cleaned:
        for name in cleaned:
            print(f"   ✅ Cleaned -latest from \\subfile{{}} in {name}")
    else:
        print("   ℹ️  No -latest suffix found in \\subfile{} references")

    print("\n📝 Step 10: Copying source figures from figures repo...")
    if fig_path is not None:
        wf.copy_figures_sources(fig_path, ol_path, base_project, base_id_module, target_id_module)
    else:
        print("   ℹ️  Figures repo not available — skipping")

    return (placeholder_folder or target_id_module), base_id_module


def setup_normal_chapter(
    overleaf_id: str,
    base_project: str,
    target_id_module: str,
    source_lang: str,
    *,
    module_pm: str = "",
    writer: str = "",
):
    """Copy a chapter from esp-technical-reference-manual-latex into an Overleaf project."""
    wf._load_env()
    require_trm_env("OVERLEAF_TOKEN", "GITLAB_TOKEN")
    chapter_id, module = parse_id_module(target_id_module)

    print(f"\n{'=' * 60}")
    print("Mode 2: Set Up Normal Chapter (from base)")
    print(f"{'=' * 60}")
    print(f"   Overleaf ID:            {overleaf_id}")
    print(f"   Base project:           {base_project}")
    print(f"   Target ID–Module:       {target_id_module}")
    print(f"   Chapter ID:             {chapter_id}")
    print(f"   Module:                 {module}")
    print(f"   Source language:    {source_lang}")
    if module_pm.strip():
        print(f"   Module PM:          {module_pm.strip()}")
    if writer.strip():
        print(f"   Writer:             {writer.strip()}")
    print()

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        trm_path = tmp / "trm"
        ol_path = tmp / "ol"
        fig_path = tmp / "fig"
        wf.clone_trm(trm_path)
        ol_repo = wf.clone_overleaf(overleaf_id, ol_path)
        wf.clone_figures_repo(fig_path)

        _placeholder, base_mid = apply_normal_chapter_to_workdirs(
            ol_path,
            trm_path,
            base_project,
            target_id_module,
            source_lang,
            fig_path=fig_path,
            module_pm=module_pm,
            writer=writer,
        )

        print("\n📤 Pushing to Overleaf...")
        if ol_repo.is_dirty(untracked_files=True):
            ol_repo.git.add(A=True)
            ol_repo.index.commit(
                f"Set up {target_id_module} chapter (based on {base_project}/{base_mid})",
            )
            ol_repo.git.push("origin", "master")
            print("✅ Pushed to Overleaf")
        else:
            print("ℹ️  No changes to commit")

    print(f"\n{'=' * 60}")
    print("🎉 DONE — Normal chapter set up in Overleaf")
    print(f"{'=' * 60}")
    print(f"\n📋 Next steps:")
    print(f"   1. Open: https://www.overleaf.com/project/{overleaf_id}")
    print(f"   2. Review the chapter content")
    print(f"   3. Delete any leftover empty folders.")
    print(f"      (known Overleaf limitation)")
    print(f"   4. Copy the register descriptions from gdvs repo if needed")
    print(f"   5. Configure the \"Main document\" and \"Compiler\" settings in the UI")

