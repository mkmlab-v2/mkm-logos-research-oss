"""mkmlife cosmic anchor orb draft — Python mirror of mkmlifeCosmicAnchorV1.ts (Wave 3 sim).

Keeps TS and offline sim aligned for resolveCosmicAnchorOrbDraft logic.
"""

from __future__ import annotations

import re
from typing import Any, Mapping


def infer_stress_from_orb_context(question: str = "", context_blob: str = "") -> float:
    blob = f"{question}\n{context_blob}".strip()
    if not blob:
        return 0.35
    if re.search(r"위기|고난|suffering|pain|panic|crisis|REDUCE", blob, re.I):
        return 0.78
    if re.search(r"불안|스트레스|긴장|잡음|과열|압박|WATCH|conflict_count", blob, re.I):
        return 0.62
    if re.search(r"회복|평안|수면|페이싱|쉬어|잔잔|관측 우선", blob, re.I):
        return 0.4
    return 0.28


def _num_draft(draft: Mapping[str, Any], key: str, fallback: float) -> float:
    v = draft.get(key)
    if isinstance(v, (int, float)):
        return float(v)
    return fallback


def _str_draft(draft: Mapping[str, Any], key: str, fallback: str) -> str:
    v = draft.get(key)
    return str(v) if isinstance(v, str) else fallback


def _alignment_row(align: list[dict[str, Any]], primitive: str) -> dict[str, Any]:
    for row in align:
        if row.get("primitive") == primitive:
            return row
    return align[0] if align else {}


def resolve_cosmic_anchor_orb_draft(
    anchor: Mapping[str, Any],
    stress: float,
) -> dict[str, Any]:
    """Resonance-weighted orb draft — rhythm/frame/spacing only ([HYPO])."""
    align = list(anchor.get("kernel_alignment") or [])
    survival = _alignment_row(align, "survival")
    pathology = _alignment_row(align, "pathology")
    circulation = _alignment_row(align, "circulation")
    harmony = _alignment_row(align, "harmony")

    stress_w = min(1.0, max(0.0, float(stress)))
    s_draft = survival.get("draft") or {}
    p_draft = pathology.get("draft") or {}
    c_draft = circulation.get("draft") or {}
    h_draft = harmony.get("draft") or {}

    resonance_score = (
        round(sum(float(r.get("similarity", 0)) for r in align) / len(align), 4)
        if align
        else 0.0
    )

    min_padding_px = round(_num_draft(s_draft, "min_padding_px", 16) + stress_w * 10)
    max_blocks_per_view = max(
        1,
        round(_num_draft(s_draft, "max_blocks_per_view", 4) - stress_w),
    )
    intensity_budget = min(
        1.0,
        max(0.15, _num_draft(p_draft, "intensity_budget", 0.65) * (1 - stress_w * 0.22)),
    )
    pulse_period_ms = round(_num_draft(c_draft, "pulse_period_ms", 3600) + stress_w * 900)
    layout_density = min(0.65, _num_draft(h_draft, "layout_density", 0.45) + stress_w * 0.06)
    contrast_cap = max(0.22, _num_draft(h_draft, "contrast_cap", 0.35) - stress_w * 0.07)

    return {
        "schema": "mkmlife_cosmic_anchor_orb_draft_v1",
        "anchor_id": anchor.get("anchor_id"),
        "verse_refs": anchor.get("verse_refs") or [],
        "stress_proxy": round(stress_w, 3),
        "resonance_score": resonance_score,
        "intensity_budget": round(intensity_budget, 4),
        "pulse_period_ms": pulse_period_ms,
        "min_padding_px": min_padding_px,
        "max_blocks_per_view": max_blocks_per_view,
        "layout_density": round(layout_density, 4),
        "contrast_cap": round(contrast_cap, 4),
        "harmony_pair_kind": _str_draft(h_draft, "pair_kind", "same"),
        "top1_primitive": align[0].get("primitive") if align else None,
        "non_gating": True,
        "forbidden_synthesis": True,
        "disclaimer_ko": (
            "[HYPO][NON_GATING] cosmic anchor resonance draft — "
            "서사·수치 공명이며 신학·체질 단정 아님."
        ),
    }


def draft_fingerprint(draft: Mapping[str, Any]) -> str:
    keys = (
        "min_padding_px",
        "max_blocks_per_view",
        "intensity_budget",
        "pulse_period_ms",
        "layout_density",
        "contrast_cap",
        "harmony_pair_kind",
    )
    parts = [f"{k}={draft.get(k)}" for k in keys]
    return "|".join(parts)
