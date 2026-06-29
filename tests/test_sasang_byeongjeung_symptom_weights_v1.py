# -*- coding: utf-8 -*-
"""sasang_byeongjeung_symptom_weights_v1 — deterministic reference table smoke."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_mod():
    path = _ROOT / "scripts" / "sasang_byeongjeung_symptom_weights_v1.py"
    spec = importlib.util.spec_from_file_location("sasang_byeongjeung_symptom_weights_v1", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_symptom_weights_structure() -> None:
    mod = _load_mod()
    doc = mod.build_symptom_weights_v1()
    assert doc["schema"] == "sasang_byeongjeung_symptom_weights_v1"
    assert doc["research_only"] is True
    assert doc["auto_clinical_trigger"] is False
    ids = {s["symptom_id"] for s in doc["symptoms"]}
    assert ids == {"jeongchung", "bujong"}
    te = doc["by_constitution"]["taeeum_in"]["weights"]
    assert te["bujong"] > te["jeongchung"]
    se = doc["by_constitution"]["soeum_in"]["weights"]
    assert se["jeongchung"] > se["bujong"]
    ty = doc["by_constitution"]["taeyang_in"]
    assert ty.get("uncertainty_boost") is True
    assert doc["ty_sparsity"]["koges_excluded_in_literature"] is True
