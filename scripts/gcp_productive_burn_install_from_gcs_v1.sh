#!/bin/bash
# Install productive burn pkg from GCS (run on Cloud Shell as project member).
set -euo pipefail
PKG_URI="gs://gen-lang-client-burn-wave2/productive_burn_shell_pkg_v1.tar.gz"
TMP="/tmp/pb_pkg.tar.gz"
echo "=== install from GCS $(date -u -Iseconds) ==="
gcloud storage cp "$PKG_URI" "$TMP"
tar xzf "$TMP" -C "${HOME}"
sed -i 's/\r$//' "${HOME}"/gcp_productive_burn_*.sh "${HOME}"/gcp_productive_burn_lane_runner_v1.py 2>/dev/null || true
chmod +x "${HOME}"/gcp_productive_burn_*.sh
ls -la "${HOME}"/gcp_productive_burn_lane_runner_v1.py "${HOME}"/fills_daily_compact_v1.json
echo "=== install ok — run: bash ~/gcp_productive_burn_bootstrap.sh ==="
