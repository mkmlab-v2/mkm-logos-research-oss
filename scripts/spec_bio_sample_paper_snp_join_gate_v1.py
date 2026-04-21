#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.84, L:0.76, K:0.81, M:0.44}
# Balance: 88
# Purpose: Refuse naive PMID-keyed SNP sidecar joins to per-sample cohort rows without explicit mapping (constitution boundary).
# Keywords: bio-sasang, SNP, sidecar, PMID, gate, constitution
"""Join gate: PMID paper sidecar vs sample_id cohort — mapping required."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def _has_cols(path: Path, required: set[str]) -> bool:
    with path.open("r", encoding="utf-8", newline="") as f:
        row = next(csv.reader(f), None)
    if not row:
        return False
    fields = {str(x).strip() for x in row}
    return required <= fields


def mapping_columns_ok(path: Path) -> bool:
    req = {"sample_id", "pmid"}
    alt = {"sample_id", "paper_pmid"}
    return _has_cols(path, req) or _has_cols(path, alt)


def check_join_gate(mapping_csv: Path | None, sidecar_json: Path) -> tuple[int, str]:
    """Return (exit_code, message) for other scripts. 0=ok, 1=missing input, 2=blocked."""
    if not sidecar_json.is_file():
        return 1, f"missing sidecar: {sidecar_json}"
    if mapping_csv is None or not mapping_csv.is_file():
        return 2, "mapping_csv required (sample_id + pmid or paper_pmid)"
    if not mapping_columns_ok(mapping_csv):
        return 2, "mapping must include sample_id and pmid (or paper_pmid)"
    return 0, f"OK mapping={mapping_csv.resolve()}"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Block unsafe joins between PMID SNP sidecar and sample-level CSV without mapping.",
    )
    ap.add_argument(
        "--sidecar-json",
        type=Path,
        default=Path("docs/final/artifacts/bio_measured_labels_paper_snp_sidecar_v1.json"),
    )
    ap.add_argument(
        "--samples-csv",
        type=Path,
        default=Path("tmp/fireprotdb_ddg_only_v1.csv"),
        help="Cohort CSV with sample_id (existence check only).",
    )
    ap.add_argument(
        "--mapping-csv",
        type=Path,
        default=None,
        help="Must include sample_id + pmid (or doi) columns to authorize join.",
    )
    ap.add_argument(
        "--explain-only",
        action="store_true",
        help="Print policy and exit 0.",
    )
    ns = ap.parse_args()

    if ns.explain_only:
        print(
            "CONSTITUTION BOUNDARY: bio_measured_labels_paper_snp_sidecar_v1.json is PMID-keyed. "
            "FireProt / ax cohort rows are sample_id-keyed. "
            "Join only with an explicit mapping table (sample_id ↔ pmid/doi). "
            "Do not merge canon/B proxy corpus into cohort classification (see KOREAN_MEDICAL_CANON_INGEST_HANDOFF).",
            flush=True,
        )
        return 0

    code, msg = check_join_gate(ns.mapping_csv, ns.sidecar_json)
    if code == 1:
        print(msg, file=sys.stderr)
        return 1
    if code == 2:
        print(f"JOIN_GATE_BLOCKED: {msg}", file=sys.stderr)
        return 2

    data = json.loads(ns.sidecar_json.read_text(encoding="utf-8"))
    if str(data.get("schema") or "") != "bio_measured_labels_paper_snp_sidecar_v1":
        print("warning: unexpected sidecar schema", file=sys.stderr)

    if ns.samples_csv.is_file() and not _has_cols(ns.samples_csv, {"sample_id"}):
        print(f"warning: {ns.samples_csv} may lack sample_id column", file=sys.stderr)

    print(f"JOIN_GATE_OK mapping={ns.mapping_csv.resolve()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
