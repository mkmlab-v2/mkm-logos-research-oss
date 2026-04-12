#!/usr/bin/env python3
"""Filter LOG_METABOLISM JSONL by time window and/or take last N rows (mtime order of lines in file).

Each line must be a JSON object with string window_start_utc (ISO). Invalid lines are skipped with stderr warning.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _parse_ts(s: str) -> datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--since",
        default="",
        help="Inclusive lower bound (ISO-8601). Empty = no lower bound.",
    )
    ap.add_argument(
        "--until",
        default="",
        help="Exclusive upper bound (ISO-8601). Empty = no upper bound.",
    )
    ap.add_argument(
        "--tail",
        type=int,
        default=0,
        help="If >0, after filtering keep only the last N rows (file order).",
    )
    args = ap.parse_args()

    inp = Path(args.inp).resolve()
    if not inp.is_file():
        print(f"FAIL: not found {inp}", file=sys.stderr)
        return 1
    since = _parse_ts(args.since) if str(args.since).strip() else None
    until = _parse_ts(args.until) if str(args.until).strip() else None
    if args.since.strip() and since is None:
        print("FAIL: --since not parseable as datetime", file=sys.stderr)
        return 1
    if args.until.strip() and until is None:
        print("FAIL: --until not parseable as datetime", file=sys.stderr)
        return 1

    rows: list[dict[str, Any]] = []
    bad = 0
    for i, line in enumerate(inp.read_text(encoding="utf-8-sig").splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        try:
            o = json.loads(s)
        except json.JSONDecodeError:
            bad += 1
            continue
        if not isinstance(o, dict):
            bad += 1
            continue
        w = o.get("window_start_utc")
        if not isinstance(w, str):
            bad += 1
            continue
        ts = _parse_ts(w)
        if ts is None:
            bad += 1
            continue
        if since is not None and ts < since:
            continue
        if until is not None and ts >= until:
            continue
        rows.append(o)

    if args.tail and args.tail > 0:
        rows = rows[-int(args.tail) :]

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for o in rows:
            f.write(json.dumps(o, ensure_ascii=False, separators=(",", ":")) + "\n")
    if bad:
        print(f"WARN: skipped {bad} bad lines", file=sys.stderr)
    print(f"OK: wrote {out} rows={len(rows)}")
    return 0 if rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
