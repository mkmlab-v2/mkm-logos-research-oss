#!/usr/bin/env python3
"""GraphRAG pilot router (Track B/K observation-only).

Uses existing FACT artifacts only:
- docs/final/artifacts/global_atom_network_nodes_latest.jsonl
- docs/final/artifacts/global_atom_network_edges_latest.jsonl
- docs/final/artifacts/multi_symbol_gate_summary_latest.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_NODES = ROOT / "docs/final/artifacts/global_atom_network_nodes_latest.jsonl"
DEFAULT_EDGES = ROOT / "docs/final/artifacts/global_atom_network_edges_latest.jsonl"
DEFAULT_GATE = ROOT / "docs/final/artifacts/multi_symbol_gate_summary_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/graphrag_pilot_router_latest.json"

ARTIFACT_SCHEMA = "graphrag_pilot_router_v1"
VERSION = "1.0.0"

TOKEN_RE = re.compile(r"[A-Za-z0-9_가-힣]+")
KEYWORD_ALIASES: dict[str, list[str]] = {
    "바벨": ["babel", "babel_tower"],
    "출애굽": ["exodus", "exodus_return"],
    "빛": ["light"],
    "어둠": ["dark", "darkness"],
    "선악과": ["tree_of_knowledge_good_evil", "knowledge"],
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return obj


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            o = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            rows.append(o)
    return rows


def _keywords(question: str) -> list[str]:
    toks = [m.group(0).lower() for m in TOKEN_RE.finditer(question)]
    # Preserve order while deduplicating.
    out: list[str] = []
    seen: set[str] = set()
    for t in toks:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
        for a in KEYWORD_ALIASES.get(t, []):
            aa = a.lower()
            if aa in seen:
                continue
            seen.add(aa)
            out.append(aa)
    return out


def _node_text(node: dict[str, Any]) -> str:
    parts: list[str] = []
    for k in ("node_id", "candidate_id", "assigned_symbol", "regime_tag"):
        v = node.get(k)
        if isinstance(v, str):
            parts.append(v)
    atom_seq = node.get("atom_sequence")
    if isinstance(atom_seq, list):
        for a in atom_seq:
            if isinstance(a, str):
                parts.append(a)
    return " ".join(parts).lower()


def _seed_nodes(nodes: list[dict[str, Any]], kws: list[str], topk: int) -> list[dict[str, Any]]:
    scored: list[tuple[int, dict[str, Any]]] = []
    for n in nodes:
        text = _node_text(n)
        score = sum(1 for kw in kws if kw and kw in text)
        if score > 0:
            scored.append((score, n))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [n for _, n in scored[:topk]]


def _build_graph(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    min_similarity: float,
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    node_map: dict[str, dict[str, Any]] = {}
    for n in nodes:
        nid = n.get("node_id")
        if isinstance(nid, str) and nid.strip():
            node_map[nid] = n

    adj: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in edges:
        src = e.get("source")
        dst = e.get("target")
        if not (isinstance(src, str) and isinstance(dst, str)):
            continue
        if src not in node_map or dst not in node_map:
            continue
        sim = e.get("similarity", 0.0)
        if not isinstance(sim, (int, float)):
            continue
        if float(sim) < min_similarity:
            continue
        gate_passed = bool(e.get("gate_passed", False))
        if not gate_passed:
            continue
        adj[src].append(
            {
                "target": dst,
                "similarity": float(sim),
                "edge_type": e.get("edge_type"),
                "gate_passed": gate_passed,
            }
        )
    return node_map, adj


def _multi_hop_expand(
    seed_ids: list[str],
    adj: dict[str, list[dict[str, Any]]],
    max_hops: int,
    max_edges: int,
) -> tuple[set[str], list[dict[str, Any]]]:
    visited: set[str] = set(seed_ids)
    q: deque[tuple[str, int]] = deque((sid, 0) for sid in seed_ids)
    traversed: list[dict[str, Any]] = []

    while q and len(traversed) < max_edges:
        cur, depth = q.popleft()
        if depth >= max_hops:
            continue
        for e in adj.get(cur, []):
            if len(traversed) >= max_edges:
                break
            nxt = e["target"]
            traversed.append(
                {
                    "source": cur,
                    "target": nxt,
                    "hop": depth + 1,
                    "similarity": e["similarity"],
                    "edge_type": e.get("edge_type"),
                    "gate_passed": e.get("gate_passed", True),
                }
            )
            if nxt not in visited:
                visited.add(nxt)
                q.append((nxt, depth + 1))
    return visited, traversed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--question", required=True, help="Natural-language question")
    ap.add_argument("--nodes-jsonl", type=Path, default=DEFAULT_NODES)
    ap.add_argument("--edges-jsonl", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--seed-topk", type=int, default=12)
    ap.add_argument("--max-hops", type=int, default=2)
    ap.add_argument("--max-edges", type=int, default=200)
    ap.add_argument("--min-similarity", type=float, default=0.9)
    ap.add_argument(
        "--emit-answer-brief",
        action="store_true",
        help="Include a short observation-only brief based on selected nodes.",
    )
    args = ap.parse_args()

    if not args.nodes_jsonl.is_file():
        print(f"Missing nodes JSONL: {args.nodes_jsonl}", file=sys.stderr)
        return 2
    if not args.edges_jsonl.is_file():
        print(f"Missing edges JSONL: {args.edges_jsonl}", file=sys.stderr)
        return 2
    if not args.gate_json.is_file():
        print(f"Missing gate JSON: {args.gate_json}", file=sys.stderr)
        return 2

    gate = _load_json(args.gate_json)
    status = (((gate.get("summary") or {}).get("status")) or "").upper()
    if status != "GO":
        print(
            f"Gate status is not GO (status={status or 'UNKNOWN'}); canceling run.",
            file=sys.stderr,
        )
        return 3

    nodes = _load_jsonl(args.nodes_jsonl)
    edges = _load_jsonl(args.edges_jsonl)
    node_map, adj = _build_graph(nodes, edges, min_similarity=args.min_similarity)

    kws = _keywords(args.question)
    seeds = _seed_nodes(nodes, kws, topk=max(1, args.seed_topk))
    seed_ids = [
        n["node_id"]
        for n in seeds
        if isinstance(n.get("node_id"), str) and n.get("node_id")
    ]

    expanded_nodes, traversed = _multi_hop_expand(
        seed_ids=seed_ids,
        adj=adj,
        max_hops=max(1, args.max_hops),
        max_edges=max(1, args.max_edges),
    )

    selected = []
    for nid in sorted(expanded_nodes):
        n = node_map.get(nid)
        if not n:
            continue
        selected.append(
            {
                "node_id": nid,
                "assigned_symbol": n.get("assigned_symbol"),
                "candidate_id": n.get("candidate_id"),
                "regime_tag": n.get("regime_tag"),
                "hub_score": n.get("hub_score"),
                "path_score": n.get("path_score"),
                "cluster_size": n.get("cluster_size"),
            }
        )

    out = {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "ts_utc": _now_utc(),
        "research_only": True,
        "observation_only": True,
        "source_track": "K",
        "hypothesis_tier": "B",
        "question": args.question,
        "router_config": {
            "seed_topk": args.seed_topk,
            "max_hops": args.max_hops,
            "max_edges": args.max_edges,
            "min_similarity": args.min_similarity,
        },
        "fact_lock": {
            "gate_path": str(args.gate_json.resolve()),
            "gate_status": status,
            "nodes_path": str(args.nodes_jsonl.resolve()),
            "edges_path": str(args.edges_jsonl.resolve()),
        },
        "seed_keywords": kws,
        "seed_node_ids": seed_ids,
        "selected_nodes": selected,
        "traversed_edges": traversed,
        "answer_scaffold": {
            "status": "OBSERVATION_ONLY",
            "notes": [
                "[HYPO] Graph traversal result for research lane only.",
                "Do not use as A-track trading trigger.",
                "Require human commander review for any operational action.",
            ],
        },
    }

    if args.emit_answer_brief:
        symbol_counts: dict[str, int] = defaultdict(int)
        for row in selected:
            sym = row.get("assigned_symbol")
            if isinstance(sym, str) and sym:
                symbol_counts[sym] += 1
        top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        out["answer_brief"] = {
            "mode": "OBSERVATION_ONLY",
            "text": (
                "GraphRAG pilot observation: selected symbols are concentrated around "
                + ", ".join(f"{k}({v})" for k, v in top_symbols)
                if top_symbols
                else "GraphRAG pilot observation: no matched seed/symbol was found for the current query."
            ),
            "top_symbols": [{"symbol": k, "count": v} for k, v in top_symbols],
            "disclaimer": "[HYPO] Research lane output only; not an operational trigger.",
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
