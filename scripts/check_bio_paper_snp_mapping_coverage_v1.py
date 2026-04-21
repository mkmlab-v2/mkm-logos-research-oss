#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.87, L:0.74, K:0.82, M:0.45}
# Balance: 88
# Purpose: Measure sample_id coverage of explicit PMID mapping vs cohort CSV before paper SNP sidecar apply.
# Keywords: bio, mapping, coverage, SNP, cohort
"""Report mapping coverage: cohort sample_ids vs mapping keys (numeric pmid required in mapping)."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def _digits_pmid(raw: str) -> str:
    s = "".join(ch for ch in (raw or "").strip() if ch.isdigit())
    return s if s.isdigit() else ""


def _load_cohort_sample_ids(path: Path) -> tuple[set[str], int, bool]:
    """Return (distinct non-empty sample_id set, total data rows, any_duplicate_ids)."""
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if "sample_id" not in (reader.fieldnames or []):
            raise ValueError("cohort CSV must include sample_id column")
        rows = list(reader)
    seen: dict[str, int] = {}
    for r in rows:
        sid = str(r.get("sample_id") or "").strip()
        if not sid:
            continue
        seen[sid] = seen.get(sid, 0) + 1
    dup_ids = any(c > 1 for c in seen.values())
    return set(seen.keys()), len(rows), dup_ids


def _load_mapping_sample_ids_with_pmid(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    pmid_col = "paper_pmid" if "paper_pmid" in fields else "pmid"
    if "sample_id" not in fields or pmid_col not in fields:
        raise ValueError("mapping CSV must include sample_id and pmid or paper_pmid")
    out: set[str] = set()
    for r in rows:
        sid = str(r.get("sample_id") or "").strip()
        if not sid:
            continue
        pm = _digits_pmid(str(r.get(pmid_col) or ""))
        if pm:
            out.add(sid)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Cohort sample_id coverage vs PMID mapping CSV.")
    ap.add_argument("--cohort-csv", type=Path, required=True)
    ap.add_argument("--mapping-csv", type=Path, required=True)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/bio_paper_snp_mapping_coverage_v1_latest.json"),
    )
    ap.add_argument(
        "--min-coverage-ratio",
        type=float,
        default=0.0,
        help="With --strict, exit 2 if (mapped_distinct / cohort_distinct) < this (0..1).",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 when coverage ratio below --min-coverage-ratio.",
    )
    ns = ap.parse_args()

    if not ns.cohort_csv.is_file():
        print(f"missing cohort: {ns.cohort_csv}", file=sys.stderr)
        return 1
    if not ns.mapping_csv.is_file():
        print(f"missing mapping: {ns.mapping_csv}", file=sys.stderr)
        return 1

    cohort_ids, n_rows, cohort_dup_ids = _load_cohort_sample_ids(ns.cohort_csv)
    map_ids = _load_mapping_sample_ids_with_pmid(ns.mapping_csv)
    covered = cohort_ids & map_ids
    n_cohort = len(cohort_ids)
    n_map = len(map_ids)
    n_covered = len(covered)
    ratio = (n_covered / n_cohort) if n_cohort else None
    orphan_map = len(map_ids - cohort_ids)

    payload: dict[str, Any] = {
        "schema": "bio_paper_snp_mapping_coverage_v1",
        "cohort_csv": str(ns.cohort_csv.resolve()),
        "mapping_csv": str(ns.mapping_csv.resolve()),
        "cohort_data_rows": n_rows,
        "cohort_distinct_sample_id": n_cohort,
        "mapping_distinct_sample_id_with_pmid": n_map,
        "cohort_sample_ids_with_mapping_pmid": n_covered,
        "mapping_sample_ids_not_in_cohort": orphan_map,
        "coverage_ratio": ratio,
        "cohort_has_duplicate_sample_id_rows": cohort_dup_ids,
        "note": "Literature PMID mapping; not genotyping coverage.",
    }

    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"WROTE: {ns.output_json.resolve()} cohort_distinct={n_cohort} "
        f"mapped_with_pmid={n_covered} ratio={ratio!s}",
        flush=True,
    )

    if ns.strict and ratio is not None and ratio + 1e-12 < float(ns.min_coverage_ratio):
        print(
            f"FAIL: coverage {ratio} < min {ns.min_coverage_ratio}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
