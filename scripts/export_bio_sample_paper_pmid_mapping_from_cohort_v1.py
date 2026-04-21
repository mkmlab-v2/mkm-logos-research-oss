#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.88, L:0.72, K:0.8, M:0.4}
# Balance: 87
# Purpose: Build sample_id↔numeric pmid CSV for paper SNP sidecar join when cohort already carries an explicit PMID column.
# Keywords: bio, mapping, pmid, cohort, CSV
"""Emit mapping CSV (sample_id, pmid) from a cohort row file for apply_bio_paper_snp_sidecar_to_samples_v1."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def _digits_pmid(raw: str) -> str:
    s = "".join(ch for ch in (raw or "").strip() if ch.isdigit())
    return s if s.isdigit() else ""


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract sample_id→pmid mapping from cohort CSV (explicit paper PMID column only).",
    )
    ap.add_argument("--input-csv", type=Path, required=True)
    ap.add_argument("--output-csv", type=Path, required=True)
    ap.add_argument(
        "--pmid-col",
        type=str,
        default="paper_pmid",
        help="Column with PubMed ID digits (fallback: try paper_pmid then pmid if missing).",
    )
    ap.add_argument(
        "--dedupe",
        choices=("last", "first", "error"),
        default="last",
        help="When duplicate sample_id: keep last non-empty pmid, first, or exit 3.",
    )
    ns = ap.parse_args()

    if not ns.input_csv.is_file():
        print(f"missing input: {ns.input_csv}", file=sys.stderr)
        return 1

    with ns.input_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)

    pmid_col = ns.pmid_col.strip()
    if pmid_col not in fields:
        if "paper_pmid" in fields:
            pmid_col = "paper_pmid"
        elif "pmid" in fields:
            pmid_col = "pmid"
        else:
            print(
                f"no PMID column: need {ns.pmid_col!r} or paper_pmid or pmid in {fields[:20]}…",
                file=sys.stderr,
            )
            return 2

    if "sample_id" not in fields:
        print("input CSV must include sample_id", file=sys.stderr)
        return 2

    by_sid: dict[str, str] = {}
    for row in rows:
        sid = str(row.get("sample_id") or "").strip()
        if not sid:
            continue
        pm = _digits_pmid(str(row.get(pmid_col) or ""))
        if not pm:
            continue
        if sid in by_sid and ns.dedupe == "error":
            print(f"duplicate sample_id with pmid data: {sid}", file=sys.stderr)
            return 3
        if ns.dedupe == "first" and sid in by_sid:
            continue
        by_sid[sid] = pm

    out_pairs = sorted(by_sid.items(), key=lambda x: x[0])

    ns.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with ns.output_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "pmid"])
        w.writeheader()
        for sid, pm in out_pairs:
            w.writerow({"sample_id": sid, "pmid": pm})

    n_in = len(rows)
    n_out = len(out_pairs)
    print(f"WROTE: {ns.output_csv.resolve()} pairs={n_out} pmid_col={pmid_col} input_rows={n_in}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
