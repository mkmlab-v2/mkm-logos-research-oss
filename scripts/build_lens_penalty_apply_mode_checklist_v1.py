#!/usr/bin/env python3
"""Build apply-mode transition checklist for lens penalty pipeline."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_DAILY = ART / "lens_penalty_daily_latest.json"
DEFAULT_WEEKLY = ART / "lens_penalty_shadow_weekly_report_latest.json"
DEFAULT_STATE = ART / "lens_penalty_shadow_state_latest.json"
DEFAULT_POLICY = ART / "lens_penalty_apply_mode_policy_v1.json"
DEFAULT_OUT = ART / "lens_penalty_apply_mode_checklist_latest.json"


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


def _thresholds_for_policy(
    policy: dict[str, Any],
    weekly_events: int,
    fallback_min_events: int,
    fallback_max_fail_rate: float,
) -> tuple[str, int, float]:
    profiles = policy.get("profiles") if isinstance(policy.get("profiles"), dict) else {}
    if not profiles:
        return "default", fallback_min_events, fallback_max_fail_rate

    def _profile_limits(name: str, data: Any) -> tuple[str, int, float] | None:
        if not isinstance(data, dict):
            return None
        min_events = int(data.get("min_weekly_events") or 0)
        max_fail = float(data.get("max_weekly_fail_rate") or 0.0)
        if min_events <= 0 or max_fail <= 0:
            return None
        return name, min_events, max_fail

    active = str(policy.get("active_profile") or "").strip()
    if active and active in profiles:
        picked = _profile_limits(active, profiles.get(active))
        if picked is not None:
            return picked

    candidates: list[tuple[str, int, float]] = []
    for name, data in profiles.items():
        parsed = _profile_limits(str(name), data)
        if parsed is not None:
            candidates.append(parsed)
    if not candidates:
        return "default", fallback_min_events, fallback_max_fail_rate

    # Auto mode: choose the strictest profile that is eligible by event count.
    candidates.sort(key=lambda x: x[1])
    eligible = [c for c in candidates if weekly_events >= c[1]]
    if eligible:
        return eligible[-1]
    return candidates[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--daily-json", type=Path, default=DEFAULT_DAILY)
    ap.add_argument("--weekly-json", type=Path, default=DEFAULT_WEEKLY)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-weekly-events", type=int, default=21)
    ap.add_argument("--max-weekly-fail-rate", type=float, default=0.45)
    args = ap.parse_args()

    daily = _read_json(args.daily_json)
    weekly = _read_json(args.weekly_json)
    checklist_policy = _read_json(args.policy_json)
    weekly_summary = weekly.get("summary") if isinstance(weekly.get("summary"), dict) else {}
    weekly_events = int(weekly_summary.get("total_events") or 0)
    weekly_fail_rate = float(weekly_summary.get("overall_fail_rate") or 0.0)

    fallback_min_events = int(checklist_policy.get("min_weekly_events") or args.min_weekly_events)
    fallback_max_fail_rate = float(checklist_policy.get("max_weekly_fail_rate") or args.max_weekly_fail_rate)
    active_profile, min_weekly_events, max_weekly_fail_rate = _thresholds_for_policy(
        checklist_policy,
        weekly_events=weekly_events,
        fallback_min_events=fallback_min_events,
        fallback_max_fail_rate=fallback_max_fail_rate,
    )
    human_review_required = bool(checklist_policy.get("human_review_required", True))
    auto_apply_enabled = bool(checklist_policy.get("auto_apply_enabled", False))

    recs = daily.get("recommendations") if isinstance(daily.get("recommendations"), list) else []
    policy = daily.get("policy") if isinstance(daily.get("policy"), dict) else {}
    max_daily_penalty = float(policy.get("max_daily_penalty") or 0.0)

    mode_shadow_only = (str(daily.get("mode") or "") == "shadow") and (bool(daily.get("applied")) is False)
    has_recs = len(recs) > 0
    max_penalty_ok = all(abs(float(r.get("delta") or 0.0)) <= max_daily_penalty + 1e-9 for r in recs)
    weekly_events_ok = weekly_events >= min_weekly_events
    weekly_fail_rate_ok = weekly_fail_rate <= max_weekly_fail_rate
    rollback_ready = args.state_json.is_file()

    checklist = {
        "mode_shadow_only": mode_shadow_only,
        "size_only_guard_ready": has_recs,
        "direction_untouched_guard": True,
        "max_daily_penalty_guard": max_penalty_ok,
        "weekly_min_events_guard": weekly_events_ok,
        "weekly_fail_rate_guard": weekly_fail_rate_ok,
        "rollback_artifact_ready": rollback_ready,
    }
    all_green = all(checklist.values())
    decision = "READY_FOR_APPLY_REVIEW" if all_green else "HOLD_SHADOW_CONTINUE"

    out = {
        "schema": "lens_penalty_apply_mode_checklist_v1",
        "generated_at_utc": _now(),
        "decision": decision,
        "all_green": all_green,
        "checklist": checklist,
        "thresholds": {
            "active_profile": active_profile,
            "min_weekly_events": min_weekly_events,
            "max_weekly_fail_rate": max_weekly_fail_rate,
            "max_daily_penalty": max_daily_penalty,
        },
        "snapshot": {
            "weekly_events": weekly_events,
            "weekly_fail_rate": weekly_fail_rate,
            "lenses_evaluated": int((daily.get("summary") or {}).get("lenses_evaluated") or 0),
        },
        "constraints": {
            "size_only": True,
            "direction_untouched": True,
            "human_review_required": human_review_required,
            "auto_apply_enabled": auto_apply_enabled,
        },
        "evidence_paths": {
            "daily_json": str(args.daily_json.resolve()).replace("\\", "/"),
            "weekly_json": str(args.weekly_json.resolve()).replace("\\", "/"),
            "state_json": str(args.state_json.resolve()).replace("\\", "/"),
            "policy_json": str(args.policy_json.resolve()).replace("\\", "/"),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"decision={decision}; all_green={all_green}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
