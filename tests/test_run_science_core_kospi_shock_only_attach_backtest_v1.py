"""Tests for science_core_kospi_shock_only_attach_backtest_v1."""
from __future__ import annotations

from scripts.run_science_core_kospi_shock_only_attach_backtest_v1 import (
    POLICY_IDS,
    _eval_soft_policies,
    _pick_lens,
    _soft_metrics,
)


def test_pick_lens_shock_only() -> None:
    assert _pick_lens("shock_only_attach", is_shock=True) == "science_plus_sasang"
    assert _pick_lens("shock_only_attach", is_shock=False) == "science_core"
    assert _pick_lens("always_science_core", is_shock=True) == "science_core"


def test_soft_metrics_mixed_outcomes() -> None:
    m = _soft_metrics(["HIT", "FAIL", "NEUTRAL_DRAW", "HIT"])
    assert m["n_scored"] == 4
    assert m["soft_hit_rate"] == 0.625
    assert m["directional_hit_rate"] == 0.6667


def test_eval_soft_policies_synthetic() -> None:
    daily = [
        {
            "session_date": "2026-05-01",
            "forward_return_bps": 150.0,
            "outcomes_short_1d": {
                "science_core": "FAIL",
                "science_plus_sasang": "HIT",
            },
        },
        {
            "session_date": "2026-05-02",
            "forward_return_bps": 20.0,
            "outcomes_short_1d": {
                "science_core": "HIT",
                "science_plus_sasang": "FAIL",
            },
        },
    ]
    block = _eval_soft_policies(daily, shock_bps=100.0)
    assert set(block["policies"].keys()) == set(POLICY_IDS)
    shock = block["policies"]["shock_only_attach"]
    assert shock["soft_hit_rate"] == 1.0
    always_sas = block["policies"]["always_science_plus_sasang"]
    assert always_sas["soft_hit_rate"] == 0.5


def test_main_live_if_data_present() -> None:
    from pathlib import Path

    from scripts.run_science_core_kospi_shock_only_attach_backtest_v1 import main

    root = Path(__file__).resolve().parents[1]
    sasang = root / "reports/btrack_market_sasang_per_date_v1.jsonl"
    kospi_sci = root / "reports/btrack_science_core_per_date_kospi_v1.jsonl"
    if not sasang.is_file() or not kospi_sci.is_file():
        return
    assert main(["--date-to", "2026-06-12"]) == 0
