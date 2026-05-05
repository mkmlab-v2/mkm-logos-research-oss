#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "sasang_daily_regime_threshold_sweep_soft_veto_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate soft-veto sweep artifact.")
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()
    if not args.report_json.is_file():
        print(f"missing report: {args.report_json}")
        return 2
    doc = json.loads(args.report_json.read_text(encoding="utf-8"))
    if doc.get("schema") != "sasang_daily_regime_threshold_sweep_soft_veto_v1":
        print("invalid schema")
        return 3
    top = doc.get("best_top20")
    if not isinstance(top, list) or not top:
        print("missing best_top20")
        return 4
    if "feasible_count" not in doc:
        print("missing feasible_count")
        return 5
    print("ok sasang_daily_regime_threshold_sweep_soft_veto_v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
