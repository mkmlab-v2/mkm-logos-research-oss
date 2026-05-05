#!/usr/bin/env python3
"""Check dispatch health gate from genius alert dispatch history."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_HISTORY = ART / "genius_reasoning_dispatch_health_history_log.jsonl"
DEFAULT_OUT = ART / "genius_reasoning_dispatch_health_gate_latest.json"


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


def _count_failures(rows: list[dict[str, Any]], prefix: str) -> tuple[int, int]:
    failed = 0
    unconfigured = 0
    for row in rows:
        should = bool(row.get(f"{prefix}_should_dispatch"))
        status = str(row.get(f"{prefix}_dispatch_status") or "")
        webhook_ok = bool(row.get(f"{prefix}_webhook_configured"))
        if not should:
            continue
        if status == "failed":
            failed += 1
        if not webhook_ok:
            unconfigured += 1
    return failed, unconfigured


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--window", type=int, default=12)
    ap.add_argument("--max-failed-count", type=int, default=0)
    ap.add_argument("--max-unconfigured-count", type=int, default=0)
    args = ap.parse_args()

    rows = _read_jsonl(args.history_jsonl)
    hist = rows[-max(1, int(args.window)) :]
    ba_failed, ba_unconfigured = _count_failures(hist, "benchmark_alert")
    hr_failed, hr_unconfigured = _count_failures(hist, "human_review_gate")
    ht_failed, ht_unconfigured = _count_failures(hist, "human_review_trend")
    failed_total = ba_failed + hr_failed + ht_failed
    unconfigured_total = ba_unconfigured + hr_unconfigured + ht_unconfigured

    reasons: list[str] = []
    status = "PASS"
    if failed_total > int(args.max_failed_count):
        status = "HOLD"
        reasons.append("dispatch_failed_count_exceeded")
    if unconfigured_total > int(args.max_unconfigured_count):
        status = "HOLD"
        reasons.append("dispatch_unconfigured_count_exceeded")

    out = {
        "schema": "genius_reasoning_dispatch_health_gate_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {"history_jsonl": str(args.history_jsonl).replace("\\", "/")},
        "thresholds": {
            "window": int(args.window),
            "max_failed_count": int(args.max_failed_count),
            "max_unconfigured_count": int(args.max_unconfigured_count),
        },
        "current": {
            "window_rows": len(hist),
            "failed_total": failed_total,
            "unconfigured_total": unconfigured_total,
            "benchmark_alert_failed": ba_failed,
            "human_review_gate_failed": hr_failed,
            "human_review_trend_failed": ht_failed,
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
