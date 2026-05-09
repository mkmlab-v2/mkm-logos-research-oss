#!/usr/bin/env python3
"""Evaluate auto-apply guardrail conditions and emit rollback signal."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_DAILY = ART / "lens_penalty_daily_latest.json"
DEFAULT_WEEKLY = ART / "lens_penalty_shadow_weekly_report_latest.json"
DEFAULT_HISTORY = REPORTS / "lens_penalty_auto_apply_guardrail_history.jsonl"
DEFAULT_OUT = ART / "lens_penalty_auto_apply_guardrail_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--daily-json", type=Path, default=DEFAULT_DAILY)
    ap.add_argument("--weekly-json", type=Path, default=DEFAULT_WEEKLY)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict-gap-alert-threshold", type=float, default=0.25)
    ap.add_argument("--penalty-count-alert-threshold", type=int, default=2)
    args = ap.parse_args()

    daily = _read_json(args.daily_json)
    weekly = _read_json(args.weekly_json)
    history = _read_jsonl(args.history_jsonl)
    prev = history[-1] if history else {}

    strict_gap = float((weekly.get("summary") or {}).get("strict_gap") or 0.0)
    penalty_count = int((daily.get("summary") or {}).get("recommendations_with_penalty") or 0)
    mode = str(daily.get("mode") or "")
    applied = bool(daily.get("applied"))

    prev_gap = float(prev.get("strict_gap") or 0.0) if prev else 0.0
    gap_worsening = strict_gap > prev_gap
    prev_worsening = bool(prev.get("gap_worsening")) if prev else False
    consecutive_worsening = gap_worsening and prev_worsening

    high_gap_penalty = strict_gap > float(args.strict_gap_alert_threshold) and penalty_count >= int(args.penalty_count_alert_threshold)
    should_rollback = (mode == "apply" and applied) and (consecutive_worsening or high_gap_penalty)

    reasons: list[str] = []
    if consecutive_worsening:
        reasons.append("strict_gap_worsening_2x")
    if high_gap_penalty:
        reasons.append("strict_gap_high_with_penalty")
    if not reasons:
        reasons.append("stable")

    out = {
        "schema": "lens_penalty_auto_apply_guardrail_v1",
        "generated_at_utc": _now(),
        "decision": "ROLLBACK_REQUIRED" if should_rollback else "KEEP_AUTO_APPLY",
        "should_rollback": should_rollback,
        "reasons": reasons,
        "snapshot": {
            "mode": mode,
            "applied": applied,
            "strict_gap": strict_gap,
            "prev_strict_gap": prev_gap,
            "gap_worsening": gap_worsening,
            "consecutive_worsening": consecutive_worsening,
            "penalty_count": penalty_count,
        },
        "thresholds": {
            "strict_gap_alert_threshold": float(args.strict_gap_alert_threshold),
            "penalty_count_alert_threshold": int(args.penalty_count_alert_threshold),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    history_row = {
        "schema": "lens_penalty_auto_apply_guardrail_history_row_v1",
        "timestamp_utc": _now(),
        "decision": out["decision"],
        "strict_gap": strict_gap,
        "gap_worsening": gap_worsening,
        "penalty_count": penalty_count,
    }
    args.history_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.history_jsonl.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(history_row, ensure_ascii=False) + "\n")

    print(f"WROTE: {args.out}")
    print(f"decision={out['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
