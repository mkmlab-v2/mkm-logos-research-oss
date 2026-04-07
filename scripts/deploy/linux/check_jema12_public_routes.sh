#!/usr/bin/env bash
# Verify jema12.com public routes (curl-based). CI-friendly.
# Usage:
#   bash scripts/deploy/linux/check_jema12_public_routes.sh
#   BASE_URL=https://www.jema12.com bash scripts/deploy/linux/check_jema12_public_routes.sh
set -euo pipefail

BASE_URL="${BASE_URL:-https://jema12.com}"
BASE_URL="${BASE_URL%/}"

code() {
  curl -sS -o /dev/null -w "%{http_code}" --max-time 25 "$1" || echo ERR
}

echo "== jema12 public route check =="
echo "BASE_URL=$BASE_URL"

fail=0
r="$(code "$BASE_URL/")"
if [[ "$r" == "200" ]]; then echo "[PASS] GET / -> $r"; else echo "[FAIL] GET / expected 200, got $r"; fail=1; fi

bc="$(code "$BASE_URL/broadcast")"
if [[ "$bc" =~ ^(301|302|200)$ ]]; then echo "[PASS] GET /broadcast -> $bc"; else
  echo "[WARN] GET /broadcast -> $bc (expect 302 after nginx handoff)"
  [[ "$bc" == "404" ]] && fail=1
fi

st="$(code "$BASE_URL/studio")"
if [[ "$st" =~ ^(301|302|200)$ ]]; then echo "[PASS] GET /studio -> $st"; else echo "[WARN] GET /studio -> $st"; fi

sts="$(code "$BASE_URL/studio/")"
if [[ "$sts" == "500" ]]; then echo "[FAIL] GET /studio/ -> 500"; fail=1
elif [[ "$sts" =~ ^(200|301|302|304|403)$ ]]; then echo "[PASS] GET /studio/ -> $sts"
else echo "[WARN] GET /studio/ -> $sts"
fi

exit "$fail"
