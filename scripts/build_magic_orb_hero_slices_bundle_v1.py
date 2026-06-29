#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build magic_orb_hero_slices_v1 — passion + Dan.2 graph blooms + chronology overlay (Phase 1)."""
from __future__ import annotations

import argparse
import importlib.util
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PASSION = ROOT / "docs/final/artifacts/magic_orb_graph_bloom_bible_topology_passion_v1_latest.json"
DEFAULT_SHOWROOM = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_CHRONOLOGY = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_chronology_overlay_v1.json"
)
DEFAULT_OUT = ROOT / "docs/final/artifacts/magic_orb_hero_slices_v1_latest.json"
MKMLIFE_OUT = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_hero_slices_v1.json"

SCHEMA = "magic_orb_hero_slices_v1"
VERSION = "1.0.0"
MAX_NODES = 64
MAX_EDGES = 72
VERSE_NODE_CAP = 63

ERA_SLICE_HINTS: dict[str, str] = {
    "gospel_logos_incarnate": "SYNOPTIC_PASSION_WEEK_v1",
    "exile_and_return": "DAN2_CLUSTER_v1",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_bloom_builder():
    path = ROOT / "scripts/build_magic_orb_graph_bloom_v1.py"
    spec = importlib.util.spec_from_file_location("build_magic_orb_graph_bloom_v1", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _lod_cap_slice(slice_doc: dict[str, Any], *, max_verse_nodes: int = VERSE_NODE_CAP) -> dict[str, Any]:
    """Hub-degree LOD cap for showroom-scale slices (128n/140e → schema max)."""
    nodes_in = list(slice_doc.get("nodes") or [])
    edges_in = list(slice_doc.get("edges") or [])
    if len(nodes_in) <= max_verse_nodes + 1 and len(edges_in) <= MAX_EDGES:
        return {"nodes": nodes_in, "edges": edges_in}

    degree: dict[str, int] = defaultdict(int)
    for edge in edges_in:
        src = str(edge.get("src") or "")
        dst = str(edge.get("dst") or "")
        if src and dst:
            degree[src] += 1
            degree[dst] += 1

    query_nodes = [n for n in nodes_in if n.get("id") == "query::center" or n.get("kind") == "query"]
    verse_nodes = [n for n in nodes_in if n not in query_nodes]
    cross_lens_node_ids: set[str] = set()
    for edge in edges_in:
        if str(edge.get("edge_type") or "") == "cross_lens_confirm":
            src = str(edge.get("src") or "")
            dst = str(edge.get("dst") or "")
            if src:
                cross_lens_node_ids.add(src)
            if dst:
                cross_lens_node_ids.add(dst)
    ranked = sorted(
        verse_nodes,
        key=lambda n: (
            - (2 if str(n.get("id") or "") in cross_lens_node_ids else 0),
            -degree.get(str(n.get("id") or ""), 0),
            str(n.get("id") or ""),
        ),
    )
    selected_ids = {str(n.get("id")) for n in ranked[:max_verse_nodes]}
    if query_nodes:
        selected_ids.add(str(query_nodes[0].get("id")))

    nodes = [n for n in nodes_in if str(n.get("id")) in selected_ids]
    edges: list[dict[str, Any]] = []

    def _edge_rank(edge: dict[str, Any]) -> tuple[float, float, str]:
        et = str(edge.get("edge_type") or "")
        type_bonus = {
            "cross_lens_confirm": 3.0,
            "parallel": 2.5,
            "timeline_anchor": 1.0,
        }.get(et, 0.5)
        return (-type_bonus, -float(edge.get("weight") or 0), str(edge.get("src")))

    cross_lens_candidates = [
        e
        for e in edges_in
        if str(e.get("edge_type") or "") == "cross_lens_confirm"
        and str(e.get("src") or "") in selected_ids
        and str(e.get("dst") or "") in selected_ids
    ]
    edge_cap = MAX_EDGES - (1 if cross_lens_candidates else 0)

    for edge in sorted(edges_in, key=_edge_rank):
        src = str(edge.get("src") or "")
        dst = str(edge.get("dst") or "")
        if src in selected_ids and dst in selected_ids:
            edges.append(edge)
        if len(edges) >= edge_cap:
            break

    if cross_lens_candidates and not any(
        str(e.get("edge_type") or "") == "cross_lens_confirm" for e in edges
    ):
        edges.append(sorted(cross_lens_candidates, key=_edge_rank)[0])

    return {"nodes": nodes, "edges": edges}


def _bloom_from_showroom(showroom: dict[str, Any], *, slice_id: str, query: str) -> dict[str, Any]:
    builder = _load_bloom_builder()
    builder.NODE_CAP = MAX_NODES
    builder.EDGE_CAP = MAX_EDGES
    capped = _lod_cap_slice(showroom)
    mini = {
        "seed_query": query,
        "nodes": capped["nodes"],
        "edges": capped["edges"],
    }
    doc = builder.bloom_from_topology_slice(mini, query)
    doc["stats"] = {
        "node_count": len(doc.get("nodes") or []),
        "edge_count": len(doc.get("edges") or []),
        "source_unique_verses": len([n for n in capped["nodes"] if n.get("kind") == "verse"]),
        "lod_capped": True,
        "showroom_node_count": showroom.get("stats", {}).get("node_count"),
        "showroom_edge_count": showroom.get("stats", {}).get("edge_count"),
    }
    doc["source"] = {
        "kind": "showroom_meaning_topology_graph_slice_v1",
        "slice_id": slice_id,
        "artifact": "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json",
    }
    return doc


def _slim_eras(chronology: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for era in chronology.get("eras") or []:
        if not isinstance(era, dict):
            continue
        era_id = str(era.get("era_id") or "").strip()
        if not era_id:
            continue
        rows.append(
            {
                "era_id": era_id,
                "label_ko": era.get("label_ko"),
                "label_en": era.get("label_en"),
                "interpretation_class": era.get("interpretation_class") or "[HYPO]",
                "verse_refs": list(era.get("verse_refs") or [])[:12],
                "theme_tags": list(era.get("theme_tags") or [])[:6],
                "hint_slice_id": ERA_SLICE_HINTS.get(era_id),
            }
        )
    return rows


def _finalize_bloom(doc: dict[str, Any]) -> dict[str, Any]:
    builder = _load_bloom_builder()
    return builder.annotate_bloom_edge_integrity(json.loads(json.dumps(doc)))


def build_bundle(
    *,
    passion_path: Path = DEFAULT_PASSION,
    showroom_path: Path = DEFAULT_SHOWROOM,
    chronology_path: Path = DEFAULT_CHRONOLOGY,
) -> dict[str, Any]:
    passion = _load_json(passion_path)
    showroom = _load_json(showroom_path)
    chronology = _load_json(chronology_path) if chronology_path.is_file() else {}

    passion_slice = {
        "slice_id": "SYNOPTIC_PASSION_WEEK_v1",
        "label_ko": "공관복음 수난 주간 (Passion week)",
        "label_en": "Synoptic passion week parallels",
        "graph_bloom": _finalize_bloom(passion),
        "stats": passion.get("stats") or {},
    }

    dan2_query = "Dan.2 cluster — cross-lens meaning topology (showroom slice, research_only)"
    dan2_bloom = _bloom_from_showroom(showroom, slice_id="DAN2_CLUSTER_v1", query=dan2_query)
    dan2_slice = {
        "slice_id": "DAN2_CLUSTER_v1",
        "label_ko": "다니엘 2장 클러스터 (Dan.2)",
        "label_en": "Daniel 2 meaning topology cluster",
        "graph_bloom": _finalize_bloom(dan2_bloom),
        "stats": dan2_bloom.get("stats") or {},
    }

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "non_gating": True,
        "default_slice_id": "SYNOPTIC_PASSION_WEEK_v1",
        "disclaimer_ko": (
            "연대기·그래프 망은 Logos Observatory 부록 [HYPO][NON_GATING]입니다. "
            "신학·예언 확정·실매매·Track A 근거가 아닙니다."
        ),
        "slices": [passion_slice, dan2_slice],
        "chronology": {
            "schema": chronology.get("schema") or "logos_chronology_showroom_overlay_v1",
            "policy": chronology.get("policy") or {"research_only": True, "non_gating": True},
            "eras": _slim_eras(chronology),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--passion", type=Path, default=DEFAULT_PASSION)
    ap.add_argument("--showroom", type=Path, default=DEFAULT_SHOWROOM)
    ap.add_argument("--chronology", type=Path, default=DEFAULT_CHRONOLOGY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sync-mkmlife", action="store_true")
    args = ap.parse_args()

    bundle = build_bundle(
        passion_path=args.passion,
        showroom_path=args.showroom,
        chronology_path=args.chronology,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.sync_mkmlife:
        MKMLIFE_OUT.parent.mkdir(parents=True, exist_ok=True)
        MKMLIFE_OUT.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    s0 = bundle["slices"][0]["graph_bloom"]["stats"]
    s1 = bundle["slices"][1]["graph_bloom"]["stats"]
    print(
        json.dumps(
            {
                "ok": True,
                "slices": 2,
                "eras": len(bundle["chronology"]["eras"]),
                "passion": {"nodes": s0.get("node_count"), "edges": s0.get("edge_count")},
                "dan2": {"nodes": s1.get("node_count"), "edges": s1.get("edge_count")},
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
