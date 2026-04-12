#!/usr/bin/env bash
# VPS/cron: 모노레포 루트에서 최신 KPI JSONL → LOG_METABOLISM JSONL.
# 사용: chmod +x scripts/vps/run_export_metabolism_from_kpi.sh
#
# KPI JSONL이 아직 없으면 먼저 한 줄 생성(프록시 로그 줄 수만):
#   export MKM_KPI_PROXY_LOG=/path/to/pm2-bitcoin-live.log   # 예시
#   python3 scripts/vps/append_proxy_kpi_snapshot_line_v1.py
#
# crontab 예 (UTC 매시 5분, 로그는 ~/log):
#   5 * * * * cd /path/to/workspace && /usr/bin/python3 scripts/vps/export_latest_kpi_snapshot_to_metabolism_jsonl.py >>~/log/metabolism_export.log 2>&1
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
exec python3 scripts/vps/export_latest_kpi_snapshot_to_metabolism_jsonl.py "$@"
