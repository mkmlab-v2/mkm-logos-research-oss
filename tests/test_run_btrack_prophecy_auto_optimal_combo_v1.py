"""Auto optimal combo orchestrator ranking helpers."""
from __future__ import annotations

from scripts.run_btrack_prophecy_auto_optimal_combo_v1 import (
    _candidates_from_lens_combo,
    _implied_all_row,
    _pick_best,
)


def test_implied_all_row() -> None:
    assert _implied_all_row(0.5, 10, 20) == 0.25


def test_pick_best_ensemble() -> None:
    doc = {
        "ranked_strategies": [
            {
                "strategy_id": "a",
                "metrics": {"n_days": 30, "n_active_days": 20, "directional_hit_rate_active": 0.5},
            }
        ]
    }
    cands = _candidates_from_lens_combo(doc, window="30")
    best = _pick_best(
        [
            {
                "candidate_type": "ensemble_profile_rebuild",
                "window": "30",
                "price_directional_hit_rate": 0.4,
            },
            {
                "candidate_type": "ensemble_profile_rebuild",
                "window": "30",
                "price_directional_hit_rate": 0.45,
            },
        ],
        ctype="ensemble_profile_rebuild",
        window="30",
    )
    assert best is not None
    assert best["price_directional_hit_rate"] == 0.45
    assert cands[0]["implied_all_row_hit_rate"] == round(0.5 * 20 / 30, 6)
