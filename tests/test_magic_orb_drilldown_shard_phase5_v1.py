"""Phase 5 [HYPO]: drill-down shard bundle + Dan.2 cross_lens LOD retention."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs/final/artifacts/magic_orb_drilldown_shards_v1_latest.json"
HERO = ROOT / "docs/final/artifacts/magic_orb_hero_slices_v1_latest.json"
DRILL_BUILDER = ROOT / "scripts/build_magic_orb_drilldown_shard_bundle_v1.py"
PASSION_SHARD = ROOT / "tests/fixtures/bible_topology/sample/sample_topology_synoptic_passion_v1.json"
SHOWROOM = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_drilldown_index_schema():
    mod = _load_module(DRILL_BUILDER, "build_magic_orb_drilldown_shard_bundle_v1")
    if not HERO.is_file():
        return
    index, sidecars = mod.build_bundle(hero_path=HERO)
    assert index["schema"] == "magic_orb_drilldown_shards_v1"
    assert index["research_only"] is True
    assert len(index["slices"]) == 2
    assert len(sidecars) == 2
    for sc in sidecars:
        assert sc["schema"] == "magic_orb_drilldown_shard_v1"
        assert sc["display"]["edge_count"] <= sc["shard_full"]["edge_count"]


def test_passion_shard_has_dropped_edges():
    mod = _load_module(DRILL_BUILDER, "build_magic_orb_drilldown_shard_bundle_v1")
    if not HERO.is_file() or not PASSION_SHARD.is_file():
        return
    _, sidecars = mod.build_bundle(hero_path=HERO, passion_shard_path=PASSION_SHARD)
    passion = next(s for s in sidecars if s["slice_id"] == "SYNOPTIC_PASSION_WEEK_v1")
    assert passion["shard_full"]["edge_count"] == 142
    assert passion["dropped"]["edge_count"] > 0
    assert passion["sample_dropped_edges"]


def test_dan2_cross_lens_in_display_after_lod():
    mod = _load_module(DRILL_BUILDER, "build_magic_orb_drilldown_shard_bundle_v1")
    if not HERO.is_file() or not SHOWROOM.is_file():
        return
    _, sidecars = mod.build_bundle(hero_path=HERO, showroom_path=SHOWROOM)
    dan2 = next(s for s in sidecars if s["slice_id"] == "DAN2_CLUSTER_v1")
    display_types = dan2.get("relation_counts_display") or {}
    assert "cross_lens_confirm" in display_types
    assert "confirmed" in (dan2.get("integrity_tiers_display") or [])


def test_mkmlife_public_drilldown_sync_when_present():
    public_index = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_drilldown_shards_v1.json"
    passion_sidecar = (
        ROOT / "projects/mkm/mkm-life/public/data/magic_orb_drilldown_shard/SYNOPTIC_PASSION_WEEK_v1.json"
    )
    if not public_index.is_file() or not INDEX.is_file():
        return
    pub = json.loads(public_index.read_text(encoding="utf-8-sig"))
    assert pub["schema"] == "magic_orb_drilldown_shards_v1"
    assert len(pub.get("slices") or []) >= 2
    if passion_sidecar.is_file():
        sc = json.loads(passion_sidecar.read_text(encoding="utf-8-sig"))
        assert sc["schema"] == "magic_orb_drilldown_shard_v1"
        assert len(sc.get("edges") or []) >= 100
