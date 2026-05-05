#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.88, L:0.9, K:0.64, M:0.52}
# Balance: 89
# Purpose: Precheck real-data readiness before unified symbolic+AGCT meta chain execution.
# Keywords: readiness, precheck, holdout, unified, agct, symbolic
"""Precheck for unified symbolic+AGCT meta chain."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _count_rows_and_fields(path: Path) -> tuple[int, set[str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        rows = list(reader)
    return len(rows), fields


def main() -> int:
    ap = argparse.ArgumentParser(description="Precheck for unified symbolic+AGCT chain readiness.")
    ap.add_argument("--cohort-csv", type=Path, required=True)
    ap.add_argument("--genotype-input-csv", type=Path, required=True)
    ap.add_argument("--mapping-coverage-report", type=Path, required=True)
    ap.add_argument("--symbolic-pairs-jsonl", type=Path, required=True)
    ap.add_argument("--symbolic-stream-jsonl", type=Path, required=True)
    ap.add_argument("--sample-col", type=str, default="sample_id")
    ap.add_argument("--label-col", type=str, default="expected_parent")
    ap.add_argument("--genotype-col", type=str, default="genotype")
    ap.add_argument("--holdout-ratio", type=float, default=0.3)
    ap.add_argument("--min-holdout-n", type=int, default=30)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports/unified_meta_chain_readiness_v1_latest.json"),
    )
    ns = ap.parse_args()

    checks: dict[str, bool] = {}
    issues: list[str] = []

    for name, p in {
        "cohort_csv": ns.cohort_csv,
        "genotype_input_csv": ns.genotype_input_csv,
        "mapping_coverage_report": ns.mapping_coverage_report,
        "symbolic_pairs_jsonl": ns.symbolic_pairs_jsonl,
        "symbolic_stream_jsonl": ns.symbolic_stream_jsonl,
    }.items():
        ok = p.is_file()
        checks[f"{name}_exists"] = ok
        if not ok:
            issues.append(f"missing:{name}:{p}")

    cohort_rows = 0
    genotype_rows = 0
    cohort_fields: set[str] = set()
    genotype_fields: set[str] = set()
    if checks.get("cohort_csv_exists"):
        cohort_rows, cohort_fields = _count_rows_and_fields(ns.cohort_csv)
        if ns.sample_col not in cohort_fields:
            issues.append(f"missing_cohort_column:{ns.sample_col}")
        if ns.label_col not in cohort_fields:
            issues.append(f"missing_cohort_column:{ns.label_col}")
    if checks.get("genotype_input_csv_exists"):
        genotype_rows, genotype_fields = _count_rows_and_fields(ns.genotype_input_csv)
        if ns.sample_col not in genotype_fields:
            issues.append(f"missing_genotype_column:{ns.sample_col}")
        if ns.genotype_col not in genotype_fields:
            issues.append(f"missing_genotype_column:{ns.genotype_col}")

    holdout_n_est = max(1, int(round(float(ns.holdout_ratio) * max(cohort_rows, 0)))) if cohort_rows > 0 else 0
    holdout_gate_ok = holdout_n_est >= int(ns.min_holdout_n)
    checks["holdout_n_gate"] = holdout_gate_ok
    if not holdout_gate_ok:
        issues.append(f"holdout_n_too_small:estimated={holdout_n_est}:required={ns.min_holdout_n}")

    checks["required_columns_ok"] = not any(x.startswith("missing_cohort_column:") or x.startswith("missing_genotype_column:") for x in issues)
    checks["all_files_exist"] = all(v for k, v in checks.items() if k.endswith("_exists"))

    decision = "GO_PRECHECK" if all(checks.values()) else "HOLD_PRECHECK"
    payload = {
        "schema": "unified_meta_chain_readiness_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "cohort_csv": str(ns.cohort_csv.resolve()) if ns.cohort_csv.exists() else str(ns.cohort_csv),
            "genotype_input_csv": str(ns.genotype_input_csv.resolve()) if ns.genotype_input_csv.exists() else str(ns.genotype_input_csv),
            "mapping_coverage_report": str(ns.mapping_coverage_report.resolve()) if ns.mapping_coverage_report.exists() else str(ns.mapping_coverage_report),
            "symbolic_pairs_jsonl": str(ns.symbolic_pairs_jsonl.resolve()) if ns.symbolic_pairs_jsonl.exists() else str(ns.symbolic_pairs_jsonl),
            "symbolic_stream_jsonl": str(ns.symbolic_stream_jsonl.resolve()) if ns.symbolic_stream_jsonl.exists() else str(ns.symbolic_stream_jsonl),
            "holdout_ratio": float(ns.holdout_ratio),
            "min_holdout_n": int(ns.min_holdout_n),
        },
        "stats": {
            "cohort_rows": cohort_rows,
            "genotype_rows": genotype_rows,
            "estimated_holdout_n": holdout_n_est,
        },
        "checks": checks,
        "issues": issues,
        "decision": decision,
    }
    ns.out.parent.mkdir(parents=True, exist_ok=True)
    ns.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.out.resolve()} decision={decision}")
    return 0 if decision == "GO_PRECHECK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
