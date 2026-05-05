#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "sasang_daily_regime_backtest_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate daily regime backtest artifact.")
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()
    if not args.report_json.is_file():
        print(f"missing report: {args.report_json}")
        return 2
    doc = json.loads(args.report_json.read_text(encoding="utf-8"))
    if doc.get("schema") != "sasang_daily_regime_backtest_v1":
        print("invalid schema")
        return 3
    summary = doc.get("summary")
    if not isinstance(summary, dict) or "veto_filter" not in summary or "buy_hold" not in summary:
        print("invalid summary")
        return 4
    yi = doc.get("yearly_improvement")
    if not isinstance(yi, dict) or "mdd_improved_ratio" not in yi or "cvar_improved_ratio" not in yi:
        print("invalid yearly improvement")
        return 5
    print("ok sasang_daily_regime_backtest_v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
