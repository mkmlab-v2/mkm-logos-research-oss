"""Smoke tests for dual strict promotion chain profile doc."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "scripts" / "run_btrack_lens_v2_dual_strict_promotion_chain_v1.py"


def _mod():
    spec = importlib.util.spec_from_file_location("dual_strict_chain", MOD)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_calibration_note_documents_expanded_off():
    m = _mod()
    assert "expanded_prior OFF" in m.CALIBRATION
    assert "source_signal" in m.CALIBRATION
