#!/usr/bin/env python3
"""Evaluate L0 geopolitical/macro warning state from policy template + snapshot."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "l0_geopolitical_macro_warning_policy_template_v1.json"
DEFAULT_SNAPSHOT = ROOT / "docs" / "final" / "artifacts" / "l0_geopolitical_macro_indicator_snapshot_latest.json"
DEFAULT_STATE = ROOT / "docs" / "final" / "artifacts" / "l0_geopolitical_macro_warning_state_latest.json"
DEFAULT_LOG = ROOT / "reports" / "l0_geopolitical_macro_warning_log.jsonl"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _indicator_state(value: float, amber: float, red: float) -> str:
    if value >= red:
        return "RED"
    if value >= amber:
        return "AMBER"
    return "GREEN"


def _normalize_score(value: float, unit: str, red_threshold: float) -> float:
    if unit == "normalized_score_0_1":
        return max(0.0, min(1.0, value))
    denom = red_threshold if red_threshold > 0 else 1.0
    return max(0.0, min(1.0, value / denom))


def _next_state(
    prev_state: str,
    composite: float,
    amber_count: int,
    red_count: int,
    prev_streak: int,
) -> tuple[str, int]:
    # Conservative finite-state transition with simple hysteresis counter.
    if prev_state == "RED":
        candidate = "RED"
        if composite < 0.65 and red_count <= 1:
            candidate = "AMBER"
    elif prev_state == "AMBER":
        candidate = "AMBER"
        if composite >= 0.72 or red_count >= 2:
            candidate = "RED"
        elif composite < 0.45 and amber_count <= 1:
            candidate = "GREEN"
    else:
        candidate = "GREEN"
        if composite >= 0.72 or red_count >= 2:
            candidate = "RED"
        elif composite >= 0.55 or amber_count >= 3:
            candidate = "AMBER"

    streak = (prev_streak + 1) if candidate == prev_state else 1
    # Apply minimum persistence for de-escalation.
    if prev_state == "RED" and candidate == "AMBER" and streak < 3:
        return "RED", streak
    if prev_state == "AMBER" and candidate == "GREEN" and streak < 5:
        return "AMBER", streak
    return candidate, streak


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--snapshot-json", type=Path, default=DEFAULT_SNAPSHOT)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    policy = _load_json(args.policy_json)
    prev_state_doc = _load_json(args.state_json)
    snapshot = _load_json(args.snapshot_json)

    indicators = policy.get("indicators") or []
    weights = ((policy.get("scoring") or {}).get("weights")) or {}
    values = snapshot.get("indicator_values") if isinstance(snapshot.get("indicator_values"), dict) else {}

    no_data = not bool(values)
    indicator_rows: list[dict[str, Any]] = []
    amber_count = 0
    red_count = 0
    weighted_sum = 0.0
    used_weight_sum = 0.0

    for ind in indicators:
        if not isinstance(ind, dict):
            continue
        iid = str(ind.get("id") or "").strip()
        if not iid:
            continue
        v = float(values.get(iid, 0.0) or 0.0)
        amber = float(ind.get("amber_threshold") or 0.0)
        red = float(ind.get("red_threshold") or 0.0)
        unit = str(ind.get("unit") or "zscore")
        st = _indicator_state(v, amber, red)
        if st == "AMBER":
            amber_count += 1
        elif st == "RED":
            red_count += 1
        norm = _normalize_score(v, unit, red)
        w = float(weights.get(iid, 0.0) or 0.0)
        weighted_sum += norm * w
        used_weight_sum += w
        indicator_rows.append(
            {
                "id": iid,
                "value": v,
                "state": st,
                "amber_threshold": amber,
                "red_threshold": red,
                "unit": unit,
                "normalized_score_0_1": round(norm, 6),
                "weight": w,
            }
        )

    composite = (weighted_sum / used_weight_sum) if used_weight_sum > 0 else 0.0
    composite = round(composite, 6)
    if no_data:
        # Conservative fallback when no snapshot exists.
        composite = max(composite, 0.56)
        amber_count = max(amber_count, 3)

    prev_state = str(prev_state_doc.get("state") or "GREEN")
    prev_streak = int(prev_state_doc.get("state_streak") or 0)
    state, streak = _next_state(prev_state, composite, amber_count, red_count, prev_streak)

    cooldown_min = int(((policy.get("state_machine") or {}).get("cooldown_minutes_after_red")) or 30)
    now = _now()
    cooldown_until = _iso(now + timedelta(minutes=cooldown_min)) if state == "RED" else None

    action_map = (policy.get("execution_binding") or {})
    if state == "RED":
        action = str(action_map.get("red_action") or "FORCE_HOLD")
    elif state == "AMBER":
        action = str(action_map.get("amber_action") or "REDUCE_EXPOSURE")
    else:
        action = str(action_map.get("green_action") or "NO_CHANGE")

    out = {
        "schema": "l0_geopolitical_macro_warning_state_v1",
        "generated_at_utc": _iso(now),
        "policy_ref": str(args.policy_json),
        "snapshot_ref": str(args.snapshot_json),
        "state": state,
        "state_streak": streak,
        "effective_action": action,
        "composite_score": composite,
        "amber_count": amber_count,
        "red_count": red_count,
        "cooldown_until_utc": cooldown_until,
        "no_data_fallback_applied": no_data,
        "indicator_states": indicator_rows,
    }
    _write_json(args.state_json, out)

    log_row = {
        "ts_utc": _iso(now),
        "schema": "l0_geopolitical_macro_warning_log_row_v1",
        "state": state,
        "composite_score": composite,
        "amber_count": amber_count,
        "red_count": red_count,
        "effective_action": action,
        "cooldown_until_utc": cooldown_until,
        "no_data_fallback_applied": no_data,
    }
    _append_jsonl(args.log_jsonl, log_row)

    print(f"WROTE: {args.state_json}")
    print(f"APPEND: {args.log_jsonl}")
    print(f"state={state} action={action} composite={composite}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

