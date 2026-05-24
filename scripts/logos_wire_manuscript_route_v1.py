#!/usr/bin/env python3
"""Wire payload helpers for manuscript routing flags (v2 fabric)."""

from __future__ import annotations

from typing import Any

from scripts.logos_canon_manuscript_fabric_v2 import (
    WIRE_FLAG_RE_ROUTE_TR,
    apply_wire_manuscript_route,
    resolve_manuscript_route,
)

__all__ = [
    "WIRE_FLAG_RE_ROUTE_TR",
    "apply_wire_manuscript_route",
    "resolve_manuscript_route",
    "decode_routing_flags",
]


def decode_routing_flags(flags: int) -> dict[str, bool]:
    return {
        "re_route_tr": bool(flags & WIRE_FLAG_RE_ROUTE_TR),
    }


def enrich_lexicon_wire_payload(
    payload: dict[str, Any],
    *,
    verse_id: str,
    fabric: dict[str, Any],
) -> dict[str, Any]:
    """Apply route metadata when payload carries a single-verse context."""
    if not verse_id:
        return payload
    return apply_wire_manuscript_route(payload, verse_id, fabric)
