#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.84, L:0.72, K:0.78, M:0.44}
# Balance: 87
# Purpose: Build PMID-keyed paper SNP sidecar JSON from PDF spike JSONL by extracting PMID/rsID mentions.
# Keywords: bio, SNP, sidecar, pdf, jsonl, pmid, rsid
"""Convert PDF spike JSONL into bio paper SNP sidecar JSON (PMID/rsID heuristic extraction)."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = "bio_measured_labels_paper_snp_sidecar_v1"
_PMID_RE = re.compile(r"\bPMID\s*[:#]?\s*([0-9]{5,9})\b", flags=re.IGNORECASE)
_PMID_FALLBACK_RE = re.compile(r"\b([0-9]{7,9})\b")
_RS_RE = re.compile(r"\brs[0-9]{2,}\b", flags=re.IGNORECASE)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _extract_pmids(text: str, allow_fallback: bool = False) -> list[str]:
    pmids = _PMID_RE.findall(text or "")
    if pmids:
        return pmids
    # Optional fallback for corpora without explicit "PMID" label.
    if allow_fallback and len(text or "") >= 120:
        return _PMID_FALLBACK_RE.findall(text or "")
    return []


def _extract_rsids(text: str) -> list[str]:
    return [x.lower() for x in _RS_RE.findall(text or "")]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build paper SNP sidecar JSON from PDF spike JSONL.")
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("tmp/bio_measured_labels_paper_snp_sidecar_from_pdf_v1.json"),
    )
    ap.add_argument(
        "--output-doc-map-csv",
        type=Path,
        default=Path("tmp/bio_pdf_doc_pmid_map_v1.csv"),
    )
    ap.add_argument(
        "--min-rsid-per-paper",
        type=int,
        default=1,
        help="Keep papers with at least this many distinct rsIDs.",
    )
    ap.add_argument(
        "--allow-pmid-fallback",
        action="store_true",
        help="Allow unlabeled 7~9 digit numbers as PMID candidates (off by default).",
    )
    ns = ap.parse_args()

    rows = _iter_jsonl(ns.input_jsonl)
    by_doc_text: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        source_pdf = str(row.get("source_pdf") or "").strip()
        text = str(row.get("text") or "")
        if not source_pdf or not text.strip():
            continue
        by_doc_text[source_pdf].append(text)

    records: list[dict[str, Any]] = []
    doc_rows: list[tuple[str, str, int, int]] = []
    for source_pdf, chunks in sorted(by_doc_text.items()):
        pmid_counter: Counter[str] = Counter()
        rs_set: set[str] = set()
        for chunk in chunks:
            pmid_counter.update(_extract_pmids(chunk, allow_fallback=bool(ns.allow_pmid_fallback)))
            rs_set.update(_extract_rsids(chunk))

        chosen_pmid = pmid_counter.most_common(1)[0][0] if pmid_counter else ""
        rs_sorted = sorted(rs_set)
        doc_rows.append((source_pdf, chosen_pmid, len(rs_sorted), len(chunks)))
        if not chosen_pmid.isdigit():
            continue
        if len(rs_sorted) < int(ns.min_rsid_per_paper):
            continue

        records.append(
            {
                "pmid": chosen_pmid,
                "doi": None,
                "publication_year": None,
                "paper_title": source_pdf,
                "pmcid": None,
                "snp_ids_final": ",".join(rs_sorted) if rs_sorted else None,
                "epmc_refsnp_ids": None,
                "snp_ids_final_v2": None,
                "epmc_catalog_refsnp_ids": None,
                "snp_ids_final_v3": ",".join(rs_sorted) if rs_sorted else None,
            }
        )

    # De-duplicate by PMID (keep longest rs list).
    by_pmid: dict[str, dict[str, Any]] = {}
    for rec in records:
        pmid = str(rec.get("pmid") or "")
        prev = by_pmid.get(pmid)
        if prev is None:
            by_pmid[pmid] = rec
            continue
        prev_rs = str(prev.get("snp_ids_final_v3") or "")
        now_rs = str(rec.get("snp_ids_final_v3") or "")
        if len(now_rs) > len(prev_rs):
            by_pmid[pmid] = rec
    final_records = sorted(by_pmid.values(), key=lambda x: int(str(x["pmid"])))

    payload = {
        "schema": _SCHEMA,
        "generated_at_utc": _utc_now(),
        "meta": {
            "source": "pdf_spike_jsonl_heuristic_v1",
            "input_jsonl": str(ns.input_jsonl.resolve()),
            "rows_in_jsonl": len(rows),
            "distinct_source_pdf": len(by_doc_text),
            "records_out": len(final_records),
            "min_rsid_per_paper": int(ns.min_rsid_per_paper),
            "allow_pmid_fallback": bool(ns.allow_pmid_fallback),
            "note": "Heuristic extraction from PDF text; validate before production joins.",
        },
        "records": final_records,
    }

    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ns.output_doc_map_csv.parent.mkdir(parents=True, exist_ok=True)
    ns.output_doc_map_csv.write_text(
        "source_pdf,pmid_candidate,distinct_rsid_count,chunk_count\n"
        + "".join(f"{a},{b},{c},{d}\n" for a, b, c, d in doc_rows),
        encoding="utf-8",
    )

    print(f"WROTE: {ns.output_json.resolve()} records={len(final_records)}", flush=True)
    print(f"WROTE: {ns.output_doc_map_csv.resolve()} docs={len(doc_rows)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
