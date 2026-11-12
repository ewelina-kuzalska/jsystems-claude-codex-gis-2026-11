#!/usr/bin/env bash
# Read-only public-course review collection. Uses the caller's existing gh auth.
set -euo pipefail
pr_number="${1:?Usage: bash read-review.sh UPSTREAM_PR_NUMBER}"
if [[ ! "$pr_number" =~ ^[1-9][0-9]*$ ]]; then
  printf '%s\n' 'PR number must be a positive integer.' >&2
  exit 2
fi
upstream='LucasMatuszewski/jsystems-claude-codex-gis-2026-11'
gh pr view "$pr_number" --repo "$upstream" --json number,url,headRefOid,headRefName,baseRefName
gh api --method GET --paginate "repos/$upstream/pulls/$pr_number/reviews"
gh api --method GET --paginate "repos/$upstream/pulls/$pr_number/comments"
gh api --method GET --paginate "repos/$upstream/issues/$pr_number/comments"
