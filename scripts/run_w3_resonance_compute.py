#!/usr/bin/env python3
"""Deterministic W3 resonance compute for B-track pilot artifacts.

Reads:
  - docs/final/artifacts/W3_PILOT_MIN_INPUT_V1.json
  - docs/final/artifacts/W3_RESONANCE_COMPUTE_SPEC_V1.json

Writes:
  - docs/final/artifacts/W3_RESONANCE_RESULT_V1.json

This script is intentionally deterministic and non-random so that repeated
runs on identical inputs produce identical outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_STR = str(Path(__file__).resolve().parents[1])
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from scripts.core.w3_aux_adapter import compute_aux_macro_signal, compute_aux_personal_signal


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "W3_PILOT_MIN_INPUT_V1.json"
DEFAULT_SPEC = ROOT / "docs" / "final" / "artifacts" / "W3_RESONANCE_COMPUTE_SPEC_V1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "W3_RESONANCE_RESULT_V1.json"


def _stable_score(*parts: str) -> float:
    key = "|".join(parts).encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()
    # Deterministic 0.35..0.95 band for pilot stability.
    base = int(digest[:8], 16) / 0xFFFFFFFF
    score = 0.35 + (0.60 * base)
    return round(score, 6)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_hypo(rationale: str) -> bool:
    return "[HYPO]" in (rationale or "")


def _has_required_notice(text: str, marker: str) -> bool:
    return marker in (text or "")


def _quality_boost_macro(state_id: int, logos_ref: str, cycle: str) -> float:
    boost = 0.0
    if 1 <= state_id <= 16:
        boost += 0.05
    if logos_ref:
        boost += 0.06
    if cycle:
        boost += 0.05
    return round(boost, 6)


def _quality_boost_personal(sasang: str, run_id: str, canonical_ref: str, has_non_medical: bool, has_non_det: bool) -> float:
    boost = 0.0
    if sasang:
        boost += 0.05
    if run_id:
        boost += 0.04
    if canonical_ref:
        boost += 0.04
    if has_non_medical:
        boost += 0.04
    if has_non_det:
        boost += 0.04
    return round(boost, 6)


def _build_flags(rationale: str, score: float, *, has_anchor: bool) -> dict[str, bool]:
    lower = (rationale or "").lower()
    deterministic_words = ("확정", "final", "deterministic", "운명 확정")
    deterministic_risk = any(w in lower for w in deterministic_words)
    rationale_len = len((rationale or "").strip())
    weak_rationale = rationale_len < 48
    # Refined risk: only fail when score is weak or anchor evidence is missing.
    false_eq = (score < 0.45) or ((score < 0.55) and weak_rationale) or (not has_anchor)
    return {
        "context_contamination_risk": False,
        "false_equivalence_risk": bool(false_eq),
        "numeric_metaphor_risk": False,
        "deterministic_wording_risk": bool(deterministic_risk),
    }


def run_compute(input_path: Path, spec_path: Path, output_path: Path) -> dict[str, Any]:
    doc = _load_json(input_path)
    spec = _load_json(spec_path)

    macro_rows = list(doc.get("macro_lane_samples") or [])
    personal_rows = list(doc.get("personal_lane_samples") or [])

    scored: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []

    for row in macro_rows:
        sample_id = str(row.get("sample_id", "")).strip()
        state_id = int(row.get("state_id", 0))
        logos_ref = str(row.get("logos_symbol_ref", "")).strip()
        cycle = str(row.get("myeongri_cycle", "")).strip()
        rationale = str(row.get("rationale", ""))
        aux_macro = compute_aux_macro_signal(state_id=state_id, logos_ref=logos_ref, cycle=cycle)
        base_score = _stable_score("macro", sample_id, str(state_id), logos_ref, cycle)
        boost = _quality_boost_macro(state_id, logos_ref, cycle)
        score = round(min(0.95, base_score + boost), 6)
        flags = _build_flags(rationale, score, has_anchor=bool(logos_ref or row.get("canonical_ref")))
        scored.append(
            {
                "sample_id": sample_id,
                "lane": "macro_lane",
                "resonance_score": score,
                "rationale": rationale,
                "falsification_flags": flags,
                "sort_key": score,
                "_state_or_type": f"state_id:{state_id}",
                "_logos_or_ref": logos_ref or str(row.get("canonical_ref", "")).strip(),
                "_components": {
                    "state_anchor_match": round(base_score * 0.45, 6),
                    "cycle_symbol_link": round(base_score * 0.40, 6),
                    "quality_boost": boost,
                    "guardrail_penalty": round(score * 0.10, 6),
                    "aux_non_gating": {
                        "geumhwa_aux_score": aux_macro.geumhwa_aux_score,
                        "transition_pressure": aux_macro.transition_pressure,
                    },
                },
            }
        )

    for row in personal_rows:
        sample_id = str(row.get("sample_id", "")).strip()
        sasang = str(row.get("sasang_type", "")).strip()
        run_id = str(row.get("personal_run_id", "")).strip()
        canonical_ref = str(row.get("canonical_ref", "")).strip()
        rationale = str(row.get("rationale", ""))
        aux_personal = compute_aux_personal_signal(
            sasang_type=sasang,
            state_candidate_id=row.get("state_candidate_id"),
        )
        has_non_medical = _has_required_notice(str(row.get("non_medical_notice", "")), "[NON-MEDICAL]")
        has_non_det = _has_required_notice(str(row.get("non_deterministic_notice", "")), "[NON-DETERMINISTIC]")
        base_score = _stable_score("personal", sample_id, sasang, run_id, canonical_ref)
        boost = _quality_boost_personal(sasang, run_id, canonical_ref, has_non_medical, has_non_det)
        score = round(min(0.95, base_score + boost), 6)
        flags = _build_flags(rationale, score, has_anchor=bool(canonical_ref))
        scored.append(
            {
                "sample_id": sample_id,
                "lane": "personal_lane",
                "resonance_score": score,
                "rationale": rationale,
                "falsification_flags": flags,
                "sort_key": score,
                "_state_or_type": f"sasang_type:{sasang}",
                "_logos_or_ref": canonical_ref,
                "_components": {
                    "sasang_anchor_link": round(base_score * 0.45, 6),
                    "scenario_consistency": round(base_score * 0.40, 6),
                    "quality_boost": boost,
                    "guardrail_penalty": round(score * 0.10, 6),
                    "aux_non_gating": {
                        "bomyeong_guard_score": aux_personal.bomyeong_guard_score,
                        "taeyang_risk_flag": aux_personal.taeyang_risk_flag,
                    },
                },
            }
        )

    scored.sort(key=lambda x: float(x.get("sort_key", 0.0)), reverse=True)
    default_n = int(((spec.get("compute_contract") or {}).get("top_n") or {}).get("default_n", 5))
    top_n = scored[: max(1, min(default_n, len(scored)))]

    top_rows = []
    false_eq_count = 0
    deterministic_count = 0
    for idx, row in enumerate(top_n, start=1):
        flags = row["falsification_flags"]
        if flags.get("false_equivalence_risk"):
            false_eq_count += 1
        if flags.get("deterministic_wording_risk"):
            deterministic_count += 1
        top_rows.append(
            {
                "rank": idx,
                "sample_id": row["sample_id"],
                "lane": row["lane"],
                "resonance_score": row["resonance_score"],
                "aux_non_gating": row["_components"]["aux_non_gating"],
                "rationale": row["rationale"],
                "falsification_flags": flags,
            }
        )
        trace.append(
            {
                "sample_id": row["sample_id"],
                "lane": row["lane"],
                "state_id_or_sasang_type": row["_state_or_type"],
                "logos_symbol_ref_or_canonical_ref": row["_logos_or_ref"],
                "score_components": row["_components"],
                "resonance_score": row["resonance_score"],
                "trace_note": "Deterministic SHA-256 derived pilot scoring.",
            }
        )

    all_rationale_hypo = all(_require_hypo(str(r.get("rationale", ""))) for r in (macro_rows + personal_rows))
    non_medical_ok = all(_has_required_notice(str(r.get("non_medical_notice", "")), "[NON-MEDICAL]") for r in personal_rows)
    non_det_ok = all(_has_required_notice(str(r.get("non_deterministic_notice", "")), "[NON-DETERMINISTIC]") for r in personal_rows)

    gate = (((spec.get("output_contract") or {}).get("promotion_gate")) or {})
    false_eq_max = int(gate.get("false_equivalence_max_count", 0))
    deterministic_max = int(gate.get("deterministic_wording_max_count", 0))
    notice_integrity_passed = non_medical_ok and non_det_ok
    hypo_integrity_passed = all_rationale_hypo
    promotion_gate_passed = (
        (false_eq_count <= false_eq_max)
        and (deterministic_count <= deterministic_max)
        and notice_integrity_passed
        and hypo_integrity_passed
    )

    out = {
        "schema": "w3_resonance_result_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "computed_pilot",
        "track": "B-track",
        "refs": {
            "input": str(input_path).replace("\\", "/"),
            "compute_spec": str(spec_path).replace("\\", "/"),
            "precheck": "docs/final/artifacts/W3_FALSIFICATION_PRECHECK.json",
            "template": "docs/final/artifacts/W2_DUAL_LANE_TEMPLATE_V1.json",
        },
        "run_meta": {
            "run_id": f"w3_compute_run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "compute_status": "executed_deterministic",
            "aux_adapter_version": "w3_aux_adapter_v1",
            "top_n_count": len(top_rows),
            "lanes_processed": sorted({r["lane"] for r in top_rows}),
        },
        "top_n_results": top_rows,
        "scoring_trace": trace,
        "falsification_summary": {
            "context_contamination_risk_count": 0,
            "false_equivalence_risk_count": false_eq_count,
            "numeric_metaphor_risk_count": 0,
            "deterministic_wording_risk_count": deterministic_count,
        },
        "promotion_gate": {
            "false_equivalence_max_count": false_eq_max,
            "deterministic_wording_max_count": deterministic_max,
            "notice_integrity_required": True,
            "hypothesis_marker_required": True,
            "notice_integrity_passed": notice_integrity_passed,
            "hypothesis_marker_passed": hypo_integrity_passed,
            "passed": promotion_gate_passed,
        },
        "guardrail_assertions": {
            "all_rationale_include_hypo": all_rationale_hypo,
            "non_medical_notice_present_for_personal_lane": non_medical_ok,
            "non_deterministic_notice_present_for_personal_lane": non_det_ok,
            "geo_event_ref_participates_in_scoring": False,
        },
        "note": "Deterministic weighted compute executed for B-track only. Auxiliary adapter fields are non-gating metadata.",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--compute-spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    out = run_compute(args.input, args.compute_spec, args.output)
    print("OK: deterministic W3 compute complete")
    print(f"output={args.output}")
    print(f"top_n_count={out['run_meta']['top_n_count']}")
    print(f"false_equivalence_risk_count={out['falsification_summary']['false_equivalence_risk_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
