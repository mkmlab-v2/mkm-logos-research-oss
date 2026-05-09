#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.88, L:0.86, K:0.62, M:0.44}
# Balance: 87
# Purpose: Generate large synthetic AGCT-Sasang cohort/genotype fixtures for gate stress testing.
# Keywords: synthetic, agct, sasang, cohort, genotype, holdout
"""Generate synthetic dataset for AGCT-Sasang chain stress test."""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path


LABELS = ["TY", "SY", "TE", "SE"]
LABEL_TO_BASE = {"TY": "A", "SY": "C", "TE": "G", "SE": "T"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate synthetic AGCT-Sasang dataset.")
    ap.add_argument("--n-samples", type=int, default=160)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--cohort-csv",
        type=Path,
        default=Path("tmp/agct_sasang_synth_cohort_v1.csv"),
    )
    ap.add_argument(
        "--genotype-csv",
        type=Path,
        default=Path("tmp/agct_sasang_synth_genotype_v1.csv"),
    )
    ap.add_argument(
        "--mapping-coverage-json",
        type=Path,
        default=Path("tmp/agct_sasang_synth_mapping_coverage_v1.json"),
    )
    ns = ap.parse_args()

    rng = random.Random(ns.seed)
    ns.cohort_csv.parent.mkdir(parents=True, exist_ok=True)
    ns.genotype_csv.parent.mkdir(parents=True, exist_ok=True)
    ns.mapping_coverage_json.parent.mkdir(parents=True, exist_ok=True)

    cohort_rows = []
    genotype_rows = []
    rs_counter = 100000
    for i in range(ns.n_samples):
        label = LABELS[i % len(LABELS)]
        base = LABEL_TO_BASE[label]
        sample_id = f"synth_{i+1:04d}"
        risk = {"TY": 0.15, "SY": 0.85, "TE": 0.35, "SE": 0.65}[label]
        # Small noise but separable.
        risk_score = max(0.0, min(1.0, risk + rng.uniform(-0.03, 0.03)))

        rsids = []
        for _ in range(3):
            rs_counter += 1
            rsid = f"rs{rs_counter}"
            rsids.append(rsid)
            # dominant genotype signal by class base
            genotype = base * 2
            # occasional perturbation
            if rng.random() < 0.05:
                genotype = rng.choice(["AA", "CC", "GG", "TT"])
            genotype_rows.append({"sample_id": sample_id, "rsid": rsid, "genotype": genotype})

        cohort_rows.append(
            {
                "sample_id": sample_id,
                "expected_parent": label,
                "risk_score": f"{risk_score:.4f}",
                "paper_snp_ids_final_v3": "|".join(rsids),
            }
        )

    with ns.cohort_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "expected_parent", "risk_score", "paper_snp_ids_final_v3"])
        w.writeheader()
        w.writerows(cohort_rows)

    with ns.genotype_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "rsid", "genotype"])
        w.writeheader()
        w.writerows(genotype_rows)

    ns.mapping_coverage_json.write_text(
        json.dumps({"schema": "bio_paper_snp_mapping_coverage_v1", "coverage_ratio": 1.0}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"WROTE: {ns.cohort_csv.resolve()}")
    print(f"WROTE: {ns.genotype_csv.resolve()}")
    print(f"WROTE: {ns.mapping_coverage_json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
