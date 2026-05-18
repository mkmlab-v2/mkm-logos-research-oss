"""Regression: per-leg hit decomposition for frozen batch score JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.compute_prophecy_hit_rate_leg_decomposition_v1 import (
    compute_decomposition,
    format_alert_lines,
)


def test_frozen_bear_matches_always_bear_baseline(tmp_path: Path) -> None:
    score = {
        "schema": "btrack_prophecy_score_v1",
        "eval_date": "2026-05-15",
        "neutral_bps": 5.0,
        "inputs": {"force_dual_leg_panel": True, "recent_trading_days": 30},
        "meta": {
            "batch_eval_dates": ["2026-05-14", "2026-05-15"],
            "frozen_prediction_note": "frozen",
        },
        "rows": [
            {
                "instrument": "btc",
                "eval_date": "2026-05-14",
                "predicted_direction": "bear",
                "actual_direction": "bear",
            },
            {
                "instrument": "btc",
                "eval_date": "2026-05-15",
                "predicted_direction": "bear",
                "actual_direction": "bull",
            },
            {
                "instrument": "kospi",
                "eval_date": "2026-05-14",
                "predicted_direction": "bear",
                "actual_direction": "bull",
            },
            {
                "instrument": "kospi",
                "eval_date": "2026-05-15",
                "predicted_direction": "bear",
                "actual_direction": "bear",
            },
        ],
    }
    path = tmp_path / "score.json"
    path.write_text(json.dumps(score), encoding="utf-8")
    out = compute_decomposition(path)
    btc = out["legs"]["btc"]
    assert btc["price_hits"] == 1
    assert btc["n_evaluated"] == 2
    assert btc["price_directional_hit_rate"] == 0.5
    assert btc["baselines"]["equals_always_frozen_direction"] is True
    pooled = out["legs"]["pooled"]
    assert pooled["n_evaluated"] == 4
    assert pooled["price_hits"] == 2
    assert pooled["price_directional_hit_rate"] == 0.5


def test_format_alert_lines_includes_alert_1b_status() -> None:
    decomp = {
        "headline_instrument": "btc",
        "scoring_mode": "per_date_direction_overrides",
        "legs": {
            "btc": {
                "available": True,
                "price_directional_hit_rate": 0.233333,
                "n_evaluated": 30,
                "price_hit_rate_on_directional_calls": 0.538462,
                "directional_call_hits": 7,
                "n_directional_calls": 13,
                "n_neutral_predictions": 17,
            },
            "pooled": {
                "available": True,
                "price_directional_hit_rate": 0.266667,
                "n_evaluated": 60,
                "baselines": {
                    "always_bear_if_directional": 0.33,
                    "always_bull_if_directional": 0.67,
                },
            },
        },
    }
    lines = format_alert_lines(
        decomp,
        0.50,
        min_promotion_rate=0.60,
        min_directional_rate=0.50,
        min_directional_calls=10,
    )
    joined = "\n".join(lines)
    assert "ALERT_1b" in joined
    assert "-> pass" in joined
    assert "informational only" in joined

    decomp_low_n = {
        **decomp,
        "legs": {
            **decomp["legs"],
            "btc": {**decomp["legs"]["btc"], "n_directional_calls": 5},
        },
    }
    lines2 = format_alert_lines(decomp_low_n, 0.50, min_directional_rate=0.50, min_directional_calls=10)
    assert any("insufficient_sample" in ln for ln in lines2)
