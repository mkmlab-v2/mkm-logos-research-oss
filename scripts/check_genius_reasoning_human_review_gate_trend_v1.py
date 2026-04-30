#!/usr/bin/env python3
"""Trend gate for genius human review gate history."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_HISTORY = ART / "genius_reasoning_human_review_gate_history_log.jsonl"
DEFAULT_OUT = ART / "genius_reasoning_human_review_gate_trend_latest.json"


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
    ap.add_argument("--window", type=int, default=6)
    ap.add_argument("--max-hold-count", type=int, default=1)
    ap.add_argument("--max-pending-ratio-avg", type=float, default=0.10)
    args = ap.parse_args()

    rows = _read_jsonl(args.history_jsonl)
    hist = rows[-max(1, int(args.window)) :]
    hold_count = 0
    ratio_sum = 0.0
    for row in hist:
        if str(row.get("status") or "") != "PASS":
            hold_count += 1
        try:
            ratio_sum += float(row.get("pending_ratio") or 0.0)
        except (TypeError, ValueError):
            pass
    n = len(hist)
    avg_ratio = ratio_sum / float(n) if n > 0 else 0.0

    reasons: list[str] = []
    status = "PASS"
    if hold_count > int(args.max_hold_count):
        status = "HOLD"
        reasons.append("hold_count_exceeded")
    if avg_ratio > float(args.max_pending_ratio_avg):
        status = "HOLD"
        reasons.append("avg_pending_ratio_exceeded")

    out = {
        "schema": "genius_reasoning_human_review_gate_trend_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {"history_jsonl": str(args.history_jsonl).replace("\\", "/")},
        "thresholds": {
            "window": int(args.window),
            "max_hold_count": int(args.max_hold_count),
            "max_pending_ratio_avg": float(args.max_pending_ratio_avg),
        },
        "current": {
            "window_rows": n,
            "hold_count": hold_count,
            "avg_pending_ratio": round(avg_ratio, 4),
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
