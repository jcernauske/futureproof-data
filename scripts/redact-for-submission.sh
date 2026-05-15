#!/usr/bin/env bash
# FutureProof — surgical history redaction for hackathon submission.
#
# Removes a small set of judge-strategy artifacts from ALL git history
# (not just HEAD). Force-push required afterwards.
#
# This is destructive and irreversible from the remote side. Read the
# script before running it. Run it on a clean working tree.
#
# Targets — files that reveal pre-submission judge-strategy analysis:
#   reports/hackathon-judge-score-2026-05-04.md
#   reports/hackathon-chances-review-2026-04-21.md
#   reports/gemma-usage-and-hackathon-review-2026-04-25.md
#
# Optional 4th target (uncomment in PATHS below to include):
#   reports/hackathon-ship-plan-2026-04-17.md
#
# Files NOT touched by this script (already absent from HEAD, never
# committed, or judged safe to leave in history):
#   - the kaggle-judge panel/holistic/video review sims
#   - docs/kaggle/winner*.txt files
#   - staff-engineer-audit, stat-calculation-audit, etc.
# Those live in ~/code/futureproof-cruft/ off-tree.

set -euo pipefail

if [ -t 1 ] && [ "${TERM:-}" != "dumb" ]; then
  G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; B=$'\033[1m'; X=$'\033[0m'
else
  G=""; R=""; Y=""; B=""; X=""
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# --- Paths to redact (edit here if scope changes) --------------------------

PATHS=(
  "reports/hackathon-judge-score-2026-05-04.md"
  "reports/hackathon-chances-review-2026-04-21.md"
  "reports/gemma-usage-and-hackathon-review-2026-04-25.md"
  "reports/hackathon-ship-plan-2026-04-17.md"
  # Kaggle judge personality dossiers — name 5 Google judges by name
  # and predict their scoring behavior. Categorically worse than the
  # reports above; must not survive in history.
  ".claude/agents/kaggle-judge.md"
  ".claude/agents/kaggle-writeup.md"
)

# --- Safety checks ---------------------------------------------------------

printf "%sFutureProof history redaction%s\n\n" "$B" "$X"

if ! command -v git-filter-repo >/dev/null 2>&1; then
  printf "%s✗%s git-filter-repo not installed.\n" "$R" "$X"
  printf "  Install: %sbrew install git-filter-repo%s  (or %spip install git-filter-repo%s)\n" "$B" "$X" "$B" "$X"
  exit 1
fi
printf "%s✓%s git-filter-repo available\n" "$G" "$X"

if ! git diff --quiet || ! git diff --cached --quiet; then
  printf "%s✗%s Working tree has uncommitted changes.\n" "$R" "$X"
  printf "  Commit or stash them first — filter-repo refuses to operate on a dirty tree.\n"
  exit 1
fi
printf "%s✓%s Working tree clean\n" "$G" "$X"

current_branch=$(git rev-parse --abbrev-ref HEAD)
printf "%s✓%s On branch: %s\n" "$G" "$X" "$current_branch"

# --- Verify targets exist in history ---------------------------------------

printf "\n%sTargets:%s\n" "$B" "$X"
missing=0
for path in "${PATHS[@]}"; do
  if git log --all --oneline -- "$path" 2>/dev/null | head -1 | grep -q .; then
    printf "  %s✓%s %s\n" "$G" "$X" "$path"
  else
    printf "  %s!%s %s (not in history — will be a no-op)\n" "$Y" "$X" "$path"
    missing=$((missing + 1))
  fi
done

# --- Backup branch ---------------------------------------------------------

backup_branch="backup-pre-redact-$(date +%Y%m%d-%H%M%S)"
printf "\n%sCreating backup branch:%s %s\n" "$B" "$X" "$backup_branch"
git branch "$backup_branch"
printf "  %s✓%s If anything goes wrong: %sgit reset --hard %s%s\n" "$G" "$X" "$B" "$backup_branch" "$X"

# --- Final confirmation ----------------------------------------------------

printf "\n%s⚠  About to rewrite history on branch '%s'.%s\n" "$Y" "$current_branch" "$X"
printf "   This is irreversible from the remote side after force-push.\n"
printf "   Files above will be removed from EVERY commit they appear in.\n\n"
read -r -p "Type 'redact' to continue, anything else to abort: " confirm
if [ "$confirm" != "redact" ]; then
  printf "%sAborted.%s Backup branch '%s' left in place.\n" "$Y" "$X" "$backup_branch"
  exit 0
fi

# --- The actual rewrite ----------------------------------------------------

printf "\n%sRunning git-filter-repo...%s\n" "$B" "$X"
filter_args=()
for path in "${PATHS[@]}"; do
  filter_args+=("--path" "$path")
done

git filter-repo --invert-paths --force "${filter_args[@]}"

printf "%s✓%s History rewritten.\n\n" "$G" "$X"

# --- Next steps ------------------------------------------------------------

printf "%sNext steps:%s\n" "$B" "$X"
printf "  1. Verify the targets are gone from history:\n"
for path in "${PATHS[@]}"; do
  printf "       git log --all --oneline -- %s\n" "$path"
done
printf "  2. Re-add the remote (filter-repo strips it):\n"
printf "       git remote add origin <your-github-url>\n"
printf "  3. Force-push when satisfied:\n"
printf "       git push --force-with-lease origin %s\n" "$current_branch"
printf "  4. If anything looks wrong: %sgit reset --hard %s%s\n" "$B" "$backup_branch" "$X"
printf "\n  Backup branch '%s' retained. Delete it once you've confirmed the rewrite is good.\n" "$backup_branch"
