#!/usr/bin/env bash
# Run from Windows: cmd /c "ssh vps-mkmlife bash -s < C:\workspace\scripts\vps_mkm_lab_hygiene_reset_v1.sh"
# VPS lab monorepo: backup full tree, align to origin/main, remove untracked (no PM2).
set -euo pipefail

LAB="/opt/mkm-lab-workspace-v2"
if [[ ! -d "$LAB" ]]; then
  echo "ERROR: $LAB missing" >&2
  exit 2
fi
REAL="$(readlink -f "$LAB")"
echo "REAL=$REAL"

mkdir -p /var/backups/mkm-hygiene-20260512-lab
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BK="/var/backups/mkm-lab-wt-${STAMP}.tar.gz"
echo "BACKUP=$BK"
tar czf "$BK" -C "$REAL" .
ls -lh "$BK"

cd "$LAB"
git fetch origin -q
git reset --hard origin/main
git clean -fd

echo "--- git status ---"
git status -sb
git log -1 --oneline
