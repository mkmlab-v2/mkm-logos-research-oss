#!/usr/bin/env python3
"""Build multi-leg B-Track score JSON for war-prolongation hypothesis.

Observation lane only. Not for live trading promotion.
Downloads daily closes from Yahoo Finance and emits a score payload that
`eval_prophecy_hit_rate_v1.py --run-mode price` can consume.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HYPOTHESIS = ROOT / "docs" / "final" / "artifacts" / "btrack_hypothesis_prophecy_war_prolong_20260406.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_war_prolong_20260406_multileg.json"
DEFAULT_MARKET_DIR = ROOT / "research" / "market_data"

SYMBOLS = {
    "xle": "XLE",
    "ita": "ITA",
    "vix": "^VIX",
    "wti": "CL=F",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _actual_direction(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def _download_symbol(symbol: str, period: str) -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval="1d", auto_adjust=False, progress=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        # yfinance may return multi-index columns with ticker as top-level.
        df.columns = [c[0] for c in df.columns]
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description="Build multi-leg score JSON from war hypothesis + Yahoo market data.")
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYPOTHESIS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--market-data-dir", type=Path, default=DEFAULT_MARKET_DIR)
    ap.add_argument("--period", type=str, default="2y")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    args = ap.parse_args()

    if not args.hypothesis_json.is_file():
        raise SystemExit(f"Missing hypothesis file: {args.hypothesis_json}")

    hypothesis = json.loads(args.hypothesis_json.read_text(encoding="utf-8"))
    predicted = str((hypothesis.get("prediction") or {}).get("direction") or "abstain").strip().lower()
    if predicted not in ("bull", "bear", "neutral"):
        raise SystemExit("Hypothesis direction must be one of bull/bear/neutral for score building.")

    args.market_data_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    warnings: list[str] = []

    for leg, symbol in SYMBOLS.items():
        df = _download_symbol(symbol, args.period)
        if df.empty:
            warnings.append(f"{leg}: no rows downloaded for {symbol}")
            continue
        csv_path = args.market_data_dir / f"{leg}_daily_external_yf.csv"
        df.to_csv(csv_path, index=True)

        if "Close" not in df.columns or len(df) < 2:
            warnings.append(f"{leg}: insufficient close data for {symbol}")
            continue

        prev_close = float(df["Close"].iloc[-2])
        close = float(df["Close"].iloc[-1])
        if prev_close == 0:
            warnings.append(f"{leg}: previous close is zero; skipped")
            continue

        eval_date = str(df.index[-1].date())
        ret = (close - prev_close) / prev_close
        rows.append(
            {
                "instrument": leg,
                "symbol": symbol,
                "eval_date": eval_date,
                "predicted_direction": predicted,
                "actual_direction": _actual_direction(ret, args.neutral_bps),
                "daily_return": round(ret, 8),
                "prev_close": prev_close,
                "close": close,
                "neutral_bps": float(args.neutral_bps),
            }
        )

    payload = {
        "schema": "btrack_prophecy_score_v1",
        "generated_at_utc": _utc_now(),
        "eval_date": max((r["eval_date"] for r in rows), default=None),
        "neutral_bps": float(args.neutral_bps),
        "hypothesis_path": str(args.hypothesis_json).replace("\\", "/"),
        "hypothesis_ts_utc": hypothesis.get("ts_utc"),
        "inputs": {
            "market_data_dir": str(args.market_data_dir).replace("\\", "/"),
            "symbols": SYMBOLS,
            "period": args.period,
        },
        "meta": {"warnings": warnings},
        "rows": rows,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    print(f"rows={len(rows)} warnings={len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

