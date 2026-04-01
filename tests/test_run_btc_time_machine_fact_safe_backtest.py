from __future__ import annotations

import pandas as pd

from scripts.run_btc_time_machine_fact_safe_backtest import BacktestConfig, run_backtest


def test_run_backtest_produces_samples_on_valid_close_series():
    df = pd.DataFrame({"close": [100 + i for i in range(80)]})
    cfg = BacktestConfig(
        warmup=20,
        horizon=3,
        stride=2,
        fee_bps_round_trip=8.0,
        slippage_bps_round_trip=5.0,
        max_position_fraction=0.2,
        daily_loss_cap_pct=1.5,
        skip_if_vol_shock_pct=8.0,
    )
    out = run_backtest(df, cfg)
    assert out["sample_count"] > 0
    assert "net_return_pct" in out
    assert "win_rate" in out
    assert "max_drawdown_pct" in out
    assert "max_loss_streak" in out


def test_run_backtest_returns_zero_when_not_enough_data():
    df = pd.DataFrame({"close": [100, 101, 102]})
    cfg = BacktestConfig(warmup=20, horizon=3, stride=1, fee_bps_round_trip=8.0)
    out = run_backtest(df, cfg)
    assert out["sample_count"] == 0


def test_run_backtest_applies_vol_shock_skip():
    closes = [100.0] * 30 + [200.0, 80.0, 190.0, 85.0, 180.0, 90.0, 170.0, 95.0]
    df = pd.DataFrame({"close": closes})
    cfg = BacktestConfig(
        warmup=20,
        horizon=1,
        stride=1,
        fee_bps_round_trip=8.0,
        skip_if_vol_shock_pct=5.0,
    )
    out = run_backtest(df, cfg)
    assert out["skipped_vol_shock"] > 0
