#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.62, M:0.42}
# Balance: 89
# Purpose: Report sample-level genotype coverage against cohort and emit missing-sample template.
# Keywords: bio, dna, genotype, cohort, coverage, template
"""Report genotype coverage vs cohort sample_id and write missing-sample template CSV."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_distinct_sample_ids(path: Path, sample_col: str = "sample_id") -> set[str]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        if sample_col not in fields:
            raise ValueError(f"missing {sample_col} in {path}")
        out: set[str] = set()
        for row in reader:
            sid = str(row.get(sample_col) or "").strip()
            if sid:
                out.add(sid)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Report genotype sample_id coverage against cohort.")
    ap.add_argument("--cohort-csv", type=Path, required=True)
    ap.add_argument("--genotype-csv", type=Path, required=True)
    ap.add_argument("--sample-col", type=str, default="sample_id")
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/bio_genotype_cohort_coverage_v1_latest.json"),
    )
    ap.add_argument(
        "--missing-template-csv",
        type=Path,
        default=Path("tmp/bio_genotype_missing_sample_template_v1.csv"),
    )
    ns = ap.parse_args()

    cohort_ids = _load_distinct_sample_ids(ns.cohort_csv, sample_col=ns.sample_col)
    genotype_ids = _load_distinct_sample_ids(ns.genotype_csv, sample_col=ns.sample_col)
    matched = cohort_ids & genotype_ids
    missing = sorted(cohort_ids - genotype_ids)
    extra = sorted(genotype_ids - cohort_ids)
    coverage_ratio = (len(matched) / len(cohort_ids)) if cohort_ids else 0.0

    ns.missing_template_csv.parent.mkdir(parents=True, exist_ok=True)
    with ns.missing_template_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "rsid", "genotype", "note"])
        w.writeheader()
        for sid in missing:
            w.writerow({"sample_id": sid, "rsid": "", "genotype": "", "note": "fill genotype rsid rows"})

    payload = {
        "schema": "bio_genotype_cohort_coverage_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "cohort_csv": str(ns.cohort_csv.resolve()),
            "genotype_csv": str(ns.genotype_csv.resolve()),
            "sample_col": ns.sample_col,
        },
        "summary": {
            "cohort_distinct_sample_id": len(cohort_ids),
            "genotype_distinct_sample_id": len(genotype_ids),
            "matched_sample_id": len(matched),
            "missing_genotype_sample_id": len(missing),
            "genotype_extra_sample_id": len(extra),
            "coverage_ratio": coverage_ratio,
        },
        "outputs": {
            "missing_template_csv": str(ns.missing_template_csv.resolve()),
        },
        "missing_sample_ids_head": missing[:50],
        "extra_genotype_sample_ids_head": extra[:50],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} coverage={coverage_ratio:.4f} "
        f"matched={len(matched)}/{len(cohort_ids)} missing={len(missing)}"
    )
    print(f"WROTE: {ns.missing_template_csv.resolve()} rows={len(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
