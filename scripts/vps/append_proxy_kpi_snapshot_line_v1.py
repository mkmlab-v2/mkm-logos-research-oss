#!/usr/bin/env python3
"""VPS 전용: PM2/앱 로그 등 '프록시 로그' 한 파일의 줄 수로 watchdog.log_lines만 채워 KPI JSONL 한 줄 append.

collect_kpi_snapshot.py 전체(Windows schtasks·상태 JSON) 없이도 export_latest_kpi_snapshot_to_metabolism_jsonl.py 가
glob으로 잡을 kpi_snapshot_YYYYMMDD.jsonl 을 만들 수 있게 한다.

주의: 위험·전략 KPI가 아니라 **대사량 프록시(로그 줄 수)** 용이다. 본선 리스크 판단에 단독 사용 금지.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[2]


def _count_lines(path: Path) -> int:
    n = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            n += chunk.count(b"\n")
    if path.stat().st_size > 0:
        with path.open("rb") as fo:
            fo.seek(-1, 2)
            if fo.read(1) != b"\n":
                n += 1
    return n


def _empty_logos_timeline() -> dict:
    return {
        "anchor_exists": False,
        "anchor_schema": None,
        "anchor_count": 0,
        "calibration_exists": False,
        "calibration_schema": None,
        "calibration_sample_count": 0,
        "calibration_nonzero_pnl_samples": 0,
        "calibration_proxy_pnl_samples": 0,
        "calibration_effective_nonzero_samples": 0,
        "calibration_sample_count_by_tradition": {},
        "calibration_base_by_tradition": {},
        "calibration_diagnostics": None,
    }


def _dual_regime_none() -> dict:
    return {
        "state_id": None,
        "state_id_source": "none",
        "state_id_present": False,
        "signal_registry_clamped": False,
        "signal_registry_cap": None,
        "source_count": {"none": 1},
        "clamp_count": 0,
        "sample_count": 1,
    }


def _mkm_core_empty() -> dict:
    return {
        "total_signals": 0,
        "buy_count": 0,
        "sell_count": 0,
        "locked_count": 0,
        "locked_ratio": None,
        "buy_ratio": None,
        "sell_ratio": None,
        "last_signal_summary": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", type=Path, default=None)
    ap.add_argument(
        "--proxy-log",
        type=Path,
        default=None,
        help="줄 수를 셀 로그 파일 (또는 환경변수 MKM_KPI_PROXY_LOG)",
    )
    ap.add_argument("--stale-restart", type=int, default=0)
    ap.add_argument("--kill-switch-events", type=int, default=0)
    ap.add_argument("--daemon-healthy", type=int, default=0)
    ap.add_argument("--daemon-started", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true", help="파일에 쓰지 않고 한 줄 JSON만 stdout")
    args = ap.parse_args()

    root = _repo_root(args.repo_root)
    proxy = args.proxy_log
    if proxy is None:
        p = (os.environ.get("MKM_KPI_PROXY_LOG") or "").strip()
        proxy = Path(p) if p else None
    else:
        proxy = Path(proxy)
        if not proxy.is_absolute():
            proxy = (root / proxy).resolve()

    if not proxy or not proxy.is_file():
        print(
            "FAIL: --proxy-log 또는 MKM_KPI_PROXY_LOG 에 유효한 파일 경로가 필요합니다.",
            file=sys.stderr,
        )
        return 2

    log_lines = _count_lines(proxy)
    now = datetime.now(timezone.utc)
    snapshot = {
        "ts_utc": now.isoformat(),
        "scheduler_ready": False,
        "kill_switch_on": False,
        "heartbeat_age_min": None,
        "status_running": None,
        "status_restart_count": None,
        "status_error_count": None,
        "status_symbol": None,
        "status_testnet": None,
        "status_enable_trading": None,
        "exchange_snapshot_24h_available": None,
        "exchange_snapshot_24h_fills_count": None,
        "exchange_snapshot_24h_realized_pnl": None,
        "exchange_snapshot_24h_commission": None,
        "exchange_snapshot_24h_funding_fee": None,
        "exchange_snapshot_24h_net": None,
        "risk_profile_pipeline": {
            "status": "absent",
            "source": "vps_proxy_append_v1",
            "mode": "proxy_log_lines_only",
            "is_n8n_source": False,
            "freshness": {
                "has_generated_at": True,
                "is_fresh": True,
                "age_minutes": 0.0,
                "max_age_minutes": 60,
            },
        },
        "mkm_singular_core": _mkm_core_empty(),
        "logos_timeline": _empty_logos_timeline(),
        "watchdog": {
            "log_lines": log_lines,
            "daemon_healthy": max(0, int(args.daemon_healthy)),
            "daemon_started": max(0, int(args.daemon_started)),
            "stale_restart": max(0, int(args.stale_restart)),
            "kill_switch_events": max(0, int(args.kill_switch_events)),
        },
        "dual_regime_state_kpi": _dual_regime_none(),
        "proxy_source_log": str(proxy).replace("\\", "/"),
    }

    line = json.dumps(snapshot, ensure_ascii=False) + "\n"
    if args.dry_run:
        sys.stdout.write(line)
        return 0

    kpi_dir = root / "projects" / "bitcoin-trading" / "memory" / "kpi"
    kpi_dir.mkdir(parents=True, exist_ok=True)
    day = now.strftime("%Y%m%d")
    jsonl_path = kpi_dir / f"kpi_snapshot_{day}.jsonl"
    latest_path = kpi_dir / "latest_kpi.json"
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(line)
    latest_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK: append 1 line -> {jsonl_path} proxy_log={proxy} log_lines={log_lines}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
