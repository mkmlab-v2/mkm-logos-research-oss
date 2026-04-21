#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.91, L:0.88, K:0.58, M:0.42}
# Balance: 91
# Purpose: Analyze failed DNA threshold-sweep policies and attribute gate failure causes.
# Keywords: bio, dna, threshold, sweep, failure, analysis, readiness
"""Analyze failed policies in DNA threshold sweep reports."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze failed DNA threshold policies.")
    ap.add_argument("--sweep-json", type=Path, required=True)
    ap.add_argument("--readiness-json", type=Path, required=False)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/bio_dna_threshold_failure_analysis_v1_latest.json"),
    )
    ns = ap.parse_args()

    sweep = _load_json(ns.sweep_json)
    observations = sweep.get("observations", {})
    if not observations:
        observations = sweep.get("evidence", {})
    obs_cov = float(observations.get("coverage_ratio") or 0.0)
    obs_target = int(observations.get("rows_with_paper_snp_targets") or 0)
    obs_match = int(observations.get("rows_with_any_genotype_match") or 0)

    readiness_summary: dict[str, Any] = {}
    if ns.readiness_json and ns.readiness_json.is_file():
        readiness = _load_json(ns.readiness_json)
        readiness_summary = {
            "path": str(ns.readiness_json.resolve()),
            "promotion_candidate_ready": bool(
                readiness.get("summary", {}).get("promotion_candidate_ready")
            ),
            "focus_sample_id": readiness.get("inputs", {}).get("focus_sample_id"),
            "focus_sample_match_ratio": readiness.get("observations", {}).get(
                "focus_sample_match_ratio"
            ),
        }

    failed_rows = []
    reason_counter: Counter[str] = Counter()
    # New-style sweep schema: policies[min_coverage_ratio/min_target_rows/min_match_rows/ready]
    if "policies" in sweep:
        for row in sweep.get("policies", []):
            if bool(row.get("ready")):
                continue
            reasons = []
            if obs_cov < float(row.get("min_coverage_ratio") or 0.0):
                reasons.append("coverage_ratio_threshold_not_met")
            if obs_target < int(row.get("min_target_rows") or 0):
                reasons.append("target_rows_threshold_not_met")
            if obs_match < int(row.get("min_match_rows") or 0):
                reasons.append("match_rows_threshold_not_met")
            if not reasons:
                reasons.append("unknown")
            for r in reasons:
                reason_counter[r] += 1
            failed_rows.append(
                {
                    "policy": {
                        "min_coverage_ratio": float(row.get("min_coverage_ratio") or 0.0),
                        "min_target_rows": int(row.get("min_target_rows") or 0),
                        "min_match_rows": int(row.get("min_match_rows") or 0),
                    },
                    "reasons": reasons,
                }
            )
    # Legacy sweep schema: candidates[thresholds..., gate_ok, gates...]
    elif "candidates" in sweep:
        for row in sweep.get("candidates", []):
            if bool(row.get("gate_ok")):
                continue
            gates = row.get("gates", {})
            reasons = []
            if gates.get("mapping_coverage_gate_ok") is False:
                reasons.append("coverage_ratio_threshold_not_met")
            if gates.get("overlap_target_rows_gate_ok") is False:
                reasons.append("target_rows_threshold_not_met")
            if gates.get("overlap_match_rows_gate_ok") is False:
                reasons.append("match_rows_threshold_not_met")
            if not reasons:
                reasons.append("unknown")
            for r in reasons:
                reason_counter[r] += 1
            th = row.get("thresholds", {})
            failed_rows.append(
                {
                    "policy": {
                        "min_coverage_ratio": float(
                            th.get("min_mapping_coverage_ratio") or 0.0
                        ),
                        "min_target_rows": int(th.get("min_overlap_target_rows") or 0),
                        "min_match_rows": int(th.get("min_overlap_match_rows") or 0),
                    },
                    "reasons": reasons,
                }
            )

    dominant_reasons = sorted(
        [{"reason": k, "count": v} for k, v in reason_counter.items()],
        key=lambda x: x["count"],
        reverse=True,
    )

    payload = {
        "schema": "bio_dna_threshold_failure_analysis_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "sweep_json": str(ns.sweep_json.resolve()),
            "readiness_json": (
                str(ns.readiness_json.resolve())
                if ns.readiness_json and ns.readiness_json.is_file()
                else None
            ),
        },
        "observations": {
            "coverage_ratio": obs_cov,
            "rows_with_paper_snp_targets": obs_target,
            "rows_with_any_genotype_match": obs_match,
        },
        "summary": {
            "total_policies": int(
                sweep.get("summary", {}).get("total_policies")
                or sweep.get("summary", {}).get("candidate_count")
                or 0
            ),
            "passing_policies": int(
                sweep.get("summary", {}).get("passing_policies")
                or sweep.get("summary", {}).get("passing_count")
                or 0
            ),
            "failing_policies": len(failed_rows),
            "dominant_failure_reasons": dominant_reasons,
            "recommended_next_action": (
                "Increase rows_with_any_genotype_match via additional real genotype coverage "
                "or lower min_match_rows policy for candidate stage."
                if reason_counter.get("match_rows_threshold_not_met", 0) > 0
                else "Investigate mixed-threshold failures manually."
            ),
        },
        "readiness_context": readiness_summary,
        "failing_policies": failed_rows,
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} failing={len(failed_rows)} reasons={dict(reason_counter)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
