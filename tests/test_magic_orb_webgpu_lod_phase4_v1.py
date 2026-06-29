"""Phase 4 [HYPO]: WebGPU LOD policy + hero slice tier resolution."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/final/artifacts/magic_orb_webgpu_lod_policy_v1_latest.json"
HERO = ROOT / "docs/final/artifacts/magic_orb_hero_slices_v1_latest.json"
BUILDER = ROOT / "scripts/build_magic_orb_webgpu_lod_policy_v1.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_magic_orb_webgpu_lod_policy_v1", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_policy_schema_and_tiers():
    mod = _load_builder()
    doc = mod.build_policy()
    assert doc["schema"] == "magic_orb_webgpu_lod_policy_v1"
    assert doc["research_only"] is True
    tiers = {t["tier"] for t in doc["tiers"]}
    assert "canvas_compact" in tiers
    assert "webgpu_hypo" in tiers


def test_resolve_tier_node_count_ladder():
    mod = _load_builder()
    assert mod.resolve_tier(12) == "canvas_compact"
    assert mod.resolve_tier(30) == "canvas_standard"
    assert mod.resolve_tier(45) == "canvas_dense"
    assert mod.resolve_tier(64, webgpu_available=True) == "webgpu_hypo"
    assert mod.resolve_tier(64, webgpu_available=False) == "canvas_dense"


def test_hero_slices_fit_lod_policy():
    if not HERO.is_file() or not POLICY.is_file():
        return
    mod = _load_builder()
    bundle = json.loads(HERO.read_text(encoding="utf-8-sig"))
    for sl in bundle.get("slices") or []:
        bloom = sl.get("graph_bloom") or {}
        n = len(bloom.get("nodes") or [])
        assert n >= 8
        tier = mod.resolve_tier(n, webgpu_available=True)
        assert tier in {"canvas_compact", "canvas_standard", "canvas_dense", "webgpu_hypo"}


def test_mkmlife_public_policy_sync_when_present():
    public = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_webgpu_lod_policy_v1.json"
    if not public.is_file() or not POLICY.is_file():
        return
    pub = json.loads(public.read_text(encoding="utf-8-sig"))
    assert pub["schema"] == "magic_orb_webgpu_lod_policy_v1"
    assert len(pub.get("tiers") or []) >= 4
