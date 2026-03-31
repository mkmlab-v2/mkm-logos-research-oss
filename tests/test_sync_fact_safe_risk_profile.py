from datetime import datetime, timezone

from scripts.sync_fact_safe_risk_profile import _derive_profile


def test_derive_profile_locked_mode_enforces_hard_limits():
    out = _derive_profile(
        risk_profile={
            "mode": "LOCKED_MODE",
            "position_scale_cap": 0.2,
            "daily_loss_cap_pct": 0.7,
            "fused_risk_pressure": 0.9,
        },
        now=datetime.now(timezone.utc),
    )
    assert out["max_trades_per_day"] == 5
    assert out["max_position_size"] == 0.03
    assert out["maker_only_level"] == "strict"
    assert out["kill_switch_threshold"] == 0.015
    assert out["singular_core"]["core_decision"] == "HOLD"


def test_derive_profile_active_mode_maps_to_bounded_fields():
    out = _derive_profile(
        risk_profile={
            "mode": "ACTIVE_MODE",
            "position_scale_cap": 0.5,
            "daily_loss_cap_pct": 1.2,
            "fused_risk_pressure": 0.6,
        },
        now=datetime.now(timezone.utc),
    )
    assert 10 <= out["max_trades_per_day"] <= 80
    assert 0.03 <= out["max_position_size"] <= 0.20
    assert out["maker_only_level"] == "preferred"
    assert 3 <= out["slippage_cap_bps"] <= 15
    assert 0.015 <= out["kill_switch_threshold"] <= 0.04


def test_derive_profile_forces_lock_when_core_hold():
    out = _derive_profile(
        risk_profile={
            "mode": "ACTIVE_MODE",
            "core_decision": "HOLD",
            "core_score": 0.25,
            "position_scale_cap": 0.9,
            "daily_loss_cap_pct": 2.0,
            "fused_risk_pressure": 0.2,
        },
        now=datetime.now(timezone.utc),
    )
    assert out["max_trades_per_day"] == 5
    assert out["max_position_size"] == 0.03
