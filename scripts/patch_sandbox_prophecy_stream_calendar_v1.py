#!/usr/bin/env python3
"""Backfill snapshot_calendar_date_utc on existing SANDBOX stream rows."""
from __future__ import annotations

import argparse
import json
import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STREAM = ROOT / "reports/sandbox_prophecy_stream_v1.jsonl"


def _lib():
    spec = importlib.util.spec_from_file_location(
        "sandbox_prophecy_lib_v1", ROOT / "scripts/sandbox_prophecy_lib_v1.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def patch_rows(rows: list[dict[str, Any]], lib: Any) -> tuple[int, list[dict[str, Any]]]:
    n_patched = 0
    out: list[dict[str, Any]] = []
    for r in rows:
        if not r.get("snapshot_calendar_date_utc"):
            lib.finalize_stream_row(r)
            n_patched += 1
        out.append(r)
    return n_patched, out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stream-jsonl", type=Path, default=DEFAULT_STREAM)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.stream_jsonl.is_file():
        print(f"Missing: {args.stream_jsonl}")
        return 2

    lib = _lib()
    rows: list[dict[str, Any]] = []
    for line in args.stream_jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if isinstance(o, dict):
            rows.append(o)

    n_patched, out = patch_rows(rows, lib)
    print(f"rows={len(rows)} patched={n_patched}")
    if args.dry_run:
        return 0

    tmp = args.stream_jsonl.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")
    tmp.replace(args.stream_jsonl)
    print(f"WROTE: {args.stream_jsonl.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
