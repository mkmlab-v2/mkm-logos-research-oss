"""Smoke: gold-query LOD caps for Magic Orb bloom."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "scripts/magic_orb_gold_lod_profiles_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("magic_orb_gold_lod_profiles_v1", MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_q04_gold_required_dense_caps():
    mod = _load()
    caps = mod.resolve_gold_lod_profile("q04")
    assert caps["lod_node_cap"] == 64
    assert caps["lod_edge_cap"] == 72
    assert caps["profile"] == "gold_dense_v1"
    assert isinstance(caps.get("hub_verse_ids"), list)


def test_unknown_query_default_caps():
    mod = _load()
    caps = mod.resolve_gold_lod_profile("q99_unknown")
    assert caps["lod_node_cap"] == 48
    assert caps["lod_edge_cap"] == 56
