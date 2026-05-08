#!/usr/bin/env python3
"""Compute size-only lens penalty recommendations in shadow mode."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_EVENTS = REPORTS / "daily_execution_insight_falsification_log.jsonl"
DEFAULT_STATE = ART / "lens_penalty_shadow_state_latest.json"
DEFAULT_OUT = ART / "lens_penalty_daily_latest.json"
DEFAULT_POLICY = ART / "lens_penalty_policy_v1.json"


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


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _policy_or_default(path: Path) -> dict[str, Any]:
    p = _read_json(path)
    if p:
        return p
    return {
        "schema": "lens_penalty_policy_v1",
        "max_daily_penalty": 0.1,
        "penalty_step": 0.05,
        "recovery_step": 0.02,
        "min_multiplier": 0.5,
        "max_multiplier": 1.0,
        "fail_rate_trigger": 0.5,
        "lookback_rows": 50,
        "cooldown_events": 3,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events-jsonl", type=Path, default=DEFAULT_EVENTS)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--apply", action="store_true", help="Persist proposed multipliers into state.")
    args = ap.parse_args()

    policy = _policy_or_default(args.policy_json)
    prev_state = _read_json(args.state_json)
    prev_by_lens = prev_state.get("lens_state") if isinstance(prev_state.get("lens_state"), dict) else {}

    rows = _read_jsonl(args.events_jsonl)
    lookback = int(policy.get("lookback_rows") or 50)
    rows = rows[-lookback:]

    grouped: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        lens_id = str(r.get("lens_id") or "").strip()
        result = str(r.get("result") or "").upper()
        if not lens_id or result not in {"HIT", "FAIL"}:
            continue
        grouped.setdefault(lens_id, []).append(r)

    max_daily_penalty = float(policy.get("max_daily_penalty") or 0.1)
    penalty_step = float(policy.get("penalty_step") or 0.05)
    recovery_step = float(policy.get("recovery_step") or 0.02)
    min_multiplier = float(policy.get("min_multiplier") or 0.5)
    max_multiplier = float(policy.get("max_multiplier") or 1.0)
    fail_rate_trigger = float(policy.get("fail_rate_trigger") or 0.5)
    cooldown_events = int(policy.get("cooldown_events") or 3)

    lens_state: dict[str, Any] = {}
    recommendations: list[dict[str, Any]] = []
    for lens_id, events in grouped.items():
        n = len(events)
        fail_n = sum(1 for e in events if str(e.get("result") or "").upper() == "FAIL")
        hit_n = n - fail_n
        fail_rate = (fail_n / n) if n > 0 else 0.0

        prev = prev_by_lens.get(lens_id) if isinstance(prev_by_lens.get(lens_id), dict) else {}
        prev_multiplier = float(prev.get("multiplier") or 1.0)
        prev_cooldown = int(prev.get("cooldown_left") or 0)

        delta = 0.0
        reason = "stable"
        cooldown_left = max(prev_cooldown - 1, 0)
        if fail_rate >= fail_rate_trigger and n >= 3:
            delta = -min(penalty_step, max_daily_penalty)
            cooldown_left = cooldown_events
            reason = "fail_rate_penalty"
        elif hit_n >= 3 and cooldown_left == 0 and prev_multiplier < max_multiplier:
            delta = min(recovery_step, max_multiplier - prev_multiplier)
            reason = "hit_recovery"

        proposed = _clamp(prev_multiplier + delta, min_multiplier, max_multiplier)
        lens_state[lens_id] = {
            "multiplier": proposed if args.apply else prev_multiplier,
            "proposed_multiplier": proposed,
            "cooldown_left": cooldown_left if args.apply else prev_cooldown,
            "last_reason": reason,
            "fail_rate": round(fail_rate, 6),
            "events": n,
        }
        recommendations.append(
            {
                "lens_id": lens_id,
                "events": n,
                "fail_count": fail_n,
                "hit_count": hit_n,
                "fail_rate": round(fail_rate, 6),
                "prev_multiplier": round(prev_multiplier, 6),
                "proposed_multiplier": round(proposed, 6),
                "delta": round(delta, 6),
                "reason": reason,
            }
        )

    out = {
        "schema": "lens_penalty_daily_v1",
        "generated_at_utc": _now(),
        "mode": "apply" if args.apply else "shadow",
        "applied": bool(args.apply),
        "inputs": {
            "events_jsonl": str(args.events_jsonl.resolve()).replace("\\", "/"),
            "state_json": str(args.state_json.resolve()).replace("\\", "/"),
            "policy_json": str(args.policy_json.resolve()).replace("\\", "/"),
        },
        "policy": policy,
        "summary": {
            "total_rows_read": len(rows),
            "lenses_evaluated": len(recommendations),
            "recommendations_with_penalty": sum(1 for r in recommendations if r["delta"] < 0),
            "recommendations_with_recovery": sum(1 for r in recommendations if r["delta"] > 0),
        },
        "recommendations": recommendations,
    }
    _write_json(args.out, out)
    if args.apply:
        state_out = {
            "schema": "lens_penalty_shadow_state_v1",
            "updated_at_utc": _now(),
            "lens_state": lens_state,
        }
        _write_json(args.state_json, state_out)
    print(f"WROTE: {args.out}")
    print(f"mode={out['mode']}; lenses={len(recommendations)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
