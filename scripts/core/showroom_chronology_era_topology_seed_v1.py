"""Chronology overlay → showroom topology era verse seed bundle ([HYPO], B-track)."""

from __future__ import annotations

from typing import Any

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

NODE_SCHEMA = "showroom_chronology_era_topology_seed_bundle_v1"
VERSE_NODE_SCHEMA = "showroom_era_verse_node_v1"


def _verse_ref_body(raw: str) -> str:
    s = str(raw or "").strip()
    if "::" in s:
        s = s.split("::", 1)[1]
    return canonical_verse_ref(s)


def _era_node_id(era_id: str) -> str:
    return f"era::{era_id}"


def _stub_verse_node_id(canon: str) -> str:
    return f"showroom_era_verse::{canon}"


def _resolve_verse_node(
    raw_ref: str,
    nodes_index: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any], bool]:
    """Return (node_id, node_row, from_full_graph)."""
    canon = _verse_ref_body(raw_ref)
    if not canon:
        raise ValueError(f"invalid verse ref: {raw_ref!r}")

    for nid, raw in nodes_index.items():
        ref = canonical_verse_ref(str(raw.get("ref") or ""))
        label = canonical_verse_ref(str(raw.get("label") or "").replace(" ", "."))
        if canon in {ref, label} or nid.endswith(f"::{canon}"):
            row = {
                "id": nid,
                "label": str(raw.get("ref") or raw.get("label") or canon),
                "ref": ref or canon,
                "kind": "verse",
                "schema": str(raw.get("schema") or "logos_graph_verse_v1"),
            }
            if raw.get("hub_score") is not None:
                row["hub_score"] = float(raw["hub_score"])
            elif raw.get("theme_tags"):
                row["hub_score"] = 0.78
            text_norm = str(raw.get("text_norm") or "").strip()
            if text_norm:
                row["text_snippet_ko"] = text_norm[:160] + ("…" if len(text_norm) > 160 else "")
            return nid, row, True

    stub_id = _stub_verse_node_id(canon)
    return (
        stub_id,
        {
            "id": stub_id,
            "label": canon,
            "ref": canon,
            "kind": "verse",
            "schema": VERSE_NODE_SCHEMA,
            "hub_score": 0.8,
        },
        False,
    )


def build_chronology_era_seed_bundle(
    chrono_doc: dict[str, Any],
    *,
    nodes_index: dict[str, dict[str, Any]] | None = None,
    edges_index: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build forced era verse nodes + era→verse edges for showroom graph slice."""
    nodes_index = nodes_index or {}
    edges_index = edges_index or []

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    verse_refs: list[str] = []
    era_verse_map: dict[str, list[str]] = {}
    resolved_from_graph = 0
    stub_count = 0

    for era in chrono_doc.get("eras") or []:
        era_id = str(era.get("era_id") or "").strip()
        if not era_id:
            continue
        era_nid = _era_node_id(era_id)
        era_verse_map[era_id] = []
        for raw_ref in era.get("verse_refs") or []:
            canon = _verse_ref_body(str(raw_ref))
            if not canon or canon in verse_refs:
                pass
            else:
                verse_refs.append(canon)
            vid, row, from_graph = _resolve_verse_node(str(raw_ref), nodes_index)
            era_verse_map[era_id].append(vid)
            if from_graph:
                resolved_from_graph += 1
            else:
                stub_count += 1
            if vid not in node_ids:
                node_ids.add(vid)
                nodes.append(row)
            edges.append(
                {
                    "src": era_nid,
                    "dst": vid,
                    "edge_type": "era_verse",
                    "weight": 0.95,
                }
            )

    selected = set(node_ids)
    for edge in edges_index:
        src = str(edge.get("src_node_id") or edge.get("src") or "")
        dst = str(edge.get("dst_node_id") or edge.get("dst") or "")
        if src in selected and dst in selected:
            edges.append(
                {
                    "src": src,
                    "dst": dst,
                    "edge_type": str(edge.get("edge_type") or "link"),
                    "weight": float(edge.get("weight") or 0.5),
                }
            )

    seen: set[tuple[str, str, str]] = set()
    edges_out: list[dict[str, Any]] = []
    for e in edges:
        key = (e["src"], e["dst"], e["edge_type"])
        if key in seen:
            continue
        seen.add(key)
        edges_out.append(e)

    return {
        "schema": NODE_SCHEMA,
        "era_count": len(era_verse_map),
        "verse_ref_count": len(verse_refs),
        "resolved_from_graph_count": resolved_from_graph,
        "stub_verse_count": stub_count,
        "node_ids": sorted(node_ids),
        "era_verse_map": era_verse_map,
        "nodes": nodes,
        "edges": edges_out,
    }
