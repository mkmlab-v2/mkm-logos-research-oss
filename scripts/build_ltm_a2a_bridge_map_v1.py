#!/usr/bin/env python3
"""Build LTM ltm_* overlay ↔ Inter-Agent wire profile bridge map ([HYPO] / B-track).

  py scripts/build_ltm_a2a_bridge_map_v1.py
  py scripts/build_ltm_a2a_bridge_map_v1.py --out reports/ltm_a2a_bridge_map_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from mkm_long_term_memory_graph_lib_v1 import (  # noqa: E402
    CONCEPT_BY_ID,
    DEFAULT_GRAPH_PATH,
    load_graph,
)
from mkm_ops_memory_index_lib_v1 import DEFAULT_INDEX_PATH, load_index  # noqa: E402

DEFAULT_OUT = SCRIPT_ROOT / "reports" / "ltm_a2a_bridge_map_v1_latest.json"
WALL = SCRIPT_ROOT / "docs/final/artifacts/ltm_a2a_bridge_wall_v1.json"
A2A_ARCH = SCRIPT_ROOT / "docs/final/artifacts/mkm_a2a_two_layer_architecture_v1_latest.json"
WIRE = SCRIPT_ROOT / "docs/final/artifacts/mkm_inter_agent_wire_profile_v0.json"


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else {}


def build_map(root: Path) -> dict[str, Any]:
    graph = load_graph(root / DEFAULT_GRAPH_PATH.relative_to(SCRIPT_ROOT))
    index = load_index(root / DEFAULT_INDEX_PATH.relative_to(SCRIPT_ROOT))
    wall = _read(root / WALL.relative_to(SCRIPT_ROOT))
    a2a = _read(root / A2A_ARCH.relative_to(SCRIPT_ROOT))
    wire = _read(root / WIRE.relative_to(SCRIPT_ROOT))

    nodes = index.get("nodes") or {}
    ltm_overlays: list[dict[str, Any]] = []
    for node_id, node in sorted(nodes.items()):
        if not str(node_id).startswith("ltm_"):
            continue
        concept_id = str(node.get("ltm_concept_id") or node_id.removeprefix("ltm_"))
        spec = CONCEPT_BY_ID.get(concept_id)
        ltm_overlays.append(
            {
                "ops_node_id": node_id,
                "ltm_concept_id": concept_id,
                "label_ko": (spec.label_ko if spec else node.get("label_ko")),
                "lane_hint": (spec.lane_hint if spec else None),
                "char_count": node.get("char_count"),
                "wire_layer": "ops_memory_governance",
                "a2a_handoff_mode": "essence_plus_must_keep_tags",
            }
        )

    graph_concepts = graph.get("concepts") or {}
    a2a_bridge_concepts = [
        cid
        for cid in graph_concepts
        if cid.startswith("a2a_") or cid in ("inter_agent_encoding_smoke_chain", "ltm_ops_inject_to_a2a_wire")
    ]

    routing_profiles = (
        (wire.get("layers") or {}).get("routing") or {}
    ).get("profiles") or []

    return {
        "schema": "ltm_a2a_bridge_map_v1",
        "track": "B",
        "research_only": True,
        "boundary_ack": wall.get("boundary_ack") or "[HYPO] bridge map — no auto promotion",
        "forbidden_auto_merge": wall.get("forbidden_auto_merge") or [],
        "a2a_architecture_schema": a2a.get("schema"),
        "a2a_layers": a2a.get("layers") or [],
        "wire_profile_schema": wire.get("schema"),
        "wire_routing_profiles": routing_profiles,
        "wire_operations": wire.get("operations") or {},
        "ltm_overlay_count": len(ltm_overlays),
        "ltm_overlays": ltm_overlays,
        "a2a_bridge_concept_ids": a2a_bridge_concepts,
        "tp_pilots": (
            (wire.get("a2a_target_points_v1") or {}).get("tp_pilots") or []
        ),
        "smoke_runner": "scripts/Invoke-MkmInterAgentEncodingSmoke_v1.ps1",
        "graph_concept_count": graph.get("concept_count"),
        "ops_index_node_count": len(nodes),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    root = args.workspace_root.resolve()

    if not (root / DEFAULT_GRAPH_PATH.relative_to(SCRIPT_ROOT)).is_file():
        print("FAIL: LTM graph missing — run build_mkm_long_term_memory_graph_v1.py", file=sys.stderr)
        return 1
    if not (root / DEFAULT_INDEX_PATH.relative_to(SCRIPT_ROOT)).is_file():
        print("FAIL: ops index missing — run build_mkm_ops_memory_index_v1.py", file=sys.stderr)
        return 1

    doc = build_map(root)
    if doc["ltm_overlay_count"] < 1:
        print("FAIL: no ltm_* overlay nodes in ops index", file=sys.stderr)
        return 1
    if len(doc["a2a_bridge_concept_ids"]) < 3:
        print("FAIL: a2a bridge concepts missing from graph", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(
        f"ltm_overlays={doc['ltm_overlay_count']} "
        f"a2a_bridge_concepts={len(doc['a2a_bridge_concept_ids'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
