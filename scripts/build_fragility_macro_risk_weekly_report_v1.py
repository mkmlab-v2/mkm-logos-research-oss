#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.8, K:0.8, M:0.4}
# Balance: 90
# Purpose: Build 7-day summary report for fragility macro risk daily runs.
# Keywords: fragility, weekly report, run log, summary, governance

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_LOG = ROOT / "reports" / "fragility_macro_risk_daily_run_log.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "fragility_macro_risk_weekly_report_latest.json"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    txt = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(txt)
    except Exception:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except Exception:
            continue
        if isinstance(doc, dict):
            out.append(doc)
    return out


def _counter_to_dict(counter: Counter[str]) -> dict[str, int]:
    return {k: int(v) for k, v in sorted(counter.items(), key=lambda item: item[0])}


def build_weekly_report(rows: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    since = now - timedelta(days=7)
    recent: list[dict[str, Any]] = []
    for row in rows:
        ts = _parse_ts(row.get("ts_utc"))
        if ts is None:
            continue
        if ts >= since:
            r = dict(row)
            r["_ts"] = ts
            recent.append(r)
    recent.sort(key=lambda x: x["_ts"])

    status_counter = Counter(str(x.get("status", "unknown")) for x in recent)
    gate_counter = Counter(str(x.get("gate", "unknown")) for x in recent if x.get("gate") is not None)
    decision_counter = Counter(str(x.get("decision_state", "unknown")) for x in recent if x.get("decision_state") is not None)
    source_counter = Counter(str(x.get("source_mode", "unknown")) for x in recent if x.get("source_mode") is not None)
    quat_counter = Counter(str(x.get("quaternion_signal", "unknown")) for x in recent if x.get("quaternion_signal") is not None)

    total = len(recent)
    pass_count = status_counter.get("pass", 0)
    pass_rate = (pass_count / total) * 100.0 if total > 0 else 0.0
    latest = recent[-1] if recent else {}
    latest_ts = latest.get("ts_utc")

    return {
        "schema": "fragility_macro_risk_weekly_report_v1",
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "window_days": 7,
        "window_start_utc": since.isoformat().replace("+00:00", "Z"),
        "window_end_utc": now.isoformat().replace("+00:00", "Z"),
        "sample_count": total,
        "pass_count": pass_count,
        "pass_rate_percent": round(pass_rate, 4),
        "status_counts": _counter_to_dict(status_counter),
        "gate_counts": _counter_to_dict(gate_counter),
        "decision_state_counts": _counter_to_dict(decision_counter),
        "source_mode_counts": _counter_to_dict(source_counter),
        "quaternion_signal_counts": _counter_to_dict(quat_counter),
        "latest_snapshot": {
            "ts_utc": latest_ts,
            "status": latest.get("status"),
            "gate": latest.get("gate"),
            "decision_state": latest.get("decision_state"),
            "risk_warning_level": latest.get("risk_warning_level"),
            "quaternion_signal": latest.get("quaternion_signal"),
            "source_mode": latest.get("source_mode"),
        },
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build 7-day fragility macro risk summary report.")
    p.add_argument("--run-log", type=Path, default=DEFAULT_RUN_LOG)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    run_log = args.run_log if args.run_log.is_absolute() else (ROOT / args.run_log)
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)

    rows = _read_jsonl(run_log)
    report = build_weekly_report(rows, _utc_now())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"fragility_macro_risk_weekly_report_v1: PASS -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
