#!/usr/bin/env python3
"""Export gap verses (MT canon minus verse_decoded_v2) as ingest backlog JSONL.

Reads missing_verse_ids from logos_verse_canon_coverage_diff_v1_latest.json and
joins rows from verse_4pipeline_full_31102.json. Track B / [HYPO] only — no ingest.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIFF = ROOT / "reports/constitution/btrack_pilot/logos_verse_canon_coverage_diff_v1_latest.json"
DEFAULT_FULL = ROOT / "data/logos/verse_4pipeline_full_31102.json"
DEFAULT_OUT = ROOT / "reports/constitution/btrack_pilot/logos_verse_gap_ingest_queue_v1_latest.jsonl"
DEFAULT_META = ROOT / "docs/final/artifacts/logos_verse_gap_ingest_queue_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _iter_full_rows(path: Path) -> Iterator[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    data = json.loads(text)
    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                yield row
        return
    if isinstance(data, dict):
        for key in ("verses", "rows", "data"):
            block = data.get(key)
            if isinstance(block, list):
                for row in block:
                    if isinstance(row, dict):
                        yield row
                return
    raise ValueError(f"unsupported full canon shape: {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--coverage-diff", type=Path, default=DEFAULT_DIFF)
    ap.add_argument("--full-json", type=Path, default=DEFAULT_FULL)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-meta", type=Path, default=DEFAULT_META)
    ap.add_argument("--max-rows", type=int, default=0, help="0 = all gap rows")
    args = ap.parse_args()

    if not args.coverage_diff.is_file():
        print(f"missing coverage diff: {args.coverage_diff}", file=sys.stderr)
        return 2
    if not args.full_json.is_file():
        print(f"missing full canon: {args.full_json}", file=sys.stderr)
        return 2

    diff = json.loads(args.coverage_diff.read_text(encoding="utf-8-sig"))
    missing = diff.get("missing_verse_ids")
    if not isinstance(missing, list):
        print("coverage diff has no missing_verse_ids list", file=sys.stderr)
        return 2
    want = {str(v).strip() for v in missing if str(v).strip()}
    if not want:
        print("empty gap set", file=sys.stderr)
        return 2

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with args.out_jsonl.open("w", encoding="utf-8") as fh:
        for row in _iter_full_rows(args.full_json):
            vid = row.get("verse_id") or row.get("id")
            if not isinstance(vid, str) or vid.strip() not in want:
                continue
            out_row = {
                "verse_id": vid.strip(),
                "ingest_status": "pending_upstream_decode",
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "source": "verse_4pipeline_full_31102",
                "gap_cause": "upstream_coverage_not_phase1_filter",
            }
            if row.get("text") is not None:
                out_row["text_preview"] = str(row.get("text"))[:240]
            fh.write(json.dumps(out_row, ensure_ascii=False) + "\n")
            written += 1
            if args.max_rows > 0 and written >= args.max_rows:
                break

    meta = {
        "schema": "logos_verse_gap_ingest_queue_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "gap_count_expected": len(want),
        "rows_written": written,
        "coverage_diff": str(args.coverage_diff.relative_to(ROOT)).replace("\\", "/"),
        "out_jsonl": str(args.out_jsonl.relative_to(ROOT)).replace("\\", "/"),
        "track_wall": {"a_track_auto_promotion": False, "ready_for_external_send": False},
    }
    args.out_meta.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out_jsonl} rows={written} expected_gap={len(want)}", flush=True)
    return 0 if written == len(want) or (args.max_rows > 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
