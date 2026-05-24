#!/usr/bin/env python3
"""Weekly SANDBOX Phase3 entry: Binance micro fetch + join + full sandbox chain.

research_only — never mutates prod btrack_prophecy_score_latest.json.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAILY_CHAIN = ROOT / "scripts/run_prophecy_sandbox_daily_chain_v1.py"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-market-fetch", action="store_true")
    ap.add_argument("--no-backfill-stream-calendar", action="store_true")
    ap.add_argument("--sync-daily-thread-log", action="store_true")
    ap.add_argument("--daily-thread", type=int, default=5)
    ap.add_argument(
        "--no-strict-health",
        action="store_true",
        help="Weekly default runs daily chain with strict sandbox health (calendar_days>=3).",
    )
    args = ap.parse_args()

    if not DAILY_CHAIN.is_file():
        print(f"Missing: {DAILY_CHAIN}", file=sys.stderr)
        return 2

    cmd = [
        sys.executable,
        str(DAILY_CHAIN),
        "--refresh-phase3-join",
        "--refresh-phase3-binance",
    ]
    if args.skip_market_fetch:
        cmd.append("--skip-market-fetch")
    if not args.no_backfill_stream_calendar:
        cmd.append("--backfill-stream-calendar")
    if args.sync_daily_thread_log:
        cmd.extend(["--sync-daily-thread-log", "--daily-thread", str(args.daily_thread)])
    if not args.no_strict_health:
        cmd.append("--strict-health")

    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
