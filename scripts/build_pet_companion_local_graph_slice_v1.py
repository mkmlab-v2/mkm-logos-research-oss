#!/usr/bin/env python3
"""Build capped local graph slice for pet companion observation bridges ([HYPO], on-device cap)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/pet_companion_observation_bridge_registry_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/pet_companion_local_graph_slice_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def build_slice(registry: dict[str, Any], *, max_nodes: int, max_edges: int) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    def add_node(node: dict[str, Any]) -> None:
        if len(nodes) >= max_nodes:
            return
        nid = str(node.get("node_id") or "")
        if nid and nid not in nodes:
            nodes[nid] = node

    def add_edge(src: str, dst: str, relation: str) -> None:
        if len(edges) >= max_edges:
            return
        if not src or not dst:
            return
        edges.append({"source": src, "target": dst, "relation": relation})

    for entry in registry.get("entries") or []:
        if not isinstance(entry, dict) or not entry.get("present"):
            continue
        rel = entry.get("artifact_path")
        if not isinstance(rel, str):
            continue
        bridge = _load_json(ROOT / rel)
        if not bridge:
            continue
        for node in bridge.get("nodes") or []:
            if isinstance(node, dict):
                add_node(node)
        for path in bridge.get("paths") or []:
            if not isinstance(path, dict):
                continue
            for step in path.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                add_edge(str(step.get("from") or ""), str(step.get("to") or ""), str(step.get("relation") or "LINK"))

    return {
        "schema": "pet_companion_local_graph_slice_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "max_nodes_cap": max_nodes,
        "max_edges_cap": max_edges,
        "nodes": list(nodes.values()),
        "edges": edges,
        "policy": {
            "on_device_cap_enforced": len(nodes) <= max_nodes and len(edges) <= max_edges,
            "must_not_merge_with": ["logos_bible_subgraph", "mkm_ops_memory_graph"],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry-json", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-nodes", type=int, default=128)
    ap.add_argument("--max-edges", type=int, default=140)
    args = ap.parse_args()

    reg_path = args.registry_json if args.registry_json.is_absolute() else ROOT / args.registry_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    registry = _load_json(reg_path)
    if not registry:
        raise SystemExit(f"missing registry: {reg_path}")

    doc = build_slice(registry, max_nodes=max(1, args.max_nodes), max_edges=max(1, args.max_edges))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "node_count": doc["node_count"], "edge_count": doc["edge_count"], "out": str(out_path)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
