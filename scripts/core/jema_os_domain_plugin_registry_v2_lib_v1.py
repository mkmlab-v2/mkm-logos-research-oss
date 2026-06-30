#!/usr/bin/env python3
"""JEMA OS domain plugin registry v2 — load + UMR slot resolve helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_V2 = ROOT / "docs/final/artifacts/jema_os_domain_plugin_registry_v2_latest.json"

_REGISTRY_CACHE: dict[str, Any] | None = None
_UMR_INDEX_CACHE: dict[str, str] | None = None


def registry_v2_path() -> Path:
    return REGISTRY_V2


def registry_v2_ref() -> str:
    if REGISTRY_V2.is_file():
        return str(REGISTRY_V2.relative_to(ROOT)).replace("\\", "/")
    return "docs/final/artifacts/jema_os_domain_plugin_registry_v2_latest.json"


def load_registry_v2(*, refresh: bool = False) -> dict[str, Any] | None:
    global _REGISTRY_CACHE, _UMR_INDEX_CACHE
    if _REGISTRY_CACHE is not None and not refresh:
        return _REGISTRY_CACHE
    if not REGISTRY_V2.is_file():
        return None
    try:
        doc = json.loads(REGISTRY_V2.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(doc, dict) or doc.get("schema") != "jema_os_domain_plugin_registry_v2":
        return None
    _REGISTRY_CACHE = doc
    _UMR_INDEX_CACHE = None
    return doc


def umr_lane_index(registry: dict[str, Any] | None = None) -> dict[str, str]:
    global _UMR_INDEX_CACHE
    if _UMR_INDEX_CACHE is not None:
        return _UMR_INDEX_CACHE
    reg = registry or load_registry_v2()
    idx: dict[str, str] = {}
    if not reg:
        _UMR_INDEX_CACHE = idx
        return idx
    slots = reg.get("slots") or {}
    for slot_id, slot in slots.items():
        if not isinstance(slot, dict):
            continue
        umr_lane = str(slot.get("umr_lane") or slot_id).strip().lower()
        idx[umr_lane] = str(slot_id)
    _UMR_INDEX_CACHE = idx
    return idx


def known_umr_lanes(registry: dict[str, Any] | None = None) -> set[str]:
    return set(umr_lane_index(registry).keys())


def resolve_slot_for_umr_domain(domain: str, registry: dict[str, Any] | None = None) -> dict[str, Any] | None:
    reg = registry or load_registry_v2()
    if not reg:
        return None
    lane = (domain or "").strip().lower()
    if lane == "oracle":
        lane = "logos"
    idx = umr_lane_index(reg)
    slot_id = idx.get(lane)
    if not slot_id:
        return None
    slot = (reg.get("slots") or {}).get(slot_id)
    if not isinstance(slot, dict):
        return None
    return dict(slot)


def build_slot_overlay(domain: str, registry: dict[str, Any] | None = None) -> dict[str, Any] | None:
    slot = resolve_slot_for_umr_domain(domain, registry)
    if not slot:
        return None
    pin = slot.get("knowledge_pin") if isinstance(slot.get("knowledge_pin"), dict) else None
    return {
        "slot_id": slot.get("slot_id"),
        "slot_kind": slot.get("slot_kind"),
        "lane_label_ko": slot.get("lane_label_ko"),
        "umr_lane": slot.get("umr_lane"),
        "spec_gap_intake_lane": slot.get("spec_gap_intake_lane"),
        "spec_gap_intent_chip": slot.get("spec_gap_intent_chip"),
        "plugin_id": slot.get("plugin_id"),
        "u3_tier": slot.get("u3_tier"),
        "has_knowledge_pin": bool(pin),
        "knowledge_pin_floor": pin.get("min_line_count_floor") if pin else None,
        "send_gate": "HOLD",
        "research_only": True,
    }


def plugin_row_from_v2_slot(slot: dict[str, Any]) -> dict[str, Any]:
    return {
        "plugin_id": str(slot.get("plugin_id") or "unknown_v2_slot"),
        "agent_read_order": [],
        "low_res_runners": list(slot.get("low_res_runners") or []),
        "hold_flags": list(slot.get("hold_flags") or []),
        "u3_tier": str(slot.get("u3_tier") or "lite"),
        "slot_id": slot.get("slot_id"),
        "slot_kind": slot.get("slot_kind"),
    }
