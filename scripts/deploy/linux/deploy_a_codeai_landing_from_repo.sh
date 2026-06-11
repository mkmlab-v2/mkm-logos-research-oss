#!/usr/bin/env bash
# Deploy A-CODEAI static landing pages from repo templates.
#
# Usage (on VPS with repo checked out):
#   bash scripts/deploy/linux/deploy_a_codeai_landing_from_repo.sh
# Optional:
#   WEB_ROOT="/var/www/a-codeai.com" bash scripts/deploy/linux/deploy_a_codeai_landing_from_repo.sh
#   SKIP_ROUTE_CHECK=1 bash scripts/deploy/linux/deploy_a_codeai_landing_from_repo.sh
#   RELOAD_NGINX=1 bash scripts/deploy/linux/deploy_a_codeai_landing_from_repo.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TEMPLATE_DIR="$REPO_ROOT/scripts/deploy/nginx"
WEB_ROOT="${WEB_ROOT:-/var/www/a-codeai-next-preview}"
SKIP_ROUTE_CHECK="${SKIP_ROUTE_CHECK:-0}"
RELOAD_NGINX="${RELOAD_NGINX:-0}"

need_file() {
  local p="$1"
  [[ -f "$p" ]] || { echo "[FAIL] missing file: $p" >&2; exit 1; }
}

echo "== deploy a-codeai landing pages =="
echo "REPO_ROOT=$REPO_ROOT"
echo "WEB_ROOT=$WEB_ROOT"

need_file "$TEMPLATE_DIR/a-codeai.com.index.en.html.example"
need_file "$TEMPLATE_DIR/a-codeai.com.pilot.en.html.example"
need_file "$TEMPLATE_DIR/a-codeai.com.benchmark.en.html.example"
need_file "$TEMPLATE_DIR/a-codeai.com.index.html.example"
need_file "$TEMPLATE_DIR/a-codeai.com.pilot.html.example"
need_file "$TEMPLATE_DIR/a-codeai.com.benchmark.html.example"
need_file "$REPO_ROOT/docs/final/artifacts/a_codeai_public_copy_web_payload_latest.json"
need_file "$REPO_ROOT/docs/final/artifacts/a_codeai_public_bench_landing_payload_v1_latest.json"

sudo mkdir -p "$WEB_ROOT/pilot" "$WEB_ROOT/benchmark" "$WEB_ROOT/ko/pilot" "$WEB_ROOT/ko/benchmark"

# EN routes
sudo cp "$TEMPLATE_DIR/a-codeai.com.index.en.html.example" "$WEB_ROOT/index.html"
sudo cp "$TEMPLATE_DIR/a-codeai.com.pilot.en.html.example" "$WEB_ROOT/pilot/index.html"
sudo cp "$TEMPLATE_DIR/a-codeai.com.benchmark.en.html.example" "$WEB_ROOT/benchmark/index.html"

# KO routes
sudo cp "$TEMPLATE_DIR/a-codeai.com.index.html.example" "$WEB_ROOT/ko/index.html"
sudo cp "$TEMPLATE_DIR/a-codeai.com.pilot.html.example" "$WEB_ROOT/ko/pilot/index.html"
sudo cp "$TEMPLATE_DIR/a-codeai.com.benchmark.html.example" "$WEB_ROOT/ko/benchmark/index.html"

# Shared dynamic payload for runtime copy binding
sudo cp "$REPO_ROOT/docs/final/artifacts/a_codeai_public_copy_web_payload_latest.json" "$WEB_ROOT/a_codeai_public_copy_web_payload_latest.json"
sudo cp "$REPO_ROOT/docs/final/artifacts/a_codeai_public_bench_landing_payload_v1_latest.json" "$WEB_ROOT/a_codeai_public_bench_landing_payload_v1_latest.json"

sudo chown -R www-data:www-data "$WEB_ROOT"
sudo find "$WEB_ROOT" -type d -exec chmod 755 {} \;
sudo find "$WEB_ROOT" -type f -exec chmod 644 {} \;

if [[ "$RELOAD_NGINX" == "1" ]]; then
  sudo nginx -t
  sudo systemctl reload nginx
fi

if [[ "$SKIP_ROUTE_CHECK" != "1" ]]; then
  bash "$REPO_ROOT/scripts/deploy/linux/check_a_codeai_public_routes.sh"
fi

echo "[OK] a-codeai landing deploy completed."
