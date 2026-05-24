#!/usr/bin/env python3
"""Merge verse_decoded_v2 + lexical fill JSONL into complete canon decode (v2 wins on duplicate)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_V2 = ROOT / "data/logos/verse_decoded_v2.jsonl"
DEFAULT_FILL = ROOT / "data/logos/verse_decoded_v2_lexical_fill_v1.jsonl"
DEFAULT_OUT = ROOT / "data/logos/verse_decoded_v2_complete_v1.jsonl"
DEFAULT_META = ROOT / "docs/final/artifacts/logos_verse_decoded_v2_complete_v1_latest.json"


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
    ap.add_argument("--fill-jsonl", type=Path, default=DEFAULT_FILL)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-meta", type=Path, default=DEFAULT_META)
    args = ap.parse_args()

    if not args.v2_jsonl.is_file():
        print(f"missing v2: {args.v2_jsonl}", file=sys.stderr)
        return 2
    if not args.fill_jsonl.is_file():
        print(f"missing fill: {args.fill_jsonl}", file=sys.stderr)
        return 2

    seen: set[str] = set()
    v2_n = fill_n = 0
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as out:
        for row in _iter_jsonl(args.v2_jsonl):
            vid = str(row.get("verse_id") or "").strip()
            if not vid or vid in seen:
                continue
            seen.add(vid)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            v2_n += 1
        for row in _iter_jsonl(args.fill_jsonl):
            vid = str(row.get("verse_id") or "").strip()
            if not vid or vid in seen:
                continue
            seen.add(vid)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            fill_n += 1

    meta = {
        "schema": "logos_verse_decoded_v2_complete_v1",
        "ts_utc": _utc_now(),
        "v2_rows": v2_n,
        "lexical_fill_rows": fill_n,
        "union_rows": v2_n + fill_n,
        "out_jsonl": _rel(args.out_jsonl),
    }
    args.out_meta.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out_jsonl} rows={v2_n + fill_n} v2={v2_n} fill={fill_n}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
