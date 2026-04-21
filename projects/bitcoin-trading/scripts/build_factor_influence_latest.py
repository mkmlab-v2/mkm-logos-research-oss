#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.6, L:0.9, K:0.7, M:0.8}
# Balance: 91
# Purpose: Build factor influence summary from recent trading logs (slim bundle).
# Keywords: bitcoin-trading, factor-influence, logs, ssh, automation

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from factor_influence_lib import (
    LINE_PATTERNS,
    build_metrics,
    compile_patterns,
    count_lines,
    filter_by_hours,
    parse_line_ts,
    read_lines,
    write_json,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync factor influence summary from logs (legacy slim schema)."
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("/root/.pm2/logs/bitcoin-live-out.log"),
        help="Input trading log file path (default: /root/.pm2/logs/bitcoin-live-out.log).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "exports" / "cursor_trade_history",
        help="Destination directory for JSON outputs.",
    )
    parser.add_argument(
        "--recent-lines",
        type=int,
        default=1200,
        help="Number of trailing lines used for practical approximation.",
    )
    parser.add_argument(
        "--window-hours",
        type=int,
        default=24,
        help="Timestamp-based window in hours.",
    )
    parser.add_argument(
        "--emit-legacy-files",
        action="store_true",
        help="Also write factor_influence_recent_lines.json and factor_influence_24h.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    now_utc = datetime.now(timezone.utc)
    if not args.log_file.exists():
        print(f"[ERROR] log file not found: {args.log_file}")
        return 2

    lines = read_lines(args.log_file)
    recent_lines = lines[-args.recent_lines :] if args.recent_lines > 0 else lines
    window_start_utc = now_utc - timedelta(hours=args.window_hours)
    by_24h_lines = filter_by_hours(lines, window_start_utc=window_start_utc)
    compiled = compile_patterns()

    recent_result = count_lines(recent_lines, compiled)
    hour_result = count_lines(by_24h_lines, compiled)

    latest_payload = {
        "schema": "factor_influence_latest_v1",
        "generated_at_utc": now_utc.isoformat(),
        "source": {
            "log_file": str(args.log_file),
            "recent_lines": args.recent_lines,
            "window_hours": args.window_hours,
        },
        "recent_lines": {
            "scope_total_lines": recent_result.total_lines,
            "matched_lines": recent_result.matched_lines,
            "counts": recent_result.counts,
            "metrics": build_metrics(recent_result.counts),
        },
        "window_24h": {
            "scope_total_lines": hour_result.total_lines,
            "matched_lines": hour_result.matched_lines,
            "counts": hour_result.counts,
            "metrics": build_metrics(hour_result.counts),
        },
        "delta_recent_minus_24h": {
            key: recent_result.counts[key] - hour_result.counts[key]
            for key in LINE_PATTERNS
        },
    }

    out_dir = args.out_dir
    write_json(out_dir / "factor_influence_latest.json", latest_payload)
    if args.emit_legacy_files:
        write_json(
            out_dir / "factor_influence_recent_lines.json",
            {
                "schema": "factor_influence_recent_lines_v1",
                "generated_at_utc": now_utc.isoformat(),
                "recent_lines": args.recent_lines,
                "counts": recent_result.counts,
                "metrics": build_metrics(recent_result.counts),
            },
        )
        write_json(
            out_dir / "factor_influence_24h.json",
            {
                "schema": "factor_influence_24h_v1",
                "generated_at_utc": now_utc.isoformat(),
                "window_hours": args.window_hours,
                "counts": hour_result.counts,
                "metrics": build_metrics(hour_result.counts),
            },
        )

    print("[OK] factor influence latest generated")
    print(f"log_file: {args.log_file}")
    print(f"output:   {out_dir / 'factor_influence_latest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
