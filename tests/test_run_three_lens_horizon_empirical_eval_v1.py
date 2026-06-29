"""Three-lens horizon empirical eval smoke."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_horizon_labels_and_matrix() -> None:
    import scripts.run_three_lens_horizon_empirical_eval_v1 as mod

    closes = {
        "2026-01-02": 100.0,
        "2026-01-03": 101.0,
        "2026-01-06": 102.0,
        "2026-01-07": 100.0,
        "2026-01-08": 99.0,
        "2026-01-09": 98.0,
        "2026-01-10": 97.0,
        "2026-01-13": 96.0,
        "2026-01-14": 95.0,
        "2026-01-15": 94.0,
        "2026-01-16": 93.0,
        "2026-01-17": 92.0,
        "2026-01-20": 91.0,
        "2026-01-21": 90.0,
        "2026-01-22": 89.0,
        "2026-01-23": 88.0,
        "2026-01-24": 87.0,
        "2026-01-27": 86.0,
        "2026-01-28": 85.0,
        "2026-01-29": 84.0,
        "2026-01-30": 83.0,
        "2026-01-31": 82.0,
        "2026-02-03": 81.0,
        "2026-02-04": 80.0,
        "2026-02-05": 79.0,
    }
    days = sorted(closes)
    labels = mod._build_forward_labels(days, closes, neutral_bps=5.0)
    assert "2026-01-02" in labels
    assert set(labels["2026-01-02"]) >= {"short_1d", "mid_10d", "macro_21d"}

    scored = [
        {
            "lens_id": "sasang",
            "horizon": "short_1d",
            "outcome": "HIT",
        },
        {
            "lens_id": "sasang",
            "horizon": "macro_21d",
            "outcome": "FAIL",
        },
    ]
    matrix = mod._rate_matrix(scored)
    assert matrix["sasang"]["short_1d"]["directional_hit_rate"] == 1.0


def test_run_eval_kospi_smoke() -> None:
    import scripts.run_three_lens_horizon_empirical_eval_v1 as mod

    if not mod.KOSPI_CSV.is_file():
        pytest.skip("KOSPI CSV missing")
    doc = mod.run_eval(
        instrument="kospi",
        csv_path=mod.KOSPI_CSV,
        date_from="2026-02-01",
        date_to="2026-04-30",
        neutral_bps=5.0,
        neutral_band=0.06,
        myeongni_jsonl=mod.DEFAULT_MYEONGNI_JSONL,
        sasang_jsonl=mod.DEFAULT_SASANG_JSONL,
        logos_lens=mod.DEFAULT_LOGOS_LENS,
        panel_csv=mod.DEFAULT_PANEL,
        myeongni_momentum_window=5,
        min_n=5,
        min_soft_delta=0.03,
    )
    assert doc["schema"] == "three_lens_horizon_empirical_eval_v1"
    assert doc["research_only"] is True
    assert "rate_matrix" in doc
    assert "alignment_verdict" in doc
    assert doc["n_eval_dates"] >= 1
