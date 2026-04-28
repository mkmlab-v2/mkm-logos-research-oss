#!/usr/bin/env python3
"""Build commercialization-readiness evidence packet for Sasang prophecy rail.

Fact-lock scope:
- Reads only on-disk artifacts.
- Never auto-binds Track B outputs into Track A.
- Emits decision artifacts for human sign-off only.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_LENS = ART / "sasang_independent_lens_latest.json"
DEFAULT_HIGH_GATE = ART / "sasang_high_reliability_gate_latest.json"
DEFAULT_HIGH_GATE_STRICT = ART / "sasang_high_reliability_gate_strict_latest.json"
DEFAULT_HIGH_GATE_STRICT_SHADOW = ART / "sasang_high_reliability_gate_strict_synthetic_calibrated_latest.json"
DEFAULT_STRICT_INPUT_INTEGRITY = ART / "sasang_strict_input_integrity_latest.json"
DEFAULT_PROD_DATA_READINESS = ART / "sasang_production_data_readiness_latest.json"
DEFAULT_GT_EXPANSION_QUEUE_REPORT = ART / "sasang_gt_expansion_queue_report_latest.json"
DEFAULT_GT_EXPANSION_PRIORITY_REPORT = ART / "sasang_gt_expansion_priority_report_latest.json"
DEFAULT_GT_MERGE_REPORT = ART / "sasang_gt_merge_report_latest.json"
DEFAULT_GT_LABELING_SHEET_REPORT = ART / "sasang_gt_labeling_sheet_report_latest.json"
DEFAULT_PROMOTION_CHAIN = ART / "sasang12_promotion_candidate_chain_latest.json"

DEFAULT_EVAL_CONTRACT = ART / "sasang_prophecy_eval_contract_latest.json"
DEFAULT_PROMOTION_GATE = ART / "sasang12_promotion_candidate_gate_latest.json"
DEFAULT_FAILURE_ANALYSIS = ART / "sasang12_gate_failure_analysis_latest.json"
DEFAULT_READINESS_PACKET = ART / "sasang_commercialization_readiness_packet_latest.json"
DEFAULT_SHADOW_GOV = ART / "sasang_shadow_governance_latest.json"


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _f(v: Any, *, default: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else default


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_optional(path: Path) -> dict[str, Any] | None:
    return _jread(path) if path.is_file() else None


def _classify_promotion_status(v1_to_v9_present: bool, standard_pass: bool, strict_pass: bool) -> tuple[str, str]:
    if not v1_to_v9_present:
        return "FAIL", "promotion_chain_missing_v1_to_v9"
    if standard_pass and strict_pass:
        return "PASS", "all_required_signals_passed"
    if standard_pass and not strict_pass:
        return "WARN", "strict_profile_not_passed"
    return "FAIL", "standard_profile_not_passed"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lens", type=Path, default=DEFAULT_LENS)
    ap.add_argument("--high-gate", type=Path, default=DEFAULT_HIGH_GATE)
    ap.add_argument("--high-gate-strict", type=Path, default=DEFAULT_HIGH_GATE_STRICT)
    ap.add_argument("--high-gate-strict-shadow", type=Path, default=DEFAULT_HIGH_GATE_STRICT_SHADOW)
    ap.add_argument("--strict-input-integrity", type=Path, default=DEFAULT_STRICT_INPUT_INTEGRITY)
    ap.add_argument("--production-data-readiness", type=Path, default=DEFAULT_PROD_DATA_READINESS)
    ap.add_argument("--gt-expansion-queue-report", type=Path, default=DEFAULT_GT_EXPANSION_QUEUE_REPORT)
    ap.add_argument("--gt-expansion-priority-report", type=Path, default=DEFAULT_GT_EXPANSION_PRIORITY_REPORT)
    ap.add_argument("--gt-merge-report", type=Path, default=DEFAULT_GT_MERGE_REPORT)
    ap.add_argument("--gt-labeling-sheet-report", type=Path, default=DEFAULT_GT_LABELING_SHEET_REPORT)
    ap.add_argument("--promotion-chain", type=Path, default=DEFAULT_PROMOTION_CHAIN)
    ap.add_argument("--eval-contract-out", type=Path, default=DEFAULT_EVAL_CONTRACT)
    ap.add_argument("--promotion-gate-out", type=Path, default=DEFAULT_PROMOTION_GATE)
    ap.add_argument("--failure-analysis-out", type=Path, default=DEFAULT_FAILURE_ANALYSIS)
    ap.add_argument("--readiness-packet-out", type=Path, default=DEFAULT_READINESS_PACKET)
    ap.add_argument("--shadow-governance-out", type=Path, default=DEFAULT_SHADOW_GOV)
    args = ap.parse_args()

    if not args.lens.is_file():
        print(f"ERROR: missing lens artifact: {args.lens}")
        return 2
    if not args.high_gate.is_file():
        print(f"ERROR: missing standard gate artifact: {args.high_gate}")
        return 2

    lens = _jread(args.lens)
    gate_std = _jread(args.high_gate)
    gate_strict = _load_optional(args.high_gate_strict)
    gate_strict_shadow = _load_optional(args.high_gate_strict_shadow)
    strict_integrity = _load_optional(args.strict_input_integrity)
    prod_data_readiness = _load_optional(args.production_data_readiness)
    gt_expansion_queue_report = _load_optional(args.gt_expansion_queue_report)
    gt_expansion_priority_report = _load_optional(args.gt_expansion_priority_report)
    gt_merge_report = _load_optional(args.gt_merge_report)
    gt_labeling_sheet_report = _load_optional(args.gt_labeling_sheet_report)

    direction_score = _f((lens.get("scores") or {}).get("direction_score"))
    confidence = _f((lens.get("scores") or {}).get("confidence"))
    mapping_target = str((lens.get("sasang_stream_outputs") or {}).get("mapping_target") or "").strip().lower()
    std_decision = str(gate_std.get("decision") or "").upper()
    strict_decision = str((gate_strict or {}).get("decision") or "MISSING").upper()
    strict_available = gate_strict is not None
    std_pass = std_decision == "PASS"
    strict_pass = strict_decision == "PASS"
    strict_shadow_decision = str((gate_strict_shadow or {}).get("decision") or "MISSING").upper()
    strict_shadow_pass = strict_shadow_decision == "PASS"

    v1_to_v9_present = args.promotion_chain.is_file()
    promotion_status, promotion_reason = _classify_promotion_status(v1_to_v9_present, std_pass, strict_pass)

    eval_contract = {
        "schema": "sasang_prophecy_eval_contract_v1",
        "generated_at_utc": _now(),
        "scope": "sasang_prophecy_b_track_commercialization_precheck",
        "inputs_contract": {
            "lens_artifact": str(args.lens.resolve()),
            "standard_gate_artifact": str(args.high_gate.resolve()),
            "strict_gate_artifact": str(args.high_gate_strict.resolve()) if strict_available else None,
            "strict_shadow_gate_artifact": (
                str(args.high_gate_strict_shadow.resolve()) if gate_strict_shadow is not None else None
            ),
            "promotion_chain_artifact": str(args.promotion_chain.resolve()) if v1_to_v9_present else None,
            "evaluation_window": "latest_single_snapshot",
            "cost_buckets_basis_points": [20, 30, 40],
            "neutral_policy": {
                "mapping_target_sideways_allows_zero_direction": True,
                "must_flag_if_direction_zero_persists": True,
            },
        },
        "reproducibility_contract": {
            "determinism": "same_inputs_same_outputs",
            "required_fields": [
                "scores.direction_score",
                "scores.confidence",
                "checks",
                "decision",
            ],
            "track_wall": {
                "track_b_only": True,
                "a_track_autobind_forbidden": True,
                "promotion_to_a_track_allowed": False,
            },
        },
        "policy_boundary": {
            "non_medical_claim_only": True,
            "no_live_trading_trigger": True,
            "human_signoff_required": True,
        },
    }

    failure_axes: list[dict[str, Any]] = []
    if not v1_to_v9_present:
        failure_axes.append(
            {
                "axis": "promotion_chain_coverage",
                "severity": "high",
                "status": "FAIL",
                "evidence": "v1~v9 executable/artifact chain is missing on-disk in current workspace snapshot",
            }
        )
    if direction_score == 0.0:
        failure_axes.append(
            {
                "axis": "independent_lens_directionality",
                "severity": "medium",
                "status": "WARN",
                "evidence": "direction_score is exactly 0.0 (neutral fixation risk)",
                "metrics": {"direction_score": direction_score, "mapping_target": mapping_target},
            }
        )
    if confidence < 0.55:
        failure_axes.append(
            {
                "axis": "independent_lens_confidence",
                "severity": "medium",
                "status": "WARN",
                "evidence": "confidence below 0.55 threshold",
                "metrics": {"confidence": confidence},
            }
        )
    if not std_pass:
        failure_axes.append(
            {
                "axis": "standard_quality_gate",
                "severity": "high",
                "status": "FAIL",
                "evidence": f"standard quality gate decision={std_decision}",
            }
        )
    if strict_available and not strict_pass:
        failure_axes.append(
            {
                "axis": "strict_quality_gate",
                "severity": "medium",
                "status": "WARN",
                "evidence": f"strict quality gate decision={strict_decision}",
            }
        )
    if not strict_available:
        failure_axes.append(
            {
                "axis": "strict_quality_gate",
                "severity": "medium",
                "status": "WARN",
                "evidence": "strict quality gate artifact missing",
            }
        )
    if strict_shadow_pass:
        failure_axes.append(
            {
                "axis": "strict_shadow_evidence_only",
                "severity": "low",
                "status": "WARN",
                "evidence": "strict shadow gate PASS exists but is not promotion-authoritative",
            }
        )
    if isinstance(strict_integrity, dict):
        integ = strict_integrity.get("integrity") or {}
        rc = str(integ.get("root_cause") or "").strip()
        if rc and rc != "NONE":
            failure_axes.append(
                {
                    "axis": "strict_input_integrity",
                    "severity": "medium",
                    "status": "WARN",
                    "evidence": f"strict input integrity root_cause={rc}",
                }
            )
    if isinstance(prod_data_readiness, dict):
        if not bool(prod_data_readiness.get("ready_for_production_strict")):
            rc = str(prod_data_readiness.get("root_cause") or "unknown")
            failure_axes.append(
                {
                    "axis": "production_data_readiness",
                    "severity": "medium",
                    "status": "WARN",
                    "evidence": f"production data readiness failed: {rc}",
                }
            )
    if isinstance(gt_expansion_queue_report, dict):
        gap_rows = int(gt_expansion_queue_report.get("gap_rows") or 0)
        queue_rows = int(gt_expansion_queue_report.get("queue_rows") or 0)
        if gap_rows > 0:
            failure_axes.append(
                {
                    "axis": "gt_expansion_pending",
                    "severity": "medium",
                    "status": "WARN",
                    "evidence": f"GT expansion pending: gap_rows={gap_rows}, queue_rows={queue_rows}",
                }
            )
    if isinstance(gt_expansion_priority_report, dict):
        selected_rows = int(gt_expansion_priority_report.get("selected_rows") or 0)
        if selected_rows <= 0:
            failure_axes.append(
                {
                    "axis": "gt_priority_missing",
                    "severity": "medium",
                    "status": "WARN",
                    "evidence": "GT priority queue has no selected rows",
                }
            )
    if isinstance(gt_merge_report, dict):
        approved_rows = int(gt_merge_report.get("approved_queue_rows") or 0)
        if approved_rows <= 0:
            failure_axes.append(
                {
                    "axis": "gt_human_approval_pending",
                    "severity": "medium",
                    "status": "WARN",
                    "evidence": "No approved GT queue rows merged yet",
                }
            )
    if isinstance(gt_labeling_sheet_report, dict):
        row_count = int(gt_labeling_sheet_report.get("row_count") or 0)
        if row_count <= 0:
            failure_axes.append(
                {
                    "axis": "gt_labeling_sheet_missing",
                    "severity": "medium",
                    "status": "WARN",
                    "evidence": "GT labeling sheet has no rows",
                }
            )

    promotion_gate = {
        "schema": "sasang12_promotion_candidate_gate_unified_v1",
        "generated_at_utc": _now(),
        "status": promotion_status,
        "reason_code": promotion_reason,
        "stages": {
            "stage_1_eval_contract": "PASS",
            "stage_2_independent_lens_quality": "PASS" if direction_score != 0.0 and confidence >= 0.55 else "WARN",
            "stage_3_standard_gate": "PASS" if std_pass else "FAIL",
            "stage_4_strict_gate": "PASS" if strict_pass else ("WARN" if strict_available else "WARN"),
            "stage_5_promotion_chain_v1_to_v9": "PASS" if v1_to_v9_present else "FAIL",
        },
        "track_wall": {
            "track_b_only": True,
            "a_track_autobind_forbidden": True,
            "promotion_to_a_track_allowed": False,
        },
        "human_signoff": {
            "required": True,
            "go_if": "status == PASS and promotion_to_a_track_allowed reviewed manually",
            "rollback_if": "strict gate downgraded or direction/confidence degrades",
        },
    }

    failure_analysis = {
        "schema": "sasang12_gate_failure_analysis_v1",
        "generated_at_utc": _now(),
        "summary": {
            "total_axes": len(failure_axes),
            "fail_count": sum(1 for x in failure_axes if x["status"] == "FAIL"),
            "warn_count": sum(1 for x in failure_axes if x["status"] == "WARN"),
            "common_root_cause": (
                "promotion_chain_missing_v1_to_v9"
                if not v1_to_v9_present
                else "quality_gate_or_lens_signal_issue"
            ),
        },
        "failure_axes": failure_axes,
        "current_snapshot": {
            "direction_score": direction_score,
            "confidence": confidence,
            "mapping_target": mapping_target,
            "standard_gate": std_decision,
            "strict_gate": strict_decision if strict_available else "MISSING",
            "strict_shadow_gate": strict_shadow_decision if gate_strict_shadow is not None else "MISSING",
        },
        "next_experiments": [
            "Improve non-neutral signal rule in independent lens while preserving non-medical boundary",
            "Raise confidence by calibrated proxy weighting and re-run strict gate",
            "Implement/restore v1~v9 promotion chain scripts with reproducible artifacts",
        ],
    }

    readiness = {
        "schema": "sasang_commercialization_readiness_packet_v1",
        "generated_at_utc": _now(),
        "decision": "READY" if promotion_status == "PASS" else ("ALMOST" if promotion_status == "WARN" else "NOT_YET"),
        "packet_scope": "human_signoff_material_only",
        "evidence": {
            "eval_contract": str(args.eval_contract_out.resolve()),
            "independent_lens": str(args.lens.resolve()),
            "promotion_gate": str(args.promotion_gate_out.resolve()),
            "failure_analysis": str(args.failure_analysis_out.resolve()),
            "standard_gate": str(args.high_gate.resolve()),
            "strict_gate": str(args.high_gate_strict.resolve()) if strict_available else None,
            "strict_shadow_gate": (
                str(args.high_gate_strict_shadow.resolve()) if gate_strict_shadow is not None else None
            ),
            "strict_input_integrity": (
                str(args.strict_input_integrity.resolve()) if strict_integrity is not None else None
            ),
            "production_data_readiness": (
                str(args.production_data_readiness.resolve()) if prod_data_readiness is not None else None
            ),
            "gt_expansion_queue_report": (
                str(args.gt_expansion_queue_report.resolve()) if gt_expansion_queue_report is not None else None
            ),
            "gt_expansion_priority_report": (
                str(args.gt_expansion_priority_report.resolve()) if gt_expansion_priority_report is not None else None
            ),
            "gt_merge_report": str(args.gt_merge_report.resolve()) if gt_merge_report is not None else None,
            "gt_labeling_sheet_report": (
                str(args.gt_labeling_sheet_report.resolve()) if gt_labeling_sheet_report is not None else None
            ),
        },
        "boundaries": {
            "track_b_to_a_autobind": "FORBIDDEN",
            "medical_claims": "FORBIDDEN",
            "live_trading_trigger": "FORBIDDEN",
            "human_signoff_required": True,
        },
        "go_no_go": {
            "go": promotion_status == "PASS",
            "blockers": [x["axis"] for x in failure_axes if x["status"] == "FAIL"],
            "warnings": [x["axis"] for x in failure_axes if x["status"] == "WARN"],
        },
    }

    shadow_governance = {
        "schema": "sasang_shadow_governance_v1",
        "generated_at_utc": _now(),
        "mode": "shadow_only_observation",
        "decision": "KEEP_OBSERVATION_ONLY" if promotion_status != "PASS" else "HUMAN_REVIEW_REQUIRED_FOR_PROMOTION",
        "current_gate": {
            "promotion_status": promotion_status,
            "standard_quality_gate": std_decision,
            "strict_quality_gate": strict_decision if strict_available else "MISSING",
        },
        "boundaries": {
            "track_b_only": True,
            "a_track_autobind_forbidden": True,
            "promotion_to_a_track_allowed": False,
            "non_medical_claim_only": True,
            "no_live_trading_trigger": True,
        },
        "blockers": [x["axis"] for x in failure_axes if x["status"] == "FAIL"],
        "warnings": [x["axis"] for x in failure_axes if x["status"] == "WARN"],
        "rollback_conditions": [
            "strict gate remains HOLD/FAIL",
            "direction_score regresses to 0 for 2 consecutive refreshes",
            "confidence falls below 0.55",
        ],
        "release_conditions": [
            "v1~v9 promotion chain implemented and reproducibly PASS",
            "strict gate PASS on refreshed inputs",
            "human sign-off recorded",
        ],
    }

    _write(args.eval_contract_out, eval_contract)
    _write(args.promotion_gate_out, promotion_gate)
    _write(args.failure_analysis_out, failure_analysis)
    _write(args.readiness_packet_out, readiness)
    _write(args.shadow_governance_out, shadow_governance)

    print(f"WROTE: {args.eval_contract_out}")
    print(f"WROTE: {args.promotion_gate_out}")
    print(f"WROTE: {args.failure_analysis_out}")
    print(f"WROTE: {args.readiness_packet_out}")
    print(f"WROTE: {args.shadow_governance_out}")
    print(f"promotion_status={promotion_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
