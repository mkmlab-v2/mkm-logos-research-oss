#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_GATE = ART / "general_prophecy_explainability_holdout_gate_v1_latest.json"
DEFAULT_HEALTH = ART / "general_prophecy_holdout_gate_health_latest.json"
DEFAULT_FAILURE = ART / "general_prophecy_daily_queue_failure_summary_latest.json"
DEFAULT_OUT = ART / "general_prophecy_holdout_evolution_candidates_latest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _f(v: Any, default: float = 0.0) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    return default


def build_candidates(
    gate_doc: dict[str, Any],
    health_doc: dict[str, Any],
    failure_doc: dict[str, Any],
) -> dict[str, Any]:
    decision = str(gate_doc.get("decision", "UNKNOWN"))
    checks = gate_doc.get("checks") if isinstance(gate_doc.get("checks"), dict) else {}
    failed_check_keys = [str(k) for k, v in checks.items() if v is False]
    thresholds = gate_doc.get("thresholds") if isinstance(gate_doc.get("thresholds"), dict) else {}
    snap = gate_doc.get("metrics_snapshot") if isinstance(gate_doc.get("metrics_snapshot"), dict) else {}
    profile = str(gate_doc.get("profile") or "research")

    candidates: list[dict[str, Any]] = []
    if "min_holdout_direct_rate_pass" in failed_check_keys:
        current = _f(snap.get("holdout_direct_match_rate"))
        threshold = _f(thresholds.get("min_holdout_direct_rate"), 0.7)
        proposed = round(max(0.0, min(1.0, threshold - 0.03)), 6)
        candidates.append(
            {
                "id": "adj_holdout_direct_threshold_down_small",
                "target": "holdout_gate.thresholds.min_holdout_direct_rate",
                "current_value": threshold,
                "proposed_value": proposed,
                "delta": round(proposed - threshold, 6),
                "reason": f"direct rate {current:.6f} below threshold {threshold:.6f}",
                "risk_level": "medium",
            }
        )
    if "min_holdout_repro_rate_pass" in failed_check_keys:
        current = _f(snap.get("holdout_reproducible_evidence_rate"))
        threshold = _f(thresholds.get("min_holdout_repro_rate"), 0.9)
        proposed = round(max(0.0, min(1.0, threshold - 0.02)), 6)
        candidates.append(
            {
                "id": "adj_holdout_repro_threshold_down_small",
                "target": "holdout_gate.thresholds.min_holdout_repro_rate",
                "current_value": threshold,
                "proposed_value": proposed,
                "delta": round(proposed - threshold, 6),
                "reason": f"repro rate {current:.6f} below threshold {threshold:.6f}",
                "risk_level": "medium",
            }
        )
    if "min_holdout_coverage_pass" in failed_check_keys:
        current = _f(snap.get("holdout_avg_biblical_keyword_coverage"))
        threshold = _f(thresholds.get("min_holdout_coverage"), 0.3)
        proposed = round(max(0.0, min(1.0, threshold - 0.02)), 6)
        candidates.append(
            {
                "id": "adj_holdout_coverage_threshold_down_small",
                "target": "holdout_gate.thresholds.min_holdout_coverage",
                "current_value": threshold,
                "proposed_value": proposed,
                "delta": round(proposed - threshold, 6),
                "reason": f"coverage {current:.6f} below threshold {threshold:.6f}",
                "risk_level": "low",
            }
        )

    # If no failed checks, provide "no-op" and exploration candidates.
    if not failed_check_keys:
        candidates.append(
            {
                "id": "noop_keep_current_policy",
                "target": "holdout_gate.thresholds",
                "current_value": thresholds,
                "proposed_value": thresholds,
                "delta": 0.0,
                "reason": "all checks passing",
                "risk_level": "low",
            }
        )
        if profile == "ops":
            # Controlled upward-hardening candidate for explicit review
            candidates.append(
                {
                    "id": "ops_hardening_direct_threshold_up_small",
                    "target": "holdout_gate.thresholds.min_holdout_direct_rate",
                    "current_value": _f(thresholds.get("min_holdout_direct_rate"), 0.85),
                    "proposed_value": round(min(1.0, _f(thresholds.get("min_holdout_direct_rate"), 0.85) + 0.01), 6),
                    "delta": 0.01,
                    "reason": "optional hardening candidate while pass is stable",
                    "risk_level": "medium",
                }
            )

    return {
        "schema": "general_prophecy_holdout_evolution_candidates_v1",
        "generated_at_utc": utc_now(),
        "mode": "proposal_only_no_auto_apply",
        "gate_decision": decision,
        "profile": profile,
        "failed_check_keys": failed_check_keys,
        "health_alert_dispatch_result": health_doc.get("alert_dispatch_result"),
        "latest_failure_step": failure_doc.get("failed_step"),
        "candidates": candidates,
        "next_action": "run_ablation_then_holdout_then_human_signoff",
        "track_wall": {"source_track": "B", "auto_apply": False, "human_signoff_required": True},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build holdout evolution candidate proposals (no auto-apply).")
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--health-json", type=Path, default=DEFAULT_HEALTH)
    ap.add_argument("--failure-json", type=Path, default=DEFAULT_FAILURE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    gate = _read_json(args.gate_json if args.gate_json.is_absolute() else ROOT / args.gate_json)
    if not gate:
        raise SystemExit(f"missing gate json: {args.gate_json}")
    health = _read_json(args.health_json if args.health_json.is_absolute() else ROOT / args.health_json)
    failure = _read_json(args.failure_json if args.failure_json.is_absolute() else ROOT / args.failure_json)

    out = build_candidates(gate, health, failure)
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "candidate_count": len(out.get("candidates") or [])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
