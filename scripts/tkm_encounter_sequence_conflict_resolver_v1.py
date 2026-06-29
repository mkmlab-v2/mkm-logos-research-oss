#!/usr/bin/env python3
"""TKM encounter_sequence L7 conflict resolver observation (Field→Lens→Conflict) [HYPO]."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def latest_records_by_sequence_id(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_seq: dict[str, dict[str, Any]] = {}
    for row in records:
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        seq_id = str(enc.get("sequence_id") or "")
        if seq_id:
            by_seq[seq_id] = row
    return list(by_seq.values())


def top_primitive_from_anchor(anchor: dict[str, Any]) -> str:
    align = anchor.get("kernel_alignment") if isinstance(anchor.get("kernel_alignment"), list) else []
    if not align:
        return "unknown"
    best = max(align, key=lambda row: float(row.get("similarity_adjusted") or row.get("similarity") or 0))
    return str(best.get("primitive") or "unknown")


def _load_anchor(ref_rel: str) -> dict[str, Any] | None:
    path = ROOT / ref_rel.replace("\\", "/")
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_observation(record: dict[str, Any]) -> dict[str, Any] | None:
    l5 = record.get("l5_myeongni_ref")
    l6 = record.get("l6_logos_ref")
    if not isinstance(l6, dict):
        return None

    summary = record.get("sequence_summary") if isinstance(record.get("sequence_summary"), dict) else {}
    l4_label = str(summary.get("final_ai_constitution") or "uncertain")
    cross = str(l5.get("cross_check_status") or "not_computed") if isinstance(l5, dict) else "not_computed"

    l6_primitive = "not_loaded"
    ref = str(l6.get("logos_cosmic_anchor_ref") or "")
    if ref:
        anchor = _load_anchor(ref)
        if anchor:
            l6_primitive = top_primitive_from_anchor(anchor)

    if not isinstance(l5, dict):
        resolver_status = "insufficient_lenses"
        conflict_count = 0
    elif cross == "match":
        resolver_status = "l5_sasang_aligned"
        conflict_count = 0
    elif cross == "partial":
        resolver_status = "advisory_partial"
        conflict_count = 1
    elif cross == "mismatch":
        resolver_status = "advisory_mismatch"
        conflict_count = 1
    else:
        resolver_status = "insufficient_lenses"
        conflict_count = 0

    physician = record.get("physician_closure") if isinstance(record.get("physician_closure"), dict) else {}
    agreement = physician.get("agreement") if isinstance(physician.get("agreement"), dict) else {}
    final_action = "hold_hypothesis"
    if physician and agreement.get("ai_physician_match") is False:
        final_action = "physician_authority_preserved"

    return {
        "hypothesis_tier": "B",
        "non_gating": True,
        "field_l4_sasang_label": l4_label,
        "lens_myeongni_cross_status": cross,
        "lens_logos_top_primitive": l6_primitive,
        "logos_lens_non_gating": True,
        "resolver_status": resolver_status,
        "conflict_count": conflict_count,
        "final_action_observed": final_action,
        "track_a_autobind_forbidden": True,
        "constitution_merge_forbidden": True,
        "note_ko": "[HYPO][NON_GATING] Field→Lens(3)→Conflict 관측; 사상 주·명리/성경 보; constitution overwrite 금지.",
    }


def attach_observation(record: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    out = dict(record)
    if out.get("l7_conflict_resolver_ref") and not force:
        return out
    obs = build_observation(out)
    if obs:
        out["l7_conflict_resolver_ref"] = obs
    return out


def validate_separation(record: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    sidecar = record.get("l7_conflict_resolver_ref")
    if not isinstance(sidecar, dict):
        return errs
    if sidecar.get("non_gating") is not True:
        errs.append("l7_conflict_resolver_ref.non_gating must be true")
    if sidecar.get("constitution_merge_forbidden") is not True:
        errs.append("l7_conflict_resolver_ref.constitution_merge_forbidden must be true")
    if sidecar.get("track_a_autobind_forbidden") is not True:
        errs.append("l7_conflict_resolver_ref.track_a_autobind_forbidden must be true")
    forbidden_actions = ("autobind", "track_a_promote", "live_trade")
    action = str(sidecar.get("final_action_observed") or "")
    if action in forbidden_actions:
        errs.append(f"forbidden final_action_observed: {action}")
    forbidden_keys = ("final_ai_constitution", "physician_constitution", "merged_constitution")
    for key in forbidden_keys:
        if key in sidecar:
            errs.append(f"l7_conflict_resolver_ref must not contain {key}")
    return errs
