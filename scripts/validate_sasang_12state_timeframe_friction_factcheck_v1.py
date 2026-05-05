#!/usr/bin/env python3
"""Validate 4h vs 15m friction fact-check artifact contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "docs" / "final" / "artifacts" / "sasang_12state_timeframe_friction_factcheck_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_PATH)
    args = ap.parse_args()

    if not args.report_json.is_file():
        print(f"missing report: {args.report_json}")
        return 2

    doc = json.loads(args.report_json.read_text(encoding="utf-8"))
    if doc.get("schema") != "sasang_12state_timeframe_friction_factcheck_v1":
        print("invalid schema")
        return 3

    tfs = doc.get("timeframes")
    if not isinstance(tfs, list) or len(tfs) != 2:
        print("invalid timeframe rows")
        return 4

    names = {str(x.get("timeframe")) for x in tfs if isinstance(x, dict)}
    if names != {"4h", "15m"}:
        print("timeframe set mismatch")
        return 5

    required = {
        "fee_bps",
        "slippage_bps",
        "friction_bps",
        "trades",
        "win_rate_net",
        "break_even_win_rate_gross",
        "total_return_net",
        "mdd_net",
        "cvar95_net",
    }
    for row in tfs:
        if not isinstance(row, dict):
            print("invalid timeframe item type")
            return 6
        missing = [k for k in required if k not in row]
        if missing:
            print(f"missing timeframe fields: {missing}")
            return 7

    summary = doc.get("summary")
    if not isinstance(summary, dict) or "short_tf_disadvantaged" not in summary or "recommended_role" not in summary:
        print("invalid summary block")
        return 8

    print("ok sasang_12state_timeframe_friction_factcheck_v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
