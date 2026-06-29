# -*- coding: utf-8 -*-
"""ops_dynamical_ty_geumhwa_link_v1 — linkage spec smoke."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_link():
    path = _ROOT / "scripts" / "ops_dynamical_ty_geumhwa_link_v1.py"
    spec = importlib.util.spec_from_file_location("ops_dynamical_ty_geumhwa_link_v1", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_geumhwa_formula_bounds() -> None:
    mod = _load_link()
    assert mod.compute_geumhwa_index(k=0.5, m=0.5, earth_mediation=0.9) == 0.225
    assert mod.compute_geumhwa_index(k=0.8, m=0.2, earth_mediation=0.9) == 0.576


def test_boundary_regime_ty_analog() -> None:
    mod = _load_link()
    doc = mod.build_ty_geumhwa_link_v1(
        slkm={"K": 0.2, "M": 0.5, "S": 0.5, "L": 0.4},
        stress_score=0.4,
        stage="watch",
        solo_ok=True,
        reddit_ok=True,
    )
    assert doc["schema"] == "ops_dynamical_ty_geumhwa_link_v1"
    assert doc["auto_trigger_forbidden"] is True
    assert doc["boundary_regime"] is True
    assert doc["regime_label"] == "boundary_sparse_ty_analog"
    assert doc["effective_uncertainty_multiplier"] == 1.25


def test_execution_mode_above_threshold() -> None:
    mod = _load_link()
    doc = mod.build_ty_geumhwa_link_v1(
        slkm={"K": 0.9, "M": 0.1, "S": 0.8, "L": 0.5},
        stress_score=0.2,
        stage="calm",
        solo_ok=True,
        reddit_ok=True,
    )
    assert doc["execution_mode"] is True
    assert doc["geumhwa_index"] > 0.5
