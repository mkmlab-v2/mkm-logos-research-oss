# -*- coding: utf-8
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from scripts.run_rq030_kospi_per_date_abstain_wf_sweep_v1 import (  # noqa: E402
    apply_abstain_filter,
    pick_best_honest,
    score_abstain_pairs,
)


def test_apply_abstain_filter_abstains_on_low_confidence() -> None:
    row = {
        "predicted_direction": "bull",
        "confidence": 0.17,
        "weighted_score": 0.30,
    }
    assert apply_abstain_filter(row, min_confidence=0.18, min_abs_margin=0.0) is None
    assert apply_abstain_filter(row, min_confidence=0.15, min_abs_margin=0.0) == "bull"


def test_apply_abstain_filter_abstains_on_low_margin() -> None:
    row = {
        "predicted_direction": "bear",
        "confidence": 0.40,
        "weighted_score": 0.08,
    }
    assert apply_abstain_filter(row, min_confidence=0.0, min_abs_margin=0.10) is None
    assert apply_abstain_filter(row, min_confidence=0.0, min_abs_margin=0.05) == "bear"


def test_score_abstain_pairs_call_rate() -> None:
    rows = [
        {"eval_date": "2026-01-02", "predicted_direction": "bull", "confidence": 0.5, "weighted_score": 0.2},
        {"eval_date": "2026-01-03", "predicted_direction": "bear", "confidence": 0.1, "weighted_score": 0.3},
    ]
    actuals = {"2026-01-02": "bull", "2026-01-03": "bull"}
    m = score_abstain_pairs(
        rows,
        actuals,
        ["2026-01-02", "2026-01-03"],
        min_confidence=0.18,
        min_abs_margin=0.0,
    )
    assert m["n_panel_days"] == 2
    assert m["n_abstain"] == 1
    assert m["call_rate"] == 0.5
    assert m["directional_hit_rate"] == 1.0


def test_pick_best_honest_requires_call_rate_floor() -> None:
    sweep = [
        {"grid_id": "a", "pooled_test_directional_hit_rate": 0.70, "pooled_call_rate": 0.10},
        {"grid_id": "b", "pooled_test_directional_hit_rate": 0.66, "pooled_call_rate": 0.40},
    ]
    best = pick_best_honest(sweep, majority_pooled=0.632, min_call_rate=0.25)
    assert best is not None
    assert best["grid_id"] == "b"
