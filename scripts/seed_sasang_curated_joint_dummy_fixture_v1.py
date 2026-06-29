#!/usr/bin/env python3
"""Append [DUMMY] curated JSONL + review-queue CSV rows for promote drill E2E [HYPO]."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
JSONL_IN = ROOT / "data/myeongni/curated_saju_joint_v1.jsonl"
CSV_QUEUE = ROOT / "data/myeongni/sasang_saju_joint_review_queue_v1.csv"
OUT = ROOT / "reports/sasang_curated_joint_dummy_seed_v1_latest.json"

CSV_HEADER = [
    "pmid",
    "pubYear",
    "title",
    "europepmc_url",
    "relevance_tier",
    "relevance_score",
    "birth_instant_utc",
    "iana_tz",
    "is_male",
    "sasang_label_ko",
    "sasang_label_en",
    "quote_from_paper",
    "curator_ok",
    "notes",
]


def _utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _build_rows(suffix: str) -> tuple[dict[str, Any], dict[str, str]]:
    jsonl_row = {
        "person_id": f"dummy_sasang_rail_jsonl_{suffix}",
        "display_name": f"[DUMMY] MKM Sasang rail JSONL fixture {suffix}",
        "dob_utc": "1992-07-14T09:00:00Z",
        "iana_tz": "Asia/Seoul",
        "is_male": True,
        "provenance_url": f"https://example.invalid/mkm/sasang-rail-dummy/{suffix}",
        "source_citation": "[DUMMY] MKM workspace auto-seed — not a real person",
        "sasang_label_ko": "태음인",
        "sasang_label_en": "Tae-Eum",
        "literature_catalog_pmids": [f"DUMMYJSONL{suffix}"],
        "provenance": "dummy_fixture_auto_seed_v1",
        "note": "[HYPO] seed_sasang_curated_joint_dummy_fixture_v1.py",
    }
    csv_row = {
        "pmid": f"DUMMYCSV{suffix}",
        "pubYear": "2026",
        "title": f"[DUMMY] MKM Sasang rail CSV fixture {suffix}",
        "europepmc_url": "",
        "relevance_tier": "high",
        "relevance_score": "1.0",
        "birth_instant_utc": "1991-12-08T00:00:00Z",
        "iana_tz": "Asia/Seoul",
        "is_male": "y",
        "sasang_label_ko": "소음인",
        "sasang_label_en": "So-Eum",
        "quote_from_paper": "[DUMMY] auto-seed fixture quote",
        "curator_ok": "y",
        "notes": "[HYPO] auto P7 seed",
    }
    return jsonl_row, csv_row


def _append_jsonl(row: dict[str, Any]) -> None:
    JSONL_IN.parent.mkdir(parents=True, exist_ok=True)
    with JSONL_IN.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _append_csv(row: dict[str, str]) -> None:
    CSV_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    if CSV_QUEUE.is_file():
        with CSV_QUEUE.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or CSV_HEADER
    else:
        fieldnames = CSV_HEADER
    write_header = not CSV_QUEUE.is_file() or CSV_QUEUE.stat().st_size == 0
    with CSV_QUEUE.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--suffix", default="", help="Fixture id suffix (default: UTC compact timestamp).")
    ap.add_argument("--apply-promote", action="store_true", help="Run P6 chain with --apply-promote after seed.")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    suffix = str(args.suffix or _utc_compact()).replace(" ", "")[:24]
    jsonl_row, csv_row = _build_rows(suffix)
    _append_jsonl(jsonl_row)
    _append_csv(csv_row)

    doc: dict[str, Any] = {
        "schema": "sasang_curated_joint_dummy_seed_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "suffix": suffix,
        "jsonl_person_id": jsonl_row["person_id"],
        "csv_pmid": csv_row["pmid"],
        "csv_person_id_expected": f"curated_csv_pmid_{csv_row['pmid']}",
        "paths": {
            "jsonl_input": str(JSONL_IN).replace("\\", "/"),
            "csv_queue": str(CSV_QUEUE).replace("\\", "/"),
        },
        "apply_promote_requested": args.apply_promote,
        "apply_ok": None,
    }

    if args.apply_promote:
        proc = subprocess.run(
            [PY, str(ROOT / "scripts/run_sasang_rail_p6_chain_v1.py"), "--apply-promote", "--skip-pytest"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        doc["apply_exit_code"] = proc.returncode
        doc["apply_ok"] = proc.returncode == 0
        doc["apply_stdout_tail"] = (proc.stdout or "")[-400:]
        if proc.returncode != 0:
            doc["apply_stderr_tail"] = (proc.stderr or "")[-300:]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "suffix": suffix, "apply_ok": doc.get("apply_ok")}, ensure_ascii=False))
    return 0 if doc.get("apply_ok") is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
