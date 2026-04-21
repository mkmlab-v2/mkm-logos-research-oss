#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.85, K:0.57, M:0.46}
# Balance: 90
# Purpose: Recommend next real-genotype sample targets to raise overlap match rows.
# Keywords: bio, dna, overlap, cohort, targeting, expansion, recommendation
"""Recommend prioritized real-sample expansion targets from overlap CSV."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_int(text: str) -> int:
    try:
        return int(float(text or 0))
    except (TypeError, ValueError):
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Recommend high-impact sample_ids for real genotype expansion."
    )
    ap.add_argument(
        "--overlap-csv",
        type=Path,
        default=Path("tmp/bio_cohort_with_genotype_overlap_v1.csv"),
    )
    ap.add_argument("--top-k", type=int, default=30)
    ap.add_argument(
        "--output-csv",
        type=Path,
        default=Path("reports/bio_dna_real_expansion_targets_v1.csv"),
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/bio_dna_real_expansion_targets_v1.json"),
    )
    ns = ap.parse_args()

    if not ns.overlap_csv.is_file():
        raise FileNotFoundError(f"missing overlap-csv: {ns.overlap_csv}")

    with ns.overlap_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    sample_agg: dict[str, dict[str, Any]] = {}
    with_match = 0
    with_target = 0
    for r in rows:
        target = _to_int(str(r.get("dna_paper_snp_target_count") or "0"))
        match = _to_int(str(r.get("dna_paper_snp_match_count") or "0"))
        geno_count = _to_int(str(r.get("dna_genotype_rsid_count") or "0"))
        sid = str(r.get("sample_id") or "").strip()
        if target > 0:
            with_target += 1
        if match > 0:
            with_match += 1
        if target <= 0 or not sid:
            continue
        # Aggregate by sample_id; prioritize samples with no current matches.
        agg = sample_agg.setdefault(
            sid,
            {
                "sample_id": sid,
                "target_count": 0,
                "match_count": 0,
                "genotype_rsid_count": 0,
                "paper_pmids": set(),
            },
        )
        agg["target_count"] = max(int(agg["target_count"]), target)
        agg["match_count"] = max(int(agg["match_count"]), match)
        agg["genotype_rsid_count"] = max(int(agg["genotype_rsid_count"]), geno_count)
        pmid = str(r.get("paper_pmid") or "").strip()
        if pmid:
            agg["paper_pmids"].add(pmid)

    candidates: list[dict[str, Any]] = []
    for sid, agg in sample_agg.items():
        target = int(agg["target_count"])
        match = int(agg["match_count"])
        geno_count = int(agg["genotype_rsid_count"])
        if target <= 0 or match > 0:
            continue
        # Higher target count = potentially larger chance to increase rows_with_any_genotype_match.
        # Higher genotype count but zero match can indicate rsid panel mismatch; keep but lower priority.
        priority_score = (target * 1000) - geno_count
        candidates.append(
            {
                "sample_id": sid,
                "target_count": target,
                "match_count": match,
                "genotype_rsid_count": geno_count,
                "paper_pmid": "|".join(sorted(agg["paper_pmids"])),
                "priority_score": priority_score,
            }
        )

    ranked = sorted(
        candidates,
        key=lambda x: (x["priority_score"], x["target_count"]),
        reverse=True,
    )
    top = ranked[: max(0, ns.top_k)]

    ns.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with ns.output_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "sample_id",
                "target_count",
                "match_count",
                "genotype_rsid_count",
                "paper_pmid",
                "priority_score",
            ],
        )
        w.writeheader()
        w.writerows(top)

    payload = {
        "schema": "bio_dna_real_expansion_targets_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "overlap_csv": str(ns.overlap_csv.resolve()),
            "top_k": ns.top_k,
        },
        "summary": {
            "rows": len(rows),
            "rows_with_paper_snp_targets": with_target,
            "rows_with_any_genotype_match": with_match,
            "rows_without_match_but_with_targets": len(candidates),
            "recommended_target_count": len(top),
        },
        "recommendation_rule": (
            "Prioritize rows with target_count>0 and match_count=0, ranked by "
            "higher target_count and lower genotype_rsid_count mismatch."
        ),
        "top_targets": top,
        "note": "Use as collection priority guidance; does not alter promotion gate directly.",
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"WROTE: {ns.output_csv.resolve()} rows={len(top)}",
        flush=True,
    )
    print(
        f"WROTE: {ns.output_json.resolve()} no_match_targets={len(candidates)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
