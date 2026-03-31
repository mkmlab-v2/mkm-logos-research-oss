from scripts.build_fact_safe_multilens_brief import (
    compute_reliability_badge,
    resolve_gate_decision,
)


def test_reliability_badge_low_on_approx_engine():
    out = compute_reliability_badge(engine_id="V1_Approx_Stub", samples=100, net_delta=5.0)
    assert out.badge == "LOW"
    assert out.decision == "HOLD"


def test_reliability_badge_mid_on_precision_and_mid_samples():
    out = compute_reliability_badge(engine_id="V2_Precision_MCP", samples=25, net_delta=-2.0)
    assert out.badge == "MID"
    assert out.decision == "PASS"


def test_reliability_badge_high_on_precision_positive_delta():
    out = compute_reliability_badge(engine_id="V2_Precision_MCP", samples=70, net_delta=0.1)
    assert out.badge == "HIGH"
    assert out.decision == "PASS"


def test_reliability_badge_low_on_small_samples_even_precision():
    out = compute_reliability_badge(engine_id="V2_Precision_MCP", samples=1, net_delta=1.0)
    assert out.badge == "LOW"
    assert out.decision == "HOLD"


def test_gate_reason_low_forces_hold():
    badge = compute_reliability_badge(engine_id="V2_Precision_MCP", samples=1, net_delta=1.0)
    gate = resolve_gate_decision(badge, "PASS")
    assert gate.decision == "HOLD"
    assert gate.reason == "low_badge_forced_hold"


def test_gate_reason_monthly_check_when_not_low():
    badge = compute_reliability_badge(engine_id="V2_Precision_MCP", samples=20, net_delta=0.0)
    gate = resolve_gate_decision(badge, "HOLD")
    assert gate.decision == "HOLD"
    assert gate.reason == "monthly_check_gate"
