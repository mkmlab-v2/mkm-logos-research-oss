"""Tests for internal KOSPI brief hypothesis sync."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_internal_kospi_morning_brief_onepager_v1 import _resolve_action_with_hypothesis


def test_bear_hypothesis_downgrades_go_conditional():
    action, conf, block = _resolve_action_with_hypothesis(
        governance_confidence=82,
        krx_open=True,
        dual_leg={"legs": {"kospi": {"price_directional_hit_rate": 0.233333, "n_evaluated": 30}}},
        hypothesis={
            "prediction": {"instrument": "kospi", "direction": "bear", "confidence": 0.12},
            "runtime_meta": {
                "weighted_score": -0.109,
                "price_meta": {
                    "kospi_overnight_overlay": {
                        "applied": True,
                        "composite_tilt": "risk_off_overnight",
                        "price_score_after_blend": -0.08,
                    }
                },
            },
        },
    )
    assert action == "WATCH"
    assert conf <= 42
    assert block["direction"] == "bear"
    assert block["hit_rate_gate_applied"] is True
