#!/usr/bin/env bash
# Verify a-codeai public routing: static home + API health/compress.
# Usage:
#   bash scripts/deploy/linux/check_a_codeai_public_routes.sh
#   BASE_URL="https://a-codeai.com" bash scripts/deploy/linux/check_a_codeai_public_routes.sh
#   API_KEY="..." bash scripts/deploy/linux/check_a_codeai_public_routes.sh
set -euo pipefail

BASE_URL="${BASE_URL:-https://a-codeai.com}"
API_KEY="${API_KEY:-}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

pass() { echo "[PASS] $*"; }
fail() { echo "[FAIL] $*" >&2; exit 1; }

request() {
  local method="$1"
  local path="$2"
  local out="$3"
  local code_file="$4"
  shift 4
  curl -sS -X "$method" "$BASE_URL$path" -o "$out" -w "%{http_code}" "$@" >"$code_file"
}

echo "== a-codeai route check =="
echo "BASE_URL=$BASE_URL"

# 1) Home should be HTML 200
HOME_BODY="$TMP_DIR/home.body"
HOME_CODE="$TMP_DIR/home.code"
request GET "/" "$HOME_BODY" "$HOME_CODE"
code="$(cat "$HOME_CODE")"
[[ "$code" == "200" ]] || fail "GET / expected 200, got $code"
if rg -n "<html|<!doctype html" "$HOME_BODY" >/dev/null 2>&1; then
  pass "GET / returns HTML (200)"
else
  fail "GET / is 200 but HTML signature not found"
fi

# 2) Health should be JSON and status ok
HEALTH_BODY="$TMP_DIR/health.body"
HEALTH_CODE="$TMP_DIR/health.code"
request GET "/health" "$HEALTH_BODY" "$HEALTH_CODE"
code="$(cat "$HEALTH_CODE")"
[[ "$code" == "200" ]] || fail "GET /health expected 200, got $code"
if rg -n "\"status\"\\s*:\\s*\"ok\"" "$HEALTH_BODY" >/dev/null 2>&1; then
  pass "GET /health returns status ok (200)"
else
  fail "GET /health missing status=ok JSON"
fi

# 3) GET /v1/compress should be 405 (POST-only)
COMPRESS_GET_BODY="$TMP_DIR/compress_get.body"
COMPRESS_GET_CODE="$TMP_DIR/compress_get.code"
request GET "/v1/compress" "$COMPRESS_GET_BODY" "$COMPRESS_GET_CODE"
code="$(cat "$COMPRESS_GET_CODE")"
[[ "$code" == "405" ]] || fail "GET /v1/compress expected 405, got $code"
pass "GET /v1/compress correctly returns 405"

# 4) POST /v1/compress should be 200 with API contract payload
COMPRESS_POST_BODY="$TMP_DIR/compress_post.body"
COMPRESS_POST_CODE="$TMP_DIR/compress_post.code"
headers=(
  -H "Content-Type: application/json"
)
if [[ -n "$API_KEY" ]]; then
  headers+=(-H "X-API-Key: $API_KEY")
fi
request POST "/v1/compress" "$COMPRESS_POST_BODY" "$COMPRESS_POST_CODE" \
  "${headers[@]}" \
  --data '{"text":"a-codeai route check sample", "eval_context":{"hydrate_metrics":false}}'
code="$(cat "$COMPRESS_POST_CODE")"
[[ "$code" == "200" ]] || fail "POST /v1/compress expected 200, got $code"
if rg -n "\"api_contract_version\"|\"schema_version\"|\"integrity_flags\"" "$COMPRESS_POST_BODY" >/dev/null 2>&1; then
  pass "POST /v1/compress returns API contract fields (200)"
else
  fail "POST /v1/compress missing expected response fields"
fi

echo "[OK] a-codeai static+API route split looks healthy."
