#!/usr/bin/env python3
"""Build Tier1 promotion candidate proposal from shadow rehearsal results."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SHADOW = ART / "external_bible_anchor_shadow_rehearsal_latest.json"
DEFAULT_APPLY_GATE = ART / "external_bible_crossref_threshold_apply_gate_latest.json"
DEFAULT_THRESHOLD_PROPOSAL = ART / "btrack_external_baseline_threshold_tuning_proposal_latest.json"
DEFAULT_OUT = ART / "external_bible_anchor_tier1_promotion_candidates_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shadow-json", type=Path, default=DEFAULT_SHADOW)
    ap.add_argument("--apply-gate-json", type=Path, default=DEFAULT_APPLY_GATE)
    ap.add_argument("--threshold-proposal-json", type=Path, default=DEFAULT_THRESHOLD_PROPOSAL)
    ap.add_argument("--min-delta-tier1", type=float, default=0.0065)
    ap.add_argument("--min-precision-tier1", type=float, default=0.03)
    ap.add_argument("--target-min-candidates", type=int, default=3)
    ap.add_argument("--target-max-candidates", type=int, default=5)
    ap.add_argument("--relaxed-delta-floor", type=float, default=0.001)
    ap.add_argument("--relaxed-precision-floor", type=float, default=0.0)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    shadow = _read_json(args.shadow_json)
    apply_gate = _read_json(args.apply_gate_json)
    threshold_proposal = _read_json(args.threshold_proposal_json)

    shadow_status = str(shadow.get("status") or "")
    shadow_pass = shadow_status == "SHADOW_PASS"
    can_apply_thresholds = bool(apply_gate.get("can_apply_thresholds"))
    candidates_raw = shadow.get("candidates") if isinstance(shadow.get("candidates"), list) else []

    strict_candidates: list[dict[str, Any]] = []
    shadow_pass_rows: list[dict[str, Any]] = []
    for row in candidates_raw:
        if not isinstance(row, dict):
            continue
        delta = float(row.get("delta_random_baseline") or 0.0)
        precision = float(row.get("precision_at_k") or 0.0)
        coverage = float(row.get("coverage_overlap") or 0.0)
        is_shadow_pass = bool(row.get("shadow_pass"))
        if is_shadow_pass:
            shadow_pass_rows.append(
                {
                    "label": row.get("label"),
                    "delta_random_baseline": delta,
                    "precision_at_k": precision,
                    "coverage_overlap": coverage,
                }
            )
        if is_shadow_pass and delta >= float(args.min_delta_tier1) and precision >= float(args.min_precision_tier1):
            strict_candidates.append(
                {
                    "label": row.get("label"),
                    "delta_random_baseline": delta,
                    "precision_at_k": precision,
                    "coverage_overlap": coverage,
                    "promotion_basis": "tier2_shadow_pass_with_min_delta_precision",
                }
            )

    target_min = max(1, int(args.target_min_candidates))
    target_max = max(target_min, int(args.target_max_candidates))

    promoted: list[dict[str, Any]] = list(strict_candidates)
    seen = {str(r.get("label")) for r in promoted}
    relaxed_added = 0
    if shadow_pass and len(promoted) < target_min:
        relaxed_pool = []
        for row in shadow_pass_rows:
            label = str(row.get("label") or "")
            if not label or label in seen:
                continue
            if float(row.get("delta_random_baseline") or 0.0) < float(args.relaxed_delta_floor):
                continue
            if float(row.get("precision_at_k") or 0.0) < float(args.relaxed_precision_floor):
                continue
            relaxed_pool.append(row)
        relaxed_pool.sort(
            key=lambda r: (
                float(r.get("delta_random_baseline") or 0.0),
                float(r.get("precision_at_k") or 0.0),
                float(r.get("coverage_overlap") or 0.0),
            ),
            reverse=True,
        )
        for row in relaxed_pool:
            if len(promoted) >= target_max:
                break
            label = str(row.get("label"))
            if label in seen:
                continue
            promoted.append(
                {
                    "label": label,
                    "delta_random_baseline": float(row.get("delta_random_baseline") or 0.0),
                    "precision_at_k": float(row.get("precision_at_k") or 0.0),
                    "coverage_overlap": float(row.get("coverage_overlap") or 0.0),
                    "promotion_basis": "shadow_pass_relaxed_backfill_for_target_range",
                }
            )
            seen.add(label)
            relaxed_added += 1

    # Tier1 promotion candidates are produced from shadow evidence.
    # Threshold apply gate is tracked as context, not hard blocker.
    ready_for_human_review = shadow_pass and len(promoted) > 0
    status = "READY_FOR_HUMAN_REVIEW" if ready_for_human_review else "NOT_READY"
    next_action = "request_tier1_manual_promotion_signoff" if ready_for_human_review else "continue_shadow_iterations"

    out = {
        "schema": "external_bible_anchor_tier1_promotion_candidates_v1",
        "generated_at_utc": _iso_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "inputs": {
            "shadow_json": str(args.shadow_json).replace("\\", "/"),
            "apply_gate_json": str(args.apply_gate_json).replace("\\", "/"),
            "threshold_proposal_json": str(args.threshold_proposal_json).replace("\\", "/"),
        },
        "checks": {
            "shadow_pass": shadow_pass,
            "can_apply_thresholds_context": can_apply_thresholds,
            "candidate_count_gt_zero": len(promoted) > 0,
            "target_min_candidates_met": len(promoted) >= target_min,
        },
        "selection_policy": {
            "target_min_candidates": target_min,
            "target_max_candidates": target_max,
            "strict_min_delta_tier1": float(args.min_delta_tier1),
            "strict_min_precision_tier1": float(args.min_precision_tier1),
            "relaxed_delta_floor": float(args.relaxed_delta_floor),
            "relaxed_precision_floor": float(args.relaxed_precision_floor),
            "strict_candidate_count": len(strict_candidates),
            "relaxed_added_count": relaxed_added,
            "shadow_pass_pool_count": len(shadow_pass_rows),
        },
        "threshold_snapshot": threshold_proposal.get("proposed_thresholds"),
        "promotion_candidates": promoted,
        "status": status,
        "recommended_next": next_action,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "status": status,
                "candidate_count": len(promoted),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
