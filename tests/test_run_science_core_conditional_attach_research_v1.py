"""Tests for science_core_conditional_attach_research_v1."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_build_research_bundle_schema() -> None:
    from scripts.run_science_core_conditional_attach_research_v1 import build_research_bundle

    gov = {
        "holdout": {"recommended_combo": "science_plus_sasang"},
        "humanist_combo_holdout": {"short_1d_soft": {"science_plus_sasang": 0.8333}},
        "triple_blend_weight_sweep": {
            "best_holdout_profile": "sci45_sa100",
            "best_holdout_triple_soft": 0.8864,
            "any_triple_beats_sasang_combo_on_holdout": True,
        },
    }
    btc_long = {
        "eras": {
            "bundle_window_market_sasang": {
                "lenses": {
                    "science_core": {"soft_hit_rate": 0.5411},
                    "science_plus_sasang": {"soft_hit_rate": 0.5285},
                }
            }
        }
    }
    kospi_stub = {
        "holdout_horizon": {
            "short_1d": {"uplift_vs_science_pp": 0.5555, "conditional_attach_hint": True},
            "mid_5d": {"uplift_vs_science_pp": 0.0556, "conditional_attach_hint": False},
            "horizon_attach_split_recommended": True,
        },
        "shock_subset_short_1d": {"science_plus_sasang": {"uplift_vs_science_pp": 0.45}},
        "calm_subset_short_1d": {"science_plus_sasang": {"uplift_vs_science_pp": 0.6}},
    }
    btc_stub = {
        "holdout_horizon": {
            "short_1d": {"uplift_vs_science_pp": -0.0147, "conditional_attach_hint": False},
            "mid_5d": {"uplift_vs_science_pp": 0.01, "conditional_attach_hint": False},
        },
        "shock_subset_short_1d": {"science_plus_sasang": {"uplift_vs_science_pp": 0.1}},
        "calm_subset_short_1d": {"science_plus_sasang": {"uplift_vs_science_pp": -0.05}},
    }

    # Patch via manual assembly using internal helpers
    from scripts.run_science_core_conditional_attach_research_v1 import (
        _btc_divergence_diagnosis,
        _horizon_slice,
        _triple_blend_policy,
    )

    div = _btc_divergence_diagnosis(kospi_stub, btc_stub, btc_long_window=btc_long)
    assert div["parity_label"] == "divergent"
    assert len(div["hypotheses"]) >= 1

    triple = _triple_blend_policy(gov)
    assert triple["attach_policy_recommendation"] == "keep_fixed_science_plus_sasang"
    assert triple["weight_beats_fixed_on_holdout"] is True

    matrix = {
        "science_core": {"short_1d": {"soft_hit_rate": 0.28, "n_scored": 18}, "mid_5d": {"soft_hit_rate": 0.39, "n_scored": 18}},
        "science_plus_sasang": {"short_1d": {"soft_hit_rate": 0.83, "n_scored": 18}, "mid_5d": {"soft_hit_rate": 0.40, "n_scored": 18}},
    }
    short = _horizon_slice(matrix, "short_1d")
    mid = _horizon_slice(matrix, "mid_5d")
    assert short["conditional_attach_hint"] is True
    assert mid["conditional_attach_hint"] is False


def test_main_live_if_data_present() -> None:
    from scripts.run_science_core_conditional_attach_research_v1 import main

    sasang = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
    kospi_sci = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"
    if not sasang.is_file() or not kospi_sci.is_file():
        pytest.skip("science core lane data missing")
    rc = main([])
    assert rc == 0
    out = ROOT / "docs/final/artifacts/science_core_conditional_attach_research_v1_latest.json"
    assert out.is_file()
