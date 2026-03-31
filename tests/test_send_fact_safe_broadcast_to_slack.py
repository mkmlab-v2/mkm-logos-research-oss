from scripts.send_fact_safe_broadcast_to_slack import build_slack_text


def test_build_slack_text_contains_core_fields():
    payload = {
        "ts_utc": "2026-03-31T05:34:07Z",
        "reliability_badge": "LOW",
        "high_reliability_decision": "HOLD",
        "gate_reason": "low_badge_forced_hold",
        "net": "21.41",
        "history_samples": "12",
        "history_net_delta": "-0.3",
        "overlap_drift_alert": False,
        "overlap_drift_alert_threshold": -0.05,
    }
    text = build_slack_text(payload)
    assert "Fact-Safe Monthly Broadcast" in text
    assert "reliability_badge: LOW" in text
    assert "high_reliability_decision: HOLD" in text
    assert "gate_reason: low_badge_forced_hold" in text
