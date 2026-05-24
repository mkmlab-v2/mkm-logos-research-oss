"""Smoke tests for lens v2 recovery sweep helpers."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "scripts" / "run_btrack_lens_v2_recovery_sweep_v1.py"


def _mod():
    spec = importlib.util.spec_from_file_location("lens_v2_recovery", MOD_PATH)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_candidates_nonempty():
    m = _mod()
    c = m._candidates()
    assert len(c) >= 5
    assert c[0]["slug"] == "baseline"


def test_deep_merge_nested():
    m = _mod()
    base = {"rules": {"v2": {"min_confidence_floor": 0.15}, "ensemble_mode": "v1"}}
    out = m._deep_merge(base, {"rules": {"v2": {"conflict_dampen": 0.9}}})
    assert out["rules"]["v2"]["min_confidence_floor"] == 0.15
    assert out["rules"]["v2"]["conflict_dampen"] == 0.9
