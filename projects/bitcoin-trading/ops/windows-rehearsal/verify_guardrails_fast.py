#!/usr/bin/env python3
"""Fast guardrail verification (no full daemon boot)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import yaml


def load_risk_config() -> dict:
    cfg_path = Path(__file__).resolve().parents[2] / "config" / "trading_config.yaml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    return (data.get("risk_management") or {})


def hard_gate(
    failure_count: int,
    max_failures: int,
    daily_pnl: float,
    balance: float,
    max_daily_loss: float,
) -> bool:
    if failure_count >= max_failures:
        return False
    daily_loss_ratio = abs(daily_pnl) / max(balance, 1e-9) if daily_pnl < 0 else 0.0
    if daily_loss_ratio >= max_daily_loss * 0.9:
        return False
    return True


def dynamic_cap_notional(
    requested_notional: float,
    balance: float,
    risk_per_trade: float,
    stop_loss_ratio: float,
    max_position_size: float,
    confidence: float,
    realized_volatility: float,
) -> float:
    stop_loss = max(float(stop_loss_ratio or 0.01), 0.001)
    risk_budget = balance * risk_per_trade
    max_notional_by_risk = risk_budget / stop_loss
    max_notional_by_ratio = balance * max_position_size

    if realized_volatility >= 0.06:
        vol_multiplier = 0.5
    elif realized_volatility >= 0.04:
        vol_multiplier = 0.7
    else:
        vol_multiplier = 1.0

    confidence_multiplier = max(0.8, min(1.1, 0.8 + float(confidence) * 0.3))
    allowed_notional = min(
        max_notional_by_ratio,
        max_notional_by_risk * vol_multiplier * confidence_multiplier,
    )
    return min(requested_notional, allowed_notional)


def main() -> int:
    risk = load_risk_config()
    risk_per_trade = float(risk.get("risk_per_trade", 0.0075))
    max_failures = int(risk.get("max_consecutive_failures_hard_gate", 3))
    max_daily_loss = float(risk.get("max_daily_loss", 0.03))
    stop_loss_ratio = float(risk.get("stop_loss_ratio", 0.008))
    max_position_size = float(risk.get("max_position_size", 0.10))

    checks = []

    checks.append((
        "hard_gate_failure_count_blocks",
        hard_gate(
            failure_count=max_failures,
            max_failures=max_failures,
            daily_pnl=0.0,
            balance=1400.0,
            max_daily_loss=max_daily_loss,
        )
        is False,
    ))
    checks.append((
        "hard_gate_daily_loss_blocks",
        hard_gate(
            failure_count=0,
            max_failures=max_failures,
            daily_pnl=-(1400.0 * max_daily_loss * 0.95),
            balance=1400.0,
            max_daily_loss=max_daily_loss,
        )
        is False,
    ))
    checks.append((
        "hard_gate_normal_passes",
        hard_gate(
            failure_count=0,
            max_failures=max_failures,
            daily_pnl=-5.0,
            balance=1400.0,
            max_daily_loss=max_daily_loss,
        )
        is True,
    ))

    requested_notional = 850.0
    capped_high_vol = dynamic_cap_notional(
        requested_notional=requested_notional,
        balance=1400.0,
        risk_per_trade=risk_per_trade,
        stop_loss_ratio=stop_loss_ratio,
        max_position_size=max_position_size,
        confidence=0.72,
        realized_volatility=0.065,
    )
    checks.append(("dynamic_cap_reduces_high_vol", capped_high_vol < requested_notional))

    capped_low_vol = dynamic_cap_notional(
        requested_notional=requested_notional,
        balance=1400.0,
        risk_per_trade=risk_per_trade,
        stop_loss_ratio=stop_loss_ratio,
        max_position_size=max_position_size,
        confidence=0.72,
        realized_volatility=0.01,
    )
    checks.append(("dynamic_cap_bounds_by_limits", 0.0 < capped_low_vol <= requested_notional))

    failed = [name for name, ok in checks if not ok]
    print("risk_per_trade=", risk_per_trade)
    print("max_consecutive_failures_hard_gate=", max_failures)
    print("capped_notional_high_vol=", round(capped_high_vol, 6))
    print("capped_notional_low_vol=", round(capped_low_vol, 6))
    print("checks=", len(checks), "failed=", len(failed))
    if failed:
        print("FAILED:", ",".join(failed))
        return 1
    print("PASS: guardrails fast verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

