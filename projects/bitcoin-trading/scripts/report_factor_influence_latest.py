#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.65, L:0.9, K:0.75, M:0.85}
# Balance: 93
# Purpose: Report factor influence JSON + alert state for SSH cron (pm2 logs).
# Keywords: bitcoin-trading, factor-influence, alerts, ssh, cron

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from factor_influence_lib import compute_snapshot, write_json


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Factor influence report + alert state for cron.")
    p.add_argument(
        "--log-file",
        type=Path,
        default=Path("/root/.pm2/logs/bitcoin-live-error.log"),
        help="PM2 log for factor diagnostics (bitcoin-live-error.log tags; use -out.log if needed).",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "exports" / "cursor_trade_history",
        help="Output directory for JSON artifacts.",
    )
    p.add_argument("--recent-lines", type=int, default=1200)
    p.add_argument("--window-hours", type=int, default=24)
    p.add_argument(
        "--alert-state-file",
        type=Path,
        default=None,
        help="Defaults to <out-dir>/factor_influence_alert_state.json",
    )
    p.add_argument(
        "--thr-vector",
        type=float,
        default=float(os.environ.get("FACTOR_INFLUENCE_CRIT_VECTOR", "0.5")),
    )
    p.add_argument(
        "--thr-engine",
        type=float,
        default=float(os.environ.get("FACTOR_INFLUENCE_CRIT_ENGINE", "0.5")),
    )
    p.add_argument(
        "--escalate-after",
        type=int,
        default=int(os.environ.get("FACTOR_INFLUENCE_ESCALATE_AFTER", "2")),
        help="Consecutive CRITICAL runs before action_required / de-suppress repeat alerts.",
    )
    p.add_argument(
        "--emit-legacy-files",
        action="store_true",
        help="Also write factor_influence_recent_lines.json and factor_influence_24h.json slices.",
    )
    return p.parse_args()


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def _critical_pair(vm: float, ef: float, thr_v: float, thr_e: float) -> bool:
    return vm >= thr_v and ef >= thr_e


def _build_alert_state(
    prev: dict[str, Any] | None,
    exported_at: str,
    vm_rate: float,
    ef_rate: float,
    td_rate: float,
    vm_rate_display: float,
    ef_rate_display: float,
    thr_v: float,
    thr_e: float,
    escalate_after: int,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    prev_consecutive = int((prev or {}).get("consecutive_critical_count") or 0)
    prev_id = (prev or {}).get("last_alert_id")
    prev_sent = (prev or {}).get("last_alert_sent_at")

    critical = _critical_pair(vm_rate, ef_rate, thr_v, thr_e)
    if critical:
        consecutive = prev_consecutive + 1
    else:
        consecutive = 0

    if consecutive >= escalate_after:
        severity = "critical_action_required"
        alert_id = "multi_factor_critical_escalated"
    elif critical:
        severity = "critical"
        alert_id = "multi_factor_critical"
    elif vm_rate >= thr_v * 0.8 or ef_rate >= thr_e * 0.8:
        severity = "warning"
        alert_id = "multi_factor_warning"
    else:
        severity = "ok"
        alert_id = "nominal"

    repeat_suppressed = bool(critical and consecutive < escalate_after)

    transition = alert_id != prev_id
    escalation_edge = critical and consecutive == escalate_after
    bump_sent = transition or escalation_edge

    last_alert_sent_at = prev_sent
    if bump_sent:
        last_alert_sent_at = exported_at if "T" in exported_at else now_iso

    return {
        "schema": "factor_influence_alert_state_v1",
        "updated_at_utc": now_iso,
        "thresholds": {
            "vector_missing_rate_ge": thr_v,
            "engine_fallback_ma_rate_ge": thr_e,
            "escalate_after_consecutive_critical": escalate_after,
        },
        "current": {
            "trade_done_rate": td_rate,
            "vector_missing_rate": vm_rate_display,
            "engine_fallback_ma_rate": ef_rate_display,
            "vector_missing_rate_uncapped": vm_rate,
            "engine_fallback_ma_rate_uncapped": ef_rate,
        },
        "severity": severity,
        "consecutive_critical_count": consecutive,
        "last_alert_id": alert_id,
        "last_alert_sent_at": last_alert_sent_at,
        "repeat_alert_suppressed": repeat_suppressed,
        "notes": (
            "repeat_alert_suppressed=true means CRITICAL pair holds but escalation count "
            f"below {escalate_after}; webhook consumers should avoid spam."
        ),
    }


def main() -> int:
    args = _parse_args()
    out_dir = args.out_dir
    alert_path = args.alert_state_file or (out_dir / "factor_influence_alert_state.json")

    try:
        payload, _, _, recent_counts, hour_counts = compute_snapshot(
            args.log_file,
            recent_lines=args.recent_lines,
            window_hours=args.window_hours,
        )
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}")
        return 2

    td_rate = float(payload["trade_done_rate"])
    vm_rate = float(payload["vector_missing_rate_uncapped"])
    ef_rate = float(payload["engine_fallback_ma_rate_uncapped"])
    exported_at = str(payload["exported_at"])

    prev = _load_json(alert_path)
    alert_state = _build_alert_state(
        prev,
        exported_at=exported_at,
        vm_rate=vm_rate,
        ef_rate=ef_rate,
        td_rate=td_rate,
        vm_rate_display=float(payload["vector_missing_rate"]),
        ef_rate_display=float(payload["engine_fallback_ma_rate"]),
        thr_v=args.thr_vector,
        thr_e=args.thr_engine,
        escalate_after=max(1, args.escalate_after),
    )

    write_json(out_dir / "factor_influence_latest.json", payload)
    write_json(alert_path, alert_state)

    if args.emit_legacy_files:
        now_utc = datetime.now(timezone.utc)
        write_json(
            out_dir / "factor_influence_recent_lines.json",
            {
                "schema": "factor_influence_recent_lines_v1",
                "generated_at_utc": now_utc.isoformat(),
                "recent_lines": args.recent_lines,
                "counts": recent_counts,
                "metrics": payload["recent_lines"]["metrics"],
            },
        )
        write_json(
            out_dir / "factor_influence_24h.json",
            {
                "schema": "factor_influence_24h_v1",
                "generated_at_utc": now_utc.isoformat(),
                "window_hours": args.window_hours,
                "counts": hour_counts,
                "metrics": payload["window_24h"]["metrics"],
            },
        )

    print("[OK] factor_influence_latest.json + alert state written")
    print(f"severity={alert_state['severity']} alert_id={alert_state['last_alert_id']} "
          f"consecutive={alert_state['consecutive_critical_count']} suppressed={alert_state['repeat_alert_suppressed']}")
    print(f"rates: trade_done={td_rate:.3f} vector_missing={vm_rate:.3f} engine_fallback_ma={ef_rate:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
