#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.3, M:0.7}
# Balance: 88
# Purpose: Record extended sweep execution status for graceful fallback visibility.
# Keywords: status, fallback, extended sweep, btrack
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Build extended sweep status artifact.")
    ap.add_argument("--status", choices=["skipped", "success", "failed"], required=True)
    ap.add_argument("--message", default="")
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_extended_sweep_status_latest.json")
    args = ap.parse_args()

    out_path = resolve(args.output_json)
    out = {
        "schema": "external_bible_crossref_extended_sweep_status_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "extended_sweep_status": args.status,
        "message": args.message,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
