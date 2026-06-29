# -*- coding: utf-8 -*-
"""lens_pack@myeongni_timeline ↔ manseryeok engine bridge v1 [HYPO · B-track]."""

from __future__ import annotations

from typing import Any

SCHEMA_ID = "lens_context_mesh_manseryeok_bridge_v1"
VERSION = "1.0.0"

ENGINE_SCRIPT = "scripts/manseryeok_engine_lookup_v1.py"
PACK_ID = "lens_pack@myeongni_timeline"

# Pedagogical slice node ids (build_myeongni_timeline_slice).
KNOWN_PILLAR_NODES = frozenset(
    {
        "pillar::year::gapsul",
        "pillar::month::byeongjin",
        "pillar::day::muja",
    }
)

_GANJI_SLUG: dict[str, str] = {
    "갑술": "gapsul",
    "甲戌": "gapsul",
    "병진": "byeongjin",
    "丙辰": "byeongjin",
    "무자": "muja",
    "戊子": "muja",
}

_DEFAULT_FIXTURE_REQUEST: dict[str, Any] = {
    "schema": "saju_global_birth_request_v1",
    "version": "1.0.0",
    "local_civil": {"year": 1984, "month": 5, "day": 15, "hour": 10, "minute": 30, "second": 0},
    "iana_tz": "Asia/Seoul",
    "is_male": True,
}


def ganji_to_slug(ganji: str | None) -> str:
    raw = (ganji or "").strip()
    if not raw:
        return "unmapped"
    return _GANJI_SLUG.get(raw, "unmapped")


def pillar_node_id(role: str, ganji: str | None) -> str:
    return f"pillar::{role}::{ganji_to_slug(ganji)}"


def bindings_from_lookup(lookup: dict[str, Any]) -> list[dict[str, Any]]:
    four = lookup.get("four_pillars") or {}
    out: list[dict[str, Any]] = []
    for role in ("year", "month", "day", "hour"):
        ganji = four.get(role)
        node_id = pillar_node_id(role, str(ganji) if ganji is not None else None)
        out.append(
            {
                "pillar_role": role,
                "ganji": ganji,
                "node_id": node_id,
                "slice_node_matched": node_id in KNOWN_PILLAR_NODES,
            }
        )
    return out


def build_manseryeok_bridge_v1(
    *,
    lookup: dict[str, Any] | None = None,
    use_fixture_if_missing: bool = True,
) -> dict[str, Any]:
    """Bridge manseryeok engine output to myeongni timeline mesh nodes."""
    engine_linked = False
    lookup_doc: dict[str, Any] | None = None
    err: str | None = None

    if lookup is not None:
        lookup_doc = lookup
        engine_linked = lookup.get("schema") == "manseryeok_engine_lookup_v1"
    elif use_fixture_if_missing:
        try:
            from scripts.manseryeok_engine_lookup_v1 import lookup_from_request

            lookup_doc = lookup_from_request(_DEFAULT_FIXTURE_REQUEST, include_full_saju=False)
            engine_linked = True
        except Exception as exc:  # noqa: BLE001 — bridge must stay deterministic shell
            err = str(exc)

    bindings = bindings_from_lookup(lookup_doc) if lookup_doc else []
    matched = sum(1 for b in bindings if b.get("slice_node_matched"))

    return {
        "schema": SCHEMA_ID,
        "version": VERSION,
        "research_only": True,
        "hypothesis_class": "HYPO",
        "send_gate": "HOLD",
        "non_gating": True,
        "pack_id": PACK_ID,
        "engine_script": ENGINE_SCRIPT,
        "engine_linked": engine_linked,
        "engine_error": err,
        "auto_gating_forbidden": True,
        "binding_rules_ko": (
            "만세력 four_pillars → pillar::{role}::{ganji_slug} 노드 id. "
            "슬라이스에 없는 slug는 orphan — UI에서 hide_orphans_default 적용. "
            "최종 중기 방향은 지휘관·NON_GATING 해석만."
        ),
        "node_bindings": bindings,
        "slice_match_summary": {
            "known_pillar_nodes": sorted(KNOWN_PILLAR_NODES),
            "matched_count": matched,
            "binding_count": len(bindings),
        },
        "reproduce": (
            "py scripts/manseryeok_engine_lookup_v1.py --request-json <saju_global_birth_request_v1.json> "
            "&& py scripts/build_lens_context_mesh_myeongni_timeline_pack_v1.py"
        ),
        "anchors": [
            "docs/research/FOUR_LENS_YINYANG_REGULARIZATION_V1.md",
            "docs/final/artifacts/MANSE_ENGINE_LOOKUP_API_V1_CONTRACT.json",
        ],
    }
