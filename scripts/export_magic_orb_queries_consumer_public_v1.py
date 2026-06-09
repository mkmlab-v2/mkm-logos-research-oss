#!/usr/bin/env python3
"""Export magic_orb sample queries with consumer_query_ko to mkmlife public data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs/final/fixtures/magic_orb_question_insight_queries_v1.json"
DEFAULT_OUT = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_question_insight_queries_v1.json"

import sys

sys.path.insert(0, str(ROOT / "scripts"))
from mkm_consumer_facade_v1 import facade_magic_orb_queries_doc  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.in_json.is_file():
        print(f"missing input: {args.in_json}")
        return 2
    doc = json.loads(args.in_json.read_text(encoding="utf-8-sig"))
    out = facade_magic_orb_queries_doc(doc)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK {args.out_json.relative_to(ROOT)} items={len(out.get('items') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
