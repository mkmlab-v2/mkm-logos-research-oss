# -*- coding: utf-8 -*-
"""lens_context_mesh_manseryeok_bridge_v1 smoke."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_bridge():
    path = _ROOT / "scripts" / "lens_context_mesh_manseryeok_bridge_v1.py"
    spec = importlib.util.spec_from_file_location("lens_context_mesh_manseryeok_bridge_v1", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bridge_fixture_engine_linked() -> None:
    mod = _load_bridge()
    doc = mod.build_manseryeok_bridge_v1()
    assert doc["schema"] == "lens_context_mesh_manseryeok_bridge_v1"
    assert doc["engine_linked"] is True
    assert doc["auto_gating_forbidden"] is True
    assert len(doc["node_bindings"]) == 4


def test_ganji_slug_mapping() -> None:
    mod = _load_bridge()
    assert mod.ganji_to_slug("무자") == "muja"
    assert mod.pillar_node_id("day", "무자") == "pillar::day::muja"
    assert mod.pillar_node_id("day", "unknown") == "pillar::day::unmapped"
