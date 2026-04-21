#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.76, K:0.83, M:0.48}
# Balance: 88
# Purpose: Compare sample-level genotype rsids against paper SNP sidecar columns after PMID join.
# Keywords: bio, dna, genotype, rsid, overlap, snp
"""Compute per-sample genotype-to-paper-SNP overlap from joined cohort CSV."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RSID_RE = re.compile(r"\brs\d+\b", re.IGNORECASE)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_rsids(text: str) -> set[str]:
    return {m.group(0).lower() for m in RSID_RE.finditer(text or "")}


def _load_genotypes(path: Path, sample_col: str, rsid_col: str) -> dict[str, set[str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        if sample_col not in fields or rsid_col not in fields:
            raise ValueError(f"genotype CSV must include {sample_col} and {rsid_col}")
        out: dict[str, set[str]] = {}
        for row in reader:
            sid = str(row.get(sample_col) or "").strip()
            rsid = str(row.get(rsid_col) or "").strip().lower()
            if not sid or not rsid.startswith("rs"):
                continue
            out.setdefault(sid, set()).add(rsid)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Check overlap between sample genotype rsids and paper_snp_ids_final_v3.")
    ap.add_argument("--cohort-csv", type=Path, required=True, help="Output of apply_bio_paper_snp_sidecar_to_samples_v1.py")
    ap.add_argument("--genotype-csv", type=Path, required=True, help="Long format CSV with sample_id,rsid rows")
    ap.add_argument("--sample-col", type=str, default="sample_id")
    ap.add_argument("--rsid-col", type=str, default="rsid")
    ap.add_argument(
        "--output-csv",
        type=Path,
        default=Path("tmp/bio_cohort_with_genotype_overlap_v1.csv"),
    )
    ap.add_argument(
        "--output-report",
        type=Path,
        default=Path("reports/bio_genotype_paper_snp_overlap_v1_latest.json"),
    )
    ns = ap.parse_args()

    if not ns.cohort_csv.is_file() or not ns.genotype_csv.is_file():
        print("missing --cohort-csv or --genotype-csv", file=sys.stderr)
        return 1

    geno = _load_genotypes(ns.genotype_csv, ns.sample_col, ns.rsid_col)
    with ns.cohort_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        if "sample_id" not in fields:
            print("cohort-csv must include sample_id", file=sys.stderr)
            return 1
        rows = list(reader)

    out_fields = fields + [c for c in [
        "dna_genotype_rsid_count",
        "dna_paper_snp_target_count",
        "dna_paper_snp_match_count",
        "dna_paper_snp_match_ratio",
        "dna_paper_snp_matched_rsids",
    ] if c not in fields]

    total_with_target = 0
    total_with_match = 0
    out_rows: list[dict[str, str]] = []
    for row in rows:
        r = {k: str(v) for k, v in row.items()}
        sid = str(r.get("sample_id") or "").strip()
        gset = geno.get(sid, set())
        tset = _parse_rsids(str(r.get("paper_snp_ids_final_v3") or ""))
        mset = gset & tset
        if tset:
            total_with_target += 1
        if mset:
            total_with_match += 1
        ratio = (len(mset) / len(tset)) if tset else 0.0
        r["dna_genotype_rsid_count"] = str(len(gset))
        r["dna_paper_snp_target_count"] = str(len(tset))
        r["dna_paper_snp_match_count"] = str(len(mset))
        r["dna_paper_snp_match_ratio"] = f"{ratio:.6f}" if tset else ""
        r["dna_paper_snp_matched_rsids"] = "|".join(sorted(mset))
        out_rows.append(r)

    ns.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with ns.output_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)

    report = {
        "schema": "bio_genotype_paper_snp_overlap_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "cohort_csv": str(ns.cohort_csv.resolve()),
            "genotype_csv": str(ns.genotype_csv.resolve()),
            "sample_col": ns.sample_col,
            "rsid_col": ns.rsid_col,
        },
        "summary": {
            "rows": len(out_rows),
            "samples_with_genotype_rows": len(geno),
            "rows_with_paper_snp_targets": total_with_target,
            "rows_with_any_genotype_match": total_with_match,
        },
        "note": "Overlap score is an evidence signal only; no direct constitution reweighting here.",
    }
    ns.output_report.parent.mkdir(parents=True, exist_ok=True)
    ns.output_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {ns.output_csv.resolve()} rows={len(out_rows)}", flush=True)
    print(f"WROTE: {ns.output_report.resolve()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
