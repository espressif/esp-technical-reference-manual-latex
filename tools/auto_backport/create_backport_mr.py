#!/usr/bin/env python3
"""
Automatic Backport MR Creation

Runs when an MR is merged (push pipeline on default branch). Resolves the merged MR
from the merge commit message (e.g. "See merge request ... !IID").

Trigger conditions:
- Original MR has 'needs backport'
- Original MR does NOT have 'backport created'

Steps:
1. Check backport labels
2. Create new backport branch from target branch commit SHA (or use existing branch)
3. Cherry-pick commit(s); paths matching revision-history file names are skipped (target branch kept) to reduce conflicts
4. Push backport branch using TRM_BACKPORT_GL_TOKEN
5. Create backport MR
6. Update original MR description with backport link
7. Add 'backport created' label to original MR
8. Notify conflicts in MR
"""

import os
import re
import shlex
import sys
import subprocess
import tempfile
import urllib3
import gitlab

# Suppress HTTPS InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CI Environment Variables
CI_PROJECT_PATH = os.environ["CI_PROJECT_PATH"]
CI_SERVER_URL = f"https://{os.environ['CI_SERVER_HOST']}:{os.environ['CI_SERVER_PORT']}"
TRM_BACKPORT_GL_TOKEN = os.environ["TRM_BACKPORT_GL_TOKEN"]
CI_COMMIT_SHA = os.environ.get("CI_COMMIT_SHA")

# Backport configuration
BACKPORT_TARGET_BRANCH = "release/v0.1"
NEEDS_BACKPORT_LABEL = "needs backport"
BACKPORT_CREATED_LABEL = "backport created"
RELEASE_LABEL = "release"
# BACKPORT_LABEL = "backport"

# Paths matching these substrings are not backported (keep target branch version; avoids merge conflicts)
REVISION_HISTORY_MARKERS = ("revision-history__", "revision-history-latest__")


def is_revision_history_path(path: str) -> bool:
    return any(m in path for m in REVISION_HISTORY_MARKERS)


def get_files_changed_in_commit(commit_id: str) -> list[str]:
    """List paths changed in commit (vs first parent)."""
    r = run(f"git diff-tree --no-commit-id --name-only -r {commit_id}^ {commit_id}", check=False)
    if r.returncode != 0 or not r.stdout.strip():
        r = run(f"git show --pretty=format: --name-only {commit_id}", check=True)
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def get_unmerged_paths() -> list[str]:
    r = run("git diff --name-only --diff-filter=U", check=True)
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def drop_revision_history_changes_from_index(commit_id: str) -> None:
    """After cherry-pick -n, restore revision-history paths to HEAD (target branch)."""
    for path in get_files_changed_in_commit(commit_id):
        if not is_revision_history_path(path):
            continue
        q = shlex.quote(path)
        r = run(f"git checkout HEAD -- {q}", check=False)
        if r.returncode != 0:
            run(f"git rm -f --ignore-unmatch {q}", check=False)


def commit_cherry_pick_with_original_message(commit_id: str) -> bool:
    """Create commit if there is anything staged; return False if nothing to commit."""
    r = run("git diff --cached --quiet", check=False)
    if r.returncode == 0:
        run("git reset", check=False)
        print(f"  (no non–revision-history changes in {commit_id[:8]}, skipping empty commit)")
        return False
    msg = run(f"git log -1 --format=%B {commit_id}", check=True).stdout
    with tempfile.NamedTemporaryFile("w", suffix=".gitmsg", delete=False, encoding="utf-8") as f:
        f.write(msg)
        msg_path = f.name
    try:
        run(f'git commit -F "{msg_path}"')
    finally:
        os.unlink(msg_path)
    return True


def cherry_pick_commit_skip_revision_history(commit_id: str) -> bool:
    """
    Cherry-pick commit without applying revision-history file changes (target branch keeps those files).
    Resolves conflicts on revision-history paths by keeping ours.
    Returns True on success, False if aborted due to unresolved conflicts.
    """
    result = run(f"git cherry-pick -n {commit_id}", check=False)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        unmerged = get_unmerged_paths()
        if not unmerged:
            run("git cherry-pick --abort", check=False)
            return False
        for path in unmerged:
            if is_revision_history_path(path):
                q = shlex.quote(path)
                run(f"git checkout --ours -- {q}")
                run(f"git add {q}")
        remaining = get_unmerged_paths()
        if remaining:
            print(f"⚠️ Unresolved conflicts (non–revision-history): {remaining}")
            run("git cherry-pick --abort", check=False)
            return False

    drop_revision_history_changes_from_index(commit_id)
    commit_cherry_pick_with_original_message(commit_id)
    return True


def get_merged_mr_iid(project, commit_sha):
    """Resolve merged MR IID from merge commit message (See merge request ... !IID)."""
    commit = project.commits.get(commit_sha)
    message = commit.message or ""
    match = re.search(r"[Ss]ee merge request\s+\S+!(\d+)", message)
    if not match:
        return None
    return int(match.group(1))


# Helper function to run shell commands
def run(cmd, check=True):
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result


# Initialize GitLab API and resolve MR
gl = gitlab.Gitlab(CI_SERVER_URL, private_token=TRM_BACKPORT_GL_TOKEN, api_version=4, ssl_verify=False)
project = gl.projects.get(CI_PROJECT_PATH)

mr_iid = get_merged_mr_iid(project, CI_COMMIT_SHA)
if mr_iid is None:
    print("Not a merge commit or no MR reference in message, skipping backport.")
    sys.exit(0)
mr = project.mergerequests.get(mr_iid)
if mr.state != "merged":
    print(f"MR !{mr_iid} is not in merged state, skipping backport.")
    sys.exit(0)

# Step 1: Check if backport is required
labels_lower = [l.lower() for l in mr.labels]
if NEEDS_BACKPORT_LABEL not in labels_lower:
    print(f"No '{NEEDS_BACKPORT_LABEL}' label. Backport not required.")
    sys.exit(0)
if BACKPORT_CREATED_LABEL in labels_lower:
    print(f"'{BACKPORT_CREATED_LABEL}' label exists. Skipping backport.")
    sys.exit(0)
print("'needs backport' label detected, proceeding with backport.")

# Step 2: Create or use existing backport branch
backport_branch = f"{mr.source_branch}_v0.1"

# Get commit SHA of target branch (needed for both create and reset-existing)
target_branch_obj = project.branches.get(BACKPORT_TARGET_BRANCH)
target_sha = target_branch_obj.commit["id"]

branch_existed = False
try:
    # Try to create new branch
    project.branches.create({'branch': backport_branch, 'ref': target_sha})
    print(f"Created backport branch '{backport_branch}' from '{BACKPORT_TARGET_BRANCH}' (SHA: {target_sha})")

except gitlab.exceptions.GitlabCreateError as e:
    if "Branch already exists" in str(e):
        branch_existed = True
        print(f"Backport branch '{backport_branch}' already exists. Will reset to target then cherry-pick.")
    else:
        print(f"Failed to create backport branch: {e}")
        sys.exit(1)

# Step 3: Checkout backport branch and cherry-pick all MR commits (record conflicts)
failed_commits = []

# Ensure we start from target branch clean state
run(f"git fetch origin {BACKPORT_TARGET_BRANCH}")
run(f"git fetch origin {backport_branch}")
run(f"git checkout -B {backport_branch} origin/{backport_branch}")

# If reusing existing backport branch, reset to target so we only have this run's cherry-pick (no stale content from previous runs)
if branch_existed:
    print(f"Resetting backport branch to {BACKPORT_TARGET_BRANCH} (SHA: {target_sha}) so only this MR's commit(s) are backported.")
    run(f"git reset --hard {target_sha}")
    remote_url = f"https://gitlab-ci-token:{TRM_BACKPORT_GL_TOKEN}@{os.environ['CI_SERVER_HOST']}:{os.environ['CI_SERVER_PORT']}/{CI_PROJECT_PATH}.git"
    run(f"git remote set-url origin {remote_url}")
    run(f"git push --force origin {backport_branch}")

# Configure git committer to original MR assignee (for cherry-pick commits)
if mr.assignee:
    assignee_name = mr.assignee["name"]
    assignee_email = f"{mr.assignee['username']}@espressif.com"

run(f'git config user.name "{assignee_name}"')
run(f'git config user.email "{assignee_email}"')

# Cherry-pick all commits of the MR (oldest first for correct history; GitLab API returns newest first)
mr_commits = list(mr.commits())[::-1]
for commit in mr_commits:
    commit_id = commit.id
    print(f"Attempting to cherry-pick {commit_id} (revision-history files skipped)...")
    if cherry_pick_commit_skip_revision_history(commit_id):
        print(f"Cherry-pick {commit_id} succeeded")
    else:
        failed_commits.append(commit_id)
        print(f"⚠️ Cherry-pick aborted for commit {commit_id}")

# Step 4: Configure remote URL with CI_JOB_TOKEN for push
remote_url = f"https://gitlab-ci-token:{TRM_BACKPORT_GL_TOKEN}@{os.environ['CI_SERVER_HOST']}:{os.environ['CI_SERVER_PORT']}/{CI_PROJECT_PATH}.git"
run(f"git remote set-url origin {remote_url}")
run(f"git push origin {backport_branch}")

# Step 5: Create backport MR
if "## Related" in mr.description:
    # Insert backport link after existing '## Related' section
    backport_description = mr.description.replace(
        "## Related",
        f"## Related\n- Backport of !{mr.iid}",
        1
    )
else:
    # No '## Related' section, append it at the end
    backport_description = f"{mr.description}\n\n## Related\n* Backport of !{mr.iid}"

# Copy original MR labels except backport- and release-specific ones
labels_exclude = {
    NEEDS_BACKPORT_LABEL.lower(),
    BACKPORT_CREATED_LABEL.lower(),
    RELEASE_LABEL.lower(),
}
backport_labels = [l for l in mr.labels if (l or "").strip() and (l.strip().lower() not in labels_exclude)]

# Create the backport MR
backport_mr = project.mergerequests.create({
    "source_branch": backport_branch,
    "target_branch": BACKPORT_TARGET_BRANCH,
    "title": f"{mr.title} (v0.1)",
    "description": backport_description,
    "assignee_id": mr.assignee["id"] if mr.assignee else None,
    "reviewer_ids": [r["id"] for r in mr.reviewers],
    "labels": backport_labels,
})
print(f"Backport MR created: !{backport_mr.iid}")

# Step 6: Update original MR description
related_line = f"- release/v0.1 backport: !{backport_mr.iid}"
if "## Related" in mr.description:
    new_desc = mr.description.replace("## Related", f"## Related\n{related_line}", 1)
else:
    new_desc = f"{mr.description}\n## Related\n{related_line}"
mr.description = new_desc
mr.save()
print("Original MR description updated with backport link.")

# Step 7: Add 'backport created' label to original MR
mr.labels.append(BACKPORT_CREATED_LABEL)
mr.save()
print("'backport created' label added to original MR.")

# Step 8: Notify conflicts in MR
if failed_commits or backport_mr.merge_status == "cannot_be_merged":
    conflict_text = "\n".join([f"* {c}" for c in failed_commits]) if failed_commits else ""
    backport_mr.notes.create({
        "body": (
            "⚠️ Automatic backport MR has conflicts. "
            "Please resolve them manually.\n"
            f"{conflict_text}"
        )
    })
    print("Conflict detected. User notified in backport MR.")

print("Backport process completed successfully.")
