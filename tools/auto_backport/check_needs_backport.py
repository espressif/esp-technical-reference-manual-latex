#!/usr/bin/env python3
"""
Automatically check merged MR for reused chapter changes and manage 'needs backport' label.
Runs when an MR is merged (push pipeline on default branch). Resolves the merged MR from
the merge commit message (e.g. "See merge request ... !IID").
"""

import os
import re
import urllib3
import gitlab

# Suppress HTTPS InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Path to reused chapters list (.tex paths and module folder paths from collect_reused_chapters.py)
REUSED_CHAPTER_LIST = os.path.join(os.path.dirname(__file__), "reused_chapter_list.txt")


def get_merged_mr_iid(project, commit_sha):
    """Resolve merged MR IID from merge commit message (See merge request ... !IID)."""
    commit = project.commits.get(commit_sha)
    message = commit.message or ""
    # GitLab appends "See merge request namespace/project!IID" to merge commit message
    match = re.search(r"[Ss]ee merge request\s+\S+!(\d+)", message)
    if not match:
        return None
    return int(match.group(1))


def normalize_modified_path(p: str) -> str:
    p = p.replace("\\", "/")
    return p if p.startswith("./") else "./" + p


def modification_triggers_backport(modified: str, reused_paths: set[str]) -> bool:
    """
    True if modified path matches a listed .tex file, or is under a listed module folder,
    or is the root __CN/__EN .tex for that module (e.g. ./ESP32-C5/02-RISCVTRACENC__CN.tex).
    """
    m = normalize_modified_path(modified)
    if m in reused_paths:
        return True
    for entry in reused_paths:
        if entry.endswith(".tex"):
            continue
        if m == entry + "__CN.tex" or m == entry + "__EN.tex":
            return True
        prefix = entry.rstrip("/") + "/"
        if m.startswith(prefix):
            return True
    return False


def collect_triggered_files(modified_files: set[str], reused_paths: set[str]) -> list[str]:
    return sorted(p for p in modified_files if modification_triggers_backport(p, reused_paths))


def main():
    # GitLab connection
    url = f"https://{os.environ['CI_SERVER_HOST']}:{os.environ['CI_SERVER_PORT']}"
    token = os.environ["TRM_BACKPORT_GL_TOKEN"]
    commit_sha = os.environ.get("CI_COMMIT_SHA")

    gl = gitlab.Gitlab(url, token, api_version=4, ssl_verify=False)
    project = gl.projects.get(os.environ["CI_PROJECT_PATH"])

    mr_iid = get_merged_mr_iid(project, commit_sha)
    if mr_iid is None:
        print("Not a merge commit or no MR reference in message, skipping.")
        return

    mr = project.mergerequests.get(mr_iid)
    if mr.state != "merged":
        print(f"MR !{mr_iid} is not in merged state, skipping.")
        return

    # Load reused chapter paths
    with open(REUSED_CHAPTER_LIST, "r", encoding="utf-8") as f:
        reused_paths = set(line.strip() for line in f if line.strip())

    # Check changes in MR
    changes = mr.changes()["changes"]
    modified_files = {
        f.get("new_path") or f.get("old_path")
        for f in changes
        if f.get("new_path") or f.get("old_path")
    }
    # Normalize to same format as list (with ./ prefix)
    modified_files = {normalize_modified_path(p) for p in modified_files}

    # Find intersection with reused chapter list
    triggered_files = collect_triggered_files(modified_files, reused_paths)

    if not triggered_files:
        print("No reused chapter files modified, no backport needed.")
        return

    labels_lower = [l.lower() for l in mr.labels]

    if "needs backport" in labels_lower:
        print("Reused chapter files modified, 'needs backport' label already present.")
        print("Triggered files:", triggered_files)
        return

    # need_backport is True and label not present, then add it
    mr.labels.append("needs backport")
    mr.save()
    mr.notes.create({
        "body": (
            "✅ This MR modifies reused chapter files and requires backport.\n"
            "Label `needs backport` added automatically.\n"
            f"Triggered files:\n- " + "\n- ".join(triggered_files)
        )
    })

    print("Reused chapter files modified, 'needs backport' label has been automatically added.")
    print("Triggered files:", triggered_files)


if __name__ == "__main__":
    main()
