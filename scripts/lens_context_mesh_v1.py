#!/usr/bin/env python3
"""Lens context mesh core — Obsidian-style hop index + BFS depth expand [HYPO]."""
from __future__ import annotations

import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_LOGOS_SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_LOGOS_LATTICE = ROOT / "docs/final/artifacts/showroom_era_insight_lattice_v1_latest.json"
DEFAULT_LOGOS_LATTICE_GENESIS = ROOT / "docs/final/artifacts/showroom_era_insight_lattice_genesis_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_hop_index_from_slice(
    slice_doc: dict[str, Any],
    *,
    lens_id: str = "logos",
    pack_id: str = "lens_pack@logos_showroom",
    source_slice_path: str | None = None,
) -> dict[str, Any]:
    """Undirected adjacency from a capped graph slice (Obsidian local-graph substrate)."""
    nodes_block: dict[str, dict[str, Any]] = {}
    pair_seen: set[tuple[str, str]] = set()

    for n in slice_doc.get("nodes") or []:
        nid = str(n.get("id") or "")
        if nid:
            nodes_block.setdefault(nid, {"neighbors": []})

    for e in slice_doc.get("edges") or []:
        src = str(e.get("src") or "")
        dst = str(e.get("dst") or "")
        if not src or not dst:
            continue
        nodes_block.setdefault(src, {"neighbors": []})
        nodes_block.setdefault(dst, {"neighbors": []})
        key = tuple(sorted((src, dst)))
        if key in pair_seen:
            continue
        pair_seen.add(key)
        edge_type = str(e.get("edge_type") or "link")
        weight = float(e.get("weight") or 0.5)
        entry = {"id": dst, "edge_type": edge_type, "weight": weight}
        entry_rev = {"id": src, "edge_type": edge_type, "weight": weight}
        nodes_block[src]["neighbors"].append(entry)
        nodes_block[dst]["neighbors"].append(entry_rev)

    for nid, block in nodes_block.items():
        block["neighbors"].sort(key=lambda x: (-float(x.get("weight") or 0), str(x.get("id"))))

    return {
        "schema_version": "lens_context_mesh_hop_index_v1",
        "generated_at_utc": _utc(),
        "lens_id": lens_id,
        "pack_id": pack_id,
        "source_slice_schema": str(slice_doc.get("schema_version") or "showroom_meaning_topology_graph_slice_v1"),
        "source_slice_path": source_slice_path,
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "stats": {
            "node_count": len(nodes_block),
            "undirected_edge_pairs": len(pair_seen),
        },
        "nodes": nodes_block,
        "reproduce": "py scripts/build_lens_context_mesh_hop_index_v1.py",
    }


def bfs_node_ids(
    hop_index: dict[str, Any],
    seed_ids: list[str],
    *,
    depth: int = 2,
    max_nodes: int = 40,
) -> list[str]:
    """BFS expand from one or more seeds — Obsidian local graph depth."""
    nodes = hop_index.get("nodes") if isinstance(hop_index.get("nodes"), dict) else {}
    if not nodes:
        return []

    depth = max(1, min(int(depth), 8))
    max_nodes = max(1, int(max_nodes))
    seeds = [s for s in seed_ids if s in nodes]
    if not seeds:
        seeds = [next(iter(nodes))]

    seen: set[str] = set()
    order: list[str] = []
    q: deque[tuple[str, int]] = deque()
    for s in seeds:
        if s not in seen:
            seen.add(s)
            order.append(s)
            q.append((s, 0))

    while q and len(order) < max_nodes:
        node_id, d = q.popleft()
        if d >= depth:
            continue
        block = nodes.get(node_id) or {}
        for nb in block.get("neighbors") or []:
            nid = str(nb.get("id") or "")
            if not nid or nid in seen:
                continue
            seen.add(nid)
            order.append(nid)
            q.append((nid, d + 1))
            if len(order) >= max_nodes:
                break
    return order


def filter_slice_to_nodes(slice_doc: dict[str, Any], keep_ids: set[str]) -> dict[str, Any]:
    out = dict(slice_doc)
    out["nodes"] = [n for n in slice_doc.get("nodes") or [] if str(n.get("id")) in keep_ids]
    present = {str(n.get("id")) for n in out["nodes"]}
    out["edges"] = [
        e
        for e in slice_doc.get("edges") or []
        if str(e.get("src")) in present and str(e.get("dst")) in present
    ]
    stats = dict(slice_doc.get("stats") or {})
    stats["node_count"] = len(out["nodes"])
    stats["edge_count"] = len(out["edges"])
    out["stats"] = stats
    return out


def build_hub_logos(
    *,
    slice_path: Path = DEFAULT_LOGOS_SLICE,
    hop_index_path: Path,
    lattice_path: Path = DEFAULT_LOGOS_LATTICE,
    lattice_genesis_path: Path = DEFAULT_LOGOS_LATTICE_GENESIS,
) -> dict[str, Any]:
    rel = lambda p: str(p.relative_to(ROOT)).replace("\\", "/") if p.is_relative_to(ROOT) else str(p)
    return {
        "schema_version": "lens_context_mesh_hub_v1",
        "generated_at_utc": _utc(),
        "lens_id": "logos",
        "pack_id": "lens_pack@logos_showroom",
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "non_gating": True,
        "ui_contract": {
            "default_depth": 2,
            "max_depth": 4,
            "max_focus_nodes": 40,
            "hide_orphans_default": True,
            "layout_mode": "obsidian_local",
        },
        "artifacts": {
            "graph_slice": rel(slice_path),
            "hop_index": rel(hop_index_path),
            "insight_lattice": rel(lattice_path) if lattice_path.is_file() else None,
            "insight_lattice_genesis": rel(lattice_genesis_path) if lattice_genesis_path.is_file() else None,
        },
        "legacy_pointers": {
            "showroom_v6_html": "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_logos_oracle_v6.html",
            "parallel_advisory_contract": "docs/final/MKM_PARALLEL_ADVISORY_LENS_CONTRACT_V1.md",
            "ontology_constitution": "docs/final/MKM_LENS_ONTOLOGY_CONSTITUTION_V1.md",
        },
        "reproduce": "py scripts/run_lens_context_mesh_logos_chain_v1.py",
    }
