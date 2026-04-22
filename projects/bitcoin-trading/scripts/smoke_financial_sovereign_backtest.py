#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.85, L:0.8, K:0.5, M:0.45}
# Balance: 88
# Purpose: Non-trading smoke run for Financial Sovereign CLI (CI/local gate)
# Keywords: backtest, smoke, sovereign, ci

from __future__ import annotations

import os
import sys
from pathlib import Path

BTC_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BTC_ROOT.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(BTC_ROOT))
sys.path.insert(0, str(BTC_ROOT / "src"))

from src.backtest.financial_sovereign_backtester import run_financial_sovereign_cli_main

# 레포에 없을 수 있는 전체 시계열(로컬) 우선, 없으면 CI용 소형 픽스처
PREFERRED_CSV = WORKSPACE_ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
FIXTURE_CSV = BTC_ROOT / "tests" / "fixtures" / "btc_smoke_daily.csv"
SMOKE_OUT = BTC_ROOT / "data" / "_smoke_financial_sovereign_backtest.json"


def _resolve_smoke_csv() -> Path | None:
    if PREFERRED_CSV.is_file():
        return PREFERRED_CSV
    if FIXTURE_CSV.is_file():
        return FIXTURE_CSV
    return None


def _require_data() -> bool:
    v = os.environ.get("MKM_SOVEREIGN_SMOKE_REQUIRE_DATA", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def main() -> int:
    csv_path = _resolve_smoke_csv()
    if csv_path is None:
        print(
            f"[smoke] CSV 없음: {PREFERRED_CSV} 또는 {FIXTURE_CSV}",
            file=sys.stderr,
        )
        if _require_data():
            return 1
        print("[smoke] SKIP (exit 0). 엄격: MKM_SOVEREIGN_SMOKE_REQUIRE_DATA=1", file=sys.stderr)
        return 0
    if csv_path == FIXTURE_CSV:
        print(f"[smoke] 픽스처 사용: {csv_path}", file=sys.stderr)
    return run_financial_sovereign_cli_main(
        [
            "--data-file",
            str(csv_path),
            "--days",
            "14",
            "--calibration",
            "--quiet",
            "--no-record-signals",
            "--no-record-equity",
            "--log-level",
            "WARNING",
            "-o",
            str(SMOKE_OUT),
        ]
    )


if __name__ == "__main__":
    sys.exit(main())
