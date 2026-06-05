#!/usr/bin/env python3
"""Download KOSPI (^KS11) daily OHLCV via yfinance into research SSOT CSV path.

Writes a single-header CSV compatible with ``load_kospi_yf_rows`` (Date-first row).
Does not touch trading or promotion gates.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_FAILOVER_SYMBOLS = ("069500.KS",)  # KODEX 200 — index proxy when ^KS11 row missing [HYPO]


def _normalize_download_df(df, pd):
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]) for c in df.columns]
    df = df.reset_index()
    rename = {c: str(c).strip() for c in df.columns}
    df = df.rename(columns=rename)
    if "Date" not in df.columns:
        return None
    out_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
    for c in out_cols:
        if c not in df.columns:
            return None
    out = df[out_cols].copy()
    out["Date"] = out["Date"].astype(str).str.slice(0, 10)
    close_num = pd.to_numeric(out["Close"], errors="coerce")
    out = out[close_num.notna() & (close_num > 0)].copy()
    return out


def _download_symbol(symbol: str, *, start: str, end: str, period: str, pd, yf):
    kwargs: dict = {"interval": "1d", "auto_adjust": False, "progress": False}
    if start.strip():
        if end.strip():
            df = yf.download(symbol, start=start.strip(), end=end.strip(), **kwargs)
        else:
            df = yf.download(symbol, start=start.strip(), **kwargs)
    else:
        df = yf.download(symbol, period=period, interval="1d", auto_adjust=False, progress=False)
    return _normalize_download_df(df, pd)


def _valid_close_dates(df) -> set[str]:
    if df is None or df.empty:
        return set()
    return set(str(d)[:10] for d in df["Date"].tolist())


def _fill_recent_gaps_from_failover(
    out,
    *,
    pd,
    yf,
    failover_symbols: tuple[str, ...],
    gap_lookback_days: int,
):
    if out is None or out.empty:
        return out, []
    dates = sorted(_valid_close_dates(out))
    if not dates:
        return out, []
    last_date = dates[-1]
    try:
        from datetime import date, timedelta

        end_d = date.fromisoformat(last_date) + timedelta(days=1)
        start_d = date.fromisoformat(last_date) - timedelta(days=max(gap_lookback_days, 7))
        fill_start = start_d.isoformat()
        fill_end = end_d.isoformat()
    except ValueError:
        return out, []

    present = _valid_close_dates(out)
    filled: list[str] = []
    for symbol in failover_symbols:
        patch = _download_symbol(symbol, start=fill_start, end=fill_end, period="60d", pd=pd, yf=yf)
        if patch is None or patch.empty:
            continue
        patch = patch.copy()
        patch["Source"] = f"failover:{symbol}"
        for dk in patch["Date"].tolist():
            if dk not in present:
                row = patch[patch["Date"] == dk].iloc[-1:]
                out = pd.concat([out, row], ignore_index=True)
                present.add(str(dk))
                filled.append(str(dk))
        if not filled:
            continue
    if filled:
        out = out.sort_values("Date").drop_duplicates(subset=["Date"], keep="first")
    return out, sorted(set(filled))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="^KS11", help="Yahoo Finance ticker (default KOSPI index)")
    ap.add_argument("--period", default="5y", help="yfinance period=… (ignored if --start is set)")
    ap.add_argument(
        "--start",
        default="",
        help="YYYY-MM-DD download start (inclusive). Use with long history, e.g. 1990-01-01 for ~30y+.",
    )
    ap.add_argument("--end", default="", help="Optional YYYY-MM-DD end (exclusive upper bound for yfinance).")
    ap.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--merge",
        action="store_true",
        help="Merge download into existing CSV by Date (keeps other history rows).",
    )
    ap.add_argument(
        "--fill-recent-gaps",
        action="store_true",
        help="After merge, fill recent missing dates from failover symbols (B-track proxy).",
    )
    ap.add_argument(
        "--failover-symbols",
        default=",".join(DEFAULT_FAILOVER_SYMBOLS),
        help="Comma-separated Yahoo symbols for gap fill (default KODEX200 proxy).",
    )
    ap.add_argument(
        "--gap-lookback-days",
        type=int,
        default=45,
        help="Calendar days to scan for missing primary rows before failover fill.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print resolved paths only; no download")
    ns = ap.parse_args()

    if ns.dry_run:
        print("ok", ns.symbol, str(ns.output.resolve()))
        return 0

    try:
        import pandas as pd
        import yfinance as yf
    except ImportError as e:  # pragma: no cover
        print("requires pandas and yfinance: pip install pandas yfinance", file=sys.stderr)
        raise SystemExit(2) from e

    out = _download_symbol(ns.symbol, start=ns.start.strip(), end=ns.end.strip(), period=ns.period, pd=pd, yf=yf)
    if out is None or out.empty:
        print(f"no rows for {ns.symbol!r}", file=sys.stderr)
        return 2

    if ns.merge and ns.output.is_file():
        existing = pd.read_csv(ns.output)
        if "Date" in existing.columns:
            existing["Date"] = existing["Date"].astype(str).str.slice(0, 10)
            ex_close = pd.to_numeric(existing["Close"], errors="coerce")
            existing = existing[ex_close.notna() & (ex_close > 0)].copy()
            combined = pd.concat([existing, out], ignore_index=True)
            combined["_close_valid"] = pd.to_numeric(combined["Close"], errors="coerce").notna() & (
                pd.to_numeric(combined["Close"], errors="coerce") > 0
            )
            combined = combined.sort_values(["Date", "_close_valid"])
            out = (
                combined.drop_duplicates(subset=["Date"], keep="last")
                .loc[lambda df: df["_close_valid"]]
                .drop(columns=["_close_valid"])
                .sort_values("Date")
            )

    failover_filled: list[str] = []
    if ns.fill_recent_gaps:
        symbols = tuple(s.strip() for s in str(ns.failover_symbols).split(",") if s.strip())
        out, failover_filled = _fill_recent_gaps_from_failover(
            out,
            pd=pd,
            yf=yf,
            failover_symbols=symbols or DEFAULT_FAILOVER_SYMBOLS,
            gap_lookback_days=int(ns.gap_lookback_days),
        )

    ns.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(ns.output, index=False)
    msg = f"{ns.output.resolve()} {len(out)}"
    if failover_filled:
        msg += f" failover_filled={','.join(failover_filled)}"
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
