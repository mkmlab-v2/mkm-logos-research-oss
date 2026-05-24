#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Harvest 보명지주·병증 한자 후보 from IJEOMA chunk table → report JSON; optional lexicon merge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.harvest_scm_boming_jiju_from_ijeoma_v1 import (  # noqa: E402
    DEFAULT_CHUNK_TABLE,
    harvest_from_chunk_table,
    merge_harvest_into_lexicon,
)

OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "scm_boming_jiju_lexicon_ijeoma_harvest_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk-table", type=Path, default=DEFAULT_CHUNK_TABLE)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--min-freq", type=int, default=2)
    ap.add_argument("--min-score", type=int, default=50, help="Drop phrases below this harvest score (default 50)")
    ap.add_argument("--max-per-constitution", type=int, default=40)
    ap.add_argument("--apply", action="store_true", help="Merge new terms into scm_boming_jiju_lexicon_v1.json")
    ap.add_argument("--dry-run", action="store_true", help="With --apply: report only, no lexicon write")
    args = ap.parse_args()

    doc = harvest_from_chunk_table(
        args.chunk_table,
        min_freq=args.min_freq,
        min_score=args.min_score,
        max_per_constitution=args.max_per_constitution,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "proposed": len(doc.get("proposed_lexicon_entries") or [])}))

    if args.apply:
        stats = merge_harvest_into_lexicon(doc, dry_run=args.dry_run)
        print(json.dumps({"merge": stats}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
