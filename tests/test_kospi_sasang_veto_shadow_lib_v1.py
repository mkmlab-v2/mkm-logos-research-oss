"""Tests for sasang veto shadow lib."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.kospi_sasang_veto_shadow_lib_v1 import apply_sasang_veto_to_lenses, veto_for_sasang_row


def test_apply_veto_forces_sasang_neutral():
    lenses = {"sasang": {"direction": "bull", "score": 0.17, "loaded": True}}
    out = apply_sasang_veto_to_lenses(lenses, force_hold=True)
    assert out["sasang"]["direction"] == "neutral"
    assert out["sasang"]["veto_applied"] is True


def test_veto_row_phase_transition():
    row = {
        "mapping_target": "sideways",
        "regime_hypothesis": "phase_transition",
        "machine_readables": {"heat_proxy": 0.58, "cold_proxy": 0.42, "volatility_rarefaction_proxy": 0.48},
    }
    v = veto_for_sasang_row(row)
    assert "force_hold" in v
    assert isinstance(v.get("reason_codes"), list)
