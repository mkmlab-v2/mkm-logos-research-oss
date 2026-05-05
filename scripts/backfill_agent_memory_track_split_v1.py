#!/usr/bin/env python3
"""Backfill split A/B memory JSONL files from combined memory JSONL."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_COMBINED = ART / "agent_memory_deltas_v1.jsonl"
DEFAULT_A = ART / "agent_memory_deltas_track_a_v1.jsonl"
DEFAULT_B = ART / "agent_memory_deltas_track_b_v1.jsonl"
DEFAULT_SUMMARY = ART / "agent_memory_track_split_backfill_summary_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def _row_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("ts_utc") or ""),
        str(row.get("mission") or ""),
        str(row.get("state") or ""),
        str(row.get("source") or ""),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--combined-jsonl", type=Path, default=DEFAULT_COMBINED)
    ap.add_argument("--track-a-jsonl", type=Path, default=DEFAULT_A)
    ap.add_argument("--track-b-jsonl", type=Path, default=DEFAULT_B)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    args = ap.parse_args()

    combined = _read_jsonl(args.combined_jsonl)

    seen_a: set[tuple[str, str, str, str]] = set()
    seen_b: set[tuple[str, str, str, str]] = set()
    rows_a: list[dict[str, Any]] = []
    rows_b: list[dict[str, Any]] = []
    skipped = 0

    for r in combined:
        track = str(r.get("track") or "B").upper()
        key = _row_key(r)
        if track == "A":
            if key in seen_a:
                skipped += 1
                continue
            seen_a.add(key)
            rows_a.append(r)
        else:
            if key in seen_b:
                skipped += 1
                continue
            seen_b.add(key)
            rows_b.append(r)

    _write_jsonl(args.track_a_jsonl, rows_a)
    _write_jsonl(args.track_b_jsonl, rows_b)

    summary = {
        "schema": "agent_memory_track_split_backfill_summary_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {"combined_jsonl": str(args.combined_jsonl).replace("\\", "/")},
        "outputs": {
            "track_a_jsonl": str(args.track_a_jsonl).replace("\\", "/"),
            "track_b_jsonl": str(args.track_b_jsonl).replace("\\", "/"),
        },
        "counts": {
            "combined_rows": len(combined),
            "track_a_rows": len(rows_a),
            "track_b_rows": len(rows_b),
            "skipped_duplicates": skipped,
        },
        "status": "PASS",
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "summary_json": str(args.summary_json), "track_a_rows": len(rows_a), "track_b_rows": len(rows_b)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
