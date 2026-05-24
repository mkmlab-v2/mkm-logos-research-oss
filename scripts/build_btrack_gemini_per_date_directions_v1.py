#!/usr/bin/env python3
"""[HYPO] Build Gemini per-eval_date direction panel (max 30d, causal loop).

Output: reports/btrack_gemini_per_date_directions_v1_latest.json (default)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_gemini_per_date_core_v1 import (
    DEFAULT_BTC,
    DEFAULT_BUNDLE,
    DEFAULT_KOSPI,
    MAX_PANEL_DAYS_DEFAULT,
    MAX_PANEL_DAYS_HARD_CAP,
    build_gemini_per_date_direction_document,
)

DEFAULT_OUT = ROOT / "reports/btrack_gemini_per_date_directions_v1_latest.json"
DEFAULT_CACHE = ROOT / "reports/btrack_model_swap_work/gemini_per_date_cache"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument(
        "--recent-trading-days",
        type=int,
        default=30,
        help=f"Last N KOSPI∩BTC dates (default cap {MAX_PANEL_DAYS_DEFAULT}; hard max {MAX_PANEL_DAYS_HARD_CAP}).",
    )
    ap.add_argument(
        "--max-panel-days",
        type=int,
        default=MAX_PANEL_DAYS_DEFAULT,
        help=f"Upper cap for --recent-trading-days (hard max {MAX_PANEL_DAYS_HARD_CAP}).",
    )
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--sleep-sec", type=float, default=2.5, help="Pause between API calls.")
    ap.add_argument("--max-retries", type=int, default=3)
    ap.add_argument("--retry-backoff-sec", type=float, default=3.0)
    ap.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--price-lookback-days", type=int, default=5)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for p in (args.bundle_json, args.btc_csv, args.kospi_csv):
        if not p.is_file():
            print(f"Missing: {p}", file=sys.stderr)
            return 2
    cap = min(int(args.max_panel_days), MAX_PANEL_DAYS_HARD_CAP)
    if args.recent_trading_days < 1 or args.recent_trading_days > cap:
        print(f"--recent-trading-days must be 1..{cap}", file=sys.stderr)
        return 2

    doc = build_gemini_per_date_direction_document(
        bundle_path=args.bundle_json,
        btc_csv=args.btc_csv,
        kospi_csv=args.kospi_csv,
        recent_trading_days=args.recent_trading_days,
        model=args.model,
        timeout=args.timeout,
        sleep_between_calls_sec=max(0.0, float(args.sleep_sec)),
        max_retries=max(1, int(args.max_retries)),
        retry_backoff_sec=max(0.5, float(args.retry_backoff_sec)),
        cache_dir=None if args.no_cache else args.cache_dir,
        price_lookback_days=max(1, int(args.price_lookback_days)),
        dry_run=bool(args.dry_run),
        max_panel_days=cap,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} rows={len(doc.get('rows') or [])} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
