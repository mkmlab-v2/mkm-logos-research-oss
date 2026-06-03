"""Tests for KOSPI overnight price overlay (Phase B [HYPO])."""

from __future__ import annotations

from scripts.kospi_overnight_price_overlay_v1 import (
    apply_kospi_overnight_price_overlay,
    compute_overnight_price_scores,
)


def test_compute_overnight_risk_off_scores():
    doc = {
        "schema": "global_market_overnight_signals_v1",
        "composite_tilt": "risk_off_overnight",
        "indices": [
            {"id": "dow", "change_pct": -1.2},
            {"id": "nasdaq", "change_pct": -1.5},
            {"id": "nikkei225", "change_pct": -0.8},
        ],
    }
    ovn = compute_overnight_price_scores(doc)
    assert ovn["present"] is True
    assert ovn["blended_overnight_score"] < 0


def test_apply_overlay_pulls_bullish_domestic_toward_bear():
    overnight = {
        "schema": "global_market_overnight_signals_v1",
        "composite_tilt": "risk_off_overnight",
        "indices": [
            {"id": "dow", "change_pct": -1.8},
            {"id": "nasdaq", "change_pct": -2.0},
            {"id": "sp500", "change_pct": -1.5},
            {"id": "nikkei225", "change_pct": -1.0},
        ],
    }
    new_score, _conf, meta = apply_kospi_overnight_price_overlay(
        0.91,
        0.62,
        {"source": "kospi_csv"},
        overnight_doc=overnight,
    )
    assert meta["kospi_overnight_overlay"]["applied"] is True
    assert new_score < 0.91
