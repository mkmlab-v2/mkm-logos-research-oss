#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build global atom topology PoC network from core candidates.")
    ap.add_argument("--insight-json", default="docs/final/artifacts/bible_meaning_insight_candidates_latest.json")
    ap.add_argument("--registry-json", default="docs/final/artifacts/atom_anchor_registry_v1.json")
    ap.add_argument("--top-n", type=int, default=100)
    ap.add_argument("--min-similarity", type=float, default=0.70)
    ap.add_argument("--nodes-out-jsonl", default="docs/final/artifacts/global_atom_network_nodes_latest.jsonl")
    ap.add_argument("--edges-out-jsonl", default="docs/final/artifacts/global_atom_network_edges_latest.jsonl")
    ap.add_argument("--matrix-out-json", default="docs/final/artifacts/global_atom_network_similarity_matrix_latest.json")
    ap.add_argument("--phase-report-out-json", default="docs/final/artifacts/global_atom_network_phase_transition_report_latest.json")
    ap.add_argument("--write-matrix", action="store_true")
    ap.add_argument("--max-edges", type=int, default=0, help="0 means unlimited; otherwise cap number of kept edges.")
    args = ap.parse_args()

    ip = resolve(args.insight_json)
    rp = resolve(args.registry_json)
    nodes_out = resolve(args.nodes_out_jsonl)
    edges_out = resolve(args.edges_out_jsonl)
    matrix_out = resolve(args.matrix_out_json)
    phase_out = resolve(args.phase_report_out_json)

    for p in (ip, rp):
        if not p.is_file():
            raise SystemExit(f"missing required input: {p}")

    insights = load(ip)
    registry = load(rp)
    candidates = insights.get("candidates") if isinstance(insights.get("candidates"), list) else []
    atoms = registry.get("atoms") if isinstance(registry.get("atoms"), list) else []
    seq_map = registry.get("seed_symbol_sequences") if isinstance(registry.get("seed_symbol_sequences"), dict) else {}

    atom_ids = [str(a.get("atom_id")) for a in atoms if isinstance(a, dict) and str(a.get("atom_id", ""))]
    if not atom_ids:
        raise SystemExit("atom registry has no atom_ids")
    atom_index = {aid: i for i, aid in enumerate(atom_ids)}
    symbol_order = ["tree_of_knowledge_good_evil", "babel_tower", "exodus_return"]
    symbol_vectors_4d = {
        "tree_of_knowledge_good_evil": [0.790868, 0.803868, 0.745368, 0.771368],
        "babel_tower": [0.735035, 0.696035, 0.709035, 0.676535],
        "exodus_return": [0.616868, 0.655868, 0.603868, 0.551868],
    }

    n = max(1, int(args.top_n))
    selected = [c for c in candidates if isinstance(c, dict)][:n]
    node_rows: list[dict[str, Any]] = []
    vectors: list[list[float]] = []

    for i, c in enumerate(selected):
        symbol = symbol_order[i % len(symbol_order)]
        seq = list(seq_map.get(symbol) or [])
        atom_vec = [0.0] * len(atom_ids)
        for aid in seq:
            idx = atom_index.get(str(aid))
            if idx is not None:
                atom_vec[idx] = 1.0

        hub = float(c.get("hub_score", 0.0) or 0.0)
        path = float(c.get("path_score", 0.0) or 0.0)
        cluster = float(c.get("cluster_size", 0.0) or 0.0) / 10.0
        vec4 = symbol_vectors_4d[symbol]
        full_vec = atom_vec + vec4 + [hub, path, cluster]
        vectors.append(full_vec)

        node_rows.append(
            {
                "node_id": str(c.get("source_node_id", f"node_{i+1}")),
                "candidate_id": str(c.get("candidate_id", f"cand_{i+1:03d}")),
                "assigned_symbol": symbol,
                "atom_sequence": seq,
                "vector_4d": {"S": vec4[0], "L": vec4[1], "K": vec4[2], "M": vec4[3]},
                "hub_score": round(hub, 6),
                "path_score": round(path, 6),
                "cluster_size": int(c.get("cluster_size", 0) or 0),
                "regime_tag": c.get("regime_tag", "unknown"),
            }
        )

    edges: list[dict[str, Any]] = []
    matrix: list[dict[str, Any]] = []
    min_sim = float(args.min_similarity)
    if vectors:
        vmat = np.asarray(vectors, dtype=np.float64)
        norms = np.linalg.norm(vmat, axis=1, keepdims=True)
        norms = np.where(norms == 0.0, 1.0, norms)
        vnorm = vmat / norms
        sim_mat = np.clip(np.matmul(vnorm, vnorm.T), 0.0, 1.0)
        sim_mat = np.round(sim_mat, 6)

        if bool(args.write_matrix):
            for i in range(len(node_rows)):
                matrix.append({"node_id": node_rows[i]["node_id"], "similarities": sim_mat[i].tolist()})

        tri_i, tri_j = np.where(np.triu(sim_mat, k=1) >= min_sim)
        if int(args.max_edges) > 0 and len(tri_i) > int(args.max_edges):
            tri_vals = sim_mat[tri_i, tri_j]
            keep_n = int(args.max_edges)
            pick = np.argpartition(tri_vals, -keep_n)[-keep_n:]
            tri_i = tri_i[pick]
            tri_j = tri_j[pick]
        for i, j in zip(tri_i.tolist(), tri_j.tolist()):
            edges.append(
                {
                    "source": node_rows[i]["node_id"],
                    "target": node_rows[j]["node_id"],
                    "similarity": float(sim_mat[i, j]),
                    "edge_type": "topological_resonance",
                    "gate_passed": True,
                }
            )

    old_symbols = {"tree_of_knowledge_good_evil", "babel_tower"}
    new_symbols = {"exodus_return"}
    old_count = sum(1 for nrow in node_rows if nrow["assigned_symbol"] in old_symbols)
    new_count = sum(1 for nrow in node_rows if nrow["assigned_symbol"] in new_symbols)
    cross_edges = sum(
        1
        for e in edges
        if (
            next((n["assigned_symbol"] for n in node_rows if n["node_id"] == e["source"]), "") in old_symbols
            and next((n["assigned_symbol"] for n in node_rows if n["node_id"] == e["target"]), "") in new_symbols
        )
        or (
            next((n["assigned_symbol"] for n in node_rows if n["node_id"] == e["source"]), "") in new_symbols
            and next((n["assigned_symbol"] for n in node_rows if n["node_id"] == e["target"]), "") in old_symbols
        )
    )
    phase_report = {
        "schema": "global_atom_network_phase_transition_report_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "summary": {
            "node_count": len(node_rows),
            "edge_count": len(edges),
            "old_symbol_nodes": old_count,
            "new_symbol_nodes": new_count,
            "old_new_cross_edges": cross_edges,
            "phase_transition_signal": "present" if cross_edges > 0 else "weak",
        },
        "note": "PoC topology report from selected core events; full canon scaling requires staged N^2 budget.",
    }

    nodes_out.parent.mkdir(parents=True, exist_ok=True)
    edges_out.parent.mkdir(parents=True, exist_ok=True)
    matrix_out.parent.mkdir(parents=True, exist_ok=True)
    phase_out.parent.mkdir(parents=True, exist_ok=True)

    nodes_out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in node_rows) + "\n", encoding="utf-8")
    edges_out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in edges) + "\n", encoding="utf-8")
    matrix_payload = {
        "schema": "global_atom_network_similarity_matrix_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "node_ids": [r["node_id"] for r in node_rows],
        "rows": matrix if bool(args.write_matrix) else [],
        "min_similarity_gate": min_sim,
        "matrix_included": bool(args.write_matrix),
    }
    matrix_out.write_text(json.dumps(matrix_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    phase_out.write_text(json.dumps(phase_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(str(nodes_out))
    print(str(edges_out))
    print(str(matrix_out))
    print(str(phase_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

