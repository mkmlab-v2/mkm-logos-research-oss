"""Promotion readiness tracker smoke."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_readiness_from_fixtures() -> None:
    import scripts.build_kospi_june2026_promotion_readiness_v1 as mod

    compare = {
        "candidate_id": "v2_lens3_heavy",
        "n_trading_days": 22,
        "june_forward_eval": {"active": {"n_scored": 3}},
        "backtest_delta": {"soft_hit_rate_delta_candidate_minus_active": 0.0464},
        "promotion_recommendation": {
            "ready_for_apply_review": False,
            "blockers": ["human_signoff_required", "june_forward_n_scored<15"],
            "apply_command": "py scripts/run_kospi_june2026_prophecy_evolution_v1.py --apply-approved --apply-candidate-id v2_lens3_heavy",
        },
        "walkforward_prefilter": {
            "selection_top1_hit_rate": 0.48,
            "min_selection_top1_hit_rate": 0.52,
            "walkforward_gate_pass": False,
            "candidate_in_top2": True,
        },
    }
    rules = {
        "weight_candidate_policy": {
            "policy_tier": "recommended_strict_v1",
            "june_forward_min_scored_for_promotion": 15,
            "min_backtest_soft_delta_vs_active": 0.06,
            "min_walkforward_selection_top1_hit_rate": 0.52,
            "promotion_requires_human_signoff": True,
        }
    }
    eval_doc = {
        "n_scored": 3,
        "rows": [{"session_date": "2026-06-02", "actual_direction": "bull"}],
        "missing_ohlcv_trading_days": ["2026-06-03", "2026-06-04"],
    }
    out = mod.build_readiness(year_month="2026-06", compare_doc=compare, eval_doc=eval_doc, rules=rules)
    assert out["forward_scoring"]["remaining_to_gate"] == 12
    assert out["forward_scoring"]["unscored_eligible_trading_days"] >= 12
    assert out["forward_scoring"]["projected_trading_days_to_gate"] == 12
    assert out["forward_scoring"].get("projected_gate_session_date") is not None
    assert out["forward_scoring"].get("gate_reachable_in_month") is True
    assert out["policy_tier"] == "recommended_strict_v1"
    assert out["gates"]["backtest_soft_delta"]["pass"] is False
    assert out["gates"]["june_forward_n_scored"]["pass"] is False
    assert out["gates"]["walkforward_prefilter"]["pass"] is False


def test_build_readiness_applied_state() -> None:
    import scripts.build_kospi_june2026_promotion_readiness_v1 as mod

    compare = {
        "candidate_id": "v2_lens3_heavy",
        "n_trading_days": 22,
        "active_weights": {
            "session_myeongni": 0.3,
            "myeongni_independent": 0.22,
            "sasang": 0.24,
            "macro": 0.24,
        },
        "candidate_weights": {
            "session_myeongni": 0.3,
            "myeongni_independent": 0.22,
            "sasang": 0.24,
            "macro": 0.24,
        },
        "june_forward_eval": {"active": {"n_scored": 4}},
        "backtest_delta": {"soft_hit_rate_delta_candidate_minus_active": 0.0},
        "forward_gate_via": "proxy_2026-05",
        "effective_weight_candidate_policy": {"policy_tier": "recommended_pragmatic_v1", "_relaxation_active": True},
        "weight_apply_status": {
            "candidate_already_applied": True,
            "last_candidate_apply_at_utc": "2026-06-05T09:36:55Z",
            "apply_state_ko": "가중치 적용 완료 — June 포워드 누적 모니터링",
        },
        "promotion_recommendation": {
            "ready_for_apply_review": False,
            "blockers": [],
            "candidate_already_applied": True,
        },
        "walkforward_prefilter": {"walkforward_gate_pass": True, "candidate_in_top2": True},
    }
    rules = {
        "last_candidate_apply_id": "v2_lens3_heavy",
        "last_candidate_apply_at_utc": "2026-06-05T09:36:55Z",
        "weight_candidate_policy": {"promotion_requires_human_signoff": True},
    }
    eval_doc = {"n_scored": 4, "rows": [], "missing_ohlcv_trading_days": ["2026-06-03"]}
    out = mod.build_readiness(year_month="2026-06", compare_doc=compare, eval_doc=eval_doc, rules=rules)
    assert out["candidate_already_applied"] is True
    assert out["blockers"] == []
    assert out["gates"]["human_signoff"]["pass"] is True
    assert out["gates"]["backtest_soft_delta"]["pass"] is True
    assert out["ready_for_apply_review"] is False
    assert "적용 완료" in out["verdict_ko"]


def test_macro_risk_coverage_counts() -> None:
    import scripts.run_three_lens_horizon_empirical_eval_v2 as mod

    rows = {
        "2026-01-02": {
            "variants": {
                "logos_macro_risk_causal": {"signal_source": "trailing_fallback"},
            }
        },
        "2026-06-01": {
            "variants": {
                "logos_macro_risk_causal": {
                    "signal_source": "operational_causal",
                    "first_causal_gate_day": "2026-05-04",
                },
            }
        },
    }
    cov = mod._macro_risk_coverage(rows)
    assert cov["by_signal_source"]["trailing_fallback"] == 1
    assert cov["by_signal_source"]["operational_causal"] == 1
