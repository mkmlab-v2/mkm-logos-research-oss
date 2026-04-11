#!/usr/bin/env bash
# Git drift guard: compare HEAD to origin/main after optional fetch.
# Usage: scripts/verify_git_origin_main_sync.sh [--strict] [--no-fetch] [REPO_ROOT]
#   --strict   exit 1 if behind origin/main, ahead (unpushed), or diverged
#   --no-fetch use only local remote-tracking refs (offline / fast; may be stale)
# Env: REMOTE_NAME (default origin), MAIN_REF (default main)

set -euo pipefail

STRICT=0
NO_FETCH=0
REPO=""
REMOTE_NAME="${REMOTE_NAME:-origin}"
MAIN_REF="${MAIN_REF:-main}"

for a in "$@"; do
  case "$a" in
    --strict) STRICT=1 ;;
    --no-fetch) NO_FETCH=1 ;;
    -h|--help)
      echo "Usage: $0 [--strict] [--no-fetch] [REPO_ROOT]"
      exit 0
      ;;
    -*)
      echo "Unknown option: $a" >&2
      exit 2
      ;;
    *)
      REPO="$a"
      ;;
  esac
done

REPO="${REPO:-.}"
cd "$REPO"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "verify_git_origin_main_sync: not a git repository: $REPO" >&2
  exit 2
fi

UPSTREAM="refs/remotes/${REMOTE_NAME}/${MAIN_REF}"
if ! git rev-parse -q --verify "$UPSTREAM" >/dev/null 2>&1; then
  echo "verify_git_origin_main_sync: missing $UPSTREAM (add remote or fetch)" >&2
  if [[ "$STRICT" -eq 1 ]]; then exit 1; fi
  exit 0
fi

if [[ "$NO_FETCH" -eq 0 ]]; then
  if ! GIT_TERMINAL_PROMPT=0 git fetch "$REMOTE_NAME" --prune 2>/dev/null; then
    echo "verify_git_origin_main_sync: WARN: git fetch $REMOTE_NAME failed (network or auth)" >&2
    if [[ "$STRICT" -eq 1 ]]; then exit 1; fi
  fi
fi

BEHIND="$(git rev-list --count HEAD.."$UPSTREAM" 2>/dev/null || echo 0)"
AHEAD="$(git rev-list --count "$UPSTREAM"..HEAD 2>/dev/null || echo 0)"
H="$(git rev-parse --short HEAD 2>/dev/null)"
R="$(git rev-parse --short "$UPSTREAM" 2>/dev/null)"

DIRTY=""
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
  DIRTY=1
fi

ok=1
if [[ "${BEHIND:-0}" -gt 0 ]]; then
  echo "verify_git_origin_main_sync: HEAD $H is ${BEHIND} commit(s) BEHIND $REMOTE_NAME/$MAIN_REF ($R)" >&2
  echo "  Fix: git pull --ff-only $REMOTE_NAME $MAIN_REF" >&2
  ok=0
fi
if [[ "${AHEAD:-0}" -gt 0 ]]; then
  echo "verify_git_origin_main_sync: HEAD $H is ${AHEAD} commit(s) AHEAD of $REMOTE_NAME/$MAIN_REF (unpushed local commits)" >&2
  ok=0
fi
if [[ "${BEHIND:-0}" -gt 0 && "${AHEAD:-0}" -gt 0 ]]; then
  echo "verify_git_origin_main_sync: DIVERGED from $REMOTE_NAME/$MAIN_REF — do not blind pull; inspect git log / merge" >&2
  ok=0
fi
if [[ -n "$DIRTY" ]]; then
  echo "verify_git_origin_main_sync: WARN: dirty working tree (stash/commit before pull)" >&2
fi

if [[ "$ok" -eq 1 ]]; then
  echo "verify_git_origin_main_sync: OK HEAD $H matches $REMOTE_NAME/$MAIN_REF ($R) (behind=0 ahead=0)"
  exit 0
fi

if [[ "$STRICT" -eq 1 ]]; then
  exit 1
fi
exit 0
