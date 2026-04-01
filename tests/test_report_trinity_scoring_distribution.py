from __future__ import annotations

from scripts import report_trinity_scoring_distribution as mod


def test_window_dual_regime_state_stats() -> None:
    rows = [
        {
            "hypothesis_metric": "KOSPI_D1_RETURN_PCT",
            "post_close_eval_decision": "HIT",
            "dual_regime_state_source": "risk_assessment.myeongni_state_id",
            "dual_regime_state_present": True,
            "dual_regime_state_clamp_count": 1,
        },
        {
            "hypothesis_metric": "KOSPI_D1_RETURN_PCT",
            "post_close_eval_decision": "NEUTRAL_DRAW",
            "dual_regime_state_source": "none",
            "dual_regime_state_present": False,
            "dual_regime_state_clamp_count": 0,
        },
        {
            "hypothesis_metric": "KOSPI_D1_RETURN_PCT",
            "post_close_eval_decision": "FAIL",
            "dual_regime_state_source": "risk_assessment.myeongni_state_id",
            "dual_regime_state_present": True,
            "dual_regime_state_clamp_count": 0,
        },
    ]
    out = mod._window_dual_regime_stats(rows)
    assert out["sample_size"] == 3
    assert out["state_id_present_count"] == 2
    assert out["clamp_count"] == 1
    assert out["top_source"] == "risk_assessment.myeongni_state_id"


def test_dual_regime_advisory_detects_unwired_state_signal() -> None:
    stats = {
        "sample_size": 10,
        "top_source": "none",
        "state_id_present_rate": 0.0,
        "clamp_rate": 0.0,
    }
    adv = mod._dual_regime_advisory(stats)
    assert adv["decision"] == "state_signal_not_wired"


def test_dual_regime_advisory_detects_high_clamp_mode() -> None:
    stats = {
        "sample_size": 10,
        "top_source": "risk_assessment.myeongni_state_id",
        "state_id_present_rate": 1.0,
        "clamp_rate": 0.7,
    }
    adv = mod._dual_regime_advisory(stats)
    assert adv["decision"] == "state_clamp_high_tight_mode"


def test_auto_hold_override_stats_group_by_trigger_and_priority() -> None:
    rows = [
        {"auto_hold_promotion": True, "override_trigger_type": "net_source_fallback", "override_priority": 100},
        {"auto_hold_promotion": True, "override_trigger_type": "dual_regime_state_clamp", "override_priority": 90},
        {"auto_hold_promotion": True, "override_trigger_type": "net_source_fallback", "override_priority": 100},
        {"auto_hold_promotion": False, "override_trigger_type": "net_source_fallback", "override_priority": 100},
    ]
    out = mod._auto_hold_override_stats(rows)
    assert out["count"] == 3
    assert out["top_trigger"] == "net_source_fallback"
    assert out["trigger_counts"]["net_source_fallback"] == 2
    assert out["trigger_counts"]["dual_regime_state_clamp"] == 1
    assert out["priority_counts"]["100"] == 2
    assert out["priority_counts"]["90"] == 1


def test_auto_hold_override_advisory_detects_net_source_skew() -> None:
    stats = {
        "count": 10,
        "top_trigger": "net_source_fallback",
        "trigger_counts": {"net_source_fallback": 8, "dual_regime_state_clamp": 2},
    }
    adv = mod._auto_hold_override_advisory(stats)
    assert adv["decision"] == "override_skew_net_source_fallback"


def test_auto_hold_override_advisory_detects_dual_regime_skew() -> None:
    stats = {
        "count": 10,
        "top_trigger": "dual_regime_state_clamp",
        "trigger_counts": {"dual_regime_state_clamp": 8, "net_source_fallback": 2},
    }
    adv = mod._auto_hold_override_advisory(stats)
    assert adv["decision"] == "override_skew_dual_regime_state_clamp"

