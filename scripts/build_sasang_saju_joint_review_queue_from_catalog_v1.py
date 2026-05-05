#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build curator CSV + joint-benchmark stub JSONL from a filtered literature catalog JSONL.

Reads rows with schema ``sasang_saju_literature_catalog_row_v1`` (optionally with relevance_* fields).
Does not invent birth times or Sasang labels — stubs are for human completion only.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "data" / "myeongni" / "sasang_saju_literature_catalog_strict_high_signal_v1.jsonl"
DEFAULT_CSV = ROOT / "data" / "myeongni" / "sasang_saju_joint_review_queue_v1.csv"
DEFAULT_JSONL = ROOT / "data" / "myeongni" / "sasang_saju_joint_stub_rows_from_catalog_v1.jsonl"


def _stub_row(catalog_row: dict[str, Any], *, catalog_path: str) -> dict[str, Any]:
    pmid = str(catalog_row.get("pmid") or "").strip()
    title = str(catalog_row.get("title") or "").strip()
    return {
        "schema": "sasang_saju_joint_benchmark_row_v1",
        "person_id": f"literature_pmid_{pmid}" if pmid else "literature_pmid_unknown",
        "display_name": title[:200] + ("…" if len(title) > 200 else ""),
        "benchmark_tier": "pending_human_merge",
        "privacy_tier": "literature_only_until_birth_verified",
        "provenance": (
            f"Auto stub from catalog row pmid={pmid}; file={catalog_path}. "
            "Fill sasang_constitution.source.quote from paper; birth_resolution only from verified public or authorized cohort cell."
        ),
        "sasang_constitution": None,
        "birth_resolution": None,
        "literature_catalog_pmids": [pmid] if pmid else [],
        "literature_catalog_snapshot": {
            "title": title,
            "pubYear": catalog_row.get("pubYear"),
            "europepmc_url": str(catalog_row.get("europepmc_url") or ""),
            "relevance_tier": catalog_row.get("relevance_tier"),
            "relevance_score": catalog_row.get("relevance_score"),
        },
        "expectations": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out-csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--max-rows", type=int, default=80)
    args = ap.parse_args()

    if not args.inp.is_file():
        print(f"Missing input: {args.inp}", file=sys.stderr)
        return 2

    max_rows = max(1, int(args.max_rows))
    stubs: list[dict[str, Any]] = []
    cat_path = str(args.inp.resolve())

    for line in args.inp.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if str(row.get("schema") or "") != "sasang_saju_literature_catalog_row_v1":
            continue
        if not str(row.get("pmid") or "").strip():
            continue
        stubs.append(_stub_row(row, catalog_path=cat_path))
        if len(stubs) >= max_rows:
            break

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
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
    with args.out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for s in stubs:
            snap = s.get("literature_catalog_snapshot") or {}
            pmid = (s.get("literature_catalog_pmids") or [""])[0]
            w.writerow(
                {
                    "pmid": pmid,
                    "pubYear": snap.get("pubYear") or "",
                    "title": snap.get("title") or "",
                    "europepmc_url": snap.get("europepmc_url") or "",
                    "relevance_tier": snap.get("relevance_tier") or "",
                    "relevance_score": snap.get("relevance_score") if snap.get("relevance_score") is not None else "",
                    "birth_instant_utc": "",
                    "iana_tz": "",
                    "is_male": "",
                    "sasang_label_ko": "",
                    "sasang_label_en": "",
                    "quote_from_paper": "",
                    "curator_ok": "",
                    "notes": "",
                }
            )

    with args.out_jsonl.open("w", encoding="utf-8") as f:
        for s in stubs:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "schema": "sasang_saju_joint_review_queue_build_v1",
                "rows": len(stubs),
                "out_csv": str(args.out_csv.resolve()),
                "out_jsonl": str(args.out_jsonl.resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
