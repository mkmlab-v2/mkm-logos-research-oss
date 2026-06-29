"""Job Reading Pack → showroom topology seed bundle (HYPO, B-track)."""

from __future__ import annotations

from typing import Any

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

NODE_SCHEMA = "showroom_job_topology_seed_bundle_v1"
VERSE_NODE_SCHEMA = "showroom_job_verse_node_v1"
STAGE_NODE_SCHEMA = "showroom_job_stage_node_v1"


def _verse_node_id(ref: str) -> str:
    return f"showroom_job_verse::{canonical_verse_ref(ref)}"


def _stage_node_id(stage_id: str) -> str:
    return f"stage::job::{stage_id}"


def build_job_seed_bundle(job_doc: dict[str, Any]) -> dict[str, Any]:
    """Build forced Job spine nodes/edges from public narrative_route."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    verse_refs: list[str] = []
    stage_node_ids: list[str] = []

    route = list(job_doc.get("narrative_route_public") or job_doc.get("narrative_route") or [])
    route.sort(key=lambda s: int(s.get("order") or 0))

    for stage in route:
        stage_id = str(stage.get("stage_id") or "").strip()
        if not stage_id:
            continue
        sid = _stage_node_id(stage_id)
        stage_node_ids.append(sid)
        if sid not in node_ids:
            node_ids.add(sid)
            nodes.append(
                {
                    "id": sid,
                    "label": str(stage.get("label_ko") or stage_id),
                    "kind": "stage",
                    "stage_id": stage_id,
                    "order": int(stage.get("order") or 0),
                    "schema": STAGE_NODE_SCHEMA,
                    "hub_score": 0.92,
                }
            )
        for raw_ref in stage.get("verse_refs") or []:
            canon = canonical_verse_ref(str(raw_ref))
            if not canon:
                continue
            vid = _verse_node_id(canon)
            if canon not in verse_refs:
                verse_refs.append(canon)
            if vid not in node_ids:
                node_ids.add(vid)
                nodes.append(
                    {
                        "id": vid,
                        "label": canon,
                        "ref": canon,
                        "kind": "verse",
                        "schema": VERSE_NODE_SCHEMA,
                        "stage_id": stage_id,
                        "hub_score": 0.88,
                    }
                )
            edges.append(
                {
                    "src": sid,
                    "dst": vid,
                    "edge_type": "stage_verse",
                    "weight": 0.92,
                }
            )

    for i in range(len(stage_node_ids) - 1):
        edges.append(
            {
                "src": stage_node_ids[i],
                "dst": stage_node_ids[i + 1],
                "edge_type": "narrative_path",
                "weight": 1.0,
            }
        )

    anchor = canonical_verse_ref(str(job_doc.get("anchor_ref") or "Job.1.6"))
    if anchor:
        aid = _verse_node_id(anchor)
        if aid not in node_ids:
            node_ids.add(aid)
            nodes.append(
                {
                    "id": aid,
                    "label": anchor,
                    "ref": anchor,
                    "kind": "verse",
                    "schema": VERSE_NODE_SCHEMA,
                    "hub_score": 0.95,
                    "anchor": True,
                }
            )
        if verse_refs and anchor not in verse_refs:
            verse_refs.insert(0, anchor)

    # dedupe edges
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
        "research_only": True,
        "hypothesis_tier": "B",
        "query_id": job_doc.get("query_id"),
        "anchor_ref": anchor,
        "stage_count": len(stage_node_ids),
        "verse_ref_count": len(verse_refs),
        "node_ids": sorted(node_ids),
        "stage_node_ids": stage_node_ids,
        "verse_refs": verse_refs,
        "nodes": nodes,
        "edges": edges_out,
    }
