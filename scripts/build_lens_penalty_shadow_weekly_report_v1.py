#!/usr/bin/env python3
"""Build 7-day summary report for lens penalty shadow operation."""
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
DEFAULT_OUT = ART / "lens_penalty_shadow_weekly_report_latest.json"
DEFAULT_APPLY_POLICY = ART / "lens_penalty_apply_mode_policy_v1.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events-jsonl", type=Path, default=DEFAULT_EVENTS)
    ap.add_argument("--apply-policy-json", type=Path, default=DEFAULT_APPLY_POLICY)
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

    by_lens: dict[str, dict[str, Any]] = {}
    for r in filtered:
        lens_id = str(r.get("lens_id") or "").strip()
        result = str(r.get("result") or "").upper()
        if not lens_id or result not in {"HIT", "FAIL"}:
            continue
        stat = by_lens.setdefault(
            lens_id,
            {"lens_id": lens_id, "events": 0, "hit_count": 0, "fail_count": 0, "fail_rate": 0.0},
        )
        stat["events"] += 1
        if result == "HIT":
            stat["hit_count"] += 1
        else:
            stat["fail_count"] += 1

    per_lens: list[dict[str, Any]] = []
    for lens_id in sorted(by_lens.keys()):
        stat = by_lens[lens_id]
        ev = int(stat["events"])
        fail = int(stat["fail_count"])
        stat["fail_rate"] = round((fail / ev), 6) if ev > 0 else 0.0
        per_lens.append(stat)

    total_events = sum(int(x["events"]) for x in per_lens)
    total_fail = sum(int(x["fail_count"]) for x in per_lens)
    total_hit = sum(int(x["hit_count"]) for x in per_lens)

    apply_policy = _read_json(args.apply_policy_json)
    profiles = apply_policy.get("profiles") if isinstance(apply_policy.get("profiles"), dict) else {}
    strict_policy = profiles.get("strict") if isinstance(profiles.get("strict"), dict) else {}
    strict_max_fail_rate = float(
        strict_policy.get("max_weekly_fail_rate")
        or apply_policy.get("max_weekly_fail_rate")
        or 0.45
    )
    overall_fail_rate = round((total_fail / total_events), 6) if total_events > 0 else 0.0
    strict_gap = round(overall_fail_rate - strict_max_fail_rate, 6)

    out = {
        "schema": "lens_penalty_shadow_weekly_report_v1",
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {
            "days": int(args.window_days),
            "start_utc": window_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "inputs": {
            "events_jsonl": str(args.events_jsonl.resolve()).replace("\\", "/"),
            "apply_policy_json": str(args.apply_policy_json.resolve()).replace("\\", "/"),
        },
        "summary": {
            "lenses": len(per_lens),
            "total_events": total_events,
            "total_hit": total_hit,
            "total_fail": total_fail,
            "overall_fail_rate": overall_fail_rate,
            "strict_max_fail_rate": strict_max_fail_rate,
            "strict_gap": strict_gap,
        },
        "per_lens": per_lens,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"lenses={len(per_lens)}; events={total_events}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
