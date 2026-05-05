# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.7, K:0.8, M:0.3}
# Balance: 88
# Purpose: FastAPI stub for public graph insights (NON_GATING, research_only).
# Keywords: FastAPI, public API, graph insights, NON_GATING
"""FastAPI stub for public graph insights.

Run:
  uvicorn scripts.public_graph_insights_api_stub:app --host 127.0.0.1 --port 8789
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_PATH = ROOT / "docs" / "final" / "artifacts" / "schemas" / "public_graph_response_v1.example.json"

app = FastAPI(title="Public Graph Insights Stub", version="1.0.0")


def _load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        raw = cursor.encode("utf-8")
        value = int(__import__("base64").b64decode(raw).decode("utf-8"))
        return value if value >= 0 else 0
    except Exception:
        return 0


def _encode_cursor(offset: int) -> str:
    return __import__("base64").b64encode(str(offset).encode("utf-8")).decode("utf-8")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "public_graph_insights_api_stub",
        "policy_label": "NON_GATING",
        "research_only": True,
    }


@app.get("/public/graph/insights")
def get_public_graph_insights(
    anchor: str | None = Query(default=None, min_length=1, max_length=64),
    theme: str | None = Query(default=None, min_length=1, max_length=64),
    confidence_band: Literal["A", "B", "C"] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=256),
) -> dict:
    doc = _load_example()
    insights = doc.get("insights", [])
    nodes = doc.get("nodes", [])
    edges = doc.get("edges", [])

    all_insights = [
        x
        for x in insights
        if (anchor is None or x.get("anchor_ref") == anchor)
        and (theme is None or x.get("theme_tag") == theme)
        and (confidence_band is None or x.get("confidence_band") == confidence_band)
    ]
    offset = _decode_cursor(cursor)
    filtered_insights = all_insights[offset : offset + limit]
    next_offset = offset + len(filtered_insights)
    next_cursor = _encode_cursor(next_offset) if next_offset < len(all_insights) else None

    linked_ids: set[str] = set()
    for item in filtered_insights:
        for n in nodes:
            if n.get("anchor_ref") == item.get("anchor_ref") or n.get("theme_tag") == item.get("theme_tag"):
                linked_ids.add(str(n.get("node_id_public")))

    if filtered_insights:
        filtered_nodes = [n for n in nodes if str(n.get("node_id_public")) in linked_ids]
    else:
        filtered_nodes = nodes

    node_ids = {str(n.get("node_id_public")) for n in filtered_nodes}
    filtered_edges = [
        e
        for e in edges
        if str(e.get("source_node_id_public")) in node_ids and str(e.get("target_node_id_public")) in node_ids
    ]

    doc["insights"] = filtered_insights
    doc["nodes"] = filtered_nodes
    doc["edges"] = filtered_edges
    doc["pagination"] = {"limit": limit, "next_cursor": next_cursor}
    return doc
