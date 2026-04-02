#!/usr/bin/env python3
"""Build weekly A-track Go/No-Go status JSON from latest artifacts.

Conservative defaults:
- Strict AND gate for stage readiness
- Any system error defaults to NO_GO (configurable)
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "a_track_go_nogo_status_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _bool(val: Any) -> bool:
    return bool(val)


def _add_check(
    checks: Dict[str, bool],
    reasons: List[str],
    key: str,
    ok: bool,
    fail_reason: str,
) -> None:
    checks[key] = ok
    if not ok:
        reasons.append(fail_reason)


def _strict_and(checks: Dict[str, bool]) -> bool:
    return all(checks.values()) if checks else False


def evaluate(
    *,
    on_system_error: str,
) -> Dict[str, Any]:
    inputs = {
        "high_reliability_mode_gate": ROOT / "docs" / "final" / "artifacts" / "high_reliability_mode_gate_latest.json",
        "trinity_track_quality": ROOT / "docs" / "final" / "artifacts" / "trinity_track_quality_report_latest.json",
        "prophecy_monthly": ROOT / "docs" / "final" / "artifacts" / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json",
        "chronos_holdout_2026": ROOT / "data" / "chronos_forward_training" / "holdout_2026_result.json",
    }

    errors: List[str] = []
    docs: Dict[str, Dict[str, Any]] = {}
    for name, path in inputs.items():
        if not path.is_file():
            errors.append(f"missing_file:{name}:{path}")
            continue
        try:
            docs[name] = _read_json(path)
        except Exception as exc:  # pragma: no cover
            errors.append(f"json_read_error:{name}:{path}:{exc}")

    meta: Dict[str, Any] = {
        "generated_at_utc": _utc_now(),
        "system_error_policy": on_system_error,
        "input_paths": {k: str(v) for k, v in inputs.items()},
        "input_errors": errors,
    }

    # System-error branch: fail-safe by default.
    if errors:
        if on_system_error == "no_go":
            return {
                "schema": "a_track_go_nogo_status_v1",
                "meta": meta,
                "result": {
                    "overall_go_no_go": "NO_GO",
                    "recommended_stage": "S0_LOCKED",
                    "failed_reasons": errors + ["system_error_fail_safe_no_go"],
                },
                "stage_readiness": {
                    "s1_shadow_ready": False,
                    "s2_paper_strict_ready": False,
                    "s3_paper_scaled_ready": False,
                    "s4_limited_live_ready": False,
                },
                "checks": {},
            }
        return {
            "schema": "a_track_go_nogo_status_v1",
            "meta": meta,
            "result": {
                "overall_go_no_go": "HOLD",
                "recommended_stage": "S1_SHADOW",
                "failed_reasons": errors + ["system_error_hold_previous_stage"],
            },
            "stage_readiness": {
                "s1_shadow_ready": True,
                "s2_paper_strict_ready": False,
                "s3_paper_scaled_ready": False,
                "s4_limited_live_ready": False,
            },
            "checks": {},
        }

    high_rel = docs["high_reliability_mode_gate"]
    trinity = docs["trinity_track_quality"]
    prophecy = docs["prophecy_monthly"]
    holdout = docs["chronos_holdout_2026"]

    checks: Dict[str, bool] = {}
    failed_reasons: List[str] = []

    # S1 checks (Shadow)
    _add_check(
        checks,
        failed_reasons,
        "high_reliability_mode_gate_pass",
        high_rel.get("decision") == "PASS",
        "high_reliability_mode_gate_not_pass",
    )
    _add_check(
        checks,
        failed_reasons,
        "trinity_overall_pass",
        (trinity.get("summary") or {}).get("overall_decision") == "PASS",
        "trinity_overall_not_pass",
    )

    s1_ready = _strict_and(
        {
            "high_reliability_mode_gate_pass": checks["high_reliability_mode_gate_pass"],
            "trinity_overall_pass": checks["trinity_overall_pass"],
        }
    )

    # S2 checks (Paper-Strict)
    high_rel_decision = (prophecy.get("meta") or {}).get("high_reliability_decision")
    price_output_locked = _bool((prophecy.get("meta") or {}).get("price_output_locked"))
    holdout_direction = float(holdout.get("direction_match_rate") or 0.0)

    _add_check(
        checks,
        failed_reasons,
        "high_reliability_decision_not_hold",
        high_rel_decision != "HOLD",
        "high_reliability_decision_is_hold",
    )
    _add_check(
        checks,
        failed_reasons,
        "price_output_unlocked",
        price_output_locked is False,
        "price_output_locked_true",
    )
    _add_check(
        checks,
        failed_reasons,
        "chronos_holdout_direction_match_gte_50",
        holdout_direction >= 50.0,
        f"chronos_holdout_direction_match_below_threshold:{holdout_direction:.4f}",
    )

    s2_ready = _strict_and(
        {
            "s1_ready": s1_ready,
            "high_reliability_decision_not_hold": checks["high_reliability_decision_not_hold"],
            "price_output_unlocked": checks["price_output_unlocked"],
            "chronos_holdout_direction_match_gte_50": checks["chronos_holdout_direction_match_gte_50"],
        }
    )

    # S3/S4 require time-series evidence not fully inferable from one snapshot.
    # Keep false unless external weekly evidence is provided.
    s3_ready = False
    s4_ready = False
    failed_reasons.append("s3_requires_multiweek_stability_evidence")
    failed_reasons.append("s4_requires_operator_explicit_approval")

    if s2_ready:
        overall = "GO"
        recommended_stage = "S2_PAPER_STRICT"
    elif s1_ready:
        overall = "HOLD"
        recommended_stage = "S1_SHADOW"
    else:
        overall = "NO_GO"
        recommended_stage = "S0_LOCKED"

    return {
        "schema": "a_track_go_nogo_status_v1",
        "meta": meta,
        "snapshot": {
            "high_reliability_mode_gate_decision": high_rel.get("decision"),
            "trinity_overall_decision": (trinity.get("summary") or {}).get("overall_decision"),
            "high_reliability_decision": high_rel_decision,
            "price_output_locked": price_output_locked,
            "chronos_holdout_direction_match_rate": holdout_direction,
        },
        "checks": checks,
        "stage_readiness": {
            "s1_shadow_ready": s1_ready,
            "s2_paper_strict_ready": s2_ready,
            "s3_paper_scaled_ready": s3_ready,
            "s4_limited_live_ready": s4_ready,
        },
        "result": {
            "overall_go_no_go": overall,
            "recommended_stage": recommended_stage,
            "failed_reasons": failed_reasons,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build A-track weekly Go/No-Go status JSON.")
    ap.add_argument(
        "--on-system-error",
        choices=("no_go", "hold_s1"),
        default="no_go",
        help="How to handle missing/corrupted inputs.",
    )
    ap.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="Output JSON path.",
    )
    args = ap.parse_args()

    payload = evaluate(on_system_error=args.on_system_error)
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"overall_go_no_go: {payload.get('result', {}).get('overall_go_no_go')}")
    print(f"recommended_stage: {payload.get('result', {}).get('recommended_stage')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
