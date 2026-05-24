#!/usr/bin/env python3
"""COMP-ATOM-05: Graph route → wire influence map (B-track, not Track A).

Maps per-case GraphRAG routing to atom_id_sequence + optional bridge_boost
for evaluate_report graph_wire_selective_bridge (semantic channel, not must_keep).
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "mkm_graph_wire_bridge_influence_v1"
ROOT = Path(__file__).resolve().parent.parent
NODES = ROOT / "docs/final/artifacts/global_atom_network_nodes_latest.jsonl"
EDGES = ROOT / "docs/final/artifacts/global_atom_network_edges_latest.jsonl"
POC = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json"
ANCHOR07 = (
    ROOT / "reports/constitution/btrack_pilot/comp_anchor07_wire_atom_candidates_v1.json"
)
_GRAPH_CACHE: dict[str, Any] | None = None
DEFAULT_BRIDGE_BOOST_MIN_SCORE = 0.35


def _anchor_terms_from_nodes(nodes: list[dict[str, Any]]) -> set[str]:
    terms: set[str] = set()
    for n in nodes:
        for key in ("assigned_symbol", "regime_tag", "candidate_id"):
            v = n.get(key)
            if isinstance(v, str) and len(v) >= 2:
                for part in re.split(r"[_\s:]+", v.lower()):
                    if len(part) >= 3 and part.isascii():
                        terms.add(part)
    return terms


def wire_influence_score(
    *,
    expanded_node_count: int,
    anchor_terms: list[str] | None,
) -> float:
    anchors = anchor_terms or []
    score = 0.15 * min(expanded_node_count, 4)
    if anchors:
        score += 0.25
    symbolic = {"babel", "exodus", "empire", "tower", "transgression", "restoration"}
    if symbolic.intersection({t.lower() for t in anchors if isinstance(t, str)}):
        score += 0.15
    return round(min(1.0, score), 4)


def build_case_graph_wire_influence_map(
    case_routes: list[dict[str, Any]],
    *,
    wire_atom_ids: list[str] | None = None,
    bridge_boost_min_score: float = DEFAULT_BRIDGE_BOOST_MIN_SCORE,
) -> dict[str, dict[str, Any]]:
    """case_id -> influence row for evaluate_report case_graph_wire_influence."""
    base_atoms = [str(x) for x in (wire_atom_ids or []) if x]
    out: dict[str, dict[str, Any]] = {}
    for row in case_routes:
        cid = str(row.get("case_id") or "")
        if not cid:
            continue
        anchors = [str(t) for t in (row.get("anchor_terms") or []) if t]
        expanded = int(row.get("expanded_node_count") or 0)
        score = wire_influence_score(expanded_node_count=expanded, anchor_terms=anchors)
        atom_seq = list(base_atoms)
        for a in anchors[:8]:
            if len(a) >= 3:
                atom_seq.append(f"graph::{a.lower()}")
        out[cid] = {
            "schema": SCHEMA,
            "atom_id_sequence": atom_seq[:32],
            "graph_anchor_terms": anchors[:24],
            "wire_influence_score": score,
            "bridge_boost": score >= float(bridge_boost_min_score),
            "expanded_node_count": expanded,
        }
    return out


def _load_graphrag_module() -> Any:
    path = ROOT / "scripts" / "run_graphrag_pilot_router_v1.py"
    spec = importlib.util.spec_from_file_location("graphrag_pilot_router_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _graph_backend() -> tuple[Any, dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]] | None:
    global _GRAPH_CACHE
    if _GRAPH_CACHE is not None:
        return _GRAPH_CACHE["gr"], _GRAPH_CACHE["node_map"], _GRAPH_CACHE["adj"]
    if not NODES.is_file() or not EDGES.is_file():
        return None
    gr = _load_graphrag_module()
    nodes = gr._load_jsonl(NODES)
    edges = gr._load_jsonl(EDGES)
    node_map, adj = gr._build_graph(nodes, edges, min_similarity=0.9)
    _GRAPH_CACHE = {"gr": gr, "node_map": node_map, "adj": adj}
    return gr, node_map, adj


def wire_atom_ids_from_poc() -> list[str]:
    if not POC.is_file():
        return []
    doc = json.loads(POC.read_text(encoding="utf-8"))
    gr = doc.get("graph_rag") or {}
    return [str(nid) for nid in (gr.get("reasoning_path_node_ids") or [])]


def wire_atom_ids_from_anchor07(*, max_n: int = 12) -> list[str]:
    if not ANCHOR07.is_file():
        return []
    doc = json.loads(ANCHOR07.read_text(encoding="utf-8"))
    ids = [str(x) for x in (doc.get("wire_atom_ids_candidates") or []) if x]
    return ids[: max(0, max_n)]


def wire_atom_ids_merged(*, anchor_max: int = 8) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for aid in wire_atom_ids_from_poc() + wire_atom_ids_from_anchor07(max_n=anchor_max):
        if aid and aid not in seen:
            seen.add(aid)
            out.append(aid)
    return out


def wire_atom_ids_lexicon_filtered(*, anchor_max: int = 12, lexicon_path: Path | None = None) -> list[str]:
    """Merged wire ids restricted to atom_ids present in master_codebook_lexicon (B-track gloss path)."""
    from scripts.core.master_codebook_lexicon_v1_bridge import _load_atom_id_to_form, resolve_latest_codebook_path

    lex = lexicon_path or resolve_latest_codebook_path()
    if lex is None or not Path(lex).is_file():
        return wire_atom_ids_merged(anchor_max=anchor_max)
    idx = _load_atom_id_to_form(str(Path(lex).resolve()))
    return [aid for aid in wire_atom_ids_merged(anchor_max=anchor_max) if aid in idx]


def wire_atom_ids_default() -> list[str]:
    """Env MKM_WIRE_ATOM_IDS_SOURCE: poc (default) | anchor07 | merged | lexicon_filtered."""
    import os

    src = (os.environ.get("MKM_WIRE_ATOM_IDS_SOURCE") or "poc").strip().lower()
    if os.environ.get("MKM_WIRE_ATOM_IDS_LEXICON_FILTER", "").strip().lower() in ("1", "true", "yes", "on"):
        return wire_atom_ids_lexicon_filtered()
    if src == "anchor07":
        return wire_atom_ids_from_anchor07()
    if src == "merged":
        return wire_atom_ids_merged()
    if src == "lexicon_filtered":
        return wire_atom_ids_lexicon_filtered()
    return wire_atom_ids_from_poc()


def route_case_for_text(text: str, *, case_id: str = "api") -> dict[str, Any]:
    """GraphRAG pilot route for one query string."""
    backend = _graph_backend()
    if backend is None:
        return {"case_id": case_id, "expanded_node_count": 0, "anchor_terms": []}
    gr, node_map, adj = backend
    kws = gr._keywords(text)
    seeds = gr._seed_nodes(list(node_map.values()), kws, topk=8)
    seed_ids = [n["node_id"] for n in seeds if n.get("node_id")]
    expanded, traversed = gr._multi_hop_expand(
        seed_ids=seed_ids, adj=adj, max_hops=2, max_edges=80
    )
    selected = [node_map[nid] for nid in sorted(expanded) if nid in node_map]
    return {
        "case_id": case_id,
        "seed_keywords": kws[:12],
        "seed_node_count": len(seed_ids),
        "expanded_node_count": len(expanded),
        "traversed_edge_count": len(traversed),
        "anchor_terms": sorted(_anchor_terms_from_nodes(selected)),
    }


def build_influence_map_from_compression_cases(
    compression_cases: list[dict[str, Any]],
    *,
    wire_atom_ids: list[str] | None = None,
    bridge_boost_min_score: float = DEFAULT_BRIDGE_BOOST_MIN_SCORE,
) -> dict[str, dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for case in compression_cases:
        cid = str(case.get("id", ""))
        raw = str(case.get("raw_text", ""))
        route = route_case_for_text(raw, case_id=cid or "case")
        routes.append(route)
    atoms = wire_atom_ids if wire_atom_ids is not None else wire_atom_ids_default()
    return build_case_graph_wire_influence_map(
        routes, wire_atom_ids=atoms, bridge_boost_min_score=bridge_boost_min_score
    )


def build_wire_influence_for_text(
    text: str,
    *,
    case_id: str = "api",
    wire_atom_ids: list[str] | None = None,
) -> dict[str, Any]:
    route = route_case_for_text(text, case_id=case_id)
    atoms = wire_atom_ids if wire_atom_ids is not None else wire_atom_ids_default()
    return build_case_graph_wire_influence_map(
        [route], wire_atom_ids=atoms
    ).get(case_id, {})


def merge_wire_into_semantic_pointer(
    sp: dict[str, Any],
    influence: dict[str, Any] | None,
) -> dict[str, Any]:
    if not influence:
        return sp
    merged = dict(sp)
    merged["graph_wire_influence_v1"] = {
        "atom_id_sequence": influence.get("atom_id_sequence"),
        "wire_influence_score": influence.get("wire_influence_score"),
        "bridge_boost": influence.get("bridge_boost"),
        "graph_anchor_terms": (influence.get("graph_anchor_terms") or [])[:12],
    }
    return merged
