"""Holdout7 prod vs Gemini panel builder."""
from __future__ import annotations

from scripts.build_btrack_holdout7_gemini_vs_prod_panel_v1 import build_holdout7_panel


def test_build_holdout7_panel_synthetic() -> None:
    holdout = ["2026-04-02", "2026-04-08"]
    actual = {"2026-04-02": "bear", "2026-04-08": "bear"}
    prod = {
        "2026-04-02": {
            "eval_date": "2026-04-02",
            "instrument": "btc",
            "predicted_direction": "bull",
            "preliminary_direction": "bull",
            "confidence": 0.25,
            "lens_values": {"price": {"score": 0.26}},
        },
        "2026-04-08": {
            "eval_date": "2026-04-08",
            "instrument": "btc",
            "predicted_direction": "neutral",
            "preliminary_direction": "bull",
            "confidence": 0.12,
        },
    }
    gem = {
        "2026-04-02": {
            "eval_date": "2026-04-02",
            "instrument": "btc",
            "predicted_direction": "bull",
            "confidence": 0.42,
            "engine": "gemini_per_date_v1",
        },
        "2026-04-08": {
            "eval_date": "2026-04-08",
            "instrument": "btc",
            "predicted_direction": "bear",
            "confidence": 0.42,
            "engine": "gemini_per_date_v1",
        },
    }
    doc = build_holdout7_panel(
        holdout_dates=holdout,
        prod_by_date=prod,
        gemini_by_date=gem,
        actual_by_date=actual,
    )
    assert doc["schema"] == "btrack_holdout7_gemini_vs_prod_panel_v1"
    assert doc["summary"]["prod_n_wrong_direction"] == 1
    assert doc["summary"]["gemini_n_wrong_direction"] == 1
    assert doc["summary"]["both_bull_on_bear_day"] == 1
    assert doc["auto_promote"] is False


def test_holdout7_panel_latest_if_present() -> None:
    from pathlib import Path

    p = Path(__file__).resolve().parents[1] / "reports" / "btrack_holdout7_gemini_vs_prod_panel_v1_latest.json"
    if not p.is_file():
        return
    import json

    doc = json.loads(p.read_text(encoding="utf-8"))
    s = doc["summary"]
    assert s["n_holdout_days"] == 7
    assert s["prod_n_wrong_direction"] == 7
    assert s["gemini_n_wrong_direction"] == 7
