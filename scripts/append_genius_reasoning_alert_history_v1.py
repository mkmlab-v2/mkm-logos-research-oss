#!/usr/bin/env python3
"""Append genius benchmark alert snapshot to monthly history log."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_ALERT = ART / "genius_reasoning_benchmark_alert_latest.json"
DEFAULT_BENCH = ART / "genius_reasoning_benchmark_report_latest.json"
DEFAULT_HISTORY = ART / "genius_reasoning_benchmark_alert_history_log.jsonl"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alert-json", type=Path, default=DEFAULT_ALERT)
    ap.add_argument("--benchmark-json", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    args = ap.parse_args()

    alert = _read_json(args.alert_json)
    bench = _read_json(args.benchmark_json)
    robustness = bench.get("robustness") if isinstance(bench.get("robustness"), dict) else {}
    summary = bench.get("summary") if isinstance(bench.get("summary"), dict) else {}
    a = alert.get("alert") if isinstance(alert.get("alert"), dict) else {}

    row = {
        "schema": "genius_reasoning_alert_history_row_v1",
        "ts_utc": _iso_now(),
        "alert_severity": a.get("severity"),
        "alert_active": a.get("active"),
        "alert_reasons": a.get("reasons"),
        "benchmark_status": summary.get("benchmark_status"),
        "robust_benchmark_status": robustness.get("robust_benchmark_status"),
        "robust_score_100": robustness.get("robust_score_100"),
        "human_coverage": robustness.get("human_coverage"),
        "freshness_gate_pass": robustness.get("freshness_gate_pass"),
        "stale_approved_count": robustness.get("stale_approved_count"),
        "calibration_gap": robustness.get("calibration_gap"),
    }
    args.history_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.history_jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "history_jsonl": str(args.history_jsonl).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
