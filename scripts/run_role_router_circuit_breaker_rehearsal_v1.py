#!/usr/bin/env python3
"""Rehearse circuit breaker triggers for role-router engine payload."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_ENGINE_INPUT = ART / "btc_limited_live_engine_input_from_role_router_latest.json"
DEFAULT_OUT = ART / "role_router_circuit_breaker_rehearsal_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _simulate(
    returns_pct: list[float],
    *,
    base_position_usd: float,
    max_consecutive_losses: int,
    max_drawdown_pct: float,
) -> dict[str, Any]:
    equity = float(base_position_usd)
    peak = equity
    consec_losses = 0
    blocked_reason = ""
    blocked_at = -1
    events: list[dict[str, Any]] = []
    for i, pct in enumerate(returns_pct):
        pnl = equity * (pct / 100.0)
        equity += pnl
        if pnl < 0:
            consec_losses += 1
        else:
            consec_losses = 0
        peak = max(peak, equity)
        dd_pct = 0.0 if peak <= 0 else ((equity / peak) - 1.0) * 100.0
        event = {
            "step": i + 1,
            "return_pct": pct,
            "equity": round(equity, 6),
            "consecutive_losses": consec_losses,
            "drawdown_pct": round(dd_pct, 6),
            "tripped": False,
            "reason": None,
        }
        if consec_losses >= max_consecutive_losses:
            blocked_reason = "max_consecutive_losses"
            blocked_at = i + 1
            event["tripped"] = True
            event["reason"] = blocked_reason
            events.append(event)
            break
        if dd_pct <= (-abs(max_drawdown_pct)):
            blocked_reason = "max_drawdown_pct"
            blocked_at = i + 1
            event["tripped"] = True
            event["reason"] = blocked_reason
            events.append(event)
            break
        events.append(event)
    return {
        "tripped": blocked_at > 0,
        "blocked_at_step": blocked_at,
        "blocked_reason": blocked_reason if blocked_reason else None,
        "events": events,
        "ending_equity": round(equity, 6),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine-input-json", type=Path, default=DEFAULT_ENGINE_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _read(args.engine_input_json)
    policy_max_losses = int(((doc.get("engine_input") or {}).get("max_consecutive_losses")) or 3)
    policy_max_dd = float(((doc.get("engine_input") or {}).get("max_drawdown_pct")) or 2.0)
    size_usd = float(((doc.get("engine_input") or {}).get("size_usd")) or 10.0)

    # Forced scenarios for deterministic breaker validation.
    # A: consecutive small losses should hit max_consecutive_losses first.
    # B: one deep loss should hit max_drawdown_pct first.
    scenario_a = _simulate(
        [-0.7, -0.8, -0.9, +0.5],
        base_position_usd=size_usd,
        max_consecutive_losses=policy_max_losses,
        max_drawdown_pct=policy_max_dd,
    )
    scenario_b = _simulate(
        [-2.2, +0.5, +0.5],
        base_position_usd=size_usd,
        max_consecutive_losses=policy_max_losses,
        max_drawdown_pct=policy_max_dd,
    )

    checks = {
        "scenario_a_trips_consecutive_loss": scenario_a.get("tripped") and scenario_a.get("blocked_reason") == "max_consecutive_losses",
        "scenario_b_trips_drawdown": scenario_b.get("tripped") and scenario_b.get("blocked_reason") == "max_drawdown_pct",
    }
    result = "PASS" if all(bool(v) for v in checks.values()) else "FAIL"

    payload = {
        "schema": "role_router_circuit_breaker_rehearsal_v1",
        "generated_at_utc": _now(),
        "engine_input_json": str(args.engine_input_json.resolve()),
        "policy_snapshot": {
            "size_usd": size_usd,
            "max_consecutive_losses": policy_max_losses,
            "max_drawdown_pct": policy_max_dd,
        },
        "checks": checks,
        "result": result,
        "scenarios": {
            "consecutive_losses": scenario_a,
            "single_deep_loss": scenario_b,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"result={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
