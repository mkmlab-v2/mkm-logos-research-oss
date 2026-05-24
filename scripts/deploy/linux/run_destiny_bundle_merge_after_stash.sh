#!/usr/bin/env bash
set -euo pipefail
cd /opt/mkm-destiny-ai-41e38ec6
git stash push -u -m "pre-bundle-sync-$(date -u +%Y%m%dT%H%MZ)" || true
git merge refs/remotes/bundle/vpssync-tip -m "sync: bundle from local workstation (approved)" --no-edit
git rev-parse --short HEAD
test -f projects/bitcoin-trading/src/api/binance_client.py && echo "binance_client_ok"
