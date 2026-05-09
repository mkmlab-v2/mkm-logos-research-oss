#!/usr/bin/env python3
"""Evaluate weekly chronicle-history-news signal history (B-track)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return rows


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_history = root / "docs" / "final" / "artifacts" / "chronicle_history_news_signal_history_latest.jsonl"
    default_out = root / "docs" / "final" / "artifacts" / "chronicle_history_news_signal_weekly_eval_latest.json"

    ap = argparse.ArgumentParser(description="Evaluate weekly chronicle-history-news signal history.")
    ap.add_argument("--history-jsonl", default=str(default_history))
    ap.add_argument("--output-json", default=str(default_out))
    ap.add_argument("--lookback-days", type=int, default=7)
    args = ap.parse_args()

    now = _now_utc()
    cutoff = now - timedelta(days=args.lookback_days)
    rows = _load_jsonl(Path(args.history_jsonl))
    window = []
    for r in rows:
        ts = r.get("generated_at_utc")
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt >= cutoff:
            window.append(r)

    if not window:
        report = {
            "schema": "chronicle_history_news_signal_weekly_eval_v1",
            "generated_at_utc": _iso(now),
            "lookback_days": args.lookback_days,
            "row_count": 0,
            "status": "insufficient_data",
            "note": "No rows in lookback window."
        }
        Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    comps = [float(r.get("composite_signal_score", 0.0)) for r in window]
    candidate_counts: dict[str, int] = {"HOLD": 0, "WATCH": 0, "REDUCE": 0}
    final_counts: dict[str, int] = {"HOLD": 0, "WATCH": 0, "REDUCE": 0}
    for r in window:
        c = str(r.get("candidate_decision", "HOLD"))
        f = str(r.get("final_decision", "HOLD"))
        if c in candidate_counts:
            candidate_counts[c] += 1
        if f in final_counts:
            final_counts[f] += 1

    avg_comp = sum(comps) / len(comps)
    min_comp = min(comps)
    max_comp = max(comps)

    report = {
        "schema": "chronicle_history_news_signal_weekly_eval_v1",
        "generated_at_utc": _iso(now),
        "lookback_days": args.lookback_days,
        "row_count": len(window),
        "avg_composite_signal_score": round(avg_comp, 6),
        "min_composite_signal_score": round(min_comp, 6),
        "max_composite_signal_score": round(max_comp, 6),
        "candidate_decision_counts": candidate_counts,
        "final_decision_counts": final_counts,
        "observation_only_guard_active": True,
        "status": "ok"
    }
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
