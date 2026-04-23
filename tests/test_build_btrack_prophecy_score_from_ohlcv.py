"""Tests for build_btrack_prophecy_score_from_ohlcv (B-Track dawn score JSON)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_actual_direction_neutral_band() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _actual_direction

    assert _actual_direction(0.00001, 5.0) == "neutral"  # 1 bp
    assert _actual_direction(0.001, 5.0) == "bull"  # 10 bps


def test_row_pair_for_eval_date() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _row_pair_for_eval_date

    rows = [
        {"date": "2000-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-02", "close": 101.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    p, c = _row_pair_for_eval_date(rows, "2000-01-02")
    assert p["close"] == 100.0 and c["close"] == 101.0


def test_build_rows_kospi(tmp_path: Path) -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {
        "prediction": {"instrument": "kospi", "direction": "bull"},
    }
    kospi = [
        {"date": "2000-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-02", "close": 102.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    rows, meta = _build_rows(
        hypothesis=hyp,
        eval_date="2000-01-02",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bull",
    )
    assert not meta.get("warnings") or meta["warnings"] == []
    assert len(rows) == 1
    assert rows[0]["actual_direction"] == "bull"
    assert rows[0]["predicted_direction"] == "bull"


def test_hypothesis_fixture_smoke() -> None:
    p = ROOT / "docs" / "final" / "artifacts" / "btrack_hypothesis_prophecy_latest.json"
    if not p.is_file():
        pytest.skip("no hypothesis fixture")
    h = json.loads(p.read_text(encoding="utf-8"))
    assert h.get("schema") == "btrack_hypothesis_prophecy_v1"
    assert "prediction" in h


def test_manual_override_detection() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _is_manual_override_hypothesis

    assert _is_manual_override_hypothesis({"provenance": {"prompt_id": "manual_override_for_hit_rate_recovery_v1"}})
    assert not _is_manual_override_hypothesis({"provenance": {"prompt_id": "generate_btrack_hypothesis_prophecy_v1.py"}})


def test_bull_reversal_override_to_neutral() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2000-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-02", "close": 96.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-03", "close": 108.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-04", "close": 110.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2000-01-04",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        bull_reversal_lookback=1,
        bull_reversal_threshold_pct=5.0,
        bull_reversal_target="neutral",
    )
    assert len(rows) == 1
    assert rows[0]["predicted_direction"] == "neutral"


def test_bull_reversal_requires_positive_flow_when_enabled() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2000-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-02", "close": 90.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-03", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-04", "close": 101.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    flow_ctx = {"2000-01": {"foreign_net_buy": -10.0, "institution_net_buy": -10.0, "program_net_buy": -10.0}}
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2000-01-04",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        bull_reversal_lookback=1,
        bull_reversal_threshold_pct=5.0,
        bull_reversal_target="neutral",
        flow_ctx=flow_ctx,
        bull_reversal_require_flow=True,
        bull_reversal_min_flow_score=0.0,
    )
    assert len(rows) == 1
    assert rows[0]["predicted_direction"] == "bear"


def test_bull_reversal_blocked_by_shock_cutoff() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2000-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-02", "close": 80.0, "open": 1, "high": 1, "low": 1, "volume": 1},  # shock
        {"date": "2000-01-03", "close": 88.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-04", "close": 90.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2000-01-04",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        bull_reversal_lookback=1,
        bull_reversal_threshold_pct=5.0,
        bull_reversal_target="bull",
        bull_reversal_enable_shock_cutoff=True,
        bull_reversal_shock_cutoff_pct=8.0,
    )
    assert rows[0]["predicted_direction"] == "bear"


def test_bull_reversal_strong_flow_promotes_to_bull() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2000-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-02", "close": 90.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-03", "close": 99.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-04", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    flow_ctx = {"2000-01": {"foreign_net_buy": 10000.0, "institution_net_buy": 10000.0, "program_net_buy": 0.0}}
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2000-01-04",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        bull_reversal_lookback=1,
        bull_reversal_threshold_pct=5.0,
        bull_reversal_target="neutral",
        flow_ctx=flow_ctx,
        bull_reversal_require_flow=True,
        bull_reversal_min_flow_score=0.0,
        bull_reversal_strong_flow_threshold=3000.0,
        bull_reversal_strong_flow_target="bull",
    )
    assert rows[0]["predicted_direction"] == "bull"


def test_bear_relax_to_neutral_when_weak_drop_and_flow_ok() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2000-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-02", "close": 99.5, "open": 1, "high": 1, "low": 1, "volume": 1},  # -0.5%
        {"date": "2000-01-03", "close": 99.6, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    flow_ctx = {"2000-01": {"foreign_net_buy": 10.0, "institution_net_buy": 10.0, "program_net_buy": 0.0}}
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2000-01-03",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        bear_relax_enable=True,
        bear_relax_max_prev_drop_pct=1.5,
        bear_relax_min_flow_score=0.0,
        flow_ctx=flow_ctx,
    )
    assert rows[0]["predicted_direction"] == "neutral"


def test_bear_relax_blocked_by_high_recent_vol() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2000-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-02", "close": 110.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-03", "close": 99.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-04", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    flow_ctx = {"2000-01": {"foreign_net_buy": 100.0, "institution_net_buy": 100.0, "program_net_buy": 0.0}}
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2000-01-04",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        bear_relax_enable=True,
        bear_relax_max_prev_drop_pct=1.5,
        bear_relax_min_flow_score=0.0,
        bear_relax_require_non_shock=True,
        bear_relax_max_recent_abs_return_mean_pct=2.0,
        bear_relax_recent_vol_lookback=2,
        flow_ctx=flow_ctx,
    )
    assert rows[0]["predicted_direction"] == "bear"


def test_year_rebound_override_applies_for_configured_year() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2026-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2026-01-02", "close": 101.0, "open": 1, "high": 1, "low": 1, "volume": 1},  # +1.0%
        {"date": "2026-01-03", "close": 102.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    flow_ctx = {"2026-01": {"foreign_net_buy": 10.0, "institution_net_buy": 10.0, "program_net_buy": 0.0}}
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2026-01-03",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        flow_ctx=flow_ctx,
        year_rebound_overrides={2026: "bull"},
        year_rebound_min_prev_ret_pct=0.4,
        year_rebound_min_flow_score=0.0,
    )
    assert rows[0]["predicted_direction"] == "bull"


def test_year_rebound_override_blocked_by_recent_vol_filter() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2026-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2026-01-02", "close": 110.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2026-01-03", "close": 96.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2026-01-04", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    flow_ctx = {"2026-01": {"foreign_net_buy": 10.0, "institution_net_buy": 10.0, "program_net_buy": 0.0}}
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2026-01-04",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        flow_ctx=flow_ctx,
        year_rebound_overrides={2026: "bull"},
        year_rebound_min_prev_ret_pct=0.2,
        year_rebound_min_flow_score=0.0,
        year_rebound_max_recent_abs_return_mean_pct=2.0,
        year_rebound_recent_vol_lookback=2,
    )
    assert rows[0]["predicted_direction"] == "bear"


def test_year_rebound_override_blocked_by_down_stress_filter() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2026-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2026-01-02", "close": 94.0, "open": 1, "high": 1, "low": 1, "volume": 1},   # down
        {"date": "2026-01-03", "close": 90.0, "open": 1, "high": 1, "low": 1, "volume": 1},   # down
        {"date": "2026-01-04", "close": 88.0, "open": 1, "high": 1, "low": 1, "volume": 1},   # down
        {"date": "2026-01-05", "close": 89.0, "open": 1, "high": 1, "low": 1, "volume": 1},   # slight up
        {"date": "2026-01-06", "close": 90.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    flow_ctx = {"2026-01": {"foreign_net_buy": 5000.0, "institution_net_buy": 5000.0, "program_net_buy": 0.0}}
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2026-01-06",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        flow_ctx=flow_ctx,
        year_rebound_overrides={2026: "bull"},
        year_rebound_min_prev_ret_pct=0.2,
        year_rebound_min_prev2_ret_pct=-0.2,
        year_rebound_min_flow_score=0.0,
        year_rebound_down_stress_lookback=4,
        year_rebound_max_down_days=2,
        year_rebound_max_cum_down_pct=5.0,
    )
    assert rows[0]["predicted_direction"] == "bear"


def test_bull_reversal_blocked_by_down_guard() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2000-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-02", "close": 94.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-03", "close": 89.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-04", "close": 95.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2000-01-04",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        bull_reversal_lookback=1,
        bull_reversal_threshold_pct=5.0,
        bull_reversal_target="bull",
        bull_reversal_down_guard_enable=True,
        bull_reversal_down_guard_lookback=2,
        bull_reversal_down_guard_max_down_days=1,
        bull_reversal_down_guard_max_cum_down_pct=5.0,
    )
    assert rows[0]["predicted_direction"] == "bear"


def test_bull_reversal_down_guard_stress_only_not_blocked_when_not_stressed() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2000-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-02", "close": 94.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-03", "close": 99.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-04", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2000-01-04",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        bull_reversal_lookback=1,
        bull_reversal_threshold_pct=3.0,
        bull_reversal_target="bull",
        bull_reversal_down_guard_enable=True,
        bull_reversal_down_guard_mode="stress_only",
        bull_reversal_down_guard_lookback=2,
        bull_reversal_down_guard_max_down_days=1,
        bull_reversal_down_guard_max_cum_down_pct=5.0,
        bull_reversal_down_guard_shock_cutoff_pct=8.0,
        bull_reversal_down_guard_high_vol_pct=10.0,
    )
    assert rows[0]["predicted_direction"] == "bull"


def test_bull_reversal_two_stage_promotes_only_with_strict_conditions() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2000-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-02", "close": 95.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-03", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-04", "close": 101.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    flow_ctx = {"2000-01": {"foreign_net_buy": 10000.0, "institution_net_buy": 10000.0, "program_net_buy": 0.0}}
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2000-01-04",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        bull_reversal_lookback=1,
        bull_reversal_threshold_pct=3.0,
        bull_reversal_target="bull",
        bull_reversal_two_stage_enable=True,
        bull_reversal_bull_min_prev_ret_pct=0.5,
        bull_reversal_bull_min_flow_score=0.0,
        bull_reversal_bull_require_non_shock=True,
        bull_reversal_bull_max_recent_abs_return_mean_pct=10.0,
        bull_reversal_bull_recent_vol_lookback=2,
    )
    assert rows[0]["predicted_direction"] == "bull"


def test_year_default_override_sets_neutral_before_reversal() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2026-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2026-01-02", "close": 99.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2026-01-02",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        year_default_overrides={2026: "neutral"},
    )
    assert rows[0]["predicted_direction"] == "neutral"


def test_downside_force_bear_overrides_neutral_default() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {"prediction": {"instrument": "kospi", "direction": "bear"}}
    kospi = [
        {"date": "2026-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2026-01-02", "close": 98.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2026-01-03", "close": 95.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2026-01-04", "close": 94.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    rows, _meta = _build_rows(
        hypothesis=hyp,
        eval_date="2026-01-04",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bear",
        year_default_overrides={2026: "neutral"},
        downside_force_bear_enable=True,
        downside_force_bear_lookback=3,
        downside_force_bear_min_down_days=2,
        downside_force_bear_min_cum_down_pct=3.0,
    )
    assert rows[0]["predicted_direction"] == "bear"
