#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gold-query LOD caps for Magic Orb graph_bloom ([HYPO], showroom only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOLD_EVAL = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"

DEFAULT_CAPS = {"lod_node_cap": 48, "lod_edge_cap": 56, "hub_verse_ids": [], "profile": "default_v1"}
GOLD_REQUIRED_CAPS = {"lod_node_cap": 64, "lod_edge_cap": 72, "profile": "gold_dense_v1"}
GOLD_SOFT_CAPS = {"lod_node_cap": 56, "lod_edge_cap": 64, "profile": "gold_soft_v1"}


def _load_gold_eval() -> dict[str, Any]:
    if not GOLD_EVAL.is_file():
        return {}
    try:
        doc = json.loads(GOLD_EVAL.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def resolve_gold_lod_profile(query_id: str) -> dict[str, Any]:
    """Return caps dict: lod_node_cap, lod_edge_cap, hub_verse_ids, profile."""
    qid = (query_id or "").strip()
    if not qid:
        return dict(DEFAULT_CAPS)

    for item in _load_gold_eval().get("items") or []:
        if not isinstance(item, dict) or str(item.get("id")) != qid:
            continue
        tier = str(item.get("eval_tier") or "")
        hubs = [str(v) for v in (item.get("gold_verse_ids") or []) if v]
        if tier == "gold_required":
            return {**GOLD_REQUIRED_CAPS, "hub_verse_ids": hubs, "query_id": qid}
        if tier == "gold_soft":
            return {**GOLD_SOFT_CAPS, "hub_verse_ids": hubs, "query_id": qid}
        if hubs:
            return {**DEFAULT_CAPS, "hub_verse_ids": hubs, "query_id": qid, "profile": "observational_v1"}

    return {**DEFAULT_CAPS, "query_id": qid}
