#!/usr/bin/env python3
"""Merge verse_decoded_v2 + gap staging into union JSONL (v2 rows win on duplicate verse_id)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_V2 = ROOT / "data/logos/verse_decoded_v2.jsonl"
DEFAULT_STAGING = ROOT / "data/logos/verse_decoded_v2_gap_staging_v1.jsonl"
DEFAULT_OUT = ROOT / "data/logos/verse_decoded_v2_union_v1.jsonl"
DEFAULT_META = ROOT / "docs/final/artifacts/logos_verse_decoded_v2_union_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2-jsonl", type=Path, default=DEFAULT_V2)
    ap.add_argument("--staging-jsonl", type=Path, default=DEFAULT_STAGING)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-meta", type=Path, default=DEFAULT_META)
    args = ap.parse_args()

    if not args.v2_jsonl.is_file():
        print(f"missing v2: {args.v2_jsonl}", file=sys.stderr)
        return 2
    if not args.staging_jsonl.is_file():
        print(f"missing staging: {args.staging_jsonl}", file=sys.stderr)
        return 2

    seen: set[str] = set()
    v2_n = 0
    staging_n = 0
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as out:
        for row in _iter_jsonl(args.v2_jsonl):
            vid = str(row.get("verse_id") or "").strip()
            if not vid or vid in seen:
                continue
            seen.add(vid)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            v2_n += 1
        for row in _iter_jsonl(args.staging_jsonl):
            vid = str(row.get("verse_id") or "").strip()
            if not vid or vid in seen:
                continue
            seen.add(vid)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            staging_n += 1

    meta = {
        "schema": "logos_verse_decoded_v2_union_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "v2_rows": v2_n,
        "staging_rows_appended": staging_n,
        "union_rows": v2_n + staging_n,
        "out_jsonl": _rel(args.out_jsonl),
        "track_wall": {"ready_for_external_send": False},
    }
    args.out_meta.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out_jsonl} union_rows={v2_n + staging_n} v2={v2_n} staging={staging_n}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
