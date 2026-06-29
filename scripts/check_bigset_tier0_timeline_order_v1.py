#!/usr/bin/env python3
"""BigSet Tier-0 timeline ordering gate — verse_ref monotonicity per conflict group [HYPO].

Persly-style longitudinal harness analog: rows within a conflict_group_id must not
invert canonical verse order when read top-to-bottom (CSV ingest order).

Reproducible (offline):
  py scripts/check_bigset_tier0_timeline_order_v1.py --csv tests/fixtures/bigset/sample_theology_tier0_rows_v1.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/bigset_tier0_timeline_order_v1_latest.json"

# Minimal Protestant canon prefix map for Tier-0 theology ingest.
BOOK_ORDER: dict[str, int] = {
    "GEN": 1,
    "GENESIS": 1,
    "EX": 2,
    "EXOD": 2,
    "EXODUS": 2,
    "LEV": 3,
    "LEVITICUS": 3,
    "NUM": 4,
    "NUMBERS": 4,
    "DEUT": 5,
    "DEUTERONOMY": 5,
}

VERSE_PATTERNS = (
    re.compile(
        r"(?i)^\s*([A-Za-z]+)\s*\.?\s*(\d+)\s*:\s*(\d+)",
    ),
    re.compile(
        r"(?i)^\s*([A-Za-z]+)\s+(\d+)\s*:\s*(\d+)",
    ),
    re.compile(
        r"(?i)^\s*([A-Za-z]+)\s*\.\s*(\d+)\s*\.\s*(\d+)",
    ),
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def parse_verse_sort_key(verse_ref: str) -> tuple[int, int, int] | None:
    text = (verse_ref or "").strip()
    if not text:
        return None
    for pat in VERSE_PATTERNS:
        m = pat.match(text)
        if not m:
            continue
        book_raw, chapter_s, verse_s = m.group(1), m.group(2), m.group(3)
        book_key = book_raw.upper().replace(".", "")
        book_ord = BOOK_ORDER.get(book_key)
        if book_ord is None:
            return None
        return (book_ord, int(chapter_s), int(verse_s))
    return None


def evaluate(rows: list[dict[str, str]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    unparsed = 0
    for i, row in enumerate(rows):
        gid = str(row.get("conflict_group_id") or "").strip() or "__ungrouped__"
        key = parse_verse_sort_key(str(row.get("verse_ref") or ""))
        if key is None:
            unparsed += 1
        entry = {
            "row_index": i,
            "verse_ref": row.get("verse_ref"),
            "sort_key": list(key) if key else None,
        }
        groups.setdefault(gid, []).append(entry)

    inversions: list[dict[str, Any]] = []
    for gid, items in groups.items():
        prev_key: tuple[int, int, int] | None = None
        prev_idx: int | None = None
        for item in items:
            key_tuple = item.get("sort_key")
            if key_tuple is None:
                continue
            key = tuple(key_tuple)
            if prev_key is not None and key < prev_key:
                inversions.append(
                    {
                        "conflict_group_id": gid,
                        "prior_row_index": prev_idx,
                        "row_index": item["row_index"],
                        "prior_sort_key": list(prev_key),
                        "sort_key": list(key),
                    }
                )
            prev_key = key
            prev_idx = item["row_index"]

    parseable = sum(1 for r in rows if parse_verse_sort_key(str(r.get("verse_ref") or "")) is not None)
    inversion_count = len(inversions)
    gate_ok = inversion_count == 0
    return {
        "schema": "bigset_tier0_timeline_order_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "row_count": len(rows),
        "parseable_verse_ref_count": parseable,
        "unparsed_verse_ref_count": unparsed,
        "inversion_count": inversion_count,
        "gate_ok": gate_ok,
        "inversions": inversions,
        "groups_sample": [
            {"conflict_group_id": gid, "row_count": len(items)} for gid, items in list(groups.items())[:10]
        ],
        "reproduce": "py scripts/check_bigset_tier0_timeline_order_v1.py --csv <tier0.csv>",
        "tier0_ref": "docs/research/raw/persly_emr_longitudinal_harness_tier0_2026-06-24.md",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.csv.is_file():
        print(json.dumps({"ok": False, "error": f"missing csv: {args.csv}"}), file=sys.stderr)
        return 2

    rows = _read_rows(args.csv)
    result = evaluate(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": result["gate_ok"],
                "gate_ok": result["gate_ok"],
                "inversion_count": result["inversion_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
