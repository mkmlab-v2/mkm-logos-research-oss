#!/usr/bin/env python3
"""Saving the News — public showroom copy facade (engineering vocabulary, IP guard).

Internal lens IDs unchanged in JSON `lens_id`; display labels and digests are sanitized
for `display_mode=public_showroom` per PUBLIC_FACING v1.7 + MYEONGRI_EXTERNAL_LEXICON.
"""
from __future__ import annotations

import copy
import re
from typing import Any

DISPLAY_INTERNAL = "internal_ops"
DISPLAY_PUBLIC = "public_showroom"

LENS_PUBLIC_LABEL: dict[str, str] = {
    "sasang": "단기 역학 (phase dynamics)",
    "myeongni": "타임라인·캘린더 컨텍스트",
    "logos": "서사 비유 채널 (관측 전용)",
    "news": "뉴스 스트림 (관측)",
    "macro": "매크로 스트림 (관측)",
}

SLOT_PUBLIC_LABEL: dict[str, str] = {
    "sasang": "단기 역학",
    "myeongni": "캘린더 컨텍스트",
    "logos": "서사 비유 (비게이팅)",
}

PUBLIC_UI = {
    "title": "Event Context — Multi-Signal Observability",
    "subtitle": "Regime field → signal channels → conflict resolver → observation posture · research_only",
    "banner": "OBSERVATION ONLY — NOT INVESTMENT ADVICE · HYPOTHESIS TIER B",
    "tab_layer_a": "Signals · Matrix",
    "tab_layer_b": "Context appendix (non-gating)",
    "layer_b_lede": "Semantic context appendix — not fact synthesis, trade advice, or broadcast trigger.",
    "flywheel_heading": "Transparency metrics (axis-separated)",
}

PUBLIC_TAGS = ["[OBSERVATION]", "[NON-TRIGGER]"]

# Substrings forbidden in public-facing string fields (case-insensitive scan).
FORBIDDEN_PUBLIC_SUBSTRINGS: tuple[str, ...] = (
    "성경",
    "시편",
    "창세",
    "출애",
    "신실",
    "언약",
    "GraphRAG",
    "graphrag",
    "Logos",
    "logos_subgraph",
    "명리",
    "사상",
    "사주",
    "만세력",
    "myeongni",
    "sasang",
    "verse",
    "bridges=",
    "paths=",
    "verses=",
    "state_id=",
    "direction_score =",
    "B-track state",
    "[NON_GATING]",
)

_THEOLOGY_RE = re.compile(
    r"시편\s*\d+|성경|신실·언약|언약|GraphRAG|Logos\s*\[|명리\s*관측|사상\s*동역학",
    re.IGNORECASE,
)
_FORMULA_RE = re.compile(
    r"state_id=\d+|direction_score\s*=|0\.\d+\*direct|mapping_target=",
    re.IGNORECASE,
)


def _public_digest(lens_id: str, digest: str, *, direction_label: str = "", confidence: object = None) -> str:
    d = str(digest or "").strip()
    if lens_id == "logos":
        return "서사 비유 매칭(관측 전용·비게이팅) — 경로·절 참조 비노출"
    if lens_id == "myeongni":
        base = f"세그먼트 컨텍스트 · posture={direction_label or 'neutral'}"
        if confidence is not None:
            return f"{base} · confidence={confidence}"
        return base
    if lens_id == "sasang":
        return f"단기 phase dynamics · posture={direction_label or 'neutral'}"
    if lens_id in {"news", "macro"}:
        return (d[:100] + "…") if len(d) > 100 else d
    return "관측 요약(내부 파이프라인 비노출)"


def _sanitize_flavor(slot: dict[str, Any]) -> str:
    lid = str(slot.get("lens_id", ""))
    scores_note = ""
    flavor = str(slot.get("flavor_ko") or "")
    if "direction_score" in flavor:
        m = re.search(r"direction_score[=:]?\s*([-0-9.]+)", flavor)
        if m:
            scores_note = f" · score={m.group(1)}"
    if lid == "logos":
        bridges = 0
        m = re.search(r"bridges=(\d+)", flavor)
        if m:
            bridges = int(m.group(1))
        return f"의미 그래프 motif 매칭 {bridges}건(관측 전용·비게이팅){scores_note}"
    if lid == "myeongni":
        return f"캘린더·타임라인 세그먼트 관측(참고 지표){scores_note}"
    if lid == "sasang":
        return f"단기 phase dynamics 관측{scores_note}"
    return "컨텍스트 관측(내부 식별자 비노출)"


def _public_coordinator_brief(headline: str, slots: list[dict[str, Any]]) -> str:
    lines = [
        "[OBSERVATION] Multi-signal context appendix — not fact fusion, trade advice, or auto-trigger.",
        f"Headline anchor: {headline[:200] or '(none)'}",
    ]
    for s in slots:
        label = SLOT_PUBLIC_LABEL.get(str(s.get("lens_id", "")), "context channel")
        lines.append(f"- {label}: {_sanitize_flavor(s)[:180]}")
    lines.append("Coordinator: Layer A matrix drives posture; this tab is explanatory only.")
    return "\n".join(lines)


def sanitize_matrix_row(row: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(row)
    lid = str(out.get("lens_id", ""))
    out["label_ko"] = LENS_PUBLIC_LABEL.get(lid, "signal channel")
    out["label_public"] = out["label_ko"]
    out["tags"] = list(PUBLIC_TAGS)
    if out.get("non_gating"):
        out["tags"].append("[EXPLANATORY-ONLY]")
    out["digest"] = _public_digest(
        lid,
        str(out.get("digest", "")),
        direction_label=str(out.get("direction_label", "")),
        confidence=out.get("confidence"),
    )
    out.pop("artifact_path", None)
    return out


def sanitize_layer_b_slot(slot: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(slot)
    lid = str(out.get("lens_id", ""))
    out["display_label"] = SLOT_PUBLIC_LABEL.get(lid, "context channel")
    out["tags"] = list(PUBLIC_TAGS)
    if out.get("non_gating"):
        out["tags"].append("[EXPLANATORY-ONLY]")
    out["flavor_ko"] = _sanitize_flavor(out)
    if out.get("source_kind") == "logos_subgraph_graphrag":
        out["source_kind"] = "semantic_motif_graph"
    elif out.get("source_kind") == "lens_snapshot":
        out["source_kind"] = "signal_snapshot"
    out.pop("artifact_path", None)
    out.pop("router_artifact_path", None)
    return out


def sanitize_flywheel_axis(axis: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(axis)
    label = str(out.get("label", ""))
    if "hit rate" in label.lower() or out.get("axis_id") == "BTRACK_PRICE_HIT_RATE":
        out["label"] = "Directional observation rate (30d window, B-track)"
    elif "jaccard" in label.lower() or out.get("axis_id") == "NEWS_RT_OFFLINE":
        out["label"] = "Offline cohort fidelity proxy (NEWS-RT bench)"
    elif out.get("axis_id") == "PANEL_ALERT_1":
        out["label"] = "24h panel performance alert (observation)"
    out.pop("source", None)
    return out


def apply_public_facade_to_panel(panel: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(panel)
    out["display_mode"] = DISPLAY_PUBLIC
    out["public_ui"] = dict(PUBLIC_UI)
    out["copy_facade"] = {
        "schema": "saving_the_news_public_copy_facade_v1",
        "version": "1.0.0",
        "disclaimer_ref": "PUBLIC_FACING_v1.7_saving_the_news",
        "internal_lens_ids_retained": True,
        "theology_verse_refs_stripped": True,
    }
    out["matrix_rows"] = [sanitize_matrix_row(r) for r in out.get("matrix_rows") or [] if isinstance(r, dict)]
    lb = out.get("layer_b")
    if isinstance(lb, dict):
        slots = lb.get("perspective_slots") or []
        lb = copy.deepcopy(lb)
        lb["perspective_slots"] = [sanitize_layer_b_slot(s) for s in slots if isinstance(s, dict)]
        lb["coordinator_brief_ko"] = _public_coordinator_brief(
            str((out.get("headline_anchor") or {}).get("headline", "")),
            slots,
        )
        lb["hypo_tags"] = list(PUBLIC_TAGS)
        lb.pop("appendix_ref", None)
        lb.pop("flywheel_as_ref", None)
        out["layer_b"] = lb
    out["flywheel_as_axes"] = [
        sanitize_flywheel_axis(a) for a in out.get("flywheel_as_axes") or [] if isinstance(a, dict)
    ]
    out.pop("external_channel_metaphor", None)
    disclaimer = out.get("external_channel_disclaimer")
    if isinstance(disclaimer, str) and disclaimer:
        out["external_channel_disclaimer"] = (
            "External metaphor channels are observational labels only — not official lens names."
        )
    field = out.get("field")
    if isinstance(field, dict):
        field = copy.deepcopy(field)
        field["note"] = "Observation snapshot — regime posture from ops gates; hypothesis tier B."
        out["field"] = field
    return out


def _collect_strings(obj: Any, prefix: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(obj, str):
        found.append((prefix, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in {"lens_id", "display_mode", "schema", "copy_facade"}:
                continue
            found.extend(_collect_strings(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found.extend(_collect_strings(item, f"{prefix}[{i}]"))
    return found


def scan_public_violations(panel: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for path, text in _collect_strings(panel):
        lower = text.lower()
        for term in FORBIDDEN_PUBLIC_SUBSTRINGS:
            if term.lower() in lower:
                violations.append(f"{path}: contains {term!r}")
                break
    return violations
