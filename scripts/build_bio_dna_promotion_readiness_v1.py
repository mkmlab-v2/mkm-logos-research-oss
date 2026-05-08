#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.91, L:0.82, K:0.56, M:0.43}
# Balance: 89
# Purpose: Build DNA promotion readiness judgment from mapping and overlap evidence.
# Keywords: bio, dna, readiness, promotion, gate, threshold
"""Build DNA promotion readiness report from evidence files."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_focus_sample_match_ratio(overlap_csv: Path, sample_id: str) -> float | None:
    with overlap_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = str(row.get("sample_id") or "").strip()
            if sid != sample_id:
                continue
            ratio_raw = str(row.get("dna_paper_snp_match_ratio") or "").strip()
            if not ratio_raw:
                return None
            try:
                return float(ratio_raw)
            except ValueError:
                return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Build bio DNA promotion readiness from coverage and overlap reports.")
    ap.add_argument("--mapping-coverage-report", type=Path, required=True)
    ap.add_argument("--overlap-report", type=Path, required=True)
    ap.add_argument("--min-coverage-ratio", type=float, default=0.30)
    ap.add_argument(
        "--min-target-rows",
        "--min-overlap-target-rows",
        type=int,
        default=1,
        help="Minimum rows_with_paper_snp_targets (--min-overlap-target-rows is an alias).",
    )
    ap.add_argument("--min-match-rows", type=int, default=1)
    ap.add_argument("--overlap-csv", type=Path, default=None)
    ap.add_argument("--focus-sample-id", type=str, default="")
    ap.add_argument("--min-focus-match-ratio", type=float, default=None)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/bio_dna_promotion_readiness_v1_latest.json"),
    )
    ns = ap.parse_args()

    mapping = _load_json(ns.mapping_coverage_report)
    overlap = _load_json(ns.overlap_report)

    coverage_ratio = float(mapping.get("coverage_ratio") or 0.0)
    target_rows = int(overlap.get("summary", {}).get("rows_with_paper_snp_targets") or 0)
    match_rows = int(overlap.get("summary", {}).get("rows_with_any_genotype_match") or 0)

    checks = {
        "mapping_coverage_ratio": coverage_ratio >= ns.min_coverage_ratio,
        "rows_with_paper_snp_targets": target_rows >= ns.min_target_rows,
        "rows_with_any_genotype_match": match_rows >= ns.min_match_rows,
    }
    focus_ratio = None
    if ns.focus_sample_id:
        if ns.overlap_csv is None:
            raise ValueError("--focus-sample-id requires --overlap-csv")
        focus_ratio = _load_focus_sample_match_ratio(ns.overlap_csv, ns.focus_sample_id)
        if ns.min_focus_match_ratio is not None:
            checks["focus_sample_match_ratio"] = (focus_ratio is not None) and (
                focus_ratio >= ns.min_focus_match_ratio
            )
    passing = sum(1 for v in checks.values() if v)
    total = len(checks)
    ready = passing == total

    payload = {
        "schema": "bio_dna_promotion_readiness_v1",
        "generated_at_utc": _utc_now(),
        "promotion_candidate_ready": ready,
        "inputs": {
            "mapping_coverage_report": str(ns.mapping_coverage_report.resolve()),
            "overlap_report": str(ns.overlap_report.resolve()),
            "overlap_csv": str(ns.overlap_csv.resolve()) if ns.overlap_csv else None,
            "focus_sample_id": ns.focus_sample_id or None,
        },
        "thresholds": {
            "min_coverage_ratio": ns.min_coverage_ratio,
            "min_target_rows": ns.min_target_rows,
            "min_match_rows": ns.min_match_rows,
            "min_focus_match_ratio": ns.min_focus_match_ratio,
        },
        "observations": {
            "coverage_ratio": coverage_ratio,
            "rows_with_paper_snp_targets": target_rows,
            "rows_with_any_genotype_match": match_rows,
            "focus_sample_match_ratio": focus_ratio,
        },
        "checks": checks,
        "summary": {
            "passing": passing,
            "total": total,
            "promotion_candidate_ready": ready,
        },
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} ready={ready} passing={passing}/{total} "
        f"coverage={coverage_ratio:.4f} targets={target_rows} matches={match_rows}"
    )
    if ns.strict and not ready:
        print("FAIL: strict readiness gate not satisfied", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
