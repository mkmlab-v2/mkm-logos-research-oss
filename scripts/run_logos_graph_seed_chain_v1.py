#!/usr/bin/env python3
"""DF-P1-01: Seed nodes → BFS on graph slice → verse_id chain (research only)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "logos_graph_seed_chain_v1"
VERSION = "1.0.0"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _node_kind(node_id: str, nodes_by_id: dict[str, dict[str, Any]]) -> str:
    row = nodes_by_id.get(node_id) or {}
    return str(row.get("kind") or "other")


def _is_verse(node_id: str, nodes_by_id: dict[str, dict[str, Any]]) -> bool:
    return _node_kind(node_id, nodes_by_id) == "verse"


def _build_adjacency(edges: list[dict[str, Any]]) -> dict[str, list[str]]:
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        src = str(edge.get("src") or edge.get("src_node_id") or "")
        dst = str(edge.get("dst") or edge.get("dst_node_id") or "")
        if not src or not dst:
            continue
        adj[src].append(dst)
        adj[dst].append(src)
    return adj


def _default_seeds(graph: dict[str, Any], seed_count: int) -> list[str]:
    selection = graph.get("selection") or {}
    from_selection = list(selection.get("seed_source_node_ids") or [])
    if from_selection:
        return [str(x) for x in from_selection[:seed_count]]
    nodes = graph.get("nodes") or []
    ranked = sorted(
        (n for n in nodes if n.get("id")),
        key=lambda n: float(n.get("hub_score") or 0),
        reverse=True,
    )
    seeds: list[str] = []
    for node in ranked:
        nid = str(node["id"])
        if _node_kind(nid, {nid: node}) in ("theme", "regime", "verse"):
            seeds.append(nid)
        if len(seeds) >= seed_count:
            break
    return seeds


def bfs_verse_chain(
    graph: dict[str, Any],
    seed_ids: list[str],
    *,
    max_hops: int,
    max_verses: int,
) -> tuple[list[str], list[str]]:
    nodes = graph.get("nodes") or []
    nodes_by_id = {str(n["id"]): n for n in nodes if n.get("id")}
    adj = _build_adjacency(list(graph.get("edges") or []))

    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque()
    for sid in seed_ids:
        if sid in nodes_by_id:
            visited.add(sid)
            queue.append((sid, 0))

    verse_ids: list[str] = []
    visit_order: list[str] = []

    while queue and len(verse_ids) < max_verses:
        node_id, hop = queue.popleft()
        visit_order.append(node_id)
        if _is_verse(node_id, nodes_by_id) and node_id not in verse_ids:
            verse_ids.append(node_id)
        if hop >= max_hops:
            continue
        for nb in adj.get(node_id, []):
            if nb not in visited and nb in nodes_by_id:
                visited.add(nb)
                queue.append((nb, hop + 1))

    return verse_ids, visit_order


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--graph-json",
        default="projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_graph_slice_v1.json",
    )
    parser.add_argument(
        "--out-json",
        default="docs/final/artifacts/logos_graph_seed_chain_v1_latest.json",
    )
    parser.add_argument("--seed-count", type=int, default=8)
    parser.add_argument("--max-hops", type=int, default=3)
    parser.add_argument("--max-verses", type=int, default=48)
    parser.add_argument("--seed-ids", default="", help="Comma-separated seed node ids (optional)")
    args = parser.parse_args()

    graph_path = ROOT / args.graph_json
    if not graph_path.is_file():
        print(f"missing graph: {graph_path}", file=sys.stderr)
        return 1

    graph = _load(graph_path)
    if args.seed_ids.strip():
        seed_ids = [s.strip() for s in args.seed_ids.split(",") if s.strip()]
    else:
        seed_ids = _default_seeds(graph, max(1, args.seed_count))

    if not seed_ids:
        print("no seeds", file=sys.stderr)
        return 1

    verse_ids, visit_order = bfs_verse_chain(
        graph,
        seed_ids,
        max_hops=max(0, args.max_hops),
        max_verses=max(1, args.max_verses),
    )
    if len(verse_ids) < 1:
        print("no verse nodes reached from seeds", file=sys.stderr)
        return 1

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": VERSION,
        "generated_at_utc": generated_at,
        "hypothesis_tier": "[HYPO]",
        "policy": {"research_only": True, "non_gating": True, "track_wall": "B_track_not_track_A"},
        "inputs": {"graph_json": str(graph_path.relative_to(ROOT)).replace("\\", "/")},
        "seeds": {"seed_node_ids": seed_ids, "count": len(seed_ids)},
        "graph_rag": {
            "verse_node_ids": verse_ids,
            "verse_count": len(verse_ids),
            "visit_order_node_ids": visit_order[:32],
            "max_hops": args.max_hops,
        },
        "boundary_ack": "BFS on capped showroom graph slice only; not full 31k graph load.",
    }

    out_path = ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(out_path), "verse_count": len(verse_ids), "seed_count": len(seed_ids)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
