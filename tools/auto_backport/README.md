# Automatic Backport Workflow

This workflow automates backporting MRs from `master` branch to `release/v0.1` branch. It ensures that reused chapter changes are correctly propagated to the target branch, while safely handling conflicts and notifications.


## Overview

**Branch roles:**
- `master`: Main integration branch for **public TRM sources**. Only this branch is pushed to GitHub.
- `release/v0.1`: Internal branch used to prepare the **initial release of new TRMs**. It is not publicly visible and is not a mirror of `master`. It receives backported updates to reused chapters from `master`.

Backporting to `release/v0.1` is primarily for **preview builds**, including:
- Internal preview (engineer reference, editor review)
- External preview for specific customers

The goal is to ensure that the document builds as a complete TRM.


## Reused Chapters

**Reused chapters** are chapters in TRM A (source TRM) that include chapter files from TRM B (the target TRM) via `\subfile`, because the two chapters are highly similar. The list of such files is maintained in `reused_chapter_list.txt` on `master`.

When a reused chapter in the source TRM is updated on `master`, the same change should be backported so that target TRMs on `release/v0.1` that reuse it stay in sync.

**Updating the list:** Run `collect_reused_chapters.py` from the repo root. It scans `.tex` files for `\subfile{../...}` and overwrites `reused_chapter_list.txt` with the collected paths:

```bash
python3 tools/auto_backport/collect_reused_chapters.py
```

Run this whenever you add or remove `\subfile` references so the backport check stays accurate.

When preparing new TRM chapters:

- If the source TRM is maintained on `master`, module PMs could manually add reused chapters to `reused_chapter_list.txt` on `master`, or run the script on `release/v0.1` and update the list on `master`.
- If the source TRM is maintained on `release/v0.1`, the TRM owner should run the script and update the list on `master` when the source TRM is published to `master`.


## Trigger Conditions

The backport flow is triggered when **reused chapters are updated** in an MR:

1. On every MR pipeline, `check_needs_backport.py` checks whether any changed file is in `reused_chapter_list.txt`. If so, it adds the **`needs backport`** label and posts a note.
2. `create_backport_mr.py` runs and adds the **`backport created`** label.


## Components

### 1. `check_needs_backport.py`
- Runs when an MR is merged.
- Compares the MR’s changed files with `reused_chapter_list.txt`.
- If any reused chapter is modified:
  - Automatically adds the **`needs backport`** label.
  - Posts a note in the MR to notify participants.
- If the label is already present or no reused files are changed, the script exits silently.

### 2. `create_backport_mr.py`
- Runs when an MR is merged.
- Creates a backport when the MR has **`needs backport`** and does not yet have **`backport created`**.
- Performs the following steps:

#### Step 1: Check Backport Labels
- Confirms that the MR requires backport and hasn't been backported yet.

#### Step 2: Create or Use Backport Branch
- Branch name: `<source-branch>_<target-branch>` (e.g., `docs/add_auto_backport_v0.1`).
- If the branch does not exist, it is created from the target branch (`release/v0.1`).
- If it exists, the existing branch is used.

#### Step 3: Cherry-pick Commit(s)
- Currently only the **latest commit** of the original MR is cherry-picked for testing. In the final design, all commits in the original MR will be backported.
- Sets Git committer info to the original MR assignee.
- Conflicts are recorded. Cherry-pick failures do **not block MR creation**.

#### Step 4: Push Backport Branch
- The branch is pushed to GitLab using `TRM_BACKPORT_GL_TOKEN` for authentication.

#### Step 5: Create Backport MR
- Title: Copies original MR title with `(v0.1)` suffix.
- Description:
  - If `## Related` exists in the original MR, a reference to the original MR is added below it.
  - Otherwise, a new `## Related` section is appended.
- Assignee and reviewers are copied from the original MR.

#### Step 6: Update Original MR
- Description:
  - If `## Related` exists in the original MR, a reference to the backport MR is added below it.
  - Otherwise, a new `## Related` section is appended.
- Adds the label **`backport created`**.

#### Step 7: Conflict Notification
- If cherry-pick conflicts occur, a note is added to the backport MR listing conflicting commits.
- Users are instructed to resolve conflicts manually.


## Revision History Handling

The `release/v0.1 branch` is not intended to maintain the source TRM’s formal revision history.

Revision history files (`revision-history__*.tex`, `revision-history-latest__*.tex`, typically under `00-chip-spec-content/`) are therefore **not** carried over from `master` during backport. The `release/v0.1` branch retains its existing revision history content, while substantive documentation changes in reused chapters are still applied.

The `create_backport_mr.py` script **excludes** any paths containing `revision-history__` or `revision-history-latest__`. For each cherry-picked commit, only non–revision history files are backported.

If a cherry-pick encounters conflicts only in revision history files, those conflicts are resolved by keeping the release branch version. Conflicts in non–revision history files will still cause the cherry-pick to abort and must be resolved manually.
