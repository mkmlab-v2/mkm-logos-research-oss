#!/usr/bin/env python3
"""Apply research/market_data/kospi_daily_flow_pending_row_v1.json via append_kospi_daily_flow_row_v1.

Operator drops pending JSON before scheduled B-track chain; on success the pending file is
renamed to *.applied.json (same directory). research_only.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PENDING = ROOT / "research" / "market_data" / "kospi_daily_flow_pending_row_v1.json"
APPEND = ROOT / "scripts" / "append_kospi_daily_flow_row_v1.py"


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pending-json", type=Path, default=DEFAULT_PENDING)
    args = ap.parse_args()
    pending = args.pending_json if args.pending_json.is_absolute() else ROOT / args.pending_json
    if not pending.is_file():
        print("skip: no pending file", pending)
        return 0

    try:
        doc = json.loads(pending.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"invalid pending JSON: {exc}", file=sys.stderr)
        return 2

    date = str(doc.get("date") or "").strip()[:10]
    if len(date) != 10:
        print("pending missing valid date (YYYY-MM-DD)", file=sys.stderr)
        return 2

    cmd = [
        sys.executable,
        str(APPEND),
        "--date",
        date,
        "--foreign",
        str(float(doc.get("foreign") or doc.get("foreign_net_buy") or 0.0)),
        "--institution",
        str(float(doc.get("institution") or doc.get("institution_net_buy") or 0.0)),
        "--program",
        str(float(doc.get("program") or doc.get("program_net_buy") or 0.0)),
        "--individual",
        str(float(doc.get("individual") or doc.get("individual_net_buy") or 0.0)),
        "--source-note",
        str(doc.get("source_note") or doc.get("note") or "pending_row_v1"),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        return proc.returncode

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    applied = pending.with_name(f"kospi_daily_flow_pending_row_v1.applied.{stamp}.json")
    pending.rename(applied)
    print("applied", applied.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
