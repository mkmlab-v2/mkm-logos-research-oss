#!/usr/bin/env python3
"""Logos canon address vs manuscript ink fabric v2 (B-track · Fact-Lock).

Separates canonical verse_id slots (31,102) from manuscript instance bindings.
Does not merge TR into verse_decoded_v2_complete or rewrite core corpus bytes.
"""

from __future__ import annotations

from typing import Any

from scripts.build_logos_gap_mt_only_residual_classify_v1 import NT_TEXTUAL_VARIANT_IDS
from scripts.logos_nt_adjacent_verse_v1 import adjacent_mt_verse_ids, pick_sblgnt_filled_neighbor

SCHEMA = "logos_canon_manuscript_fabric_v2"
VERSION = "2.0.0"

INSTANCE_SBLGNT = "sblgnt_bhs_v2_core"
INSTANCE_TR = "tr_kjv_textual_variant_v1"

WIRE_FLAG_RE_ROUTE_TR = 0x01
EDGE_TYPE_VARIANT_OMISSION_BRIDGE = "variant_omission_bridge_v2"


def is_nt_textual_variant_gap(verse_id: str) -> bool:
    return verse_id in NT_TEXTUAL_VARIANT_IDS


def binding_row(
    verse_id: str,
    *,
    ink_present: bool,
    decode_status: str,
    instance_id: str,
    role: str,
) -> dict[str, Any]:
    return {
        "verse_id": verse_id,
        "instance_id": instance_id,
        "role": role,
        "ink_present": ink_present,
        "decode_status": decode_status,
    }


def build_manuscript_bindings(
    gap_verse_ids: list[str],
    variant_entries: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """M:N bindings: every canon slot; gap slots get TR secondary + SBLGNT absent."""
    variant_entries = variant_entries or {}
    gaps = set(gap_verse_ids)
    bindings: list[dict[str, Any]] = []
    for vid in sorted(gaps):
        tr_row = variant_entries.get(vid, {})
        tr_ingested = str((tr_row.get("tr_tradition") or {}).get("ingest_status") or "") == "ingested"
        bindings.append(
            binding_row(
                vid,
                ink_present=False,
                decode_status="mt_canon_only_no_critical_text",
                instance_id=INSTANCE_SBLGNT,
                role="primary_absent",
            )
        )
        bindings.append(
            binding_row(
                vid,
                ink_present=tr_ingested,
                decode_status="tr_tradition_observation_only",
                instance_id=INSTANCE_TR,
                role="secondary_tradition",
            )
        )
    return bindings


def build_virtual_bridge_edges(
    gap_verse_ids: list[str],
    *,
    span: int = 2,
) -> list[dict[str, Any]]:
    """L2 bypass edges: gap node -> adjacent canon anchors (SBLGNT rail continuity)."""
    edges: list[dict[str, Any]] = []
    for vid in sorted(gap_verse_ids):
        neighbors = adjacent_mt_verse_ids(vid, span=span)
        if not neighbors:
            continue
        edges.append(
            {
                "schema": "logos_graph_edge_v2",
                "edge_type": EDGE_TYPE_VARIANT_OMISSION_BRIDGE,
                "source_verse_id": vid,
                "target_verse_ids": neighbors,
                "routing_policy": {
                    "sblgnt_rail": "bypass_ink_absent",
                    "energy_split": "uniform_over_targets",
                    "forbidden": ["pretend_sblgnt_decode"],
                },
                "hypothesis_tier": "B",
            }
        )
    return edges


def build_wire_routing_table(gap_verse_ids: list[str]) -> dict[str, dict[str, Any]]:
    table: dict[str, dict[str, Any]] = {}
    for vid in sorted(gap_verse_ids):
        table[vid] = {
            "routing_flags": WIRE_FLAG_RE_ROUTE_TR,
            "routing_flags_hex": hex(WIRE_FLAG_RE_ROUTE_TR),
            "decode_hint": "use_tr_proxy_decoder_or_adjacent_bypass",
            "forbidden": ["primary_bhs_sblgnt_decode"],
        }
    return table


def resolve_manuscript_route(
    verse_id: str,
    fabric: dict[str, Any],
    *,
    corpus_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Runtime resolver: which instance to draw for a canon address."""
    wire = (fabric.get("wire_routing") or {}).get("by_verse_id") or {}
    if verse_id not in wire:
        return {
            "verse_id": verse_id,
            "route": "primary_sblgnt",
            "instance_id": INSTANCE_SBLGNT,
            "re_route_tr": False,
        }
    entry = wire[verse_id]
    corpus_index = corpus_index or {}
    neighbor = pick_sblgnt_filled_neighbor(verse_id, corpus_index) if corpus_index else None
    return {
        "verse_id": verse_id,
        "route": "gap_textual_variant",
        "instance_id": INSTANCE_TR,
        "re_route_tr": bool(entry.get("routing_flags", 0) & WIRE_FLAG_RE_ROUTE_TR),
        "sblgnt_ink_present": False,
        "adjacent_sblgnt_proxy": neighbor[0] if neighbor else None,
        "decode_hint": entry.get("decode_hint"),
    }


def apply_wire_manuscript_route(payload: dict[str, Any], verse_id: str, fabric: dict[str, Any]) -> dict[str, Any]:
    """Attach routing_flags to mkm_lexicon_wire-style payload without changing codec tag bytes."""
    resolved = resolve_manuscript_route(verse_id, fabric)
    out = dict(payload)
    flags = int(out.get("routing_flags") or 0)
    if resolved.get("re_route_tr"):
        flags |= WIRE_FLAG_RE_ROUTE_TR
    out["routing_flags"] = flags
    out["manuscript_route"] = {
        "verse_id": verse_id,
        "instance_id": resolved.get("instance_id"),
        "route": resolved.get("route"),
    }
    return out
