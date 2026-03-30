#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 경량 과거 데이터 로더 (Data-only Fetcher)

전략·ProphecyStack·FinancialSovereignBacktester를 전혀 로드하지 않고
OOS 비트코인 일봉만 가져오기 위한 모듈.
의존성: pandas, requests 만 사용.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd


BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
SYMBOL_DEFAULT = "BTCUSDT"
INTERVAL_DEFAULT = "1d"


def fetch_historical_data_light(
    start_date: datetime,
    end_date: datetime,
    data_file: Optional[str] = None,
    min_candles: int = 365,
    months_fallback: int = 36,
    symbol: str = SYMBOL_DEFAULT,
) -> pd.DataFrame:
    """
    CSV 또는 Binance 공개 API로 OOS 일봉 데이터만 조회.
    전략/백테스터/ProphecyStack import 없음.

    Returns:
        DatetimeIndex, columns 포함 최소 'close' (open, high, low, volume 있으면 유지)
    """
    data_path = Path(data_file) if data_file else None

    # 1) 파일이 있으면 CSV 로드
    if data_path and data_path.exists():
        try:
            df = _load_csv_light(data_path, start_date, end_date)
            if len(df) >= min_candles:
                return df
        except Exception:
            pass

    # 2) 부족하거나 없으면 Binance 공개 API로 다운로드
    return _download_binance_light(
        start_date=start_date,
        end_date=end_date,
        symbol=symbol,
        months=months_fallback,
    )


def _load_csv_light(
    data_path: Path,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    df = pd.read_csv(data_path)

    if "timestamp" in df.columns:
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    elif "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    else:
        return pd.DataFrame()

    df.set_index("date", inplace=True)
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[df.index >= start_date]
    df = df[df.index <= end_date]
    return df.sort_index()


def _download_binance_light(
    start_date: datetime,
    end_date: datetime,
    symbol: str = SYMBOL_DEFAULT,
    months: int = 36,
    interval: str = INTERVAL_DEFAULT,
) -> pd.DataFrame:
    import time

    import requests

    # OOS 구간 확보를 위해 충분히 앞에서부터
    effective_start = start_date - timedelta(days=months * 30)
    start_ts = int(effective_start.timestamp() * 1000)
    end_ts = int(end_date.timestamp() * 1000)

    all_klines = []
    current_start = start_ts
    limit = 1000

    while current_start < end_ts:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": current_start,
            "endTime": end_ts,
            "limit": limit,
        }
        resp = requests.get(BINANCE_KLINES_URL, params=params, timeout=30)
        resp.raise_for_status()
        klines = resp.json()
        if not klines:
            break
        all_klines.extend(klines)
        current_start = klines[-1][6] + 1
        time.sleep(0.1)

    if not all_klines:
        return pd.DataFrame()

    df = pd.DataFrame(
        all_klines,
        columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore",
        ],
    )
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("date", inplace=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df = df.drop_duplicates(subset=["timestamp"]).sort_index()
    df = df[df.index >= start_date]
    df = df[df.index <= end_date]
    return df
