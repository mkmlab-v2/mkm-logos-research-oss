#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.86, L:0.77, K:0.63, M:0.41}
# Balance: 88
# Purpose: Fill missing genotype template with synthetic rsid/genotype rows for E2E pipeline testing.
# Keywords: bio, dna, synthetic, genotype, template, e2e
"""Generate synthetic genotype CSV from missing-sample template (research-only)."""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate synthetic genotype rows from missing template CSV.")
    ap.add_argument(
        "--missing-template-csv",
        type=Path,
        default=Path("tmp/bio_genotype_missing_sample_template_v1.csv"),
    )
    ap.add_argument(
        "--output-csv",
        type=Path,
        default=Path("tmp/bio_genotype_long_synthetic_v1.csv"),
    )
    ap.add_argument(
        "--output-report",
        type=Path,
        default=Path("reports/bio_genotype_synthetic_build_v1_latest.json"),
    )
    ap.add_argument("--seed", type=int, default=20260421)
    ap.add_argument(
        "--fallback-cohort-csv",
        type=Path,
        default=None,
        help="If missing template has zero rows, rebuild sample list from cohort sample_id.",
    )
    ns = ap.parse_args()

    if not ns.missing_template_csv.is_file():
        raise FileNotFoundError(f"missing template: {ns.missing_template_csv}")

    rng = random.Random(ns.seed)
    rsids = ["rs10937331", "rs12431592", "rs7180547", "rs7193144"]
    genotypes = ["AA", "AG", "GG", "CC", "CT", "TT"]

    with ns.missing_template_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        sample_ids = []
        for row in reader:
            sid = str(row.get("sample_id") or "").strip()
            if sid:
                sample_ids.append(sid)

    if not sample_ids and ns.fallback_cohort_csv is not None and ns.fallback_cohort_csv.is_file():
        with ns.fallback_cohort_csv.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if "sample_id" in (reader.fieldnames or []):
                seen: set[str] = set()
                for row in reader:
                    sid = str(row.get("sample_id") or "").strip()
                    if sid and sid not in seen:
                        seen.add(sid)
                        sample_ids.append(sid)

    out_rows: list[dict[str, str]] = []
    for sid in sample_ids:
        for rs in rsids:
            out_rows.append(
                {
                    "sample_id": sid,
                    "rsid": rs,
                    "genotype": rng.choice(genotypes),
                    "source_tag": "synthetic_e2e_only",
                }
            )

    ns.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with ns.output_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "rsid", "genotype", "source_tag"])
        w.writeheader()
        w.writerows(out_rows)

    payload = {
        "schema": "bio_genotype_synthetic_build_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_forbidden": True,
        "inputs": {
            "missing_template_csv": str(ns.missing_template_csv.resolve()),
            "seed": ns.seed,
        },
        "summary": {
            "sample_count": len(sample_ids),
            "rsids_per_sample": len(rsids),
            "output_rows": len(out_rows),
            "rsids": rsids,
        },
        "outputs": {"output_csv": str(ns.output_csv.resolve())},
        "note": "Synthetic genotype rows for E2E validation only. Not valid for scientific or production claims.",
    }
    ns.output_report.parent.mkdir(parents=True, exist_ok=True)
    ns.output_report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_csv.resolve()} rows={len(out_rows)}")
    print(f"WROTE: {ns.output_report.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

