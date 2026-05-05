#!/usr/bin/env python3
"""Build weekly report from chronicle human-gate ledger JSONL."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


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


def _manual_review_index(rows: list[dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for r in rows:
        target = str(r.get("reviewed_recorded_at_utc", "")).strip()
        if target:
            keys.add(target)
    return keys


def _ending_streak(rows: list[dict[str, Any]], predicate) -> int:
    streak = 0
    for row in reversed(rows):
        if predicate(row):
            streak += 1
        else:
            break
    return streak


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_ledger = root / "docs" / "final" / "artifacts" / "chronicle_human_gate_ledger_latest.jsonl"
    default_manual_reviews = root / "docs" / "final" / "artifacts" / "chronicle_human_gate_manual_reviews_latest.jsonl"
    default_out = root / "docs" / "final" / "artifacts" / "chronicle_human_gate_weekly_report_latest.json"

    ap = argparse.ArgumentParser(description="Build chronicle human-gate weekly report.")
    ap.add_argument("--ledger-jsonl", default=str(default_ledger))
    ap.add_argument("--manual-reviews-jsonl", default=str(default_manual_reviews))
    ap.add_argument("--output-json", default=str(default_out))
    ap.add_argument("--lookback-days", type=int, default=7)
    ap.add_argument("--threshold-switch-min-rows", type=int, default=14)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=args.lookback_days)
    all_rows = _load_jsonl(Path(args.ledger_jsonl))
    filtered: list[dict[str, Any]] = []
    for r in all_rows:
        ts = _parse_iso(str(r.get("recorded_at_utc", "")))
        if ts is None:
            continue
        if ts >= cutoff:
            filtered.append(r)

    filtered.sort(key=lambda r: str(r.get("recorded_at_utc", "")))

    review_required_count = sum(1 for r in filtered if bool(r.get("human_review_required", False)))
    warning_streak = _ending_streak(
        filtered,
        lambda r: str(r.get("severity", "OK")).upper() in {"WARNING", "CRITICAL"},
    )
    critical_streak = _ending_streak(
        filtered,
        lambda r: str(r.get("severity", "OK")).upper() == "CRITICAL",
    )
    severity_counts = {"OK": 0, "WARNING": 0, "CRITICAL": 0}
    for r in filtered:
        sev = str(r.get("severity", "OK")).upper()
        if sev in severity_counts:
            severity_counts[sev] += 1

    manual_rows = _load_jsonl(Path(args.manual_reviews_jsonl))
    manual_index = _manual_review_index(manual_rows)
    required_rows = [r for r in filtered if bool(r.get("human_review_required", False))]
    review_gap_count = sum(1 for r in required_rows if str(r.get("recorded_at_utc", "")) not in manual_index)
    manual_review_count = len(required_rows) - review_gap_count

    review_required_ratio = round(review_required_count / max(1, len(filtered)), 6)
    readiness = (
        "ready"
        if (
            len(filtered) >= args.threshold_switch_min_rows
            and critical_streak == 0
            and warning_streak <= 1
            and review_required_ratio <= 0.2
        )
        else "not_ready"
    )
    recommendation = (
        "consider_threshold_switch_review"
        if readiness == "ready"
        else "keep_shadow_compare_until_more_data"
    )

    out = {
        "schema": "chronicle_human_gate_weekly_report_v1",
        "generated_at_utc": _iso_now(),
        "lookback_days": args.lookback_days,
        "threshold_switch_min_rows": args.threshold_switch_min_rows,
        "row_count": len(filtered),
        "review_required_count": review_required_count,
        "review_required_ratio": review_required_ratio,
        "manual_review_count": manual_review_count,
        "review_gap_count": review_gap_count,
        "review_gap_detected": review_gap_count > 0,
        "warning_streak": warning_streak,
        "critical_streak": critical_streak,
        "severity_counts": severity_counts,
        "readiness_for_threshold_switch": readiness,
        "threshold_switch_recommendation": recommendation,
        "ledger_jsonl": str(Path(args.ledger_jsonl)),
        "manual_reviews_jsonl": str(Path(args.manual_reviews_jsonl)),
    }
    Path(args.output_json).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
