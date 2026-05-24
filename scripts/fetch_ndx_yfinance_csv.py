#!/usr/bin/env python3
"""Download ^IXIC (Nasdaq Composite) daily OHLCV — sandbox research leg."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "research" / "market_data" / "ndx_daily_external_yf.csv"
FETCH_BTC = ROOT / "scripts" / "fetch_btc_yfinance_csv.py"


def main() -> int:
    out = DEFAULT_OUT
    for i, a in enumerate(sys.argv[1:]):
        if a in ("-o", "--output") and i + 1 < len(sys.argv[1:]):
            out = Path(sys.argv[1:][i + 1])
            break
    cmd = [
        sys.executable,
        str(FETCH_BTC),
        "--symbol",
        "^IXIC",
        "--output",
        str(out),
        *sys.argv[1:],
    ]
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
