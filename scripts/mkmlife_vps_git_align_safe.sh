#!/usr/bin/env bash
# mkmlife-com VPS: safe working-tree align (stash untracked+tracked, ff-only pull).
# Run ON the VPS from repo root, e.g.:
#   cd /var/www/mkmlife_runtime/mkm-life
#   bash /path/to/mkmlife_vps_git_align_safe.sh
# Or after copying this file into the repo:
#   bash scripts/mkmlife_vps_git_align_safe.sh
#
# Does NOT run: git reset --hard, git clean -fd (requires explicit operator approval).
# Set MKMLIFE_GIT_ALIGN_DRY_RUN=1 to print commands only.

set -e

REPO_ROOT="${1:-$(pwd)}"
cd "$REPO_ROOT"

if [[ ! -d .git ]]; then
  echo "ERROR: not a git repo: $REPO_ROOT" >&2
  exit 1
fi

run() {
  if [[ "${MKMLIFE_GIT_ALIGN_DRY_RUN:-}" == "1" ]]; then
    echo "DRY_RUN: $*"
  else
    "$@"
  fi
}

echo "== mkmlife VPS safe align =="
echo "REPO_ROOT=$REPO_ROOT"
run git rev-parse --abbrev-ref HEAD
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

echo "== remote =="
run git remote -v

echo "== fetch =="
run git fetch origin

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
MSG="VPS safe align ${STAMP} (${BRANCH})"

echo "== stash (includes untracked; preserves server WIP in stash list) =="
# -u: include untracked; avoids 'git add .' and keeps rollback via stash pop
if ! run git stash push -u -m "${MSG}"; then
  echo "WARN: stash failed or nothing to stash; continuing." >&2
fi

echo "== pull (ff-only, upstream) =="
# Uses branch.<name>.merge (e.g. main -> origin/main).
run git pull --ff-only

echo "== status =="
run git status -sb

echo "== HEAD =="
run git rev-parse HEAD
if git show-ref --verify --quiet "refs/remotes/origin/${BRANCH}"; then
  echo "origin/${BRANCH}:"
  run git rev-parse "origin/${BRANCH}"
fi

echo "== recent stashes =="
run git stash list | head -n 8

echo ""
echo "OK: align pass done. If deploy needed: rebuild/restart app (e.g. pm2) per Hostinger runbook."
echo "Restore WIP: git stash list   then   git stash pop   (or apply a specific stash@{n})"
