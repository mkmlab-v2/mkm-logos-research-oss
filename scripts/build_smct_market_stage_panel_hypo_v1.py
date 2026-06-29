#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build SMCT market stage panel from KOSPI OHLCV [HYPO][research_only]."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_envelope_smct_hypo_lib_v1 import (  # noqa: E402
    DEFAULT_KOSPI_CSV,
    load_kospi_features,
)

DEFAULT_OUT_CSV = ROOT / "reports/smct_market_stage_panel_hypo_v1_latest.csv"
DEFAULT_OUT_META = ROOT / "reports/smct_market_stage_panel_hypo_v1_latest.meta.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=ROOT / DEFAULT_KOSPI_CSV)
    ap.add_argument("--date-from", type=str, default="")
    ap.add_argument("--date-to", type=str, default="")
    ap.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    ap.add_argument("--out-meta-json", type=Path, default=DEFAULT_OUT_META)
    args = ap.parse_args()

    if not args.kospi_csv.is_file():
        print(f"missing kospi csv: {args.kospi_csv}", file=sys.stderr)
        return 1

    by_date = load_kospi_features(args.kospi_csv)
    dates = sorted(by_date.keys())
    if args.date_from:
        dates = [d for d in dates if d >= args.date_from]
    if args.date_to:
        dates = [d for d in dates if d <= args.date_to]
    if not dates:
        print("no rows after date filter", file=sys.stderr)
        return 1

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(next(iter(by_date.values())).keys())
    with args.out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for dk in dates:
            w.writerow(by_date[dk])

    stage_counts: dict[str, int] = {}
    subset_n = 0
    trend_gate_n = 0
    for dk in dates:
        st = str(by_date[dk].get("smct_stage") or "none")
        stage_counts[st] = stage_counts.get(st, 0) + 1
        if by_date[dk].get("smct_subset_allow_envelope"):
            subset_n += 1
        if by_date[dk].get("envelope_trend_gate_v1"):
            trend_gate_n += 1

    meta = {
        "schema": "smct_market_stage_panel_hypo_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "kospi_csv": str(args.kospi_csv.relative_to(ROOT)) if args.kospi_csv.is_relative_to(ROOT) else str(args.kospi_csv),
        "date_from": dates[0],
        "date_to": dates[-1],
        "n_rows": len(dates),
        "stage_counts": stage_counts,
        "smct_subset_allow_envelope_rows": subset_n,
        "envelope_trend_gate_v1_rows": trend_gate_n,
        "out_csv": str(args.out_csv.relative_to(ROOT)) if args.out_csv.is_relative_to(ROOT) else str(args.out_csv),
        "design_ssot": "reports/smct_market_constitution_hypo_v1_latest.json",
    }
    args.out_meta_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK rows={len(dates)} subset={subset_n} -> {args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
