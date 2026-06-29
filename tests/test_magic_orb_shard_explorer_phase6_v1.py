"""Phase 6 [HYPO]: shard explorer policy + sidecar→bloom stats."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/final/artifacts/magic_orb_shard_explorer_policy_v1_latest.json"
PASSION_SIDECAR = (
    ROOT / "projects/mkm/mkm-life/public/data/magic_orb_drilldown_shard/SYNOPTIC_PASSION_WEEK_v1.json"
)
DAN2_SIDECAR = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_drilldown_shard/DAN2_CLUSTER_v1.json"
POLICY_BUILDER = ROOT / "scripts/build_magic_orb_shard_explorer_policy_v1.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_policy_schema_and_eligibility():
    mod = _load_module(POLICY_BUILDER, "build_magic_orb_shard_explorer_policy_v1")
    if not PASSION_SIDECAR.is_file() or not DAN2_SIDECAR.is_file():
        return
    doc = mod.build_policy()
    assert doc["schema"] == "magic_orb_shard_explorer_policy_v1"
    assert doc["research_only"] is True
    assert len(doc["slices"]) >= 2
    eligible = [s for s in doc["slices"] if s.get("explorer_eligible")]
    assert len(eligible) >= 2


def test_passion_explorer_stats():
    mod = _load_module(POLICY_BUILDER, "build_magic_orb_shard_explorer_policy_v1")
    if not PASSION_SIDECAR.is_file():
        return
    sidecar = json.loads(PASSION_SIDECAR.read_text(encoding="utf-8-sig"))
    stats = mod.sidecar_to_explorer_stats(sidecar)
    assert stats["edge_count"] == 142
    assert stats["node_count"] >= 80
    assert stats["eligible"] is True


def test_dan2_explorer_has_cross_lens_edges():
    mod = _load_module(POLICY_BUILDER, "build_magic_orb_shard_explorer_policy_v1")
    if not DAN2_SIDECAR.is_file():
        return
    sidecar = json.loads(DAN2_SIDECAR.read_text(encoding="utf-8-sig"))
    stats = mod.sidecar_to_explorer_stats(sidecar)
    assert stats["edge_count"] == 140
    assert stats["node_count"] >= 100
    types = {str(e.get("edge_type")) for e in sidecar.get("edges") or []}
    assert "cross_lens_confirm" in types


def test_mkmlife_public_policy_sync_when_present():
    public = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_shard_explorer_policy_v1.json"
    if not public.is_file() or not POLICY.is_file():
        return
    pub = json.loads(public.read_text(encoding="utf-8-sig"))
    assert pub["schema"] == "magic_orb_shard_explorer_policy_v1"
    assert pub["limits"]["canvas_size_px"] == 340
