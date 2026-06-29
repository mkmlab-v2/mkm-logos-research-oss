from __future__ import annotations

from scripts.build_commander_telegram_advanced_briefing_v1 import _leg_hit_rate_last_n_trading_days


def test_leg_hit_rate_last_n_trading_days_rolling():
    doc = {
        "rows": [
            {"instrument": "kospi", "eval_date": "2026-05-26", "predicted_direction": "bull", "actual_direction": "bull"},
            {"instrument": "kospi", "eval_date": "2026-05-27", "predicted_direction": "bull", "actual_direction": "bull"},
            {"instrument": "kospi", "eval_date": "2026-05-28", "predicted_direction": "bull", "actual_direction": "bear"},
            {"instrument": "kospi", "eval_date": "2026-05-29", "predicted_direction": "bull", "actual_direction": "bull"},
            {"instrument": "btc", "eval_date": "2026-05-29", "predicted_direction": "bear", "actual_direction": "bear"},
        ]
    }
    rate, n = _leg_hit_rate_last_n_trading_days(doc, "kospi", n_days=7)
    assert n == 4
    assert rate == 0.75
