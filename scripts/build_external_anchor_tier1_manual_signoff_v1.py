#!/usr/bin/env python3
"""Create manual signoff artifact for Tier1 anchor promotion candidates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "external_bible_anchor_tier1_manual_signoff_latest.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--approved", action="store_true")
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--reason", required=True)
    ap.add_argument("--expires-in-hours", type=int, default=24)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    now = _utc_now()
    expires = now + timedelta(hours=max(1, int(args.expires_in_hours)))
    out = {
        "schema": "external_bible_anchor_tier1_manual_signoff_v1",
        "generated_at_utc": _fmt(now),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "approved": bool(args.approved),
        "reviewer": str(args.reviewer),
        "reason": str(args.reason),
        "expires_at_utc": _fmt(expires),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.output_json).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
