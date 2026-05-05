#!/usr/bin/env python3
"""Check genius alert trend gate from alert history log."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_HISTORY = ART / "genius_reasoning_benchmark_alert_history_log.jsonl"
DEFAULT_OUT = ART / "genius_reasoning_benchmark_alert_trend_gate_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--window", type=int, default=8)
    ap.add_argument("--max-warning-count", type=int, default=2)
    ap.add_argument("--max-critical-count", type=int, default=0)
    ap.add_argument("--max-active-ratio", type=float, default=0.40)
    args = ap.parse_args()

    rows = _read_jsonl(args.history_jsonl)
    window_rows = rows[-max(1, int(args.window)) :]
    warning_count = 0
    critical_count = 0
    active_count = 0
    for row in window_rows:
        sev = str(row.get("alert_severity") or "INFO").upper()
        active = bool(row.get("alert_active"))
        if active:
            active_count += 1
        if sev == "WARNING":
            warning_count += 1
        if sev == "CRITICAL":
            critical_count += 1
    n = len(window_rows)
    active_ratio = (float(active_count) / float(n)) if n > 0 else 0.0

    reasons: list[str] = []
    status = "PASS"
    if warning_count > int(args.max_warning_count):
        status = "HOLD"
        reasons.append("warning_count_exceeded")
    if critical_count > int(args.max_critical_count):
        status = "HOLD"
        reasons.append("critical_count_exceeded")
    if active_ratio > float(args.max_active_ratio):
        status = "HOLD"
        reasons.append("active_alert_ratio_exceeded")

    out = {
        "schema": "genius_reasoning_alert_trend_gate_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {"history_jsonl": str(args.history_jsonl).replace("\\", "/")},
        "thresholds": {
            "window": int(args.window),
            "max_warning_count": int(args.max_warning_count),
            "max_critical_count": int(args.max_critical_count),
            "max_active_ratio": float(args.max_active_ratio),
        },
        "current": {
            "window_rows": n,
            "warning_count": warning_count,
            "critical_count": critical_count,
            "active_count": active_count,
            "active_ratio": round(active_ratio, 4),
        },
        "status": status,
        "reasons": reasons,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "status": status, "output_json": str(args.output_json).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
