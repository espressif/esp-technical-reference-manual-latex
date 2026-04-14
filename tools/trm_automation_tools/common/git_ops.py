"""Shared git/GitLab workflow helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path


def checkout_or_create_branch(repo, branch_name: str):
    """Checkout existing branch or create new from master."""
    repo.git.fetch("origin")
    remote_ref = f"origin/{branch_name}"
    try:
        repo.git.rev_parse("--verify", remote_ref)
        repo.git.checkout("-B", branch_name, remote_ref)
        print(f"✅ Checked out existing branch: {branch_name}")
        return True
    except Exception:  # pylint: disable=broad-exception-caught
        repo.git.checkout("-b", branch_name, "origin/master")
        print(f"✅ Created new branch: {branch_name}")
        return False


def get_or_create_mr(
    gl_instance,
    project,
    source_branch,
    target_branch,
    title,
    description,
    labels=None,
    assignee_id=None,
):
    """Get existing MR or create a new one."""
    existing = project.mergerequests.list(
        state="opened", source_branch=source_branch, target_branch=target_branch,
    )
    if existing:
        mr = existing[0]
        mr.description = description
        if labels:
            mr.labels = labels
        mr.save()
        print(f"ℹ️  Updated existing MR: {mr.web_url}")
        return mr, False

    mr_data = {
        "source_branch": source_branch,
        "target_branch": target_branch,
        "title": title,
        "description": description,
        "remove_source_branch": True,
    }
    aid = assignee_id
    if aid is None and getattr(gl_instance, "user", None) is not None:
        aid = gl_instance.user.id
    if aid is not None:
        mr_data["assignee_id"] = aid
    if labels:
        mr_data["labels"] = labels
    mr = project.mergerequests.create(mr_data)
    print(f"✅ Created new MR: {mr.web_url}")
    return mr, True


def run_pre_commit(repo_path: Path, files: list[str] | None = None):
    """Run pre-commit hooks; returns ``True`` if clean."""
    print("\n🔍 Running pre-commit checks...")
    cmd = ["pre-commit", "run", "--config", ".pre-commit-config.yaml"]
    if files:
        cmd.extend(["--files"] + files)
    else:
        cmd.append("--all-files")
    result = subprocess.run(
        cmd, cwd=repo_path, capture_output=True, text=True, check=False,
    )
    if result.returncode == 0:
        print("   ✅ Pre-commit checks passed")
        return True
    print("   ⚠️  Pre-commit found issues:")
    for line in result.stdout.split("\n"):
        if line.strip():
            print(f"      {line}")
    if result.stderr:
        for line in result.stderr.split("\n")[:10]:
            if line.strip():
                print(f"      {line}")
    return False
