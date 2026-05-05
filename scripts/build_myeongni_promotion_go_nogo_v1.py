#!/usr/bin/env python3
"""Build myeongni promotion go/no-go packet from commercialization artifacts."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_READINESS = ART / "myeongni_commercialization_readiness_packet_latest.json"
DEFAULT_CONTRACT = ART / "myeongni_eval_contract_latest.json"
DEFAULT_QUALITY = ART / "myeongni_16state_data_quality_report_latest.json"
DEFAULT_FUSION = ART / "independent_lens_fusion_stub_latest.json"
DEFAULT_SHADOW_GATE = ART / "independent_lens_shadow_gate_latest.json"
DEFAULT_SENSITIVITY = ART / "myeongni_readiness_sensitivity_report_latest.json"
DEFAULT_WEATHER_QUALITY = ART / "general_prophecy_explainability_quality_v1_latest.json"
DEFAULT_GEMATRIA_BLEND = ART / "gematria_myeongri_spike_blend_latest.json"
DEFAULT_GEMATRIA_ABLATION = ART / "gematria_4d_ablation_latest.json"

DEFAULT_PROMOTION_GATE = ART / "myeongni_promotion_gate_latest.json"
DEFAULT_FAILURE = ART / "myeongni_promotion_failure_analysis_latest.json"
DEFAULT_SHADOW_GOV = ART / "myeongni_shadow_governance_latest.json"
DEFAULT_REVIEW_PACKET = ART / "myeongni_promotion_review_packet_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _f(v: Any, default: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else default


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
    ap.add_argument("--eval-contract", type=Path, default=DEFAULT_CONTRACT)
    ap.add_argument("--quality", type=Path, default=DEFAULT_QUALITY)
    ap.add_argument("--fusion", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--shadow-gate", type=Path, default=DEFAULT_SHADOW_GATE)
    ap.add_argument("--sensitivity", type=Path, default=DEFAULT_SENSITIVITY)
    ap.add_argument("--weather-quality", type=Path, default=DEFAULT_WEATHER_QUALITY)
    ap.add_argument("--gematria-blend", type=Path, default=DEFAULT_GEMATRIA_BLEND)
    ap.add_argument("--gematria-ablation", type=Path, default=DEFAULT_GEMATRIA_ABLATION)
    ap.add_argument("--promotion-gate-out", type=Path, default=DEFAULT_PROMOTION_GATE)
    ap.add_argument("--failure-out", type=Path, default=DEFAULT_FAILURE)
    ap.add_argument("--shadow-gov-out", type=Path, default=DEFAULT_SHADOW_GOV)
    ap.add_argument("--review-packet-out", type=Path, default=DEFAULT_REVIEW_PACKET)
    args = ap.parse_args()

    readiness = _read_json(args.readiness)
    contract = _read_json(args.eval_contract)
    quality = _read_json(args.quality)
    fusion = _read_json(args.fusion)
    shadow_gate = _read_json(args.shadow_gate)
    sensitivity = _read_json(args.sensitivity)
    weather_quality = _read_json(args.weather_quality)
    gematria_blend = _read_json(args.gematria_blend)
    gematria_ablation = _read_json(args.gematria_ablation)

    summary = readiness.get("summary") if isinstance(readiness.get("summary"), dict) else {}
    integrity = readiness.get("shadow_history_integrity") if isinstance(readiness.get("shadow_history_integrity"), dict) else {}
    go_ready = str(readiness.get("readiness") or "").upper() == "READY"
    contract_ok = bool(summary.get("contract_alignment_ok"))
    quality_ok = bool(summary.get("data_quality_ok"))
    non_neutral = bool(summary.get("signal_non_neutral"))
    blockers = shadow_gate.get("blockers") if isinstance(shadow_gate.get("blockers"), list) else []
    override_exceeded = bool(summary.get("shadow_override_ratio_exceeded"))
    agreement = _f((fusion.get("consensus") or {}).get("agreement_rate"))
    consistency_ok = agreement >= 0.5
    sensitivity_rows = sensitivity.get("sensitivity_sweep") if isinstance(sensitivity.get("sensitivity_sweep"), list) else []
    sensitivity_all_ready = all(str((x or {}).get("readiness") or "").upper() == "READY" for x in sensitivity_rows) if sensitivity_rows else False
    weather_rows = weather_quality.get("rows") if isinstance(weather_quality.get("rows"), list) else []
    brier_rows = [r for r in weather_rows if str((r or {}).get("question_id") or "").startswith("ci.brier_")]
    weather_linked = len(brier_rows) > 0 and all(bool((r or {}).get("coverage_ok")) for r in brier_rows)
    blend_metrics = gematria_blend.get("metrics") if isinstance(gematria_blend.get("metrics"), dict) else {}
    ablation_snapshot = gematria_ablation.get("snapshot") if isinstance(gematria_ablation.get("snapshot"), dict) else {}
    cosine_hybrid = _f(blend_metrics.get("cosine_vanilla_hybrid"))
    cosine_myeongri = _f(blend_metrics.get("cosine_vanilla_myeongri"))
    ablation_delta = _f(ablation_snapshot.get("delta_with_minus_without"))
    allow_exec = bool((gematria_ablation.get("policy_gate") or {}).get("allow_execution_trigger"))
    gematria_linked = cosine_hybrid >= cosine_myeongri and ablation_delta > 0.0 and (not allow_exec)

    fail_axes: list[dict[str, Any]] = []
    if not go_ready:
        fail_axes.append({"axis": "readiness_packet", "severity": "high", "status": "FAIL", "evidence": f"readiness={readiness.get('readiness')}"})
    if not contract_ok:
        fail_axes.append({"axis": "eval_contract_alignment", "severity": "high", "status": "FAIL", "evidence": "contract_alignment_ok=false"})
    if not quality_ok:
        fail_axes.append({"axis": "data_quality", "severity": "high", "status": "FAIL", "evidence": f"status={quality.get('status')}"})
    if not non_neutral:
        fail_axes.append({"axis": "non_neutral_signal", "severity": "medium", "status": "WARN", "evidence": "signal_non_neutral=false"})
    if blockers:
        fail_axes.append({"axis": "shadow_gate_blockers", "severity": "high", "status": "FAIL", "evidence": f"blockers={blockers}"})
    if override_exceeded:
        fail_axes.append({"axis": "shadow_override_ratio", "severity": "high", "status": "FAIL", "evidence": "shadow_override_ratio_exceeded=true"})
    if not consistency_ok:
        fail_axes.append({"axis": "fusion_consistency", "severity": "medium", "status": "WARN", "evidence": f"agreement_rate={agreement}"})
    if not sensitivity_all_ready:
        fail_axes.append({"axis": "sensitivity_sweep", "severity": "medium", "status": "WARN", "evidence": "not all thresholds yielded READY"})
    if not weather_linked:
        fail_axes.append(
            {
                "axis": "weather_signal_linkage",
                "severity": "medium",
                "status": "WARN",
                "evidence": "weather-linked (ci.brier_*) quality rows missing or coverage not all true",
            }
        )
    if not gematria_linked:
        fail_axes.append(
            {
                "axis": "gematria_4d_linkage",
                "severity": "medium",
                "status": "WARN",
                "evidence": (
                    f"cosine_hybrid={cosine_hybrid}, cosine_myeongri={cosine_myeongri}, "
                    f"ablation_delta={ablation_delta}, allow_execution_trigger={allow_exec}"
                ),
            }
        )

    fail_count = sum(1 for x in fail_axes if x["status"] == "FAIL")
    warn_count = sum(1 for x in fail_axes if x["status"] == "WARN")
    status = "PASS" if fail_count == 0 else "FAIL"

    promotion_gate = {
        "schema": "myeongni_promotion_gate_v1",
        "ts_utc": _now(),
        "status": status,
        "track": "B",
        "decision": "MANUAL_PROMOTION_REVIEW_GO" if status == "PASS" else "MANUAL_PROMOTION_REVIEW_HOLD",
        "go_for_manual_signoff": status == "PASS",
        "stage_checks": {
            "readiness_packet_ready": go_ready,
            "eval_contract_ok": contract_ok,
            "data_quality_ok": quality_ok,
            "shadow_gate_blockers_zero": len(blockers) == 0,
            "shadow_override_under_limit": not override_exceeded,
            "sensitivity_sweep_all_ready": sensitivity_all_ready,
            "weather_signal_linked": weather_linked,
            "gematria_4d_linked": gematria_linked,
        },
        "policy": {
            "track_b_to_a_auto_bridge": False,
            "live_trigger_auto_enabled": False,
            "human_signoff_required": True,
        },
    }

    failure = {
        "schema": "myeongni_promotion_failure_analysis_v1",
        "ts_utc": _now(),
        "summary": {"fail_count": fail_count, "warn_count": warn_count, "total_axes": len(fail_axes)},
        "axes": fail_axes,
        "snapshot": {
            "readiness": readiness.get("readiness"),
            "quality_status": quality.get("status"),
            "fusion_agreement_rate": agreement,
            "shadow_override_ratio": integrity.get("override_ratio"),
            "shadow_override_ratio_limit": summary.get("shadow_override_ratio_limit"),
            "weather_brier_row_count": len(brier_rows),
            "gematria_cosine_hybrid": cosine_hybrid,
            "gematria_cosine_myeongri": cosine_myeongri,
            "gematria_ablation_delta": ablation_delta,
        },
    }

    shadow_governance = {
        "schema": "myeongni_shadow_governance_v1",
        "ts_utc": _now(),
        "decision": "HUMAN_REVIEW_REQUIRED_FOR_PROMOTION" if status == "PASS" else "KEEP_OBSERVATION_ONLY",
        "allow_a_track_binding": False,
        "allow_live_trigger": False,
        "blockers": [x["axis"] for x in fail_axes if x["status"] == "FAIL"],
        "warnings": [x["axis"] for x in fail_axes if x["status"] == "WARN"],
        "linked_inputs": {
            "weather_quality": str(args.weather_quality.resolve()),
            "gematria_blend": str(args.gematria_blend.resolve()),
            "gematria_ablation": str(args.gematria_ablation.resolve()),
        },
    }

    review_packet = {
        "schema": "myeongni_promotion_review_packet_v1",
        "ts_utc": _now(),
        "promotion_gate": str(args.promotion_gate_out.resolve()),
        "failure_analysis": str(args.failure_out.resolve()),
        "shadow_governance": str(args.shadow_gov_out.resolve()),
        "inputs": {
            "readiness_packet": str(args.readiness.resolve()),
            "eval_contract": str(args.eval_contract.resolve()),
            "data_quality_report": str(args.quality.resolve()),
            "fusion_stub": str(args.fusion.resolve()),
            "shadow_gate": str(args.shadow_gate.resolve()),
            "sensitivity_report": str(args.sensitivity.resolve()),
            "weather_quality": str(args.weather_quality.resolve()),
            "gematria_blend": str(args.gematria_blend.resolve()),
            "gematria_ablation": str(args.gematria_ablation.resolve()),
        },
    }

    _write(args.promotion_gate_out, promotion_gate)
    _write(args.failure_out, failure)
    _write(args.shadow_gov_out, shadow_governance)
    _write(args.review_packet_out, review_packet)
    print(f"WROTE: {args.promotion_gate_out}")
    print(f"WROTE: {args.failure_out}")
    print(f"WROTE: {args.shadow_gov_out}")
    print(f"WROTE: {args.review_packet_out}")
    print(f"promotion_status={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
