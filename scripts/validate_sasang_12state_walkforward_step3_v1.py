#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "sasang_12state_walkforward_step3_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate step3 walkforward artifact.")
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()
    if not args.report_json.is_file():
        print(f"missing report: {args.report_json}")
        return 2
    doc = json.loads(args.report_json.read_text(encoding="utf-8"))
    if doc.get("schema") != "sasang_12state_walkforward_step3_v1":
        print("invalid schema")
        return 3
    lanes = doc.get("lane_results")
    if not isinstance(lanes, list) or len(lanes) < 1:
        print("missing lanes")
        return 4
    for lane in lanes:
        if not isinstance(lane, dict):
            return 5
        rows = lane.get("rows")
        summ = lane.get("summary")
        if not isinstance(rows, list) or not rows:
            print("empty lane rows")
            return 6
        if not isinstance(summ, dict) or "window_count" not in summ:
            print("missing lane summary")
            return 7
    print("ok sasang_12state_walkforward_step3_v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
