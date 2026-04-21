#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.88, L:0.78, K:0.52, M:0.34}
# Balance: 88
# Purpose: Normalize genotype input into canonical long format sample_id,rsid,genotype.
# Keywords: bio, dna, genotype, normalize, long, csv
"""Normalize genotype CSV to canonical long format."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

RSID_RE = re.compile(r"\brs\d+\b", re.IGNORECASE)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _split_rsids(raw: str) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return []
    found = [m.group(0).lower() for m in RSID_RE.finditer(text)]
    if found:
        return found
    parts = re.split(r"[,\s;|/]+", text)
    return [p.lower() for p in parts if p.lower().startswith("rs")]


def main() -> int:
    ap = argparse.ArgumentParser(description="Normalize genotype CSV to sample_id,rsid,genotype long format.")
    ap.add_argument("--input-csv", type=Path, required=True)
    ap.add_argument("--sample-col", type=str, default="sample_id")
    ap.add_argument("--rsid-col", type=str, default="rsid")
    ap.add_argument("--rsid-list-col", type=str, default="rsid_list")
    ap.add_argument("--genotype-col", type=str, default="genotype")
    ap.add_argument("--output-csv", type=Path, default=Path("tmp/bio_genotype_long_v1.csv"))
    ap.add_argument(
        "--output-report",
        type=Path,
        default=Path("reports/bio_genotype_normalize_long_v1_latest.json"),
    )
    ns = ap.parse_args()

    with ns.input_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        if ns.sample_col not in fields:
            raise ValueError(f"missing sample column: {ns.sample_col}")
        rows = list(reader)

    out: list[dict[str, str]] = []
    invalid_rows = 0
    for row in rows:
        sid = str(row.get(ns.sample_col) or "").strip()
        if not sid:
            invalid_rows += 1
            continue
        rsid = str(row.get(ns.rsid_col) or "").strip().lower()
        genotype = str(row.get(ns.genotype_col) or "").strip().upper()
        if rsid.startswith("rs"):
            out.append({"sample_id": sid, "rsid": rsid, "genotype": genotype})
            continue
        rsid_list = str(row.get(ns.rsid_list_col) or "")
        split_rsids = _split_rsids(rsid_list)
        if not split_rsids:
            invalid_rows += 1
            continue
        for r in split_rsids:
            out.append({"sample_id": sid, "rsid": r, "genotype": genotype})

    ns.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with ns.output_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "rsid", "genotype"])
        w.writeheader()
        w.writerows(out)

    uniq_samples = {r["sample_id"] for r in out}
    uniq_rsids = {r["rsid"] for r in out}
    report = {
        "schema": "bio_genotype_normalize_long_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {"input_csv": str(ns.input_csv.resolve())},
        "summary": {
            "input_rows": len(rows),
            "output_rows": len(out),
            "distinct_sample_id": len(uniq_samples),
            "distinct_rsid": len(uniq_rsids),
            "invalid_or_skipped_rows": invalid_rows,
        },
        "outputs": {"output_csv": str(ns.output_csv.resolve())},
    }
    ns.output_report.parent.mkdir(parents=True, exist_ok=True)
    ns.output_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_csv.resolve()} rows={len(out)}")
    print(f"WROTE: {ns.output_report.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
