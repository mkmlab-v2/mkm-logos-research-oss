from scripts.run_btc_time_machine_backtest_sweep import _score


def test_score_prefers_better_net_pf_and_support():
    a = {"sample_count": 100, "net_return_pct": 2.0, "profit_factor": 1.1, "win_rate": 0.45}
    b = {"sample_count": 300, "net_return_pct": 3.0, "profit_factor": 1.2, "win_rate": 0.5}
    assert _score(b) > _score(a)
