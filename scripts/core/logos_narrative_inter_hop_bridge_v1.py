"""Narrative inter-hop bridge curation — shared primitive/motif/natural atoms (HYPO)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.core.logos_narrative_lemma_bridge_v1 import (
    _canon_verse,
    _strip_accents,
    merge_jsonl,
)
from scripts.core.logos_narrative_lemma_overlap_eval_v1 import load_bidirectional_atoms

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
BIDIRECTIONAL = ROOT / "reports/logos_bidirectional_anchor_index_v1_latest.json"
LEMMA_EDGES = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
PATH_ID = "narrative_inter_hop_bridge_v1"


def _anchor_by_id(bridge: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("anchor_id") or ""): row for row in bridge.get("per_anchor") or []}


def _atom_ids_for_verse(bidirectional: dict[str, list[dict[str, Any]]], verse_ref: str) -> set[str]:
    return {str(a.get("atom_id") or "") for a in bidirectional.get(verse_ref, []) if a.get("atom_id")}


def _motif_set(anchor: dict[str, Any]) -> set[str]:
    return {_strip_accents(t) for t in anchor.get("motif_tokens") or [] if len(str(t)) >= 3}


def curate_inter_hop_pair(
    *,
    sample_id: str,
    pair_index: int,
    verse_a: str,
    verse_b: str,
    anchor_a: dict[str, Any],
    anchor_b: dict[str, Any],
    bidirectional: dict[str, list[dict[str, Any]]],
    edge_types: list[str],
) -> list[dict[str, Any]]:
    bridges: list[dict[str, Any]] = []
    atoms_a = _atom_ids_for_verse(bidirectional, verse_a)
    atoms_b = _atom_ids_for_verse(bidirectional, verse_b)
    for atom_id in sorted(atoms_a & atoms_b)[:3]:
        bridges.append(
            {
                "bridge_kind": "natural_shared_atom",
                "bridge_atom_id": atom_id,
                "weight": 0.7,
            }
        )

    prim_a = str(anchor_a.get("top_primitive") or "")
    prim_b = str(anchor_b.get("top_primitive") or "")
    if prim_a and prim_a == prim_b:
        bridges.append(
            {
                "bridge_kind": "shared_primitive",
                "bridge_atom_id": f"primitive_bridge::{prim_a}",
                "weight": 0.65,
            }
        )

    for motif in sorted(_motif_set(anchor_a) & _motif_set(anchor_b))[:2]:
        bridges.append(
            {
                "bridge_kind": "shared_motif",
                "bridge_atom_id": f"motif_bridge::{motif}",
                "weight": 0.6,
            }
        )

    shared_themes = sorted(
        set(anchor_a.get("themed_bridge_ids") or []) & set(anchor_b.get("themed_bridge_ids") or [])
    )
    for theme in shared_themes[:1]:
        bridges.append(
            {
                "bridge_kind": "shared_theme",
                "bridge_atom_id": f"theme_bridge::{theme}",
                "weight": 0.55,
            }
        )

    if not bridges and "curated_narrative_transition" in edge_types:
        bridges.append(
            {
                "bridge_kind": "curated_narrative_transition",
                "bridge_atom_id": f"narrative_bridge::{sample_id}::pair_{pair_index}",
                "weight": 0.5,
            }
        )
    if not bridges:
        bridges.append(
            {
                "bridge_kind": "resonance_hypo_fallback",
                "bridge_atom_id": f"narrative_bridge::{sample_id}::pair_{pair_index}",
                "weight": 0.45,
            }
        )

    dedup: dict[str, dict[str, Any]] = {}
    for bridge in bridges:
        dedup[str(bridge["bridge_atom_id"])] = bridge
    out: list[dict[str, Any]] = []
    for bridge_atom_id, bridge in dedup.items():
        out.append(
            {
                "sample_id": sample_id,
                "pair_index": pair_index,
                "verse_refs": [verse_a, verse_b],
                "bridge_kind": bridge["bridge_kind"],
                "bridge_atom_id": bridge_atom_id,
                "weight": bridge["weight"],
                "anchor_ids": [
                    str(anchor_a.get("anchor_id") or ""),
                    str(anchor_b.get("anchor_id") or ""),
                ],
            }
        )
    return out


def build_inter_hop_bridge_rows(bridge: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bidirectional = load_bidirectional_atoms(BIDIRECTIONAL)
    anchors = _anchor_by_id(bridge)
    pair_rows: list[dict[str, Any]] = []
    lemma_edges: list[dict[str, Any]] = []
    edge_i = 0

    for sample in bridge.get("narrative_path_samples") or []:
        sample_id = str(sample.get("sample_id") or "")
        path = list(sample.get("path") or [])
        edge_types = list(sample.get("edge_types") or [])
        for pair_index in range(len(path) - 1):
            hop_a, hop_b = path[pair_index], path[pair_index + 1]
            verse_a = _canon_verse(str(hop_a.get("verse_ref") or ""))
            verse_b = _canon_verse(str(hop_b.get("verse_ref") or ""))
            anchor_a = anchors.get(str(hop_a.get("anchor_id") or ""), {})
            anchor_b = anchors.get(str(hop_b.get("anchor_id") or ""), {})
            bridges = curate_inter_hop_pair(
                sample_id=sample_id,
                pair_index=pair_index,
                verse_a=verse_a,
                verse_b=verse_b,
                anchor_a=anchor_a,
                anchor_b=anchor_b,
                bidirectional=bidirectional,
                edge_types=edge_types,
            )
            pair_rows.append(
                {
                    "sample_id": sample_id,
                    "pair_index": pair_index,
                    "verse_refs": [verse_a, verse_b],
                    "bridge_count": len(bridges),
                    "bridges": bridges,
                }
            )
            for bridge_row in bridges:
                bridge_atom_id = str(bridge_row["bridge_atom_id"])
                weight = float(bridge_row.get("weight") or 0.5)
                for verse_ref in (verse_a, verse_b):
                    lemma_edges.append(
                        {
                            "schema": "logos_lemma_verse_edge_v1",
                            "edge_id": f"lemma_verse::inter_hop_{edge_i}",
                            "src_node_id": bridge_atom_id,
                            "dst_node_id": verse_ref,
                            "edge_type": "INTER_HOP_BRIDGE_CONTAIN",
                            "weight": weight,
                            "hypothesis_tier": "B",
                            "research_only": True,
                            "path_id": PATH_ID,
                            "source_bridge": "scripts/core/logos_narrative_inter_hop_bridge_v1.py",
                            "sample_id": sample_id,
                            "pair_index": pair_index,
                        }
                    )
                    edge_i += 1
    return pair_rows, lemma_edges


def build_inter_hop_bridge_report(bridge: dict[str, Any] | None = None) -> dict[str, Any]:
    bridge = bridge or json.loads(BRIDGE.read_text(encoding="utf-8"))
    pair_rows, lemma_edges = build_inter_hop_bridge_rows(bridge)
    pair_count = len(pair_rows)
    bridge_pair_hits = sum(1 for row in pair_rows if row["bridge_count"] > 0)
    natural_pairs = sum(
        1
        for row in pair_rows
        if any(b["bridge_kind"] == "natural_shared_atom" for b in row["bridges"])
    )
    curated_pairs = sum(
        1
        for row in pair_rows
        if any(b["bridge_kind"] != "natural_shared_atom" for b in row["bridges"])
    )

    return {
        "schema": "logos_narrative_inter_hop_bridge_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "note_ko": (
            "B-track inter-hop bridge curation for 8 narrative paths. "
            "Synthetic primitive/motif bridges are HYPO — not morphology proof."
        ),
        "summary": {
            "inter_hop_pair_count": pair_count,
            "bridge_pair_rate": round(bridge_pair_hits / pair_count, 4) if pair_count else 0.0,
            "natural_shared_pair_count": natural_pairs,
            "curated_bridge_pair_count": curated_pairs,
            "lemma_edges_built": len(lemma_edges),
        },
        "pairs": pair_rows,
        "lemma_edges": lemma_edges,
        "reproducible_command": "py scripts/run_logos_narrative_inter_hop_bridge_chain_v1.py",
    }


def merge_inter_hop_lemma_edges(edges: list[dict[str, Any]]) -> tuple[int, int]:
    merged, added = merge_jsonl(
        base_path=LEMMA_EDGES,
        new_rows=edges,
        strip_path_id=PATH_ID,
    )
    LEMMA_EDGES.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + ("\n" if merged else ""),
        encoding="utf-8",
    )
    return added, len(merged)
