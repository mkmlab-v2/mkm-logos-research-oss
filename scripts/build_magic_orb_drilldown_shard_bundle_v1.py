#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build magic_orb_drilldown_shards_v1 — full-shard sidecars for LOD-capped hero blooms (Phase 5)."""
from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HERO = ROOT / "docs/final/artifacts/magic_orb_hero_slices_v1_latest.json"
DEFAULT_PASSION_SHARD = (
    ROOT / "tests/fixtures/bible_topology/sample/sample_topology_synoptic_passion_v1.json"
)
DEFAULT_SHOWROOM = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/magic_orb_drilldown_shards_v1_latest.json"
MKMLIFE_INDEX = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_drilldown_shards_v1.json"
MKMLIFE_SHARD_DIR = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_drilldown_shard"

SCHEMA_INDEX = "magic_orb_drilldown_shards_v1"
SCHEMA_SIDECAR = "magic_orb_drilldown_shard_v1"
VERSION = "1.0.0"
SAMPLE_DROPPED = 16


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _normalize_ref(raw: str) -> str:
    t = str(raw or "").strip()
    if "::" in t:
        t = t.split("::")[-1]
    return t.replace(" ", "").upper()


def _shard_edge_key(src: str, dst: str, relation: str) -> tuple[str, str, str]:
    a, b = sorted([_normalize_ref(src), _normalize_ref(dst)])
    return (a, b, str(relation or "").strip().lower())


def _topology_edge_key(src: str, dst: str, edge_type: str) -> tuple[str, str, str]:
    return _shard_edge_key(src, dst, edge_type)


def _bloom_display_keys(bloom: dict[str, Any]) -> set[tuple[str, str, str]]:
    id_to_ref: dict[str, str] = {}
    for node in bloom.get("nodes") or []:
        nid = str(node.get("id") or "")
        ref = str(node.get("ref") or "")
        if nid:
            id_to_ref[nid] = _normalize_ref(ref or nid)
    keys: set[tuple[str, str, str]] = set()
    for edge in bloom.get("edges") or []:
        src_id = str(edge.get("src") or "")
        dst_id = str(edge.get("dst") or "")
        et = str(edge.get("edge_type") or "")
        src_ref = id_to_ref.get(src_id, _normalize_ref(src_id))
        dst_ref = id_to_ref.get(dst_id, _normalize_ref(dst_id))
        keys.add(_topology_edge_key(src_ref, dst_ref, et))
    return keys


def _integrity_tiers_from_edges(edges: list[dict[str, Any]], *, edge_type_field: str) -> list[str]:
    builder_path = ROOT / "scripts/build_magic_orb_graph_bloom_v1.py"
    spec = importlib.util.spec_from_file_location("build_magic_orb_graph_bloom_v1", builder_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    tiers: set[str] = set()
    for edge in edges:
        et = str(edge.get(edge_type_field) or "")
        tier = mod.EDGE_INTEGRITY_TIER_BY_TYPE.get(et, "observation")
        tiers.add(tier)
    return sorted(tiers)


def _slim_shard_edges_passion(shard: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for edge in shard.get("edges") or []:
        rows.append(
            {
                "src_ref": edge.get("src_ref"),
                "dst_ref": edge.get("dst_ref"),
                "relation": edge.get("relation"),
            }
        )
    return rows


def _slim_shard_edges_showroom(showroom: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for edge in showroom.get("edges") or []:
        rows.append(
            {
                "src": edge.get("src"),
                "dst": edge.get("dst"),
                "edge_type": edge.get("edge_type"),
                "weight": edge.get("weight"),
            }
        )
    return rows


def _unique_verses_passion(shard: dict[str, Any]) -> int:
    refs: set[str] = set()
    for edge in shard.get("edges") or []:
        refs.add(_normalize_ref(str(edge.get("src_ref") or "")))
        refs.add(_normalize_ref(str(edge.get("dst_ref") or "")))
    refs.discard("")
    return len(refs)


def _unique_verses_showroom(showroom: dict[str, Any]) -> int:
    return len([n for n in showroom.get("nodes") or [] if n.get("kind") == "verse"])


def build_passion_sidecar(
    *,
    slice_entry: dict[str, Any],
    shard: dict[str, Any],
) -> dict[str, Any]:
    bloom = slice_entry.get("graph_bloom") or {}
    display_keys = _bloom_display_keys(bloom)
    shard_edges = _slim_shard_edges_passion(shard)
    shard_keys = {
        _shard_edge_key(str(e["src_ref"]), str(e["dst_ref"]), str(e.get("relation") or ""))
        for e in shard_edges
    }
    dropped_keys = shard_keys - display_keys
    relation_shard = Counter(str(e.get("relation") or "unknown") for e in shard_edges)
    relation_display = Counter(
        str(e.get("edge_type") or "unknown") for e in (bloom.get("edges") or [])
    )
    dropped_samples = [
        e
        for e in shard_edges
        if _shard_edge_key(str(e["src_ref"]), str(e["dst_ref"]), str(e.get("relation") or ""))
        in dropped_keys
    ][:SAMPLE_DROPPED]

    stats = bloom.get("stats") or slice_entry.get("stats") or {}
    return {
        "schema": SCHEMA_SIDECAR,
        "version": VERSION,
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "non_gating": True,
        "slice_id": "SYNOPTIC_PASSION_WEEK_v1",
        "source_kind": "bible_topology_shard_v1",
        "display": {
            "node_count": stats.get("node_count") or len(bloom.get("nodes") or []),
            "edge_count": stats.get("edge_count") or len(bloom.get("edges") or []),
            "lod_capped": stats.get("lod_capped") is True,
        },
        "shard_full": {
            "edge_count": len(shard_edges),
            "unique_verses": _unique_verses_passion(shard),
            "shard_schema": shard.get("schema"),
        },
        "dropped": {
            "edge_count": len(dropped_keys),
            "node_count_estimate": max(
                0,
                _unique_verses_passion(shard)
                - int(stats.get("source_unique_verses") or stats.get("node_count") or 0),
            ),
        },
        "relation_counts_shard": dict(relation_shard),
        "relation_counts_display": dict(relation_display),
        "integrity_tiers_display": _integrity_tiers_from_edges(
            bloom.get("edges") or [], edge_type_field="edge_type"
        ),
        "integrity_tiers_shard": _integrity_tiers_from_edges(
            [{"edge_type": e.get("relation")} for e in shard_edges], edge_type_field="edge_type"
        ),
        "sample_dropped_edges": dropped_samples,
        "edges": shard_edges,
    }


def build_dan2_sidecar(
    *,
    slice_entry: dict[str, Any],
    showroom: dict[str, Any],
) -> dict[str, Any]:
    bloom = slice_entry.get("graph_bloom") or {}
    display_keys = _bloom_display_keys(bloom)
    shard_edges = _slim_shard_edges_showroom(showroom)
    id_to_ref: dict[str, str] = {}
    for node in showroom.get("nodes") or []:
        nid = str(node.get("id") or "")
        if nid:
            id_to_ref[nid] = _normalize_ref(str(node.get("ref") or nid))

    def _showroom_key(edge: dict[str, Any]) -> tuple[str, str, str]:
        src = id_to_ref.get(str(edge.get("src") or ""), _normalize_ref(str(edge.get("src") or "")))
        dst = id_to_ref.get(str(edge.get("dst") or ""), _normalize_ref(str(edge.get("dst") or "")))
        return _topology_edge_key(src, dst, str(edge.get("edge_type") or ""))

    shard_keys = {_showroom_key(e) for e in shard_edges}
    dropped_keys = shard_keys - display_keys
    relation_shard = Counter(str(e.get("edge_type") or "unknown") for e in shard_edges)
    relation_display = Counter(
        str(e.get("edge_type") or "unknown") for e in (bloom.get("edges") or [])
    )
    dropped_samples = [e for e in shard_edges if _showroom_key(e) in dropped_keys][:SAMPLE_DROPPED]

    stats = bloom.get("stats") or slice_entry.get("stats") or {}
    showroom_stats = showroom.get("stats") or {}
    return {
        "schema": SCHEMA_SIDECAR,
        "version": VERSION,
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "non_gating": True,
        "slice_id": "DAN2_CLUSTER_v1",
        "source_kind": "showroom_meaning_topology_graph_slice_v1",
        "display": {
            "node_count": stats.get("node_count") or len(bloom.get("nodes") or []),
            "edge_count": stats.get("edge_count") or len(bloom.get("edges") or []),
            "lod_capped": stats.get("lod_capped") is True,
        },
        "shard_full": {
            "edge_count": showroom_stats.get("edge_count") or len(shard_edges),
            "unique_verses": _unique_verses_showroom(showroom),
            "showroom_schema": showroom.get("schema_version"),
        },
        "dropped": {
            "edge_count": len(dropped_keys),
            "node_count_estimate": max(
                0,
                int(showroom_stats.get("node_count") or 0)
                - int(stats.get("node_count") or len(bloom.get("nodes") or [])),
            ),
        },
        "relation_counts_shard": dict(relation_shard),
        "relation_counts_display": dict(relation_display),
        "integrity_tiers_display": _integrity_tiers_from_edges(
            bloom.get("edges") or [], edge_type_field="edge_type"
        ),
        "integrity_tiers_shard": _integrity_tiers_from_edges(
            shard_edges, edge_type_field="edge_type"
        ),
        "sample_dropped_edges": dropped_samples,
        "edges": shard_edges,
    }


def build_index(sidecars: list[dict[str, Any]]) -> dict[str, Any]:
    entries = []
    for doc in sidecars:
        entries.append(
            {
                "slice_id": doc["slice_id"],
                "source_kind": doc.get("source_kind"),
                "sidecar_url": f"/data/magic_orb_drilldown_shard/{doc['slice_id']}.json",
                "summary": {
                    "display_edges": doc["display"]["edge_count"],
                    "shard_edges": doc["shard_full"]["edge_count"],
                    "dropped_edges": doc["dropped"]["edge_count"],
                    "lod_capped": doc["display"]["lod_capped"],
                    "integrity_tiers_display": doc.get("integrity_tiers_display") or [],
                    "integrity_tiers_shard": doc.get("integrity_tiers_shard") or [],
                },
            }
        )
    return {
        "schema": SCHEMA_INDEX,
        "version": VERSION,
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "non_gating": True,
        "disclaimer_ko": (
            "전체 샤드 드릴다운은 Logos Observatory [HYPO][NON_GATING] 연구 전용입니다. "
            "신학·예언 확정·실매매·Track A 근거가 아닙니다."
        ),
        "slices": entries,
    }


def build_bundle(
    *,
    hero_path: Path = DEFAULT_HERO,
    passion_shard_path: Path = DEFAULT_PASSION_SHARD,
    showroom_path: Path = DEFAULT_SHOWROOM,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    hero = _load_json(hero_path)
    by_id = {str(s.get("slice_id")): s for s in hero.get("slices") or []}
    passion_slice = by_id.get("SYNOPTIC_PASSION_WEEK_v1")
    dan2_slice = by_id.get("DAN2_CLUSTER_v1")
    if not passion_slice or not dan2_slice:
        raise ValueError("hero_slices missing SYNOPTIC_PASSION_WEEK_v1 or DAN2_CLUSTER_v1")

    passion_shard = _load_json(passion_shard_path)
    showroom = _load_json(showroom_path)
    sidecars = [
        build_passion_sidecar(slice_entry=passion_slice, shard=passion_shard),
        build_dan2_sidecar(slice_entry=dan2_slice, showroom=showroom),
    ]
    return build_index(sidecars), sidecars


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hero", type=Path, default=DEFAULT_HERO)
    ap.add_argument("--passion-shard", type=Path, default=DEFAULT_PASSION_SHARD)
    ap.add_argument("--showroom", type=Path, default=DEFAULT_SHOWROOM)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sync-mkmlife", action="store_true")
    args = ap.parse_args()

    if not args.hero.is_file():
        print(json.dumps({"ok": False, "error": f"hero_missing:{args.hero}"}), file=sys.stderr)
        return 2

    index, sidecars = build_bundle(
        hero_path=args.hero,
        passion_shard_path=args.passion_shard,
        showroom_path=args.showroom,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    written = [str(args.out.relative_to(ROOT)).replace("\\", "/")]
    if args.sync_mkmlife:
        MKMLIFE_INDEX.parent.mkdir(parents=True, exist_ok=True)
        MKMLIFE_SHARD_DIR.mkdir(parents=True, exist_ok=True)
        MKMLIFE_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(str(MKMLIFE_INDEX.relative_to(ROOT)).replace("\\", "/"))
        for doc in sidecars:
            sid = doc["slice_id"]
            path = MKMLIFE_SHARD_DIR / f"{sid}.json"
            path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            written.append(str(path.relative_to(ROOT)).replace("\\", "/"))

    summaries = [
        {
            "slice_id": s["slice_id"],
            "display_edges": s["display"]["edge_count"],
            "shard_edges": s["shard_full"]["edge_count"],
            "dropped": s["dropped"]["edge_count"],
            "cross_lens_in_display": "cross_lens_confirm"
            in (s.get("relation_counts_display") or {}),
        }
        for s in sidecars
    ]
    print(json.dumps({"ok": True, "slices": summaries, "written": written}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
