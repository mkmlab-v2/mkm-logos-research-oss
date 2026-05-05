from __future__ import annotations

import json

from scripts.build_fragility_composite_v1 import evaluate_fragility


def test_custom_policy_changes_thresholds() -> None:
    payload = {
        "as_of_utc": "2026-05-04T00:00:00Z",
        "metrics": {"move": 126.0, "vix": 18.5, "hy_oas": 3.9, "dxy_vol": 0.118},
        "baselines": {
            "move": {"median_156w": 112.0, "mad_156w": 8.0},
            "vix": {"median_156w": 17.2, "mad_156w": 2.2},
            "hy_oas": {"median_156w": 3.7, "mad_156w": 0.35},
            "dxy_vol": {"median_156w": 0.104, "mad_156w": 0.012},
        },
        "aux": {"hy_oas_4w_change_pct": 5.0, "hy_oas_4w_change_pct_p85": 9.5},
        "state_memory": {"red_active": False, "below66_streak": 0, "recent_gates": ["GREEN"], "red_streak": 0},
        "prev_state_4d": {"stress": 0.1, "liquidity": 0.1, "credit": 0.1, "currency": 0.1},
        "quaternion_history": [0.1, 0.11, 0.12, 0.13, 0.15, 0.17, 0.18, 0.2, 0.21, 0.23],
    }
    policy = {
        "schema": "fragility_quaternion_threshold_policy_v1",
        "rolling_min_history_count": 5,
        "rolling_quantile_low": 0.5,
        "rolling_quantile_high": 0.7,
        "fallback_low_cut": 0.25,
        "fallback_high_cut": 0.4,
        "min_band_gap": 0.02,
    }
    out = evaluate_fragility(payload, policy_doc=policy)
    th = out["quaternion_delta"]["thresholds"]
    assert th["mode"] == "rolling_quantile"
    assert th["rolling_quantile_low"] == 0.5
    assert th["rolling_quantile_high"] == 0.7
