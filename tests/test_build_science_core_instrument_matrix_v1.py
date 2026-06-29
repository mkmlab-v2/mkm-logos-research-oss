"""Tests for science_core_instrument_matrix_v1 builder."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_build_matrix_from_fixture(tmp_path: Path) -> None:
    from scripts.build_science_core_instrument_matrix_v1 import build_matrix

    gov = {
        "generated_at_utc": "2026-06-08T00:00:00Z",
        "window": {"from": "2026-01-01", "to": "2026-06-08"},
        "holdout": {"kospi_holdout_n": 18, "kospi_holdout_uplift_soft": 0.5555},
        "humanist_combo_holdout": {
            "n_eval_dates": 18,
            "short_1d_soft": {
                "science_core": 0.2778,
                "science_plus_sasang": 0.8333,
                "science_plus_myeongni": 0.3889,
                "science_plus_sasang_myeongni": 0.6944,
            },
            "triple_beats_sasang_on_holdout": False,
            "attach_eligible_short_1d_ranking": [{"lens_id": "science_plus_sasang"}],
        },
        "btc_holdout_auxiliary": {
            "n_eval_dates": 34,
            "short_1d_soft": {"science_core": 0.6029, "science_plus_sasang": 0.5882},
            "science_plus_sasang_uplift_vs_science_short_1d": -0.0147,
            "gates_primary_attach": False,
            "uplift_directional_parity_with_kospi": "divergent",
            "auxiliary_recommendation": "observe_only",
        },
        "composite_attach": {
            "composite_attach_recommended": True,
            "recommended_lane": "science_plus_sasang",
            "macro_blockers": ["macro_gate_low_entropy_binary"],
        },
        "promotion_gate": {"track_a_ready": False, "live_trading_ready": False},
        "pnl_economic_significance": {
            "holdout": {
                "science_core": {"total_return": -0.15},
                "science_plus_sasang": {"total_return": 0.5},
            },
            "economic_edge_claim_allowed": False,
        },
        "walkforward": {"selection_top1_hit_rate": 1.0, "mean_test_uplift_vs_science_alone": 0.28},
    }
    doc = build_matrix(governance=gov, attach_gate={"combo_backtest_ran": True, "recommended_lane": "science_plus_sasang"})
    assert doc["schema"] == "science_core_instrument_matrix_v1"
    assert doc["research_only"] is True
    assert doc["instrument_slices"]["kospi"]["role"] == "primary_attach"
    assert doc["instrument_slices"]["btc"]["gates_primary_attach"] is False
    assert doc["task_type_slices"]["compression_track_a"]["role"] == "out_of_scope_for_science_core_matrix"
    assert doc["global_final_action"]["track_a_ready"] is False
    assert doc["instrument_slices"]["kospi"]["lens_overlay"]["uplift_vs_science_short_1d_pp"] == pytest.approx(0.5555)


def test_build_matrix_merges_conditional_research() -> None:
    from scripts.build_science_core_instrument_matrix_v1 import build_matrix

    gov = {
        "generated_at_utc": "2026-06-08T00:00:00Z",
        "window": {"from": "2026-01-01", "to": "2026-06-08"},
        "holdout": {"kospi_holdout_uplift_soft": 0.5555},
        "humanist_combo_holdout": {
            "short_1d_soft": {"science_core": 0.28, "science_plus_sasang": 0.83},
        },
        "btc_holdout_auxiliary": {"short_1d_soft": {"science_core": 0.6, "science_plus_sasang": 0.59}},
        "composite_attach": {"composite_attach_recommended": True, "recommended_lane": "science_plus_sasang"},
        "promotion_gate": {"track_a_ready": False, "live_trading_ready": False},
    }
    cond = {
        "schema": "science_core_conditional_attach_research_v1",
        "generated_at_utc": "2026-06-08T12:00:00Z",
        "horizon_conditional_attach": {"recommended_hypothesis": "attach_sasang_on_short_1d_only"},
        "btc_divergence": {"hypotheses": [{"id": "btc_shock_calm_asymmetry", "summary_ko": "test"}]},
        "instrument_slices": {
            "kospi": {
                "holdout_horizon": {"horizon_attach_split_recommended": True, "uplift_gap_short_minus_mid_pp": 0.5},
                "shock_subset_short_1d": {"science_plus_sasang": {"uplift_vs_science_pp": 0.5}},
            },
            "btc": {
                "shock_subset_short_1d": {"science_plus_sasang": {"uplift_vs_science_pp": -0.08}},
                "holdout_horizon": {"short_1d": {"uplift_vs_science_pp": -0.01}},
            },
        },
        "final_action": {"action_id": "WATCH_CONDITIONAL_ATTACH_HYPOTHESES"},
    }
    doc = build_matrix(governance=gov, attach_gate=None, conditional_research=cond)
    assert doc.get("conditional_attach_research") is not None
    assert "Horizon/Shock subset" in doc["reporting_order"]
    assert doc["global_final_action"]["action_id"] == "WATCH_CONDITIONAL_ATTACH_HYPOTHESES"
    assert doc["instrument_slices"]["kospi"]["conditional_attach_research"]["shock_subset_sasang_uplift_pp"] == 0.5


def test_build_matrix_live_from_governance_if_present() -> None:
    from scripts.build_science_core_instrument_matrix_v1 import build_matrix, main

    gov_path = ROOT / "docs/final/artifacts/science_core_governance_bundle_v1_latest.json"
    if not gov_path.is_file():
        pytest.skip("governance bundle missing")
    gov = json.loads(gov_path.read_text(encoding="utf-8-sig"))
    doc = build_matrix(governance=gov, attach_gate=None)
    assert doc["field"]["field_id"] == "regime_science_core_v1_evaluation"
    assert "kospi" in doc["instrument_slices"]
    assert "btc" in doc["instrument_slices"]

    rc = main(["--governance-json", str(gov_path)])
    assert rc == 0
    out = ROOT / "docs/final/artifacts/science_core_instrument_matrix_v1_latest.json"
    assert out.is_file()
