#!/usr/bin/env bash
# MKM monorepo — create host-side env file from repo template (Linux VPS).
# Run ON the VPS after git pull, from repo root: bash scripts/deploy/linux/bootstrap_mkm_monorepo_host_env_v1.sh
# Does not print secrets. Idempotent: skips if target already exists.

set -euo pipefail

TARGET="${MKM_VPS_ENV_FILE:-/etc/mkm/mkm-monorepo.env}"
TEMPLATE_REL="scripts/deploy/linux/mkm-monorepo-vps.env.example"

die() { echo "ERROR: $*" >&2; exit 1; }

if [[ ! -f "$TEMPLATE_REL" ]]; then
  die "Run from monorepo root (missing $TEMPLATE_REL). pwd=$(pwd)"
fi

if [[ -f "$TARGET" ]]; then
  echo "[ok] Host env already exists: $TARGET (leave unchanged)"
  exit 0
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Need root once to create $TARGET. Re-run with:"
  echo "  sudo MKM_VPS_ENV_FILE=$TARGET bash scripts/deploy/linux/bootstrap_mkm_monorepo_host_env_v1.sh"
  exit 2
fi

install -d -m 0755 /etc/mkm
install -m 0600 -o root -g root "$TEMPLATE_REL" "$TARGET"
echo "[ok] Installed template -> $TARGET (mode 0600). Edit values, then wire systemd/PM2 EnvironmentFile= per runbook."
echo "SSOT: docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md (비밀 키 절)"
