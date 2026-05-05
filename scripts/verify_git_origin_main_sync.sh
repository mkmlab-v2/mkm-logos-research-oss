#!/usr/bin/env bash
# Git drift guard: compare HEAD to origin/main after optional fetch.
# Usage: scripts/verify_git_origin_main_sync.sh [--strict] [--no-fetch] [--check-internal-safety] [REPO_ROOT]
#   --strict   exit 1 if behind origin/main, ahead (unpushed), or diverged
#   --no-fetch use only local remote-tracking refs (offline / fast; may be stale)
#   --check-internal-safety
#              additionally verify internal remote safety:
#              - internal URL should match REMOTE_NAME URL (alias mode)
#              - HEAD and internal/main should share merge-base (no unrelated history)
# Env: REMOTE_NAME (default origin), MAIN_REF (default main)

set -euo pipefail

STRICT=0
NO_FETCH=0
CHECK_INTERNAL_SAFETY=0
REPO=""
REMOTE_NAME="${REMOTE_NAME:-origin}"
MAIN_REF="${MAIN_REF:-main}"
INTERNAL_NAME="${INTERNAL_NAME:-internal}"

for a in "$@"; do
  case "$a" in
    --strict) STRICT=1 ;;
    --no-fetch) NO_FETCH=1 ;;
    --check-internal-safety) CHECK_INTERNAL_SAFETY=1 ;;
    -h|--help)
      echo "Usage: $0 [--strict] [--no-fetch] [--check-internal-safety] [REPO_ROOT]"
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

if [[ "$CHECK_INTERNAL_SAFETY" -eq 1 ]]; then
  origin_url="$(git remote get-url "$REMOTE_NAME" 2>/dev/null || true)"
  internal_url="$(git remote get-url "$INTERNAL_NAME" 2>/dev/null || true)"
  if [[ -z "$internal_url" ]]; then
    echo "verify_git_origin_main_sync: WARN: missing remote '$INTERNAL_NAME' (internal safety check skipped)" >&2
    if [[ "$STRICT" -eq 1 ]]; then exit 1; fi
  else
    if [[ "$origin_url" != "$internal_url" ]]; then
      echo "verify_git_origin_main_sync: WARN: $INTERNAL_NAME URL differs from $REMOTE_NAME URL" >&2
      echo "  Fix: git remote set-url $INTERNAL_NAME \"$origin_url\"" >&2
      if [[ "$STRICT" -eq 1 ]]; then exit 1; fi
    fi
    if ! GIT_TERMINAL_PROMPT=0 git fetch "$INTERNAL_NAME" --prune >/dev/null 2>&1; then
      echo "verify_git_origin_main_sync: WARN: git fetch $INTERNAL_NAME failed (cannot validate ancestry)" >&2
      if [[ "$STRICT" -eq 1 ]]; then exit 1; fi
    else
      internal_upstream="refs/remotes/${INTERNAL_NAME}/${MAIN_REF}"
      if git rev-parse -q --verify "$internal_upstream" >/dev/null 2>&1; then
        if ! git merge-base HEAD "$internal_upstream" >/dev/null 2>&1; then
          echo "verify_git_origin_main_sync: WARN: HEAD and $INTERNAL_NAME/$MAIN_REF have no merge-base (likely unrelated histories)" >&2
          echo "  Stop: do not run blind pull/merge across different repo lineages." >&2
          if [[ "$STRICT" -eq 1 ]]; then exit 1; fi
        else
          mb="$(git merge-base --short HEAD "$internal_upstream" 2>/dev/null || true)"
          echo "verify_git_origin_main_sync: OK merge-base HEAD <-> $INTERNAL_NAME/$MAIN_REF = ${mb:-present}"
        fi
      fi
    fi
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
