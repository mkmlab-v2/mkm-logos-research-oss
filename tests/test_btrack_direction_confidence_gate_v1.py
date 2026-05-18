"""Min-confidence direction gate for B-track hypothesis ensemble."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.btrack_direction_confidence_gate_v1 import (
    apply_min_direction_confidence_gate,
    min_direction_confidence_threshold,
)


def test_bear_below_threshold_becomes_neutral() -> None:
    direction, confidence, meta = apply_min_direction_confidence_gate(
        "bear", 0.18, rules={"min_direction_confidence": 0.25}
    )
    assert direction == "neutral"
    assert meta["applied"] is True
    assert meta["prior_direction"] == "bear"


def test_bear_at_threshold_stays_bear() -> None:
    direction, _, meta = apply_min_direction_confidence_gate(
        "bear", 0.25, rules={"min_direction_confidence": 0.25}
    )
    assert direction == "bear"
    assert meta["applied"] is False


def test_env_overrides_rules(monkeypatch) -> None:
    monkeypatch.setenv("MKM_BTRACK_MIN_DIRECTION_CONFIDENCE", "0.40")
    assert min_direction_confidence_threshold({"min_direction_confidence": 0.25}) == 0.40
    monkeypatch.delenv("MKM_BTRACK_MIN_DIRECTION_CONFIDENCE", raising=False)
