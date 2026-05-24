"""B-track read-only interpretive bridge slice (shared by bundle builder and contemplation)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def interpretive_bridge_payload(full: dict[str, Any] | None, *, source_path: Path) -> dict[str, Any]:
    """Redacted slice of sasang_interpretive_insight_bundle — no interpretive_depth_ko."""
    base: dict[str, Any] = {
        "schema": "sasang_interpretive_bridge_slice_v1",
        "bridge_mode": "read_only_observation",
        "auto_weight_adjustment_forbidden": True,
        "track_a_live_routing_forbidden": True,
        "source_path": str(source_path.resolve()),
    }
    if not full:
        return {
            **base,
            "available": False,
            "reason": "interpretive_bundle_missing",
            "fact_safe_note": "Sasang interpretive bundle absent; run build_sasang_interpretive_insight_bundle_v1.py. "
            "No ensemble weight or direction change.",
        }
    if full.get("decision_authority") != "human_only":
        return {
            **base,
            "available": False,
            "reason": "decision_authority_not_human_only",
            "fact_safe_note": "Interpretive bundle rejected: decision_authority must be human_only.",
        }
    sections_slice: list[dict[str, Any]] = []
    for sec in full.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        sections_slice.append(
            {
                "axis_id": sec.get("axis_id"),
                "title_ko": sec.get("title_ko"),
                "availability": sec.get("availability"),
                "summary_ko": sec.get("summary_ko"),
            }
        )
    syn = full.get("synthesis_v1") if isinstance(full.get("synthesis_v1"), dict) else {}
    return {
        **base,
        "available": True,
        "source_bundle_schema": full.get("schema"),
        "source_bundle_version": full.get("version"),
        "generated_at_utc": full.get("generated_at_utc"),
        "decision_authority": full.get("decision_authority"),
        "rail": full.get("rail"),
        "axis_count": len(sections_slice),
        "sections_slice": sections_slice,
        "synthesis_guardrails_ko": {
            "forbidden_synthesis_ko": syn.get("forbidden_synthesis_ko"),
            "disagreement_protocol_ko": syn.get("disagreement_protocol_ko"),
        },
        "fact_safe_note": "Interpretive bridge is human_only reference. Forbidden: linear merge with sasang "
        "direction_score, clinical verdict, or live order sizing.",
    }


def compact_interpretive_for_prompt(bridge: dict[str, Any], *, max_axes: int = 8) -> str:
    """One-line-per-axis digest for LLM prompts (B-track, non-gating)."""
    if not bridge.get("available"):
        return f"interpretive_bridge: unavailable ({bridge.get('reason', 'unknown')})"
    lines = [
        "interpretive_bridge: available human_only B-track reference (non-gating)",
        f"axes={bridge.get('axis_count', 0)} version={bridge.get('source_bundle_version')}",
    ]
    guard = bridge.get("synthesis_guardrails_ko") if isinstance(bridge.get("synthesis_guardrails_ko"), dict) else {}
    forb = str(guard.get("forbidden_synthesis_ko") or "")[:240]
    if forb:
        lines.append(f"forbidden_synthesis: {forb}")
    for sec in (bridge.get("sections_slice") or [])[:max_axes]:
        if not isinstance(sec, dict):
            continue
        aid = sec.get("axis_id") or "?"
        avail = sec.get("availability") or "?"
        title = str(sec.get("title_ko") or "")[:80]
        lines.append(f"  - {aid} [{avail}] {title}")
    return "\n".join(lines)
