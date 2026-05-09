"""Contract tests for market_myeongni overlay (no calendar core changes)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from scripts.market_myeongni_overlay_engine_v1 import (  # noqa: E402
    apply_market_myeongni_overlay,
    build_market_myeongni_lens_payload,
    load_overlay_policy,
)


def test_apply_overlay_scales_and_clamp() -> None:
    policy = {
        "schema": "market_myeongni_overlay_policy_v1",
        "direction_score_scale": 0.5,
        "confidence_scale": 0.8,
        "max_abs_direction_score": 0.3,
        "state_id_direction_tilt": {},
    }
    d, c, _ = apply_market_myeongni_overlay(
        base_direction=0.8,
        base_confidence=0.5,
        state_id=None,
        policy=policy,
    )
    assert d == pytest.approx(0.3)
    assert c == pytest.approx(0.4)


def test_state_id_tilt() -> None:
    policy = {
        "schema": "market_myeongni_overlay_policy_v1",
        "direction_score_scale": 1.0,
        "confidence_scale": 1.0,
        "max_abs_direction_score": 1.0,
        "state_id_direction_tilt": {"15": -0.05},
    }
    d, _, app = apply_market_myeongni_overlay(
        base_direction=0.1,
        base_confidence=0.9,
        state_id=15,
        policy=policy,
    )
    assert d == pytest.approx(0.05)
    assert app["state_id_direction_tilt_applied"] == pytest.approx(-0.05)


def test_build_payload_from_upstream() -> None:
    upstream = {
        "schema": "myeongni_independent_lens_v0",
        "lens_id": "myeongni",
        "scores": {"direction_score": 0.2, "confidence": 0.5},
        "myeongri_stream_outputs": {"state_id": 12},
    }
    policy_path = ROOT / "data" / "market_myeongni" / "market_myeongni_overlay_policy_v1.json"
    policy = load_overlay_policy(policy_path)
    out = build_market_myeongni_lens_payload(
        myeongni_lens_doc=upstream,
        policy=policy,
        policy_path=str(policy_path),
        source_input_path="/tmp/x.json",
    )
    assert out["schema"] == "market_myeongni_lens_v1"
    assert out["lens_id"] == "market_myeongni"
    assert "scores" in out
    assert out["overlay"]["base_direction_score"] == 0.2


def test_policy_file_loads() -> None:
    p = ROOT / "data" / "market_myeongni" / "market_myeongni_overlay_policy_v1.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc["schema"] == "market_myeongni_overlay_policy_v1"
