#!/usr/bin/env python3
"""Compare verse_decoded_v2 (BHS+SBLGNT) vs verse_4pipeline_full_31102 (MT canon SSOT).

Fixes boundary facts for Track B: gap verses are upstream coverage, not Phase-1 4D drops.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FULL = ROOT / "data" / "logos" / "verse_4pipeline_full_31102.json"
DEFAULT_V2 = ROOT / "data" / "logos" / "verse_decoded_v2.jsonl"
DEFAULT_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "logos_verse_canon_coverage_diff_v1_latest.json"

ARTIFACT_SCHEMA = "logos_verse_canon_coverage_diff_v1"
VERSION = "1.0.0"

OT_BOOKS = frozenset(
    {
        "Gen",
        "Exod",
        "Lev",
        "Num",
        "Deut",
        "Josh",
        "Judg",
        "Ruth",
        "1Sam",
        "2Sam",
        "1Kgs",
        "2Kgs",
        "1Chr",
        "2Chr",
        "Ezra",
        "Neh",
        "Esth",
        "Job",
        "Ps",
        "Prov",
        "Eccl",
        "Song",
        "Isa",
        "Jer",
        "Lam",
        "Ezek",
        "Dan",
        "Hos",
        "Joel",
        "Amos",
        "Obad",
        "Jonah",
        "Mic",
        "Nah",
        "Hab",
        "Zeph",
        "Hag",
        "Zech",
        "Mal",
    }
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def _book_from_verse_id(verse_id: str) -> str:
    return verse_id.split(".", 1)[0] if verse_id else ""


def _testament(book: str) -> str:
    return "OT" if book in OT_BOOKS else "NT"


def _load_full_ids(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("full canon input must be a top-level JSON array")
    ids: set[str] = set()
    for row in data:
        if not isinstance(row, dict):
            continue
        vid = row.get("verse_id")
        if isinstance(vid, str) and vid.strip():
            ids.add(vid.strip())
    return ids


def _load_v2(path: Path) -> tuple[set[str], Counter[str]]:
    ids: set[str] = set()
    editions: Counter[str] = Counter()
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            vid = row.get("verse_id")
            if isinstance(vid, str) and vid.strip():
                ids.add(vid.strip())
            ed = row.get("edition") or row.get("source_edition") or "unknown"
            editions[str(ed)] += 1
    return ids, editions


def build_report(
    *,
    full_path: Path,
    v2_path: Path,
    include_missing_ids: bool = True,
) -> dict[str, Any]:
    full_ids = _load_full_ids(full_path)
    v2_ids, editions = _load_v2(v2_path)

    only_full = sorted(full_ids - v2_ids)
    only_v2 = sorted(v2_ids - full_ids)
    both = full_ids & v2_ids

    gap_by_book = Counter(_book_from_verse_id(vid) for vid in only_full)
    gap_by_testament = Counter(_testament(_book_from_verse_id(vid)) for vid in only_full)

    return {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "purpose": "Transparent verse_id boundary between MT 31,102 SSOT and verse_decoded_v2 (BHS+SBLGNT).",
        "inputs": {
            "full_canon_json": _rel(full_path),
            "full_canon_sha256": _sha256_file(full_path),
            "verse_decoded_v2_jsonl": _rel(v2_path),
            "verse_decoded_v2_sha256": _sha256_file(v2_path),
        },
        "counts": {
            "full_canon_verse_count": len(full_ids),
            "verse_decoded_v2_count": len(v2_ids),
            "intersection_count": len(both),
            "only_in_full_count": len(only_full),
            "only_in_v2_count": len(only_v2),
            "gap_count": len(only_full),
        },
        "verse_decoded_v2_editions": dict(sorted(editions.items())),
        "gap_by_testament": dict(sorted(gap_by_testament.items())),
        "gap_by_book": [
            {"book": book, "count": count}
            for book, count in gap_by_book.most_common()
        ],
        "interpretation": {
            "phase1_logos_verse_4d_rows_dropped": 0,
            "phase1_manifest": "docs/final/artifacts/logos_verse_4d_corpus_v1_latest.json",
            "gap_cause": "upstream_coverage_not_phase1_filter",
            "accurate_framing_ko": (
                "정경 31,102절 SSOT 대비 verse_decoded_v2(BHS+SBLGNT)에 없는 "
                f"{len(only_full)}절; Track B 구절 4D/그래프는 {len(v2_ids)}행 범위."
            ),
        },
        "track_wall": {
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
        },
        **(
            {"missing_verse_ids": only_full}
            if include_missing_ids
            else {"missing_verse_ids_omitted": True}
        ),
        **({"extra_in_v2_verse_ids": only_v2} if only_v2 else {}),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--full", type=Path, default=DEFAULT_FULL)
    ap.add_argument("--v2", type=Path, default=DEFAULT_V2)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--omit-missing-ids",
        action="store_true",
        help="Skip embedding full missing_verse_ids list (counts/aggregates only).",
    )
    args = ap.parse_args()

    if not args.full.is_file():
        print(f"missing full canon: {args.full}", file=sys.stderr)
        return 2
    if not args.v2.is_file():
        print(f"missing verse_decoded_v2: {args.v2}", file=sys.stderr)
        return 2

    report = build_report(
        full_path=args.full,
        v2_path=args.v2,
        include_missing_ids=not args.omit_missing_ids,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    c = report["counts"]
    print(
        f"wrote {args.output} "
        f"full={c['full_canon_verse_count']} v2={c['verse_decoded_v2_count']} "
        f"gap={c['gap_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
