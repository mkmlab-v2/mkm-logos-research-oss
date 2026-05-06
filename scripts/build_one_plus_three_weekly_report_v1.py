#!/usr/bin/env python3
"""Build weekly summary report from 1+3 daily gate logs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports" / "one_plus_three_daily_gate_log.jsonl"
DEFAULT_OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "one_plus_three_weekly_report_latest.json"
DEFAULT_OUT_MD = ROOT / "docs" / "final" / "artifacts" / "one_plus_three_weekly_report_latest.md"


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _load_rows(path: Path, since_utc: datetime) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
            ts = _parse_ts(str(row.get("ts_utc", "")))
            if ts >= since_utc:
                rows.append(row)
        except Exception:
            continue
    return rows


def _build_report(rows: list[dict[str, Any]], days: int) -> dict[str, Any]:
    status_counts = Counter(str(r.get("status", "UNKNOWN")) for r in rows)
    severity_counts = Counter(str(r.get("severity", "unknown")) for r in rows)
    gate_counts = Counter(str(r.get("gate_level", "unknown")) for r in rows)
    total = len(rows)
    pass_count = status_counts.get("PASS", 0)
    hold_count = status_counts.get("HOLD", 0)
    pass_rate = (pass_count / total) if total else 0.0
    critical_rate = (severity_counts.get("critical", 0) / total) if total else 0.0

    if total == 0:
        decision = "NO_DATA"
    elif critical_rate > 0.0:
        decision = "HOLD_CRITICAL_PRESENT"
    elif hold_count > 0:
        decision = "HOLD_WARNING_OR_REVIEW"
    else:
        decision = "GO_STABLE"

    return {
        "schema": "one_plus_three_weekly_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "window_days": days,
        "sample_count": total,
        "pass_count": pass_count,
        "hold_count": hold_count,
        "pass_rate": round(pass_rate, 6),
        "critical_rate": round(critical_rate, 6),
        "status_counts": dict(status_counts),
        "severity_counts": dict(severity_counts),
        "gate_level_counts": dict(gate_counts),
        "decision": decision,
    }


def _build_md(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# One Plus Three Weekly Report",
            "",
            f"- generated_at_utc: `{report['generated_at_utc']}`",
            f"- window_days: `{report['window_days']}`",
            f"- sample_count: `{report['sample_count']}`",
            f"- pass_rate: `{report['pass_rate']}`",
            f"- critical_rate: `{report['critical_rate']}`",
            f"- decision: `{report['decision']}`",
            "",
            "## Counts",
            f"- status_counts: `{report['status_counts']}`",
            f"- severity_counts: `{report['severity_counts']}`",
            f"- gate_level_counts: `{report['gate_level_counts']}`",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build 1+3 weekly report from daily gate logs.")
    parser.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--window-days", type=int, default=7)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()

    since = datetime.now(timezone.utc) - timedelta(days=args.window_days)
    rows = _load_rows(args.log_jsonl, since)
    report = _build_report(rows, args.window_days)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_build_md(report), encoding="utf-8")

    print(f"[one+3-weekly] sample_count={report['sample_count']} decision={report['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
