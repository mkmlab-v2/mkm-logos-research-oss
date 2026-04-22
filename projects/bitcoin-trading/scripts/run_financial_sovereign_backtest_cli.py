#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.88, L:0.82, K:0.45, M:0.55}
# Balance: 90
# Purpose: CLI entry for Financial Sovereign black-box backtest with quiet/logging flags
# Keywords: backtest, sovereign, btc, cli

from __future__ import annotations

import sys
from pathlib import Path

BTC_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(BTC_ROOT))
sys.path.insert(0, str(BTC_ROOT / "src"))

from src.backtest.financial_sovereign_backtester import run_financial_sovereign_cli_main


def main() -> int:
    return run_financial_sovereign_cli_main()


if __name__ == "__main__":
    sys.exit(main())
