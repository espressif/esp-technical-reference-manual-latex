"""Mode 3 (new chapter from outline template) workflow."""

from __future__ import annotations

import tempfile
from pathlib import Path

from tools.trm_automation_tools.common.id_ops import parse_id_module
from tools.trm_automation_tools.common.tex_sections import replace_chapter_content
from tools.trm_automation_tools.common.trm_env import require_trm_env
from tools.trm_automation_tools.setup import core as wf


def apply_new_chapter_to_workdir(
    ol_path: Path,
    target_id_module: str,
    source_lang: str,
    *,
    module_pm: str = "",
    writer: str = "",
) -> str:
    """Apply mode-3 file transforms on an existing Overleaf tree (no clone/push)."""
    placeholder_folder, source_id = wf.resolve_overleaf_source_id(ol_path, target_id_module)

    if module_pm.strip() or writer.strip():
        print("\n📝 Step 1: Updating 00-shared/config/readme.tex...")
        readme = ol_path / "00-shared" / "config" / "readme.tex"
        if wf.update_readme_module_contacts(readme, module_pm, writer):
            print("   ✅ Filled Module PM / Writer in readme.tex")
        else:
            print("   ℹ️  readme.tex unchanged or file missing")

    print(f"\n📝 Step 2: Renaming {source_id} → {target_id_module}...")
    wf.rename_in_repo(ol_path, source_id, target_id_module)

    print("\n📝 Step 3: Updating \\modulefiles...")
    wf.ensure_root_main_modulefiles(ol_path, target_id_module)

    non_source = "CN" if source_lang.upper() == "EN" else "EN"
    print(f"\n📝 Step 4: Moving {non_source} main file into module folder...")
    wf.move_non_source_main_to_module(ol_path, target_id_module, source_lang)

    print(f"\n📝 Step 5: Applying outline template...")
    shared = ol_path / "00-shared"
    template = wf.find_outline_template(shared, source_lang)
    if template:
        print(f"   Found template: {template.name}")
        template_content = wf.extract_outline_template(template)
        src_main = ol_path / f"{target_id_module}__{source_lang.upper()}.tex"
        if src_main.exists():
            replace_chapter_content(src_main, template_content)
            print(f"   ✅ Applied template to {src_main.name}")
        else:
            print(
                f"   ⚠️  Main file {target_id_module}__{source_lang.upper()}.tex not found",
            )
    else:
        print(f"   ⚠️  Outline template for {source_lang} not found in 00-shared/")

    return placeholder_folder or target_id_module


def setup_new_chapter(
    overleaf_id: str,
    target_id_module: str,
    source_lang: str,
    *,
    module_pm: str = "",
    writer: str = "",
):
    """Set up a brand-new chapter in Overleaf from the outline template."""
    wf._load_env()
    require_trm_env("OVERLEAF_TOKEN")
    chapter_id, module = parse_id_module(target_id_module)

    print(f"\n{'=' * 60}")
    print("Mode 3: Set Up New Chapter (from template)")
    print(f"{'=' * 60}")
    print(f"   Overleaf ID:            {overleaf_id}")
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
        ol_path = tmp / "ol"
        ol_repo = wf.clone_overleaf(overleaf_id, ol_path)

        apply_new_chapter_to_workdir(
            ol_path,
            target_id_module,
            source_lang,
            module_pm=module_pm,
            writer=writer,
        )

        print("\n📤 Pushing to Overleaf...")
        if ol_repo.is_dirty(untracked_files=True):
            ol_repo.git.add(A=True)
            ol_repo.index.commit(
                f"Set up new {target_id_module} chapter from template",
            )
            ol_repo.git.push("origin", "master")
            print("✅ Pushed to Overleaf")
        else:
            print("ℹ️  No changes to commit")

    print(f"\n{'=' * 60}")
    print("🎉 DONE — New chapter set up in Overleaf")
    print(f"{'=' * 60}")
    print(f"\n📋 Next steps:")
    print(f"   1. Open: https://www.overleaf.com/project/{overleaf_id}")
    print(f"   2. Review the chapter content")
    print(f"   3. Configure the \"Main document\" and \"Compiler\" settings in the UI")

