#!/usr/bin/env python3
"""Myeongni lens context mesh timeline pack v1 — Obsidian-style local graph [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lens_context_mesh_manseryeok_bridge_v1 import build_manseryeok_bridge_v1
from scripts.lens_context_mesh_v1 import (  # noqa: E402
    build_hop_index_from_slice,
    build_hub_logos,
)

OUT_SLICE = ROOT / "docs/final/artifacts/lens_context_mesh_graph_slice_myeongni_v1_latest.json"
OUT_HOP = ROOT / "docs/final/artifacts/lens_context_mesh_hop_index_myeongni_v1_latest.json"
OUT_HUB = ROOT / "docs/final/artifacts/lens_context_mesh_hub_myeongni_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_myeongni_timeline_slice() -> dict[str, Any]:
    """Minimal timeline nodes — mid-term direction metaphor only (NON_GATING)."""
    nodes = [
        {"id": "timeline::birth_chart", "kind": "theme", "label": "원국", "hub_score": 0.82},
        {"id": "timeline::sewoon::2026", "kind": "regime", "label": "2026 세운", "hub_score": 0.74},
        {"id": "timeline::daewoon::3", "kind": "regime", "label": "대운 3", "hub_score": 0.7},
        {"id": "pillar::year::gapsul", "kind": "theme", "label": "연주 갑술", "hub_score": 0.55},
        {"id": "pillar::month::byeongjin", "kind": "theme", "label": "월주 병진", "hub_score": 0.52},
        {"id": "pillar::day::muja", "kind": "theme", "label": "일주 무자", "hub_score": 0.58},
        {"id": "cycle::ten_god::jeongjae", "kind": "theme", "label": "정재", "hub_score": 0.48},
        {"id": "cycle::ten_god::siksin", "kind": "theme", "label": "식신", "hub_score": 0.46},
        {"id": "context::mid_term_direction", "kind": "theme", "label": "중기 방향 슬롯", "hub_score": 0.62},
    ]
    edges = [
        {"src": "timeline::birth_chart", "dst": "pillar::day::muja", "edge_type": "contains", "weight": 0.9},
        {"src": "timeline::birth_chart", "dst": "pillar::month::byeongjin", "edge_type": "contains", "weight": 0.85},
        {"src": "timeline::birth_chart", "dst": "pillar::year::gapsul", "edge_type": "contains", "weight": 0.85},
        {"src": "timeline::sewoon::2026", "dst": "pillar::year::gapsul", "edge_type": "activates", "weight": 0.72},
        {"src": "timeline::daewoon::3", "dst": "timeline::sewoon::2026", "edge_type": "frames", "weight": 0.68},
        {"src": "pillar::day::muja", "dst": "cycle::ten_god::jeongjae", "edge_type": "derives", "weight": 0.6},
        {"src": "pillar::day::muja", "dst": "cycle::ten_god::siksin", "edge_type": "derives", "weight": 0.58},
        {"src": "context::mid_term_direction", "dst": "timeline::daewoon::3", "edge_type": "lens_slot", "weight": 0.55},
        {"src": "context::mid_term_direction", "dst": "timeline::sewoon::2026", "edge_type": "lens_slot", "weight": 0.55},
    ]
    return {
        "schema_version": "showroom_meaning_topology_graph_slice_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "non_gating": True,
        "lens_id": "myeongni",
        "pack_id": "lens_pack@myeongni_timeline",
        "stats": {"node_count": len(nodes), "edge_count": len(edges)},
        "nodes": nodes,
        "edges": edges,
        "reproduce": "py scripts/build_lens_context_mesh_myeongni_timeline_pack_v1.py",
    }


def build_myeongni_hub(*, slice_path: Path, hop_path: Path) -> dict[str, Any]:
    rel = lambda p: str(p.relative_to(ROOT)).replace("\\", "/")
    return {
        "schema_version": "lens_context_mesh_hub_v1",
        "generated_at_utc": _utc(),
        "lens_id": "myeongni",
        "pack_id": "lens_pack@myeongni_timeline",
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "non_gating": True,
        "ui_contract": {
            "default_depth": 2,
            "max_depth": 3,
            "max_focus_nodes": 24,
            "hide_orphans_default": True,
            "layout_mode": "obsidian_local",
            "visual_metaphor": "timeline_not_verse_graph",
        },
        "artifacts": {
            "graph_slice": rel(slice_path),
            "hop_index": rel(hop_path),
        },
        "legacy_pointers": {
            "parallel_advisory_contract": "docs/final/MKM_PARALLEL_ADVISORY_LENS_CONTRACT_V1.md",
            "charter_myeongni_role": "docs/final/LENS_UTILIZATION_CHARTER_V1.md",
            "manseryeok_engine": "scripts/manseryeok_engine_lookup_v1.py",
        },
        "manseryeok_bridge_v1": build_manseryeok_bridge_v1(),
        "reproduce": "py scripts/build_lens_context_mesh_myeongni_timeline_pack_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-slice", type=Path, default=OUT_SLICE)
    ap.add_argument("--out-hop", type=Path, default=OUT_HOP)
    ap.add_argument("--out-hub", type=Path, default=OUT_HUB)
    args = ap.parse_args()

    slice_doc = build_myeongni_timeline_slice()
    hop = build_hop_index_from_slice(
        slice_doc,
        lens_id="myeongni",
        pack_id="lens_pack@myeongni_timeline",
        source_slice_path=str(args.out_slice.relative_to(ROOT)).replace("\\", "/"),
    )
    hub = build_myeongni_hub(slice_path=args.out_slice, hop_path=args.out_hop)

    for path, doc in ((args.out_slice, slice_doc), (args.out_hop, hop), (args.out_hub, hub)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "slice": str(args.out_slice),
                "hop": str(args.out_hop),
                "hub": str(args.out_hub),
                "nodes": slice_doc["stats"]["node_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
