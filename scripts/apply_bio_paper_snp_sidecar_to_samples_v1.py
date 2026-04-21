#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.86, L:0.78, K:0.79, M:0.46}
# Balance: 87
# Purpose: Join PMID-keyed paper SNP sidecar onto sample_id rows using explicit mapping (constitution-gated).
# Keywords: bio, SNP, sidecar, cohort, join, CSV
"""Add paper-level SNP columns to a sample CSV using sidecar + sample_id↔pmid mapping."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from spec_bio_sample_paper_snp_join_gate_v1 import check_join_gate

SCHEMA = "bio_paper_snp_sidecar_sample_join_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_pmid_to_record(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for rec in data.get("records") or []:
        if not isinstance(rec, dict):
            continue
        pmid = str(rec.get("pmid") or "").strip()
        if pmid.isdigit():
            out[pmid] = rec
    return out


def _load_sample_to_pmid(path: Path) -> dict[str, str]:
    """sample_id -> pmid digits."""
    out: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        fp = "paper_pmid" if "paper_pmid" in fields else "pmid"
        if "sample_id" not in fields:
            raise ValueError("mapping CSV must include sample_id")
        if fp not in fields:
            raise ValueError("mapping CSV must include pmid or paper_pmid")
        for row in reader:
            sid = str(row.get("sample_id") or "").strip()
            pm = str(row.get(fp) or "").strip()
            if not sid:
                continue
            pm = "".join(ch for ch in pm if ch.isdigit())
            if pm.isdigit():
                out[sid] = pm
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Join paper SNP sidecar onto samples via mapping CSV.")
    ap.add_argument("--samples-csv", type=Path, required=True)
    ap.add_argument(
        "--sidecar-json",
        type=Path,
        default=Path("docs/final/artifacts/bio_measured_labels_paper_snp_sidecar_v1.json"),
    )
    ap.add_argument("--mapping-csv", type=Path, required=True)
    ap.add_argument(
        "--output-csv",
        type=Path,
        default=Path("tmp/bio_cohort_with_paper_snp_sidecar_v1.csv"),
    )
    ap.add_argument(
        "--output-report",
        type=Path,
        default=Path("reports/bio_paper_snp_sidecar_sample_join_v1_latest.json"),
    )
    ap.add_argument(
        "--skip-gate",
        action="store_true",
        help="Unsafe: skip constitution join gate (not recommended).",
    )
    ns = ap.parse_args()

    if not ns.skip_gate:
        code, msg = check_join_gate(ns.mapping_csv, ns.sidecar_json)
        if code != 0:
            print(f"BLOCKED: {msg}", file=sys.stderr)
            return code

    if not ns.samples_csv.is_file():
        print(f"missing samples: {ns.samples_csv}", file=sys.stderr)
        return 1

    by_pmid = _load_pmid_to_record(ns.sidecar_json)
    sample_pmid = _load_sample_to_pmid(ns.mapping_csv)

    extra_cols = [
        "paper_pmid",
        "paper_snp_ids_final_v3",
        "paper_epmc_refsnp_ids",
        "paper_epmc_catalog_refsnp_ids",
    ]

    with ns.samples_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames_in = list(reader.fieldnames or [])
        rows = list(reader)

    if "sample_id" not in fieldnames_in:
        print("samples-csv must include sample_id", file=sys.stderr)
        return 1

    out_fields = fieldnames_in + [c for c in extra_cols if c not in fieldnames_in]
    n_matched = 0
    n_snp_nonempty = 0
    out_rows: list[dict[str, str]] = []
    for row in rows:
        r = {k: str(v) for k, v in row.items()}
        sid = str(r.get("sample_id") or "").strip()
        pmid = sample_pmid.get(sid, "")
        rec = by_pmid.get(pmid) if pmid else None
        r["paper_pmid"] = pmid
        if rec:
            n_matched += 1
            v3 = str(rec.get("snp_ids_final_v3") or "").strip()
            r["paper_snp_ids_final_v3"] = v3
            r["paper_epmc_refsnp_ids"] = str(rec.get("epmc_refsnp_ids") or "").strip()
            r["paper_epmc_catalog_refsnp_ids"] = str(rec.get("epmc_catalog_refsnp_ids") or "").strip()
            if v3:
                n_snp_nonempty += 1
        else:
            r["paper_snp_ids_final_v3"] = ""
            r["paper_epmc_refsnp_ids"] = ""
            r["paper_epmc_catalog_refsnp_ids"] = ""
        out_rows.append(r)

    ns.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with ns.output_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)

    report = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "inputs": {
            "samples_csv": str(ns.samples_csv.resolve()),
            "sidecar_json": str(ns.sidecar_json.resolve()),
            "mapping_csv": str(ns.mapping_csv.resolve()),
            "skip_gate": bool(ns.skip_gate),
        },
        "summary": {
            "output_rows": len(out_rows),
            "mapping_distinct_samples": len(sample_pmid),
            "rows_with_paper_pmid": n_matched,
            "rows_with_nonempty_paper_snp_v3": n_snp_nonempty,
        },
        "outputs": {
            "output_csv": str(ns.output_csv.resolve()),
        },
        "note": "paper_* columns are literature-mined; not per-subject genotyping. No 12-state reweighting here.",
    }
    ns.output_report.parent.mkdir(parents=True, exist_ok=True)
    ns.output_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"WROTE: {ns.output_csv.resolve()} rows={len(out_rows)} "
        f"with_pmid={n_matched} with_snp_v3={n_snp_nonempty}",
        flush=True,
    )
    print(f"WROTE: {ns.output_report.resolve()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())