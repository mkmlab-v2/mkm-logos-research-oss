#!/usr/bin/env python3
"""Build 3-lens fusion + coordinator decision (Sasang/Myeongni/Logos)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SASANG = ROOT / "reports" / "sasang_rule_based_response_v1_latest.json"
DEFAULT_MYEONGNI = ROOT / "docs" / "final" / "artifacts" / "mkm_myeongni_response_v2_latest.json"
DEFAULT_LOGOS = ROOT / "docs" / "final" / "artifacts" / "logos_response_v1_retry_selected_latest.json"
DEFAULT_FIELD_GATE = ROOT / "docs" / "final" / "artifacts" / "one_plus_three_gate_decision_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "three_lens_fusion_coordinator_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sasang_decision(doc: dict[str, Any]) -> str:
    sec = doc.get("sections") if isinstance(doc.get("sections"), dict) else {}
    trans = sec.get("byungjeungyakri_transition") if isinstance(sec.get("byungjeungyakri_transition"), dict) else {}
    state = str(trans.get("state") or "").lower()
    probs = trans.get("next_state_probabilities") if isinstance(trans.get("next_state_probabilities"), list) else []
    stress_p = 0.0
    crisis_p = 0.0
    for row in probs:
        if not isinstance(row, dict):
            continue
        name = str(row.get("state") or "").lower()
        p = float(row.get("probability") or 0.0)
        if name == "stress":
            stress_p = p
        if name == "crisis":
            crisis_p = p
    if state in {"stress", "crisis"} or (stress_p + crisis_p) >= 0.45:
        return "REDUCE"
    if state == "calm":
        return "WATCH"
    return "WATCH"


def _myeongni_decision(doc: dict[str, Any]) -> str:
    final = doc.get("final_action") if isinstance(doc.get("final_action"), dict) else {}
    return str(final.get("decision") or "WATCH").upper()


def _logos_context(doc: dict[str, Any]) -> str:
    phase = doc.get("archetypal_chaos_order_phase") if isinstance(doc.get("archetypal_chaos_order_phase"), dict) else {}
    tension = float(phase.get("tension_score") or 0.0)
    if tension >= 0.7:
        return "RISK_ELEVATED"
    if tension <= 0.35:
        return "STABILITY_CANDIDATE"
    return "MIXED"


def _extract_sasang_stress_score(doc: dict[str, Any]) -> float:
    sec = doc.get("sections") if isinstance(doc.get("sections"), dict) else {}
    trans = sec.get("byungjeungyakri_transition") if isinstance(sec.get("byungjeungyakri_transition"), dict) else {}
    probs = trans.get("next_state_probabilities") if isinstance(trans.get("next_state_probabilities"), list) else []
    stress = 0.0
    crisis = 0.0
    for row in probs:
        if not isinstance(row, dict):
            continue
        name = str(row.get("state") or "").lower()
        p = float(row.get("probability") or 0.0)
        if name == "stress":
            stress = p
        elif name == "crisis":
            crisis = p
    return max(0.0, min(1.0, stress + crisis))


def _extract_myeongni_scores(doc: dict[str, Any]) -> tuple[float, float]:
    core = doc.get("core_layer") if isinstance(doc.get("core_layer"), dict) else {}
    coord = doc.get("coordinator_layer") if isinstance(doc.get("coordinator_layer"), dict) else {}
    direction_core = float(core.get("direction_core") or 0.0)
    confidence_adjusted = float(coord.get("confidence_adjusted") or core.get("confidence_core") or 0.0)
    # direction_core in [-1,1] -> [0,1]
    direction_norm = max(0.0, min(1.0, (direction_core + 1.0) / 2.0))
    confidence_norm = max(0.0, min(1.0, confidence_adjusted))
    return direction_norm, confidence_norm


def _extract_logos_tension(doc: dict[str, Any]) -> float:
    phase = doc.get("archetypal_chaos_order_phase") if isinstance(doc.get("archetypal_chaos_order_phase"), dict) else {}
    return max(0.0, min(1.0, float(phase.get("tension_score") or 0.0)))


def _extract_chronicle_signal(doc: dict[str, Any]) -> tuple[float | None, list[str]]:
    rows = doc.get("chronicle_mapping") if isinstance(doc.get("chronicle_mapping"), list) else []
    pointers: list[str] = []
    scores: list[float] = []
    pat = re.compile(r"관측점수=([0-9]*\.?[0-9]+)")
    for row in rows:
        if not isinstance(row, dict):
            continue
        ptr = str(row.get("evidence_pointer") or "").strip()
        if ptr:
            pointers.append(ptr)
        summary = str(row.get("summary") or "")
        m = pat.search(summary)
        if m:
            try:
                scores.append(float(m.group(1)))
            except ValueError:
                pass
    chronicle_signal = None if not scores else max(0.0, min(1.0, sum(scores) / len(scores)))
    unique_pointers = sorted(set(pointers))
    return chronicle_signal, unique_pointers


def _logos_non_gating_ok(doc: dict[str, Any]) -> bool:
    marker_ok = str(doc.get("final_insight_non_gating") or "").upper().find("NON_GATING") >= 0
    ontology = doc.get("ontology_trace") if isinstance(doc.get("ontology_trace"), dict) else {}
    deep = doc.get("deep_logos_tension_gematria") if isinstance(doc.get("deep_logos_tension_gematria"), dict) else {}
    morph = doc.get("morphology_layer") if isinstance(doc.get("morphology_layer"), dict) else {}
    trace_non_gating = any(
        [
            ontology.get("non_gating_only") is True,
            deep.get("non_gating_only") is True,
            morph.get("non_gating_only") is True,
        ]
    )
    return bool(marker_ok and trace_non_gating)


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return _read_json(path)


def _field_gate_override(gate_doc: dict[str, Any]) -> tuple[str | None, str | None]:
    level = str(gate_doc.get("gate_level") or "").lower()
    if level == "critical":
        return "HOLD", "field_gate_critical_override"
    if level == "warning":
        return "WATCH", "field_gate_warning_cap"
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sasang-json", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--myeongni-json", type=Path, default=DEFAULT_MYEONGNI)
    ap.add_argument("--logos-json", type=Path, default=DEFAULT_LOGOS)
    ap.add_argument("--field-gate-json", type=Path, default=DEFAULT_FIELD_GATE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sasang_path = args.sasang_json if args.sasang_json.is_absolute() else ROOT / args.sasang_json
    myeongni_path = args.myeongni_json if args.myeongni_json.is_absolute() else ROOT / args.myeongni_json
    logos_path = args.logos_json if args.logos_json.is_absolute() else ROOT / args.logos_json
    field_gate_path = args.field_gate_json if args.field_gate_json.is_absolute() else ROOT / args.field_gate_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    for p in (sasang_path, myeongni_path, logos_path):
        if not p.is_file():
            raise SystemExit(f"Missing required input: {p}")

    sasang = _read_json(sasang_path)
    myeongni = _read_json(myeongni_path)
    logos = _read_json(logos_path)
    field_gate = _read_json_optional(field_gate_path)

    d_sasang = _sasang_decision(sasang)
    d_myeongni = _myeongni_decision(myeongni)
    logos_ctx = _logos_context(logos)
    logos_non_gating = _logos_non_gating_ok(logos)
    sasang_stress = _extract_sasang_stress_score(sasang)
    myeongni_dir, myeongni_conf = _extract_myeongni_scores(myeongni)
    logos_tension = _extract_logos_tension(logos)
    chronicle_signal, chronicle_pointers = _extract_chronicle_signal(logos)

    primary = [d_sasang, d_myeongni]
    if "REDUCE" in primary:
        action = "REDUCE"
    elif "GO" in primary:
        action = "GO"
    elif "WATCH" in primary:
        action = "WATCH"
    else:
        action = "HOLD"
    field_override_action, field_override_reason = _field_gate_override(field_gate)
    if field_override_action == "HOLD":
        action = "HOLD"
    elif field_override_action == "WATCH" and action == "GO":
        action = "WATCH"

    conflicts: list[str] = []
    if d_sasang != d_myeongni:
        conflicts.append("sasang_vs_myeongni")
    if logos_ctx == "RISK_ELEVATED" and action == "GO":
        conflicts.append("logos_context_vs_primary")

    payload = {
        "schema": "three_lens_fusion_coordinator_v1",
        "generated_at_utc": _now(),
        "track": "B_TRACK",
        "inputs": {
            "sasang_json": str(sasang_path),
            "myeongni_json": str(myeongni_path),
            "logos_json": str(logos_path),
        },
        "lens_contract": {
            "sasang_role": "short_term_intensity",
            "myeongni_role": "mid_term_direction",
            "logos_role": "macro_context_non_gating",
            "field_role": "ops_regime_gate_primary",
            "final_policy": "field gate > sasang+myeongni primary > logos contextual only",
        },
        "fusion": {
            "sasang_decision": d_sasang,
            "myeongni_decision": d_myeongni,
            "logos_context": logos_ctx,
            "logos_non_gating_ok": logos_non_gating,
            "conflicts": conflicts,
            "common_feature_vector_v1": {
                "schema": "three_lens_common_feature_vector_v1",
                "sasang_stress_score_0_1": round(sasang_stress, 6),
                "myeongni_direction_score_0_1": round(myeongni_dir, 6),
                "myeongni_confidence_score_0_1": round(myeongni_conf, 6),
                "logos_tension_score_0_1": round(logos_tension, 6),
                "chronicle_signal_score_0_1": None if chronicle_signal is None else round(chronicle_signal, 6),
                "chronicle_evidence_pointers": chronicle_pointers,
            },
        },
        "coordinator": {
            "action": action,
            "risk_level": "elevated" if action == "REDUCE" else "moderate",
            "human_signoff_required": True,
            "research_only": True,
            "field_override": {
                "applied": bool(field_override_action is not None),
                "action": field_override_action,
                "reason": field_override_reason,
                "source_json": str(field_gate_path),
                "gate_level": field_gate.get("gate_level"),
            },
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "action": action}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
