#!/usr/bin/env python3
"""Emit per-eval_date predicted_direction rows for ensemble v1 or v2 (causal price lens).

Output default: reports/btrack_ensemble_per_date_directions_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_ensemble_per_date_core_v1 import build_per_date_direction_document

DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/btrack_ensemble_per_date_directions_v1_latest.json"


def _eval_dates_from_recent_trading_days(
    *,
    kospi_csv: Path,
    btc_csv: Path,
    n: int,
) -> list[str]:
    if n < 1:
        return []
    from scripts.build_btrack_prophecy_score_from_ohlcv import (
        _last_n_intersection_trading_dates,
    )
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    kospi_rows = load_kospi_yf_rows(kospi_csv)
    btc_rows = load_kospi_yf_rows(btc_csv)
    return _last_n_intersection_trading_dates(kospi_rows, btc_rows, n)


def _eval_dates_from_score(score_path: Path, *, instrument: str) -> list[str]:
    doc = json.loads(score_path.read_text(encoding="utf-8"))
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    inst = instrument.strip().lower()
    dates = {
        str(r.get("eval_date") or "")[:10]
        for r in rows
        if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == inst
    }
    return sorted(d for d in dates if d)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument(
        "--recent-trading-days",
        type=int,
        default=0,
        help="When >0, last N KOSPI∩BTC past dates (matches dual-leg score panel). Overrides score-json date list.",
    )
    ap.add_argument("--target-instrument", default="btc")
    ap.add_argument(
        "--ensemble-mode",
        choices=("v1", "v2_confidence_fusion"),
        default=None,
        help="Override rules.ensemble_mode in config.",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    for p in (args.bundle_json, args.btc_csv):
        if not p.is_file():
            print(f"Missing: {p}", file=sys.stderr)
            return 2

    eval_dates: list[str] = []
    n_recent = max(0, int(args.recent_trading_days))
    if n_recent > 0:
        if not args.kospi_csv.is_file():
            print(f"Missing kospi csv for --recent-trading-days: {args.kospi_csv}", file=sys.stderr)
            return 2
        eval_dates = _eval_dates_from_recent_trading_days(
            kospi_csv=args.kospi_csv, btc_csv=args.btc_csv, n=n_recent
        )
    elif args.score_json.is_file():
        eval_dates = _eval_dates_from_score(args.score_json, instrument=args.target_instrument)
    if not eval_dates:
        print(
            "No eval_dates: pass --recent-trading-days N or --score-json with btc rows.",
            file=sys.stderr,
        )
        return 2

    doc = build_per_date_direction_document(
        bundle_path=args.bundle_json,
        ensemble_config_path=args.ensemble_config,
        eval_dates=eval_dates,
        btc_csv=args.btc_csv,
        ensemble_mode_override=args.ensemble_mode,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} rows={len(doc.get('rows') or [])} mode={doc.get('ensemble_mode')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
