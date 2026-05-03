#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "mkm_ai_micro_scale_rollout_policy_v1.json"
DEFAULT_ROLLOUT_STATE = ROOT / "docs" / "final" / "artifacts" / "mkm_ai_micro_scale_rollout_status_latest.json"
DEFAULT_STRATEGY_GATE = (
    ROOT / "projects" / "bitcoin-trading" / "exports" / "cursor_trade_history" / "strategy_promotion_gate_latest.json"
)
DEFAULT_LIVE_HEALTH = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "ops" / "live_trading_health_latest.json"
DEFAULT_BLOCKERS = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "ops" / "live_trading_blockers_latest.json"
DEFAULT_NOFILL = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "ops" / "live_trading_nofill_alert_latest.json"
DEFAULT_RISK = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "risk" / "risk_profile_fact_safe_latest.json"
DEFAULT_ENGINE_INPUT = ROOT / "docs" / "final" / "artifacts" / "btc_limited_live_engine_input_from_lens_combo_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_json_safe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return _read_json(path)
    except Exception:
        return {}


def _stage_lookup(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    stages = policy.get("stages") or []
    return {str(s.get("id")): s for s in stages if isinstance(s, dict) and s.get("id")}


def _ordered_stages(policy: dict[str, Any]) -> list[dict[str, Any]]:
    stages = [s for s in (policy.get("stages") or []) if isinstance(s, dict)]
    return sorted(stages, key=lambda s: int(s.get("order") or 0))


def _next_stage(ordered: list[dict[str, Any]], stage_id: str) -> str | None:
    ids = [str(s.get("id")) for s in ordered]
    if stage_id not in ids:
        return ids[0] if ids else None
    idx = ids.index(stage_id)
    if idx + 1 >= len(ids):
        return None
    return ids[idx + 1]


def _prev_stage(ordered: list[dict[str, Any]], stage_id: str) -> str:
    ids = [str(s.get("id")) for s in ordered]
    if stage_id not in ids:
        return ids[0] if ids else "shadow"
    idx = ids.index(stage_id)
    if idx <= 0:
        return ids[0]
    return ids[idx - 1]


def _bool(v: Any) -> bool:
    return bool(v)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    policy = _read_json(args.policy)
    strategy = _read_json_safe(args.strategy_gate)
    health = _read_json_safe(args.live_health)
    blockers = _read_json_safe(args.blockers)
    nofill = _read_json_safe(args.nofill)
    risk = _read_json_safe(args.risk_profile)
    engine_input = _read_json_safe(args.engine_input)
    prev_state = _read_json_safe(args.previous_state)

    ordered = _ordered_stages(policy)
    stage_map = _stage_lookup(policy)
    if not ordered:
        raise SystemExit("policy has no stages")

    current_stage = str(args.current_stage or policy.get("current_stage") or prev_state.get("current_stage") or "shadow")
    if current_stage not in stage_map:
        current_stage = str(ordered[0].get("id"))
    current = stage_map[current_stage]
    requires = current.get("promotion_requires") or {}

    strategy_ready = _bool((strategy.get("decision") or {}).get("promotion_ready"))
    health_pass = str(health.get("result") or "").upper() == "PASS"
    blockers_pass = str(blockers.get("result") or "").upper() == "PASS"
    nofill_warn = _bool(nofill.get("warn"))
    risk_fresh = risk.get("generated_at") is not None
    daemon_status = _read_json_safe(args.daemon_status)
    daemon_fresh = (((daemon_status.get("risk_profile") or {}).get("freshness") or {}).get("is_fresh"))
    if isinstance(daemon_fresh, bool):
        risk_fresh = daemon_fresh
    exchange_fills_24h = int(float(health.get("exchange_fills_24h") or 0))
    daily_loss_cap_pct = float(((risk.get("trinity_governor") or {}).get("daily_loss_cap_pct") or 999.0))

    checks = {
        "strategy_promotion_ready": strategy_ready == _bool(requires.get("strategy_promotion_ready", True)),
        "health_pass": health_pass == _bool(requires.get("health_pass", True)),
        "blockers_pass": blockers_pass == _bool(requires.get("blockers_pass", True)),
        "nofill_warn_allowed": (True if _bool(requires.get("nofill_warn_allowed", True)) else (not nofill_warn)),
        "risk_profile_fresh_required": (True if not _bool(requires.get("risk_profile_fresh_required", True)) else risk_fresh),
        "exchange_fills_24h_min": exchange_fills_24h >= int(requires.get("exchange_fills_24h_min", 0)),
        "max_daily_loss_cap_pct": daily_loss_cap_pct <= float(requires.get("max_daily_loss_cap_pct", 999.0)),
    }
    promotion_ready = all(checks.values())

    hard_rules = policy.get("hard_downgrade_rules") or {}
    hard_downgrade = False
    hard_reasons: list[str] = []
    if _bool(hard_rules.get("health_fail")) and not health_pass:
        hard_downgrade = True
        hard_reasons.append("health_fail")
    if _bool(hard_rules.get("blockers_fail")) and not blockers_pass:
        hard_downgrade = True
        hard_reasons.append("blockers_fail")
    if _bool(hard_rules.get("risk_profile_not_fresh")) and not risk_fresh:
        hard_downgrade = True
        hard_reasons.append("risk_profile_not_fresh")
    max_loss = float(hard_rules.get("daily_loss_cap_pct_gt") or 999.0)
    if daily_loss_cap_pct > max_loss:
        hard_downgrade = True
        hard_reasons.append("daily_loss_cap_pct_gt")

    cycles = int(prev_state.get("cycle_count_in_stage") or 0) + 1
    min_cycles = int(current.get("min_cycles_before_promotion") or 1)

    decision = "HOLD_STAGE"
    target_stage = current_stage
    reasons: list[str] = []

    if hard_downgrade:
        decision = "DOWNGRADE_ONE_STAGE"
        target_stage = _prev_stage(ordered, current_stage)
        reasons = hard_reasons
        cycles = 0
    elif promotion_ready and cycles >= min_cycles:
        ns = _next_stage(ordered, current_stage)
        if ns:
            decision = "PROMOTE_ONE_STAGE"
            target_stage = ns
            reasons = ["promotion_checks_passed", "min_cycles_reached"]
            cycles = 0
        else:
            decision = "KEEP_MAX_STAGE"
            reasons = ["already_at_max_stage"]
    else:
        if not promotion_ready:
            reasons.append("promotion_checks_not_passed")
        if cycles < min_cycles:
            reasons.append("min_cycles_not_reached")

    target_cfg = stage_map.get(target_stage, current)
    base_size = float(policy.get("base_size_usd") or 10.0)
    cap_size = float(policy.get("max_size_usd") or base_size)
    mul = float(target_cfg.get("size_multiplier") or 0.0)
    recommended_size = round(min(cap_size, base_size * mul), 4)
    if target_stage == "shadow":
        recommended_size = 0.0

    current_engine_size = float(((engine_input.get("engine_input") or {}).get("size_usd") or base_size))

    return {
        "schema": "mkm_ai_micro_scale_rollout_status_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "policy": str(args.policy),
            "strategy_gate": str(args.strategy_gate),
            "live_health": str(args.live_health),
            "blockers": str(args.blockers),
            "nofill": str(args.nofill),
            "risk_profile": str(args.risk_profile),
            "daemon_status": str(args.daemon_status),
            "engine_input": str(args.engine_input),
            "previous_state": str(args.previous_state),
        },
        "current_stage": current_stage,
        "target_stage": target_stage,
        "decision": decision,
        "decision_reasons": reasons,
        "cycle_count_in_stage": cycles,
        "min_cycles_before_promotion": min_cycles,
        "promotion_ready": promotion_ready,
        "checks": checks,
        "observability": {
            "strategy_promotion_ready": strategy_ready,
            "health_pass": health_pass,
            "blockers_pass": blockers_pass,
            "nofill_warn": nofill_warn,
            "risk_profile_fresh": risk_fresh,
            "exchange_fills_24h": exchange_fills_24h,
            "daily_loss_cap_pct": daily_loss_cap_pct,
        },
        "sizing": {
            "current_engine_size_usd": current_engine_size,
            "recommended_size_usd": recommended_size,
            "base_size_usd": base_size,
            "max_size_usd": cap_size,
            "stage_size_multiplier": mul,
            "apply_mode": "manual_confirm_required"
        },
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate staged MKM AI micro-size rollout decision.")
    p.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    p.add_argument("--strategy-gate", type=Path, default=DEFAULT_STRATEGY_GATE)
    p.add_argument("--live-health", type=Path, default=DEFAULT_LIVE_HEALTH)
    p.add_argument("--blockers", type=Path, default=DEFAULT_BLOCKERS)
    p.add_argument("--nofill", type=Path, default=DEFAULT_NOFILL)
    p.add_argument("--risk-profile", type=Path, default=DEFAULT_RISK)
    p.add_argument(
        "--daemon-status",
        type=Path,
        default=ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "status" / "trading_daemon_status.json",
    )
    p.add_argument("--engine-input", type=Path, default=DEFAULT_ENGINE_INPUT)
    p.add_argument("--previous-state", type=Path, default=DEFAULT_ROLLOUT_STATE)
    p.add_argument("--current-stage", default="")
    p.add_argument("--out", type=Path, default=DEFAULT_ROLLOUT_STATE)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    payload = evaluate(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] wrote: {args.out}")
    print(f"decision={payload.get('decision')} target_stage={payload.get('target_stage')}")
    print(f"recommended_size_usd={payload.get('sizing', {}).get('recommended_size_usd')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
