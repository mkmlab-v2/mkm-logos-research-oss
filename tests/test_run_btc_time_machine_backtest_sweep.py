from scripts.run_btc_time_machine_backtest_sweep import (
    DEFAULT_PERIODS,
    _parse_periods_spec,
    _score,
)


def test_default_periods_include_10y_and_15y_windows():
    labels = [f"{a}..{b}" for a, b in DEFAULT_PERIODS]
    assert "2016-01-01..2025-12-31" in labels
    assert "2011-01-01..2025-12-31" in labels


def test_parse_periods_spec():
    got = _parse_periods_spec("2020-01-01:2020-12-31 , 2021-01-01:2021-06-30")
    assert got == [("2020-01-01", "2020-12-31"), ("2021-01-01", "2021-06-30")]


def test_score_prefers_better_net_pf_and_support():
    a = {
        "sample_count": 100,
        "net_return_pct": 2.0,
        "profit_factor": 1.1,
        "win_rate": 0.45,
        "max_drawdown_pct": 15.0,
        "max_loss_streak": 8,
    }
    b = {
        "sample_count": 300,
        "net_return_pct": 3.0,
        "profit_factor": 1.2,
        "win_rate": 0.5,
        "max_drawdown_pct": 8.0,
        "max_loss_streak": 4,
    }
    assert _score(b) > _score(a)
