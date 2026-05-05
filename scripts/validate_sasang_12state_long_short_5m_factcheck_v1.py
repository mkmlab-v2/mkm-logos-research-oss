#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "sasang_12state_long_short_5m_factcheck_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate long/short 5m factcheck artifact.")
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    if not args.report_json.is_file():
        print(f"missing report: {args.report_json}")
        return 2
    doc = json.loads(args.report_json.read_text(encoding="utf-8"))
    if doc.get("schema") != "sasang_12state_long_short_5m_factcheck_v1":
        print("invalid schema")
        return 3
    results = doc.get("results")
    if not isinstance(results, list) or len(results) != 2:
        print("invalid results")
        return 4
    modes = {str(x.get("mode")) for x in results if isinstance(x, dict)}
    if modes != {"long_only", "short_only"}:
        print("mode set mismatch")
        return 5
    required = {"active_trades", "win_rate", "total_return", "mdd", "cvar95"}
    for r in results:
        if not isinstance(r, dict):
            print("invalid result row type")
            return 6
        miss = [k for k in required if k not in r]
        if miss:
            print(f"missing result keys: {miss}")
            return 7
    print("ok sasang_12state_long_short_5m_factcheck_v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
