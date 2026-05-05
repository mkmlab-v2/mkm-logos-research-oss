from __future__ import annotations

from scripts.build_fragility_composite_v1 import evaluate_fragility


def _base_input() -> dict:
    return {
        "as_of_utc": "2026-05-04T00:00:00Z",
        "metrics": {
            "move": 112.0,
            "vix": 17.2,
            "hy_oas": 3.7,
            "dxy_vol": 0.104,
        },
        "baselines": {
            "move": {"median_156w": 112.0, "mad_156w": 8.0},
            "vix": {"median_156w": 17.2, "mad_156w": 2.2},
            "hy_oas": {"median_156w": 3.7, "mad_156w": 0.35},
            "dxy_vol": {"median_156w": 0.104, "mad_156w": 0.012},
        },
        "aux": {"hy_oas_4w_change_pct": 2.0, "hy_oas_4w_change_pct_p85": 9.0},
        "state_memory": {"red_active": False, "below66_streak": 0, "recent_gates": ["GREEN"], "red_streak": 0},
        "prev_state_4d": {"stress": 0.1, "liquidity": 0.1, "credit": 0.1, "currency": 0.1},
        "quaternion_history": [0.12, 0.18, 0.22, 0.25, 0.28, 0.33, 0.35, 0.39, 0.41, 0.44],
    }


def test_fragility_gate_green_with_baseline_inputs() -> None:
    out = evaluate_fragility(_base_input())
    assert out["validity"]["all_valid"] is True
    assert out["gate"] == "GREEN"
    assert out["score"]["scaled_0_100"] == 50.0


def test_fragility_hard_trigger_and_red() -> None:
    payload = _base_input()
    payload["metrics"]["move"] = 180.0
    payload["metrics"]["hy_oas"] = 6.5
    payload["metrics"]["vix"] = 32.0
    payload["aux"]["hy_oas_4w_change_pct"] = 14.0
    payload["aux"]["hy_oas_4w_change_pct_p85"] = 10.0

    out = evaluate_fragility(payload)
    assert out["gate"] == "RED"
    assert out["gate_details"]["hard_trigger"] is True


def test_fragility_outputs_quaternion_delta() -> None:
    out = evaluate_fragility(_base_input())
    assert "quaternion_delta" in out
    assert out["quaternion_delta"]["label"] in {"phase_shift_low", "phase_shift_mid", "phase_shift_high"}
    assert isinstance(out["quaternion_delta"]["magnitude"], float)
    assert "thresholds" in out["quaternion_delta"]
    assert out["quaternion_delta"]["thresholds"]["mode"] in {"rolling_quantile", "fallback_fixed"}
    assert "rolling_quantile_low" in out["quaternion_delta"]["thresholds"]


def test_fragility_red_hysteresis_hold() -> None:
    payload = _base_input()
    payload["state_memory"] = {
        "red_active": True,
        "below66_streak": 0,
        "recent_gates": ["RED", "RED", "AMBER"],
        "red_streak": 2,
    }
    out = evaluate_fragility(payload)
    assert out["gate"] == "RED"
    assert out["gate_details"]["hysteresis_hold_red"] is True
