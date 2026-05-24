#!/usr/bin/env python3
"""Manifest + stats for full-NT TR Greek JSONL (honza ingest, B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "data/logos/manuscripts/tr_greek_by_verse_v1.full_nt.jsonl"
DEFAULT_GAP_POLICY = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_tr_nt_corpus_manifest_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_IN)
    ap.add_argument("--gap-policy-jsonl", type=Path, default=DEFAULT_GAP_POLICY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.input_jsonl.is_file():
        print(f"missing {args.input_jsonl} — run ingest_tr_greek_from_honza_v1.py --full-nt", file=sys.stderr)
        return 2

    gap_ids: set[str] = set()
    if args.gap_policy_jsonl.is_file():
        for line in args.gap_policy_jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                gap_ids.add(str(json.loads(line)["verse_id"]))

    books: Counter[str] = Counter()
    n = 0
    gap_hits = 0
    for line in args.input_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        n += 1
        vid = str(row["verse_id"])
        books[vid.split(".", 1)[0]] += 1
        if vid in gap_ids:
            gap_hits += 1

    doc = {
        "schema": "logos_tr_nt_corpus_manifest_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "row_count": n,
        "book_counts": dict(sorted(books.items())),
        "gap_policy_hits": gap_hits,
        "gap_policy_total": len(gap_ids),
        "input_jsonl": str(args.input_jsonl.relative_to(ROOT)).replace("\\", "/"),
        "track_wall": {"merge_into_complete_jsonl": False},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} rows={n} gap_hits={gap_hits}/{len(gap_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
