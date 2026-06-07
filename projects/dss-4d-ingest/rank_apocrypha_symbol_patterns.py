#!/usr/bin/env python3
"""Rank apocrypha NDJSON works by token surface count (metadata only · [HYPO])."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from _frontline_legacy_common import ROOT, load_ndjson, research_meta, utc_now, write_json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--ndjson", type=Path, default=None)
    ap.add_argument("--top-n", type=int, default=10)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    ndjson_path = args.ndjson or ROOT / "outputs" / "apocrypha_tokens_pilot_manifest_ext3_hebrew_priority.ndjson"
    out_path = args.out_json or ROOT / "outputs" / f"apocrypha_symbol_pattern_rank_{args.tag}.json"
    rows = load_ndjson(ndjson_path)
    counter: Counter[str] = Counter()
    for row in rows:
        work = str(row.get("work") or row.get("work_id") or "unknown").strip()
        counter[work] += 1

    ranked = [{"work": work, "token_rows": count} for work, count in counter.most_common(args.top_n)]
    payload = {
        "schema": "apocrypha_symbol_pattern_rank_v1",
        "generated_at_utc": utc_now(),
        "tag": args.tag,
        "ndjson": str(ndjson_path),
        "total_rows": len(rows),
        "unique_works": len(counter),
        "top_n": args.top_n,
        "ranked": ranked,
        **research_meta(),
    }
    write_json(out_path, payload)
    print(f"ranked={len(ranked)}\njson={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
