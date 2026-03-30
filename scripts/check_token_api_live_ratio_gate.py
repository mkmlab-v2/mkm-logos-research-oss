#!/usr/bin/env python3
"""Gate token API live_ratio with warning/block modes."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TREND = ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_hydration_trend_latest.json"
LOG = ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_hydration_mix_log.jsonl"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_live_ratio_gate_latest.json"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Check token API live_ratio gate status.")
    p.add_argument("--mode", choices=("warning", "block"), default="warning")
    p.add_argument("--target-live-ratio", type=float, default=0.70)
    p.add_argument("--arming-floor-ratio", type=float, default=0.60)
    p.add_argument("--arming-success-rate", type=float, default=0.80)
    p.add_argument("--arming-window-rows", type=int, default=10)
    return p


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            rows.append(json.loads(s.lstrip("\ufeff")))
    return rows


def main() -> int:
    args = _parser().parse_args()
    trend = _load_json(TREND)
    rows = _load_jsonl(LOG)
    recent = rows[-args.arming_window_rows :] if args.arming_window_rows > 0 else rows

    latest = float(trend.get("latest_live_ratio", 0.0))
    above_floor = sum(1 for r in recent if float(r.get("live_ratio", 0.0)) >= args.arming_floor_ratio)
    success_rate = (above_floor / len(recent)) if recent else 0.0
    armed = len(recent) >= args.arming_window_rows and success_rate >= args.arming_success_rate

    status = "pass"
    should_fail = False
    if args.mode == "warning":
        if latest < args.target_live_ratio:
            status = "warn_below_target"
    else:  # block
        if not armed:
            status = "blocking_not_armed"
        elif latest < args.target_live_ratio:
            status = "fail_below_target"
            should_fail = True

    report = {
        "schema": "token_api_live_ratio_gate_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "status": status,
        "target_live_ratio": args.target_live_ratio,
        "latest_live_ratio": latest,
        "arming": {
            "armed": armed,
            "floor_ratio": args.arming_floor_ratio,
            "success_rate_required": args.arming_success_rate,
            "window_rows_required": args.arming_window_rows,
            "window_rows_observed": len(recent),
            "window_success_rate_observed": success_rate,
        },
        "source_trend": "reports/constitution/btrack_pilot/token_api_hydration_trend_latest.json",
        "source_log": "reports/constitution/btrack_pilot/token_api_hydration_mix_log.jsonl",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(f"GATE_STATUS: {status}")
    return 1 if should_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
