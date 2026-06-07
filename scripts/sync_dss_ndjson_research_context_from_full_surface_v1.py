#!/usr/bin/env python3
"""Copy full-surface NDJSON research context to AB SSOT path."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = ROOT / "docs/final/artifacts/news_observation_v1_dss_ndjson_full_surface_latest.jsonl"
DEFAULT_DST = ROOT / "docs/final/artifacts/news_observation_v1_dss_ndjson_research_context_latest.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-jsonl", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--dest-jsonl", type=Path, default=DEFAULT_DST)
    args = ap.parse_args()
    if not args.source_jsonl.is_file():
        print(json.dumps({"ok": False, "error": f"missing {args.source_jsonl}"}), file=sys.stderr)
        return 2
    args.dest_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.dest_jsonl.write_text(args.source_jsonl.read_text(encoding="utf-8"), encoding="utf-8")
    rows = sum(1 for line in args.dest_jsonl.read_text(encoding="utf-8").splitlines() if line.strip())
    print(json.dumps({"ok": True, "dest": str(args.dest_jsonl), "row_count": rows}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
