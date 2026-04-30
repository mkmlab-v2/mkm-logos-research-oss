#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.3, M:0.7}
# Balance: 88
# Purpose: Create/refresh one-shot threshold apply approval artifact.
# Keywords: approval, threshold apply, one-shot
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def fmt_utc(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Build one-shot threshold apply approval artifact.")
    ap.add_argument("--approved-by", required=True)
    ap.add_argument("--approved-reason", required=True)
    ap.add_argument("--expires-in-hours", type=int, default=24)
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_threshold_apply_approval_latest.json")
    args = ap.parse_args()

    now = now_utc()
    expires = now + timedelta(hours=max(1, int(args.expires_in_hours)))
    out = {
        "schema": "external_bible_crossref_threshold_apply_approval_v1",
        "generated_at_utc": fmt_utc(now),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "approved": True,
        "approved_by": str(args.approved_by),
        "approved_reason": str(args.approved_reason),
        "expires_at_utc": fmt_utc(expires),
        "note": "Manual one-shot approval for gated threshold apply.",
    }
    out_path = resolve(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
