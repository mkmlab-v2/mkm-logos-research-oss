#!/usr/bin/env bash
set -euo pipefail

REPO_PATH=""
BRANCH="main"
RELOAD_CMD=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-path)
      REPO_PATH="${2:-}"
      shift 2
      ;;
    --branch)
      BRANCH="${2:-}"
      shift 2
      ;;
    --reload-cmd)
      RELOAD_CMD="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$REPO_PATH" ]]; then
  echo "Missing required argument: --repo-path" >&2
  exit 2
fi

if [[ ! -d "$REPO_PATH" ]]; then
  echo "Repo path not found: $REPO_PATH" >&2
  exit 2
fi

cd "$REPO_PATH"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "Not a git repository: $REPO_PATH" >&2
  exit 2
fi

git fetch origin --prune >/dev/null 2>&1
BEFORE_HEAD="$(git rev-parse --short HEAD)"
REMOTE_HEAD="$(git rev-parse --short "refs/remotes/origin/$BRANCH")"

echo "[DEPLOY] repo=$REPO_PATH branch=$BRANCH"
echo "[DEPLOY] before_head=$BEFORE_HEAD origin_head=$REMOTE_HEAD"

git pull --ff-only origin "$BRANCH" >/dev/null

AFTER_HEAD="$(git rev-parse --short HEAD)"
BEHIND="$(git rev-list --count HEAD.."refs/remotes/origin/$BRANCH")"
AHEAD="$(git rev-list --count "refs/remotes/origin/$BRANCH"..HEAD)"

echo "[DEPLOY] after_head=$AFTER_HEAD behind=$BEHIND ahead=$AHEAD"

if [[ "$BEHIND" -ne 0 || "$AHEAD" -ne 0 ]]; then
  echo "[DEPLOY] sync_failed: HEAD diverged from origin/$BRANCH" >&2
  exit 1
fi

if [[ -n "$RELOAD_CMD" ]]; then
  echo "[DEPLOY] running reload_cmd=$RELOAD_CMD"
  bash -lc "$RELOAD_CMD"
else
  echo "[DEPLOY] reload step skipped (no --reload-cmd)."
fi

if command -v pm2 >/dev/null 2>&1; then
  echo "[DEPLOY] pm2 status snapshot:"
  pm2 ls | sed -n '1,20p'
fi

echo "[DEPLOY] OK"
