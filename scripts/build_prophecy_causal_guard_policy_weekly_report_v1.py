#!/usr/bin/env python3
"""Build weekly summary report from causal guard policy decision JSONL history."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports" / "prophecy_causal_active_guard_policy_decision_log.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_causal_active_guard_policy_weekly_report_latest.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
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
    ap = argparse.ArgumentParser(description="Build weekly report for prophecy causal guard policy profile selections.")
    ap.add_argument("--decision-log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    log_path = args.decision_log_jsonl if args.decision_log_jsonl.is_absolute() else ROOT / args.decision_log_jsonl
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    now = _now()
    start = now - timedelta(days=max(1, int(args.window_days)))
    events = _load_jsonl(log_path)

    in_window: list[dict[str, Any]] = []
    for ev in events:
        ts_raw = str(ev.get("generated_at_utc") or "").strip()
        try:
            ts = datetime.strptime(ts_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if ts >= start:
            in_window.append(ev)

    total = len(in_window)
    profile_counts: dict[str, int] = {}
    hit_vals: list[float] = []
    wf_vals: list[float] = []
    transitions = 0
    prev_profile: str | None = None
    for ev in sorted(in_window, key=lambda x: str(x.get("generated_at_utc") or "")):
        profile = str(ev.get("selected_profile") or "unknown")
        profile_counts[profile] = profile_counts.get(profile, 0) + 1
        if prev_profile is not None and prev_profile != profile:
            transitions += 1
        prev_profile = profile
        hv = _safe_float(ev.get("observed_hit_rate"))
        wv = _safe_float(ev.get("observed_walkforward_mean_test_accuracy"))
        if hv is not None:
            hit_vals.append(hv)
        if wv is not None:
            wf_vals.append(wv)

    aggressive_share = (profile_counts.get("aggressive", 0) / total) if total else 0.0
    out = {
        "schema": "prophecy_causal_active_guard_policy_weekly_report_v1",
        "generated_at_utc": _to_iso(now),
        "window_days": int(args.window_days),
        "window_start_utc": _to_iso(start),
        "window_end_utc": _to_iso(now),
        "decision_log_jsonl": str(log_path),
        "summary": {
            "total_decisions": total,
            "profile_counts": profile_counts,
            "profile_transitions": transitions,
            "aggressive_share": round(aggressive_share, 6),
            "avg_observed_hit_rate": round(sum(hit_vals) / len(hit_vals), 6) if hit_vals else None,
            "avg_observed_walkforward_mean_test_accuracy": round(sum(wf_vals) / len(wf_vals), 6) if wf_vals else None,
        },
        "latest_decision": in_window[-1] if in_window else None,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    print(
        f"window_days={args.window_days} total_decisions={total} "
        f"aggressive_share={out['summary']['aggressive_share']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
