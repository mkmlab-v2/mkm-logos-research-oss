#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.84, L:0.81, K:0.59, M:0.37}
# Balance: 87
# Purpose: Sweep DNA readiness thresholds and recommend highest passing policy.
# Keywords: bio, dna, threshold, sweep, readiness, promotion
"""Run threshold sweep for DNA promotion readiness."""

from __future__ import annotations

import argparse
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_list_float(text: str) -> list[float]:
    return [float(x.strip()) for x in text.split(",") if x.strip()]


def _as_list_int(text: str) -> list[int]:
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep thresholds for DNA readiness gates.")
    ap.add_argument("--mapping-coverage-report", type=Path, required=True)
    ap.add_argument("--overlap-report", type=Path, required=True)
    ap.add_argument(
        "--coverage-grid",
        "--coverage-threshold-grid",
        type=str,
        default="0.10,0.20,0.30,0.40",
        help="Comma-separated min coverage ratios (--coverage-threshold-grid is an alias).",
    )
    ap.add_argument(
        "--target-grid",
        "--target-rows-threshold-grid",
        type=str,
        default="1,2,3",
        help="Comma-separated min target rows (--target-rows-threshold-grid is an alias).",
    )
    ap.add_argument(
        "--match-grid",
        "--match-rows-threshold-grid",
        type=str,
        default="1,2,3",
        help="Comma-separated min match rows (--match-rows-threshold-grid is an alias).",
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/bio_dna_promotion_threshold_sweep_v1_latest.json"),
    )
    ns = ap.parse_args()

    mapping = _load_json(ns.mapping_coverage_report)
    overlap = _load_json(ns.overlap_report)
    obs_cov = float(mapping.get("coverage_ratio") or 0.0)
    obs_target = int(overlap.get("summary", {}).get("rows_with_paper_snp_targets") or 0)
    obs_match = int(overlap.get("summary", {}).get("rows_with_any_genotype_match") or 0)

    covs = _as_list_float(ns.coverage_grid)
    targets = _as_list_int(ns.target_grid)
    matches = _as_list_int(ns.match_grid)
    rows: list[dict[str, Any]] = []
    for c, t, m in itertools.product(covs, targets, matches):
        ok = (obs_cov >= c) and (obs_target >= t) and (obs_match >= m)
        rows.append(
            {
                "min_coverage_ratio": c,
                "min_target_rows": t,
                "min_match_rows": m,
                "ready": ok,
            }
        )

    passing = [r for r in rows if r["ready"]]
    recommended = None
    if passing:
        recommended = sorted(
            passing,
            key=lambda r: (r["min_coverage_ratio"], r["min_target_rows"], r["min_match_rows"]),
            reverse=True,
        )[0]

    recommended_canonical = None
    if recommended is not None:
        recommended_canonical = {
            "min_mapping_coverage_ratio": recommended["min_coverage_ratio"],
            "min_overlap_target_rows": recommended["min_target_rows"],
            "min_overlap_match_rows": recommended["min_match_rows"],
        }

    payload = {
        "schema": "bio_dna_promotion_threshold_sweep_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "mapping_coverage_report": str(ns.mapping_coverage_report.resolve()),
            "overlap_report": str(ns.overlap_report.resolve()),
        },
        "observations": {
            "coverage_ratio": obs_cov,
            "rows_with_paper_snp_targets": obs_target,
            "rows_with_any_genotype_match": obs_match,
        },
        "grid": {
            "coverage_grid": covs,
            "target_grid": targets,
            "match_grid": matches,
        },
        "summary": {
            "total_policies": len(rows),
            "passing_policies": len(passing),
            "candidate_count": obs_target,
            "passing_count": len(passing),
            "recommended_policy": recommended_canonical,
        },
        "policies": rows,
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} policies={len(rows)} passing={len(passing)} "
        f"recommended={recommended}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
