#!/usr/bin/env bash
# VPS: 프록시 KPI 한 줄 append → metabolism JSONL export (한 번에).
#
# 필수: MKM_KPI_PROXY_LOG=/path/to/pm2-out.log (또는 append 스크립트가 읽을 단일 로그)
# 선택: append_proxy / export 스크립트에 넘길 추가 인자는 이 래퍼 뒤에 붙이면 export에만 전달됨
#
# Cron 예 (10분마다 append+export, 로그 append):
#   */10 * * * * cd /opt/mkm-lab-workspace-v2 && MKM_KPI_PROXY_LOG=/root/.pm2/logs/foo-out.log \
#     bash scripts/vps/run_proxy_append_then_export_v1.sh >>/var/log/mkm_metabolism_export.log 2>&1
#
# 로그 로테이트: 시스템 logrotate에 위 로그 파일 등록(압축·주간 truncate). 레포 밖 운영 설정.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
if [ -z "${MKM_KPI_PROXY_LOG:-}" ]; then
  echo "FAIL: set MKM_KPI_PROXY_LOG to a readable log file path" >&2
  exit 2
fi
python3 scripts/vps/append_proxy_kpi_snapshot_line_v1.py
exec python3 scripts/vps/export_latest_kpi_snapshot_to_metabolism_jsonl.py "$@"
