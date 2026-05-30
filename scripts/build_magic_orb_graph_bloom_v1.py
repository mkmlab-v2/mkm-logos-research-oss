#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build magic_orb_graph_bloom_v1 for Magic Orb STEP 2 canvas ([HYPO], NON_GATING)."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
DEFAULT_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/magic_orb_graph_bloom_v1_latest.json"

SCHEMA = "magic_orb_graph_bloom_v1"
VERSION = "1.0.0"
NODE_CAP = 48
EDGE_CAP = 56

DISCLAIMER_KO = (
    "질문 기준 활성화 부분 망(observation)입니다. [HYPO][NON_GATING] — "
    "신학·예언 확정·실매매·Track A 근거 아님."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _slug_id(raw: str, kind: str) -> str:
    clean = re.sub(r"[^\w.:가-힣/-]+", "_", raw)[:96]
    return f"{kind}::{clean}"


def _kind_from_step(step: str) -> str:
    if step.startswith("verse:"):
        return "verse"
    if step.startswith("concept:"):
        return "concept"
    if step.startswith("lemma:"):
        return "lemma"
    if step.startswith("function:"):
        return "theme"
    return "other"


def _label_from_step(step: str) -> str:
    if step.startswith("verse:"):
        return step.split(":", 1)[1]
    tail = step.split(":")[-1]
    return tail.replace("_", " ")


def _node_from_step(step: str) -> dict[str, Any]:
    kind = _kind_from_step(step)
    node_id = _slug_id(step, kind)
    row: dict[str, Any] = {
        "id": node_id,
        "label": _label_from_step(step),
        "kind": kind,
        "hub_score": 0.72 if kind == "verse" else 0.58,
    }
    if kind == "verse":
        row["ref"] = _label_from_step(step)
    return row


def _verse_node_id(vid: str) -> str:
    if "::" in vid:
        return vid if vid.count("::") >= 1 else _slug_id(vid, "verse")
    return _slug_id(f"verse:{vid}", "verse")


def _verse_label(vid: str) -> str:
    if "::" in vid:
        return vid.split("::", 1)[-1]
    return vid.replace("verse:", "")


def bloom_from_router_paths(
    query: str,
    router: dict[str, Any],
    *,
    ann_top_verse_ids: list[str] | None = None,
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_edges: set[tuple[str, str, str]] = set()

    def add_node(n: dict[str, Any]) -> None:
        if n["id"] in seen_nodes or len(nodes) >= NODE_CAP:
            return
        seen_nodes.add(n["id"])
        nodes.append(n)

    def add_edge(src: str, dst: str, edge_type: str = "path_step", weight: float = 0.65) -> None:
        if src not in seen_nodes or dst not in seen_nodes:
            return
        key = (src, dst, edge_type)
        if key in seen_edges or len(edges) >= EDGE_CAP:
            return
        seen_edges.add(key)
        edges.append({"src": src, "dst": dst, "edge_type": edge_type, "weight": weight})

    q = query.strip()
    if q:
        add_node({"id": "query::center", "label": q[:48], "kind": "query", "hub_score": 1.0})

    for path in router.get("paths") or []:
        if not isinstance(path, dict):
            continue
        steps = path.get("steps") or []
        prev: str | None = None
        for step in steps:
            if not isinstance(step, str):
                continue
            n = _node_from_step(step)
            add_node(n)
            if prev:
                add_edge(prev, n["id"], "path_step", 0.7)
            elif seen_nodes and "query::center" in seen_nodes:
                add_edge("query::center", n["id"], "query_anchor", 0.85)
            prev = n["id"]

    for vid in router.get("verse_ids") or []:
        if not isinstance(vid, str):
            continue
        nid = _verse_node_id(vid)
        row_v: dict[str, Any] = {
            "id": nid,
            "label": _verse_label(vid),
            "kind": "verse",
            "hub_score": 0.62,
            "ref": _verse_label(vid),
        }
        if "::" in vid:
            row_v["corpus"] = vid.split("::")[0]
        add_node(row_v)
        if "query::center" in seen_nodes:
            add_edge("query::center", nid, "verse_ref", 0.5)

    for vid in ann_top_verse_ids or []:
        if not isinstance(vid, str):
            continue
        nid = _verse_node_id(vid)
        add_node(
            {
                "id": nid,
                "label": _verse_label(vid),
                "kind": "verse",
                "hub_score": 0.5,
                "ref": _verse_label(vid),
            }
        )
        if "query::center" in seen_nodes:
            add_edge("query::center", nid, "ann_lite", 0.45)

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "seed_query": q or router.get("query"),
        "disclaimer_ko": DISCLAIMER_KO,
        "stats": {"node_count": len(nodes), "edge_count": len(edges)},
        "nodes": nodes,
        "edges": edges,
        "source": {"kind": "logos_subgraph_router_paths", "router_schema": router.get("schema")},
    }


def _expand_graph_seeds(
    seed_ids: set[str],
    nodes_path: Path,
    edges_path: Path,
    *,
    max_nodes: int,
    max_edges: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Minimal subgraph expansion (same algorithm as showroom slice)."""
    selected = set(seed_ids)
    pending_edges: list[dict[str, Any]] = []
    neighbor_score: dict[str, float] = defaultdict(float)

    for row in _iter_jsonl(edges_path):
        src = str(row.get("src_node_id") or "")
        dst = str(row.get("dst_node_id") or "")
        if not src or not dst:
            continue
        weight = float(row.get("weight") or 0.5)
        edge_type = str(row.get("edge_type") or "link")
        if src in selected or dst in selected:
            pending_edges.append(
                {"src": src, "dst": dst, "edge_type": edge_type, "weight": weight}
            )
            other = dst if src in selected else src
            if other not in selected:
                neighbor_score[other] += weight

    while len(selected) < max_nodes:
        ranked = sorted(neighbor_score.items(), key=lambda x: x[1], reverse=True)
        if not ranked:
            break
        added = 0
        for node_id, _ in ranked:
            if len(selected) >= max_nodes:
                break
            if node_id not in selected:
                selected.add(node_id)
                added += 1
        if added == 0:
            break
        neighbor_score = defaultdict(float)
        pending_edges = []
        for row in _iter_jsonl(edges_path):
            src = str(row.get("src_node_id") or "")
            dst = str(row.get("dst_node_id") or "")
            if not src or not dst:
                continue
            weight = float(row.get("weight") or 0.5)
            edge_type = str(row.get("edge_type") or "link")
            if src in selected or dst in selected:
                pending_edges.append(
                    {"src": src, "dst": dst, "edge_type": edge_type, "weight": weight}
                )
                other = dst if src in selected else src
                if other not in selected:
                    neighbor_score[other] += weight

    nodes_index: dict[str, dict[str, Any]] = {}
    for row in _iter_jsonl(nodes_path):
        nid = row.get("node_id")
        if nid:
            nodes_index[str(nid)] = row

    def node_kind(raw: dict[str, Any]) -> str:
        kind = str(raw.get("kind") or "").lower()
        if kind in ("theme", "regime"):
            return kind
        if raw.get("ref") or raw.get("corpus"):
            return "verse"
        return "other"

    nodes_out: list[dict[str, Any]] = []
    for node_id in sorted(selected):
        raw = nodes_index.get(node_id)
        if not raw:
            continue
        kind = node_kind(raw)
        label = str(raw.get("label") or raw.get("ref") or node_id.split("::")[-1])
        row: dict[str, Any] = {"id": node_id, "label": label, "kind": kind}
        if raw.get("corpus"):
            row["corpus"] = raw["corpus"]
        if raw.get("ref"):
            row["ref"] = raw["ref"]
        if kind == "verse":
            row["hub_score"] = 0.55
        nodes_out.append(row)

    pending_edges.sort(key=lambda e: float(e["weight"]), reverse=True)
    edges_out: list[dict[str, Any]] = []
    seen_edge: set[tuple[str, str, str]] = set()
    for edge in pending_edges:
        if edge["src"] not in selected or edge["dst"] not in selected:
            continue
        key = (edge["src"], edge["dst"], edge["edge_type"])
        if key in seen_edge:
            continue
        seen_edge.add(key)
        edges_out.append(edge)
        if len(edges_out) >= max_edges:
            break

    return nodes_out, edges_out


def merge_bloom(
    base: dict[str, Any],
    extra_nodes: list[dict[str, Any]],
    extra_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = list(base.get("nodes") or [])
    edges = list(base.get("edges") or [])
    seen_n = {n["id"] for n in nodes}
    seen_e = {(e["src"], e["dst"], e.get("edge_type", "")) for e in edges}

    for n in extra_nodes:
        if n["id"] in seen_n or len(nodes) >= NODE_CAP:
            continue
        seen_n.add(n["id"])
        nodes.append(n)

    for e in extra_edges:
        key = (e["src"], e["dst"], e.get("edge_type", ""))
        if key in seen_e or len(edges) >= EDGE_CAP:
            continue
        if e["src"] not in seen_n or e["dst"] not in seen_n:
            continue
        seen_e.add(key)
        edges.append(e)

    out = dict(base)
    out["nodes"] = nodes
    out["edges"] = edges
    out["stats"] = {"node_count": len(nodes), "edge_count": len(edges)}
    out["generated_at_utc"] = _utc_now()
    return out


def bloom_from_topology_slice(slice_doc: dict[str, Any], query: str) -> dict[str, Any]:
    nodes = list(slice_doc.get("nodes") or [])[:NODE_CAP]
    edges = list(slice_doc.get("edges") or [])[:EDGE_CAP]
    if query.strip():
        for n in nodes:
            if n.get("id") == "query::center":
                n["label"] = query.strip()[:48]
                break
        else:
            nodes.insert(
                0,
                {"id": "query::center", "label": query.strip()[:48], "kind": "query", "hub_score": 1.0},
            )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "seed_query": query.strip() or slice_doc.get("seed_query"),
        "disclaimer_ko": DISCLAIMER_KO,
        "stats": {"node_count": len(nodes), "edge_count": len(edges)},
        "nodes": nodes,
        "edges": edges,
        "source": {"kind": "showroom_meaning_topology_graph_slice_v1"},
    }


def build_bloom(
    *,
    query: str,
    router: dict[str, Any] | None,
    ann_top_verse_ids: list[str] | None = None,
    expand_graph: bool = False,
    nodes_path: Path = DEFAULT_NODES,
    edges_path: Path = DEFAULT_EDGES,
    topology_slice: dict[str, Any] | None = None,
    lod_node_cap: int = 48,
    lod_edge_cap: int = 56,
) -> dict[str, Any]:
    global NODE_CAP, EDGE_CAP
    NODE_CAP = min(48, max(8, lod_node_cap))
    EDGE_CAP = min(56, max(8, lod_edge_cap))

    if topology_slice and topology_slice.get("nodes"):
        base = bloom_from_topology_slice(topology_slice, query)
    elif router:
        base = bloom_from_router_paths(query, router, ann_top_verse_ids=ann_top_verse_ids)
    else:
        raise ValueError("router or topology_slice required")

    if not expand_graph or not router:
        return base

    seeds: set[str] = set()
    for vid in router.get("verse_ids") or []:
        if isinstance(vid, str):
            seeds.add(vid)
    for vid in router.get("seed_chain_verse_sample") or []:
        if isinstance(vid, str):
            seeds.add(vid)
    for step_path in router.get("paths") or []:
        for step in (step_path.get("steps") or []) if isinstance(step_path, dict) else []:
            if isinstance(step, str) and step.startswith("verse:"):
                ref = step.split(":", 1)[1]
                seeds.add(f"hebrew::{ref}")

    room = NODE_CAP - len(base.get("nodes") or [])
    if room < 4 or not nodes_path.is_file() or not edges_path.is_file():
        return base

    extra_nodes, extra_edges = _expand_graph_seeds(
        seeds,
        nodes_path,
        edges_path,
        max_nodes=room + len(seeds),
        max_edges=EDGE_CAP - len(base.get("edges") or []),
    )
    return merge_bloom(base, extra_nodes, extra_edges)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build magic_orb_graph_bloom_v1 JSON.")
    ap.add_argument("--query", required=True)
    ap.add_argument("--router-json", type=Path, default=ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json")
    ap.add_argument("--topology-slice-json", type=Path, default=None)
    ap.add_argument("--nodes-jsonl", type=Path, default=DEFAULT_NODES)
    ap.add_argument("--edges-jsonl", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--expand-graph", action="store_true")
    ap.add_argument("--ann-verse-ids", default="", help="comma-separated verse refs")
    ap.add_argument("--lod-node-cap", type=int, default=48)
    ap.add_argument("--lod-edge-cap", type=int, default=56)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    router = _load_json(args.router_json) if args.router_json.is_file() else None
    slice_doc = _load_json(args.topology_slice_json) if args.topology_slice_json and args.topology_slice_json.is_file() else None
    ann_ids = [x.strip() for x in args.ann_verse_ids.split(",") if x.strip()]

    doc = build_bloom(
        query=args.query,
        router=router,
        ann_top_verse_ids=ann_ids or None,
        expand_graph=args.expand_graph,
        nodes_path=args.nodes_jsonl,
        edges_path=args.edges_jsonl,
        topology_slice=slice_doc,
        lod_node_cap=args.lod_node_cap,
        lod_edge_cap=args.lod_edge_cap,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "nodes": doc["stats"]["node_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
