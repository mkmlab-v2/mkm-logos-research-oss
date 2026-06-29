"""Tests for science_core_prophecy_combo_sensitivity_v1."""
from __future__ import annotations

from scripts.run_science_core_prophecy_combo_sensitivity_v1 import build_sensitivity_summary


def test_build_sensitivity_summary_extracts_lane() -> None:
    backtest = {
        "fee_sensitivity": [
            {
                "fee_bps": 5.0,
                "ranked_strategies": [
                    {
                        "strategy_id": "science+sasang",
                        "metrics": {"total_return": 0.5, "cagr": 1.2, "sharpe": 2.0, "n_active_days": 10},
                    },
                    {"strategy_id": "science", "metrics": {"total_return": -0.1, "cagr": -0.2}},
                ],
                "best_strategy": {"strategy_id": "science+sasang", "metrics": {"total_return": 0.5}},
            },
            {
                "fee_bps": 20.0,
                "ranked_strategies": [
                    {
                        "strategy_id": "science+sasang",
                        "metrics": {"total_return": 0.3, "cagr": 0.8, "sharpe": 1.5, "n_active_days": 10},
                    },
                ],
                "best_strategy": {"strategy_id": "science+sasang", "metrics": {"total_return": 0.3}},
            },
        ]
    }
    doc = build_sensitivity_summary(
        backtest=backtest,
        recommended_lane="science_plus_sasang",
        fee_grid=[5.0, 20.0],
    )
    assert doc["recommended_lane_strategy_id"] == "science+sasang"
    assert len(doc["fee_sensitivity_rows"]) == 2
    assert doc["robust_positive_return_up_to_20bps"] is True
    assert doc["headline_claim_allowed"] is False
