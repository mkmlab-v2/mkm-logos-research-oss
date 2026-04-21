#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.85, L:0.5, K:0.75, M:0.35}
# Balance: 86
# Purpose: Export paper-level SNP columns from consolidated labels CSV to JSON for downstream gates.
# Keywords: bio, measured-labels, europepmc, sidecar, json, snp
"""Export PMID-keyed SNP sidecar JSON from bio_measured_labels consolidated CSV (v3)."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "bio_measured_labels_paper_snp_sidecar_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build paper SNP sidecar JSON from consolidated labels CSV.")
    ap.add_argument(
        "--input-csv",
        type=Path,
        default=Path("tmp/bio_measured_labels_consolidated_v3.csv"),
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/final/artifacts/bio_measured_labels_paper_snp_sidecar_v1.json"),
    )
    ns = ap.parse_args()

    if not ns.input_csv.exists():
        raise FileNotFoundError(str(ns.input_csv))

    with ns.input_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    by_pmid: dict[str, dict[str, Any]] = {}
    for r in rows:
        pmid = str(r.get("pmid") or "").strip()
        if not pmid.isdigit():
            continue
        rec = {
            "pmid": pmid,
            "doi": str(r.get("doi") or "").strip() or None,
            "publication_year": str(r.get("publication_year") or "").strip() or None,
            "paper_title": str(r.get("paper_title") or "").strip() or None,
            "pmcid": str(r.get("pmcid") or "").strip() or None,
            "snp_ids_final": str(r.get("snp_ids_final") or "").strip() or None,
            "epmc_refsnp_ids": str(r.get("epmc_refsnp_ids") or "").strip() or None,
            "snp_ids_final_v2": str(r.get("snp_ids_final_v2") or "").strip() or None,
            "epmc_catalog_refsnp_ids": str(r.get("epmc_catalog_refsnp_ids") or "").strip() or None,
            "snp_ids_final_v3": str(r.get("snp_ids_final_v3") or "").strip() or None,
        }
        by_pmid[pmid] = rec

    records = list(by_pmid.values())
    records.sort(key=lambda x: int(str(x["pmid"])))

    rows_with_pmid = sum(1 for x in rows if str(x.get("pmid") or "").strip().isdigit())
    with_any = sum(1 for x in records if (x.get("snp_ids_final_v3") or "").strip())

    payload = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "meta": {
            "source_csv": str(ns.input_csv.resolve()),
            "rows_in_csv": len(rows),
            "rows_with_numeric_pmid": rows_with_pmid,
            "unique_pmids": len(records),
            "rows_skipped_no_numeric_pmid": len(rows) - rows_with_pmid,
            "rows_collapsed_duplicate_pmid": max(0, rows_with_pmid - len(records)),
            "rows_with_snp_ids_final_v3": with_any,
        },
        "records": records,
    }

    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} unique_pmids={len(records)} with_v3_snp={with_any}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
