#!/usr/bin/env bash
set -euo pipefail

# Exit 0 if all paths in DEPLOY_GIT_POINTER_V1.json exist under repo root; else 1 + stderr hints.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
POINTER="$BT_ROOT/ops/v2/DEPLOY_GIT_POINTER_V1.json"

if [[ ! -f "$POINTER" ]]; then
  echo "[ERROR] missing pointer: $POINTER" >&2
  exit 2
fi

echo "[INFO] bitcoin-trading root: $BT_ROOT"
echo "[INFO] pointer: $POINTER"

MISSING=0
while IFS= read -r rel; do
  [[ -z "$rel" ]] && continue
  p="$BT_ROOT/$rel"
  if [[ -f "$p" ]]; then
    echo "[OK] $rel"
  else
    echo "[MISSING] $rel  (expected after correct git pull / branch)" >&2
    MISSING=1
  fi
done < <(python3 <<PY
import json
with open("$POINTER", encoding="utf-8") as f:
    d = json.load(f)
for rel in d.get("deploy_alignment", {}).get("verify_paths_after_pull", []) or []:
    print(rel)
PY
)

if [[ "$MISSING" -ne 0 ]]; then
  echo "" >&2
  echo "Hint: align VPS branch with DEPLOY_GIT_POINTER_V1.json deploy_alignment," >&2
  echo "      or push your commits to that remote/branch (GitHub is optional exception)." >&2
  exit 1
fi

echo "[OK] all verify_paths present"
