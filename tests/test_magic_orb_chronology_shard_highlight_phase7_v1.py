"""Phase 7 [HYPO]: chronology era → display/shard node highlight map."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIGHLIGHT = ROOT / "docs/final/artifacts/magic_orb_chronology_shard_highlight_v1_latest.json"
HERO = ROOT / "docs/final/artifacts/magic_orb_hero_slices_v1_latest.json"
BUILDER = ROOT / "scripts/build_magic_orb_chronology_shard_highlight_v1.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_highlight_map_schema():
    mod = _load_module(BUILDER, "build_magic_orb_chronology_shard_highlight_v1")
    if not HERO.is_file():
        return
    doc = mod.build_highlight_map()
    assert doc["schema"] == "magic_orb_chronology_shard_highlight_v1"
    assert doc["research_only"] is True
    assert len(doc["entries"]) >= 20


def test_intertestamental_dan2_shard_hits():
    mod = _load_module(BUILDER, "build_magic_orb_chronology_shard_highlight_v1")
    if not HERO.is_file():
        return
    doc = mod.build_highlight_map()
    row = next(
        e
        for e in doc["entries"]
        if e["era_id"] == "intertestamental_empire_handoff" and e["slice_id"] == "DAN2_CLUSTER_v1"
    )
    assert row["shard_hit_count"] >= 3
    assert row["display_hit_count"] >= 1


def test_gospel_passion_shard_parallel_hits():
    mod = _load_module(BUILDER, "build_magic_orb_chronology_shard_highlight_v1")
    if not HERO.is_file():
        return
    doc = mod.build_highlight_map()
    row = next(
        e
        for e in doc["entries"]
        if e["era_id"] == "gospel_logos_incarnate" and e["slice_id"] == "SYNOPTIC_PASSION_WEEK_v1"
    )
    assert row["verse_ref_count"] >= 1
    assert row["shard_hit_count"] == 0 or row["display_hit_count"] == 0


def test_mkmlife_public_highlight_sync_when_present():
    public = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_chronology_shard_highlight_v1.json"
    if not public.is_file() or not HIGHLIGHT.is_file():
        return
    pub = json.loads(public.read_text(encoding="utf-8-sig"))
    assert pub["schema"] == "magic_orb_chronology_shard_highlight_v1"
    assert len(pub.get("entries") or []) >= 20
