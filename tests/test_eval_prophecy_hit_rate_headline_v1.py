"""Headline instrument selection for price-mode hit rate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.eval_prophecy_hit_rate_v1 import _eval_price


def test_headline_auto_btc_excludes_kospi_rows(tmp_path: Path) -> None:
    score = {
        "inputs": {"hypothesis_instrument_declared": "btc", "force_dual_leg_panel": True},
        "rows": [
            {
                "instrument": "btc",
                "predicted_direction": "bear",
                "actual_direction": "bear",
            },
            {
                "instrument": "btc",
                "predicted_direction": "bear",
                "actual_direction": "bull",
            },
            {
                "instrument": "kospi",
                "predicted_direction": "bear",
                "actual_direction": "bear",
            },
            {
                "instrument": "kospi",
                "predicted_direction": "bear",
                "actual_direction": "bull",
            },
        ],
    }
    path = tmp_path / "score.json"
    path.write_text(json.dumps(score), encoding="utf-8")
    metrics, _meta = _eval_price(path, headline_instrument="auto")
    assert metrics["headline_instrument"] == "btc"
    assert metrics["price_directional_hit_rate"] == 0.5
    assert metrics["n_evaluated"] == 2
    assert metrics["pooled_price_directional_hit_rate"] == 0.5
    assert metrics["pooled_n_evaluated"] == 4


def test_directional_calls_only_excludes_neutral_predictions(tmp_path: Path) -> None:
    score = {
        "inputs": {"hypothesis_instrument_declared": "btc"},
        "rows": [
            {
                "instrument": "btc",
                "predicted_direction": "neutral",
                "actual_direction": "bull",
            },
            {
                "instrument": "btc",
                "predicted_direction": "bear",
                "actual_direction": "bear",
            },
            {
                "instrument": "btc",
                "predicted_direction": "bull",
                "actual_direction": "bear",
            },
        ],
    }
    path = tmp_path / "score.json"
    path.write_text(json.dumps(score), encoding="utf-8")
    metrics, _meta = _eval_price(path, headline_instrument="btc")
    assert metrics["price_directional_hit_rate"] == round(1 / 3, 6)
    assert metrics["n_evaluated"] == 3
    assert metrics["n_neutral_predictions"] == 1
    assert metrics["n_directional_calls"] == 2
    assert metrics["directional_call_hits"] == 1
    assert metrics["price_hit_rate_on_directional_calls"] == 0.5
