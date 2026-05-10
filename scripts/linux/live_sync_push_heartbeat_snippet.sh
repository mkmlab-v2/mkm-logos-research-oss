#!/usr/bin/env bash
# MVP: VPS cron에서 분 단위로 호출 → JSON 한 줄 경로로 저장 후 로컬로 scp/rsync (별도 설정).
# 비밀·키는 커밋하지 말 것.
set -euo pipefail
OUT_JSON="${1:-/tmp/daemon_alive_check.json}"
HOST_TAG="${MKM_VPS_HOST:-$(hostname -f 2>/dev/null || hostname)}"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
cat >"$OUT_JSON" <<EOF
{"schema":"live_sync_heartbeat_v1","generated_at_utc":"$TS","source_host":"$HOST_TAG","role":"manual_snippet","notes":"scp this file to workspace live_sync/incoming/daemon_alive_check.json"}
EOF
echo "Wrote $OUT_JSON"

# Cron example (every 5 minutes, paths must exist):
# */5 * * * * root /opt/mkm-tools/live_sync_push_heartbeat_snippet.sh /tmp/daemon_alive_check.json
