#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.86, L:0.84, K:0.48, M:0.28}
# Balance: 88
# Purpose: Pre-bake KOSPI/BTC OHLCV prior+expanded_prior maps as static LUT for B-track sweeps
# Keywords: prophecy, btrack, ohlcv, lut, walkforward, cache
"""Build static OHLCV feature LUT for B-track walk-forward / sweep acceleration.

Output matches in-process maps used by ``run_prophecy_per_date_combo_walkforward_v1.py``.
Does not touch live trading or Track A.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_ohlcv_feature_lut_lib_v1 import build_lut_document
DEFAULT_KOSPI = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports" / "btrack_ohlcv_feature_lut_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build B-track OHLCV static feature LUT JSON.")
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument(
        "--last-n-intersection",
        type=int,
        default=0,
        help="If >0, keep only the last N dual-leg intersection dates (align-panel 180d parity).",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.kospi_csv.is_file():
        raise SystemExit(f"missing kospi csv: {args.kospi_csv}")
    if not args.btc_csv.is_file():
        raise SystemExit(f"missing btc csv: {args.btc_csv}")

    last_n = int(args.last_n_intersection) if int(args.last_n_intersection) > 0 else None
    doc = build_lut_document(
        kospi_csv=args.kospi_csv,
        btc_csv=args.btc_csv,
        generated_at_utc=_utc_now(),
        last_n_intersection=last_n,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"ok n_intersection={doc['stats']['n_intersection_dates']} "
        f"out={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
