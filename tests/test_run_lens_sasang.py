from __future__ import annotations

from scripts import run_lens_sasang as mod


def test_sideways_mapping_emits_micro_tilt_when_heat_cold_separated() -> None:
    row = {
        "mapping_target": "sideways",
        "machine_readables": {
            "heat_proxy": 0.585,
            "cold_proxy": 0.415,
            "volatility_rarefaction_proxy": 0.48,
        },
    }
    score = mod._direction_from_mapping(row, "sideways")
    assert score > 0.0
    assert score <= 0.18


def test_b_track_axis_scores_v1_thermal_imbalance() -> None:
    row = {
        "machine_readables": {
            "heat_proxy": 0.7,
            "cold_proxy": 0.3,
            "volatility_rarefaction_proxy": 0.5,
        },
    }
    ax = mod._b_track_axis_scores_v1(row)
    assert ax["schema"] == "sasang_b_track_axis_scores_v1"
    assert ax["thermal_imbalance_proxy"] == 0.4
    assert ax["heat_proxy"] == 0.7


def test_confidence_boosted_for_clear_proxy_imbalance() -> None:
    row = {
        "machine_readables": {
            "heat_proxy": 0.585,
            "cold_proxy": 0.415,
            "volatility_rarefaction_proxy": 0.48,
        },
    }
    conf = mod._confidence_from_machine(row)
    assert conf >= 0.55
    assert conf <= 1.0
