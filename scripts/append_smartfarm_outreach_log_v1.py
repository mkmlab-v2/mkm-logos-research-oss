#!/usr/bin/env python3
"""Append one line to smartfarm vendor outreach log (JSONL)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports" / "smartfarm_vendor_outreach_log_v1.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True, help="e.g. quote_revision_sent")
    ap.add_argument("--vendor", default="(주)큐빅스")
    ap.add_argument("--verdict", default="awaiting_revised_quote")
    ap.add_argument("--note", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()
    row = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "vendor": args.vendor,
        "channel": args.channel,
        "verdict": args.verdict,
        "note": args.note,
    }
    line = json.dumps(row, ensure_ascii=False) + "\n"
    if args.dry_run:
        print(line, end="")
        return 0
    log_path = args.log if args.log.is_absolute() else ROOT / args.log
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)
    print(f"OK: appended to {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
