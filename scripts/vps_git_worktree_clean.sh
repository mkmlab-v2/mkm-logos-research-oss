#!/usr/bin/env bash
# VPS / SSH Cursor: monorepo 워킹 트리를 origin/main과 맞추고, 알려진 로컬 드리프트를 정리한다.
# SSOT는 GitHub; 서버에서 소스만 고치면 다음 pull과 어긋난다.
#
# 사용 (레포 루트에서):
#   bash scripts/vps_git_worktree_clean.sh --dry-run
#   bash scripts/vps_git_worktree_clean.sh
#   bash scripts/vps_git_worktree_clean.sh --remove-untracked-btc-env-example
#
# 옵션:
#   --dry-run     fetch/status/diff만 (복구 없음)
#   --no-pull     pull 생략 (fetch만)
#   --remove-untracked-btc-env-example
#                 추적되지 않는 projects/bitcoin-trading/.env.example 삭제(루트 .env.example이 SSOT인 경우 중복 제거)

set -euo pipefail

REMOTE_NAME="${REMOTE_NAME:-origin}"
MAIN_REF="${MAIN_REF:-main}"
DRY_RUN=0
NO_PULL=0
REMOVE_UNTRACKED_BTC_ENV=0

for a in "$@"; do
  case "$a" in
    --dry-run) DRY_RUN=1 ;;
    --no-pull) NO_PULL=1 ;;
    --remove-untracked-btc-env-example) REMOVE_UNTRACKED_BTC_ENV=1 ;;
    -h|--help)
      sed -n '1,20p' "$0"
      exit 0
      ;;
    -*)
      echo "Unknown option: $a" >&2
      exit 2
      ;;
  esac
done

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "vps_git_worktree_clean: run from inside a git repository (cd /opt/mkm-lab-workspace-v2)" >&2
  exit 2
fi

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
echo "== repo root: $ROOT"

echo "== fetch $REMOTE_NAME"
GIT_TERMINAL_PROMPT=0 git fetch "$REMOTE_NAME" --prune

echo "== status (before)"
git status -sb

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "== dry-run: diff (tracked)"
  git diff --stat || true
  echo "== dry-run: no restore/pull changes applied"
  exit 0
fi

CURRENT="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT" != "$MAIN_REF" ]]; then
  echo "WARN: current branch is '$CURRENT', not $MAIN_REF — continuing anyway" >&2
fi

if [[ "$NO_PULL" -eq 0 ]]; then
  echo "== pull --ff-only $REMOTE_NAME/$MAIN_REF"
  GIT_TERMINAL_PROMPT=0 git pull --ff-only "$REMOTE_NAME" "$MAIN_REF" || {
    echo "pull failed — fix conflicts or network, then re-run" >&2
    exit 1
  }
fi

# 알려진 추적 파일 드리프트: SSOT는 원격
TRACKED_RESET=(
  "projects/bitcoin-trading/src/analysis/strategic_failure_event.py"
)
for f in "${TRACKED_RESET[@]}"; do
  if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
    if ! git diff --quiet -- "$f" 2>/dev/null; then
      echo "== git restore (tracked drift): $f"
      git restore -- "$f"
    fi
  fi
done

BTC_ENV="projects/bitcoin-trading/.env.example"
if [[ -f "$BTC_ENV" ]]; then
  if git ls-files --error-unmatch "$BTC_ENV" >/dev/null 2>&1; then
    if ! git diff --quiet -- "$BTC_ENV" 2>/dev/null; then
      echo "== git restore (tracked drift): $BTC_ENV"
      git restore -- "$BTC_ENV"
    fi
  else
    echo "== untracked: $BTC_ENV (not in origin/main — often duplicate of repo root .env.example)"
    if [[ "$REMOVE_UNTRACKED_BTC_ENV" -eq 1 ]]; then
      rm -f -- "$BTC_ENV"
      echo "   removed."
    else
      echo "   to remove: $0 --remove-untracked-btc-env-example"
    fi
  fi
fi

echo "== status (after)"
git status -sb

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "WARN: remaining local changes — review: git diff" >&2
else
  echo "OK: working tree clean (or only untracked left as shown)."
fi
