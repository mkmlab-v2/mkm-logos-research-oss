#!/usr/bin/env python3
"""Mirror PersonaDiary Logos sidebar smoke JSON to no1kmedi public/data."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = ROOT / "docs/final/artifacts/personadiary_logos_sidebar_smoke_v1_latest.json"
DEFAULT_DST = (
    ROOT / "projects/no1kmedi/public/data/personadiary_logos_sidebar_smoke_v1_latest.json"
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--dst", type=Path, default=DEFAULT_DST)
    args = ap.parse_args(argv)

    if not args.src.is_file():
        print(f"FAIL: missing src {args.src}", file=sys.stderr)
        return 1

    doc = json.loads(args.src.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "personadiary_logos_sidebar_smoke_v1":
        print("FAIL: unexpected schema", file=sys.stderr)
        return 1
    if doc.get("prophecy_vote") != "none" or doc.get("send_gate") != "HOLD":
        print("FAIL: wall contract drift", file=sys.stderr)
        return 1

    args.dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.src, args.dst)
    print(f"OK -> {args.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
