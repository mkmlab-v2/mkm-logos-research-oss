from __future__ import annotations

import pandas as pd

from scripts.run_btc_time_machine_fact_safe_backtest import BacktestConfig, run_backtest


def test_run_backtest_produces_samples_on_valid_close_series():
    df = pd.DataFrame({"close": [100 + i for i in range(80)]})
    cfg = BacktestConfig(warmup=20, horizon=3, stride=2, fee_bps_round_trip=8.0)
    out = run_backtest(df, cfg)
    assert out["sample_count"] > 0
    assert "net_return_pct" in out
    assert "win_rate" in out


def test_run_backtest_returns_zero_when_not_enough_data():
    df = pd.DataFrame({"close": [100, 101, 102]})
    cfg = BacktestConfig(warmup=20, horizon=3, stride=1, fee_bps_round_trip=8.0)
    out = run_backtest(df, cfg)
    assert out["sample_count"] == 0
