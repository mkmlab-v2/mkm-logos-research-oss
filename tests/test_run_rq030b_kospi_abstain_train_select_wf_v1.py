# -*- coding: utf-8
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from scripts.run_rq030b_kospi_abstain_train_select_wf_v1 import select_best_grid_on_train  # noqa: E402


def test_select_best_grid_on_train_picks_highest_hr() -> None:
    rows = [
        {"eval_date": "2026-01-02", "predicted_direction": "bull", "confidence": 0.5, "weighted_score": 0.2},
        {"eval_date": "2026-01-03", "predicted_direction": "bear", "confidence": 0.5, "weighted_score": -0.2},
        {"eval_date": "2026-01-06", "predicted_direction": "bull", "confidence": 0.05, "weighted_score": 0.1},
    ]
    actuals = {"2026-01-02": "bull", "2026-01-03": "bear", "2026-01-06": "bull"}
    sel = select_best_grid_on_train(
        rows,
        actuals,
        ["2026-01-02", "2026-01-03", "2026-01-06"],
        min_call_rate=0.20,
        min_directional_calls=2,
    )
    assert sel["selection_status"] == "train_grid_max_hr"
    assert sel["grid_id"] == "abstain_c0.00_m0.00"


def test_select_best_grid_on_train_fallback_when_no_candidate() -> None:
    rows = [
        {"eval_date": "2026-01-02", "predicted_direction": "neutral", "confidence": 0.9, "weighted_score": 0.5},
    ]
    actuals = {"2026-01-02": "bull"}
    sel = select_best_grid_on_train(
        rows,
        actuals,
        ["2026-01-02"],
        min_call_rate=0.20,
        min_directional_calls=8,
    )
    assert sel["grid_id"] == "fallback_per_date_full"
