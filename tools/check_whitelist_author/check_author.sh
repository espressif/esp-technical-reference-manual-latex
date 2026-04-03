#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# This script checks commit authors in the current branch.
# It verifies that *every commit* from the merge base (branch point)
# with the comparison branch to HEAD has a whitelisted author.
#
# Comparison branch:
#   - MR pipeline: CI_MERGE_REQUEST_TARGET_BRANCH_NAME (e.g. release/v0.1 for backport MRs),
#     so only commits on top of the MR target are checked—not the whole release line vs master.
#   - Otherwise: master
#
# Whitelist source:
#   CI/CD variable AUTHOR_WHITELIST, format: comma-separated emails, e.g. user1@company.com,user2@company.com
# ============================================================

if [[ -z "${AUTHOR_WHITELIST:-}" ]]; then
  echo "❌ AUTHOR_WHITELIST is not set. Set CI/CD variable AUTHOR_WHITELIST (comma-separated emails)."
  exit 1
fi

# Parse comma-separated list, trim each entry, drop empty
WHITELIST=()
while IFS= read -r line; do
  trimmed=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  [[ -n "$trimmed" ]] && WHITELIST+=("$trimmed")
done < <(echo "$AUTHOR_WHITELIST" | tr ',' '\n')

if [[ ${#WHITELIST[@]} -eq 0 ]]; then
  echo "❌ AUTHOR_WHITELIST is empty or invalid (use comma-separated emails)."
  exit 1
fi

echo "📄 Loaded $((${#WHITELIST[@]})) whitelisted author(s) from AUTHOR_WHITELIST"

BASE_BRANCH="${CI_MERGE_REQUEST_TARGET_BRANCH_NAME:-master}"
if ! git rev-parse --verify "origin/$BASE_BRANCH" >/dev/null 2>&1; then
  echo "❌ Ref origin/$BASE_BRANCH not found. Fetch that branch in CI before_script (e.g. git fetch origin $BASE_BRANCH)."
  exit 1
fi

MERGE_BASE=$(git merge-base "origin/$BASE_BRANCH" HEAD)

echo "🔍 Commit range to check (vs origin/$BASE_BRANCH):"
echo "   From: $MERGE_BASE"
echo "   To:   $(git rev-parse HEAD)"
echo ""

COMMITS=$(git log "$MERGE_BASE"..HEAD --pretty=format:"%H")

if [[ -z "$COMMITS" ]]; then
  echo "✅ No new commits compared to master. Nothing to check."
  exit 0
fi

# Validate each commit
has_violation=false

for commit in $COMMITS; do
  AUTHOR_EMAIL=$(git show -s --pretty=format:'%ae' "$commit")
  AUTHOR_NAME=$(git show -s --pretty=format:'%an' "$commit")

  echo "🔎 Checking commit $commit — $AUTHOR_NAME <$AUTHOR_EMAIL>"

  whitelisted=false
  for allowed in "${WHITELIST[@]}"; do
    if [[ "$AUTHOR_EMAIL" == "$allowed" ]]; then
      whitelisted=true
      break
    fi
  done

  if [[ "$whitelisted" == false ]]; then
    echo "❌ Commit $commit is NOT whitelisted:"
    echo "   $AUTHOR_NAME <$AUTHOR_EMAIL>"
    has_violation=true
  fi
done

if [[ "$has_violation" == true ]]; then
  echo ""
  echo "🚫 Some commits have non-whitelisted authors."
  echo "👉 Please rewrite commits locally:"
  echo ""
  echo "     git rebase -i [commit_id_placeholder]"
  echo "     git commit --amend --author=\"Bot <bot@yourcompany.com>\""
  echo "     git push --force-with-lease"
  echo ""
  exit 1
fi

echo ""
echo "✅ All commit authors are whitelisted."
exit 0
