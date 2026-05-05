# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCR = _ROOT / "scripts" / "myeongri_core_v2_upgrade.py"


def _load():
    spec = importlib.util.spec_from_file_location("myeongri_core_v2_upgrade", _SCR)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["myeongri_core_v2_upgrade"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_structural_tension_clamped():
    mod = _load()
    val, _ = mod._structural_tension_v1(
        {"year": "갑자", "month": "갑자", "day": "경진", "hour": "무인"}
    )
    assert 0.0 <= val <= 1.0


def test_latent_energy_four_vector_sums():
    mod = _load()
    vec, axes, _note = mod._latent_energy_vector_4d(
        {"wood": 0.2, "fire": 0.2, "earth": 0.2, "metal": 0.2, "water": 0.2}
    )
    assert len(vec) == 4
    assert len(axes) == 4
    assert abs(sum(vec) - 1.0) < 1e-6


def test_nearest_probe_state_id_matches_master_probe_file():
    mod = _load()
    sid, dist, st = mod._nearest_probe_state_id(
        {"wood": 0.2, "fire": 0.2, "earth": 0.2, "metal": 0.2, "water": 0.2}
    )
    assert st == "ok"
    assert sid is not None and 1 <= int(sid) <= 16
    assert dist >= 0.0


def test_build_upgrade_doc_includes_probe_nearest_block():
    mod = _load()
    doc = {
        "scores": {"confidence": 0.5, "direction_score": 0.0},
        "advanced": {
            "input_summary": {
                "pillars": {"year": "갑자", "month": "갑자", "day": "갑자", "hour": "갑자"}
            }
        },
    }
    out = mod.build_upgrade_doc(doc, source_path="test")
    pb = out.get("myeongni_16state_probe_nearest_v1")
    assert isinstance(pb, dict)
    assert pb.get("contract") == "btrack_16state_master_probe_nearest_v1"
    assert pb.get("nearest_state_id") is not None
