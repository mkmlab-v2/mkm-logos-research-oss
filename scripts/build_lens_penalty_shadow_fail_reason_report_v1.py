#!/usr/bin/env python3
"""Build fail-reason analysis report for lens penalty shadow events."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_EVENTS = REPORTS / "daily_execution_insight_falsification_log.jsonl"
DEFAULT_OUT = ART / "lens_penalty_shadow_fail_reason_report_latest.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


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


def _parse_ts(s: Any) -> datetime | None:
    if not isinstance(s, str) or not s.strip():
        return None
    x = s.strip()
    if x.endswith("Z"):
        x = x[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(x)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _reason(pred: str, actual: str, result: str) -> str:
    if result != "FAIL":
        return "NON_FAIL"
    if not actual or actual == "UNKNOWN":
        return "ACTUAL_UNKNOWN"
    if not pred or pred == "UNKNOWN":
        return "PREDICTION_UNKNOWN"
    if pred == actual:
        return "RESULT_INCONSISTENT"
    return "DIRECTION_MISMATCH"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events-jsonl", type=Path, default=DEFAULT_EVENTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--window-days", type=int, default=7)
    args = ap.parse_args()

    now = _now()
    window_start = now - timedelta(days=max(args.window_days, 1))
    rows = _read_jsonl(args.events_jsonl)

    filtered: list[dict[str, Any]] = []
    for r in rows:
        ts = _parse_ts(r.get("timestamp_utc"))
        if ts is None:
            continue
        if ts >= window_start:
            filtered.append(r)

    fail_rows: list[dict[str, Any]] = []
    reason_counts: dict[str, int] = {}
    lens_reason_counts: dict[str, dict[str, int]] = {}
    for r in filtered:
        result = str(r.get("result") or "").upper()
        if result != "FAIL":
            continue
        lens_id = str(r.get("lens_id") or "").strip() or "unknown_lens"
        pred = str(r.get("prediction_label") or "").strip().upper()
        actual = str(r.get("actual_label") or "").strip().upper()
        reason = _reason(pred, actual, result)
        fail_rows.append(r)
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        bucket = lens_reason_counts.setdefault(lens_id, {})
        bucket[reason] = bucket.get(reason, 0) + 1

    reason_ranked = sorted(
        [{"reason_code": k, "count": v} for k, v in reason_counts.items()],
        key=lambda x: (-int(x["count"]), str(x["reason_code"])),
    )
    per_lens = []
    for lens_id in sorted(lens_reason_counts.keys()):
        breakdown = lens_reason_counts[lens_id]
        per_lens.append(
            {
                "lens_id": lens_id,
                "fail_count": sum(int(v) for v in breakdown.values()),
                "reason_breakdown": dict(sorted(breakdown.items(), key=lambda kv: (-int(kv[1]), kv[0]))),
            }
        )

    out = {
        "schema": "lens_penalty_shadow_fail_reason_report_v1",
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {
            "days": int(args.window_days),
            "start_utc": window_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "inputs": {
            "events_jsonl": str(args.events_jsonl.resolve()).replace("\\", "/"),
        },
        "summary": {
            "events_in_window": len(filtered),
            "fail_events": len(fail_rows),
            "top_reason_code": reason_ranked[0]["reason_code"] if reason_ranked else "NONE",
        },
        "reason_ranked": reason_ranked,
        "per_lens": per_lens,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"fails={len(fail_rows)}; top_reason={out['summary']['top_reason_code']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
