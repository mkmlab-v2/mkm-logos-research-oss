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
DEFAULT_HERO_SLICES = ROOT / "docs/final/artifacts/magic_orb_hero_slices_v1_latest.json"

SCHEMA = "magic_orb_graph_bloom_v1"
VERSION = "1.0.0"
MAX_ABS_NODE_CAP = 64
MAX_ABS_EDGE_CAP = 72
NODE_CAP = 48
EDGE_CAP = 56

DISCLAIMER_KO = (
    "질문 기준 활성화 부분 망(observation)입니다. [HYPO][NON_GATING] — "
    "신학·예언 확정·실매매·Track A 근거 아님."
)

EDGE_INTEGRITY_TIER_BY_TYPE: dict[str, str] = {
    "cross_lens_confirm": "confirmed",
    "parallel": "parallel_evidence",
    "timeline_anchor": "chrono_anchor",
    "hub_anchor": "anchor",
    "query_anchor": "anchor",
    "path_step": "path_inferred",
    "seed_chain": "seed_inferred",
    "seed_chain_anchor": "seed_inferred",
    "verse_ref": "reference",
    "ann_lite": "reference",
}


def annotate_bloom_edge_integrity(doc: dict[str, Any]) -> dict[str, Any]:
    """Attach integrity_tier per edge for Phase 3 canvas coloring ([HYPO], visual only)."""
    for edge in doc.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        et = str(edge.get("edge_type") or "")
        edge["integrity_tier"] = EDGE_INTEGRITY_TIER_BY_TYPE.get(et, "observation")
    doc["edge_integrity_policy"] = {
        "schema": "magic_orb_graph_bloom_edge_integrity_v1",
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "non_gating": True,
        "note_ko": "시각적 관측 등급이며 신학·예언 확정·Track A 근거 아님.",
    }
    return doc


def _finalize_bloom(doc: dict[str, Any]) -> dict[str, Any]:
    return annotate_bloom_edge_integrity(doc)


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


class _BridgeLabelLookup:
    """Resolve display labels from logos_concept_bridge_v1 node label_ko."""

    def __init__(self) -> None:
        self._by_bridge: dict[str, dict[str, str]] = {}

    def _keys_for_step(self, step: str) -> list[str]:
        keys = [step]
        if step.startswith("node:"):
            keys.append(step[5:])
        elif not step.startswith(("concept:", "function:", "lemma:", "verse:")):
            keys.append(f"node:{step}")
        else:
            keys.append(f"node:{step}")
        return keys

    def load_bridge(self, bridge_artifact: str) -> None:
        rel = bridge_artifact.replace("\\", "/").strip()
        if not rel or rel in self._by_bridge:
            return
        mapping: dict[str, str] = {}
        path = ROOT / rel
        if path.is_file():
            try:
                doc = json.loads(path.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError:
                doc = {}
            for node in doc.get("nodes") or []:
                if not isinstance(node, dict):
                    continue
                nid = str(node.get("node_id") or "").strip()
                lko = str(node.get("label_ko") or "").strip()
                if nid and lko:
                    mapping[nid] = lko
                    for alt in self._keys_for_step(nid):
                        mapping.setdefault(alt, lko)
                vid = str(node.get("verse_id") or "").strip()
                if vid and lko:
                    mapping[vid] = lko
                    if "::" in vid:
                        mapping.setdefault(vid.split("::", 1)[-1], lko)
            q = doc.get("query") or {}
            if isinstance(q, dict):
                cid = str(q.get("concept_id") or "").strip()
                qlko = str(q.get("label_ko") or "").strip()
                if cid and qlko:
                    mapping.setdefault(cid, qlko)
        self._by_bridge[rel] = mapping

    def label_for_verse_id(self, vid: str) -> str | None:
        for mapping in self._by_bridge.values():
            for key in (vid, vid.split("::")[-1] if "::" in vid else vid):
                hit = mapping.get(key)
                if hit:
                    return hit
        return None

    def label_for_step(self, bridge_artifact: str | None, step: str) -> str | None:
        if not bridge_artifact:
            return None
        rel = bridge_artifact.replace("\\", "/").strip()
        self.load_bridge(rel)
        mapping = self._by_bridge.get(rel) or {}
        for key in self._keys_for_step(step):
            hit = mapping.get(key)
            if hit:
                return hit
        return None


def _node_from_step(step: str, *, label_ko: str | None = None) -> dict[str, Any]:
    kind = _kind_from_step(step)
    node_id = _slug_id(step, kind)
    display = (label_ko or "").strip() or _label_from_step(step)
    row: dict[str, Any] = {
        "id": node_id,
        "label": display,
        "kind": kind,
        "hub_score": 0.72 if kind == "verse" else 0.58,
    }
    if label_ko:
        row["label_ko"] = label_ko
    if kind == "verse":
        row["ref"] = display
    return row


def _verse_node_id(vid: str) -> str:
    if "::" in vid:
        return vid if vid.count("::") >= 1 else _slug_id(vid, "verse")
    return _slug_id(f"verse:{vid}", "verse")


def _verse_label(vid: str) -> str:
    if "::" in vid:
        return vid.split("::", 1)[-1]
    return vid.replace("verse:", "")


def _normalize_hub_verse_id(vid: str) -> str:
    v = vid.strip()
    if v.startswith("John."):
        return "Jhn." + v[5:]
    return v


def _enforce_caps(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    pinned_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if len(nodes) <= NODE_CAP:
        return nodes, edges[:EDGE_CAP]

    ranked = sorted(
        nodes,
        key=lambda n: (
            0 if n.get("id") in pinned_ids or n.get("id") == "query::center" else 1,
            -float(n.get("hub_score") or 0),
        ),
    )
    keep_ids = {n["id"] for n in ranked[:NODE_CAP]}
    trimmed_nodes = [n for n in nodes if n["id"] in keep_ids]
    trimmed_edges = [
        e
        for e in edges
        if e.get("src") in keep_ids and e.get("dst") in keep_ids
    ][:EDGE_CAP]
    return trimmed_nodes, trimmed_edges


def _bloom_is_sparse(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> bool:
    verse_count = sum(1 for n in nodes if n.get("kind") == "verse")
    return verse_count == 0 or len(edges) == 0


def _apply_seed_chain_fallback(
    router: dict[str, Any],
    *,
    add_node,
    add_edge,
    label_lookup: _BridgeLabelLookup,
) -> None:
    """When router paths miss, wire seed_chain_verse_sample into a minimal chain bloom."""
    seeds = [v for v in (router.get("seed_chain_verse_sample") or []) if isinstance(v, str) and v.strip()]
    if not seeds:
        return
    prev: str | None = None
    for vid in seeds:
        norm = _normalize_hub_verse_id(vid.strip())
        nid = _verse_node_id(norm)
        vlko = label_lookup.label_for_verse_id(norm)
        vlabel = vlko or _verse_label(norm)
        row: dict[str, Any] = {
            "id": nid,
            "label": vlabel,
            "kind": "verse",
            "hub_score": 0.68,
            "ref": vlabel,
        }
        if vlko:
            row["label_ko"] = vlko
        if "::" in norm:
            row["corpus"] = norm.split("::")[0]
        add_node(row)
        if prev:
            add_edge(prev, nid, "seed_chain", 0.62)
        else:
            add_edge("query::center", nid, "seed_chain_anchor", 0.78)
        prev = nid


def _pick_hero_slice_id(router: dict[str, Any] | None, query: str) -> str:
    seeds = [str(v) for v in (router or {}).get("seed_chain_verse_sample") or []]
    if any(v.upper().startswith("DAN.") or "DAN." in v.upper() for v in seeds):
        return "DAN2_CLUSTER_v1"
    q = query.strip().lower()
    if any(k in q for k in ("passion", "synoptic", "수난", "공관")):
        return "SYNOPTIC_PASSION_WEEK_v1"
    if any(k in q for k in ("daniel", "dan.", "다니엘", "dan 2", "dan2")):
        return "DAN2_CLUSTER_v1"
    return "SYNOPTIC_PASSION_WEEK_v1"


def _hero_slice_bloom_fallback(
    query: str,
    router: dict[str, Any] | None,
    *,
    hero_slices_path: Path = DEFAULT_HERO_SLICES,
) -> dict[str, Any] | None:
    if not hero_slices_path.is_file():
        return None
    try:
        bundle = json.loads(hero_slices_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    if bundle.get("schema") != "magic_orb_hero_slices_v1":
        return None
    slice_id = _pick_hero_slice_id(router, query)
    for entry in bundle.get("slices") or []:
        if not isinstance(entry, dict) or entry.get("slice_id") != slice_id:
            continue
        bloom = entry.get("graph_bloom")
        if not isinstance(bloom, dict) or bloom.get("schema") != "magic_orb_graph_bloom_v1":
            continue
        out = json.loads(json.dumps(bloom))
        q = query.strip()
        if q:
            for n in out.get("nodes") or []:
                if n.get("id") == "query::center":
                    n["label"] = q[:120]
                    break
            else:
                out.setdefault("nodes", []).insert(
                    0,
                    {"id": "query::center", "label": q[:120], "kind": "query", "hub_score": 1.0},
                )
            out["seed_query"] = q
        src = out.get("source") if isinstance(out.get("source"), dict) else {}
        out["source"] = {
            **src,
            "fallback": "magic_orb_hero_slices_v1",
            "hero_slice_id": slice_id,
        }
        return out
    return None


def bloom_from_router_paths(
    query: str,
    router: dict[str, Any],
    *,
    ann_top_verse_ids: list[str] | None = None,
    hub_verse_refs: list[str] | None = None,
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_edges: set[tuple[str, str, str]] = set()
    pinned_ids: set[str] = {"query::center"}

    def add_node(n: dict[str, Any], *, force: bool = False) -> None:
        if n["id"] in seen_nodes:
            return
        if not force and len(nodes) >= NODE_CAP:
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
        add_node({"id": "query::center", "label": q[:120], "kind": "query", "hub_score": 1.0}, force=True)

    label_lookup = _BridgeLabelLookup()
    for path in router.get("paths") or []:
        if isinstance(path, dict) and isinstance(path.get("bridge_artifact"), str):
            label_lookup.load_bridge(path["bridge_artifact"].strip())

    for vid in hub_verse_refs or []:
        if not isinstance(vid, str) or not vid.strip():
            continue
        norm = _normalize_hub_verse_id(vid.strip())
        nid = _verse_node_id(norm)
        pinned_ids.add(nid)
        vlko = label_lookup.label_for_verse_id(norm)
        vlabel = vlko or _verse_label(norm)
        hub_row: dict[str, Any] = {
            "id": nid,
            "label": vlabel,
            "kind": "verse",
            "hub_score": 0.96,
            "ref": vlabel,
            "pinned_hub": True,
        }
        if vlko:
            hub_row["label_ko"] = vlko
        add_node(hub_row, force=True)
        if "query::center" in seen_nodes:
            add_edge("query::center", nid, "hub_anchor", 0.92)

    for path in router.get("paths") or []:
        if not isinstance(path, dict):
            continue
        bridge_artifact = path.get("bridge_artifact")
        steps = path.get("steps") or []
        prev: str | None = None
        for step in steps:
            if not isinstance(step, str):
                continue
            lko = label_lookup.label_for_step(
                bridge_artifact if isinstance(bridge_artifact, str) else None,
                step,
            )
            n = _node_from_step(step, label_ko=lko)
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
        vlko = label_lookup.label_for_verse_id(vid)
        vlabel = vlko or _verse_label(vid)
        row_v: dict[str, Any] = {
            "id": nid,
            "label": vlabel,
            "kind": "verse",
            "hub_score": 0.62,
            "ref": vlabel,
        }
        if vlko:
            row_v["label_ko"] = vlko
        if "::" in vid:
            row_v["corpus"] = vid.split("::")[0]
        add_node(row_v)
        if "query::center" in seen_nodes:
            add_edge("query::center", nid, "verse_ref", 0.5)

    for vid in ann_top_verse_ids or []:
        if not isinstance(vid, str):
            continue
        nid = _verse_node_id(vid)
        vlko = label_lookup.label_for_verse_id(vid)
        vlabel = vlko or _verse_label(vid)
        add_node(
            {
                "id": nid,
                "label": vlabel,
                "kind": "verse",
                "hub_score": 0.5,
                "ref": vlabel,
                **({"label_ko": vlko} if vlko else {}),
            }
        )
        if "query::center" in seen_nodes:
            add_edge("query::center", nid, "ann_lite", 0.45)

    if _bloom_is_sparse(nodes, edges):
        _apply_seed_chain_fallback(
            router,
            add_node=add_node,
            add_edge=add_edge,
            label_lookup=label_lookup,
        )

    nodes, edges = _enforce_caps(nodes, edges, pinned_ids=pinned_ids)

    return _finalize_bloom(
        {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "seed_query": q or router.get("query"),
        "disclaimer_ko": DISCLAIMER_KO,
        "display_locale": "ko",
        "stats": {"node_count": len(nodes), "edge_count": len(edges)},
        "nodes": nodes,
        "edges": edges,
        "source": {"kind": "logos_subgraph_router_paths", "router_schema": router.get("schema")},
    }
    )


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
    return _finalize_bloom(out)


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
    return _finalize_bloom(
        {
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
    )


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
    hub_verse_refs: list[str] | None = None,
) -> dict[str, Any]:
    global NODE_CAP, EDGE_CAP
    NODE_CAP = min(MAX_ABS_NODE_CAP, max(8, lod_node_cap))
    EDGE_CAP = min(MAX_ABS_EDGE_CAP, max(8, lod_edge_cap))

    if topology_slice and topology_slice.get("nodes"):
        base = bloom_from_topology_slice(topology_slice, query)
    elif router:
        base = bloom_from_router_paths(
            query,
            router,
            ann_top_verse_ids=ann_top_verse_ids,
            hub_verse_refs=hub_verse_refs,
        )
        if _bloom_is_sparse(list(base.get("nodes") or []), list(base.get("edges") or [])):
            hero = _hero_slice_bloom_fallback(query, router)
            if hero and not _bloom_is_sparse(list(hero.get("nodes") or []), list(hero.get("edges") or [])):
                base = hero
    else:
        raise ValueError("router or topology_slice required")

    if not expand_graph or not router:
        return _finalize_bloom(base)

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
        return _finalize_bloom(base)

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
    ap.add_argument(
        "--hub-verse-ids",
        default="",
        help="comma-separated canonical verse_ids pinned as bloom hubs (gold profile)",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    router = _load_json(args.router_json) if args.router_json.is_file() else None
    slice_doc = _load_json(args.topology_slice_json) if args.topology_slice_json and args.topology_slice_json.is_file() else None
    ann_ids = [x.strip() for x in args.ann_verse_ids.split(",") if x.strip()]
    hub_ids = [x.strip() for x in args.hub_verse_ids.split(",") if x.strip()]

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
        hub_verse_refs=hub_ids or None,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "nodes": doc["stats"]["node_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
