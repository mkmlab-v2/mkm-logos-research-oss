#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ BTC-6 multiplier 경량 백테스트

Heavy한 QuadFusion / AthenaRouter / GDELT 파이프라인 없이
단순 가격 기반 전략으로 multiplier 효과만 빠르게 비교하기 위한 유틸입니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

import numpy as np
import pandas as pd


@dataclass
class SimpleBacktestResult:
    initial_capital: float
    final_capital: float
    total_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float


def run_simple_multiplier_backtest(
    historical_data: pd.DataFrame,
    multiplier: float,
    initial_capital: float = 10_000.0,
    commission_rate: float = 0.001,
) -> Dict[str, Any]:
    """
    BTC 일봉 데이터를 이용한 경량 multiplier 백테스트.

    - 전략: 전일 대비 수익률이 양수면 LONG, 음수면 FLAT
    - 포지션 크기: 자본 30% × multiplier
    - 손절/익절 등은 단순화하고, 포지션은 하루 단위로 리밸런싱
    """
    if len(historical_data) == 0:
        return {}

    closes = historical_data["close"].astype(float)
    returns = closes.pct_change().fillna(0.0).to_numpy()

    capital = initial_capital
    equity_curve: list[float] = []
    peak = initial_capital
    max_dd = 0.0

    total_trades = 0
    winning_trades = 0
    losing_trades = 0

    # 하루 단위로 LONG / FLAT 결정
    for r in returns:
        # 전일이 양수면 오늘 하루 LONG, 아니면 FLAT
        if r > 0:
            position_exposure = 0.3 * float(multiplier)
            gross_pnl = capital * position_exposure * r
            commission = abs(capital * position_exposure) * commission_rate
            pnl = gross_pnl - commission

            total_trades += 1
            if pnl > 0:
                winning_trades += 1
            elif pnl < 0:
                losing_trades += 1

            capital += pnl
        # FLAT이면 자본 변화 없음

        equity_curve.append(capital)
        if capital > peak:
            peak = capital
        drawdown = (peak - capital) / peak if peak > 0 else 0.0
        if drawdown > max_dd:
            max_dd = drawdown

    final_capital = capital
    total_return = (final_capital - initial_capital) / initial_capital
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

    result = SimpleBacktestResult(
        initial_capital=initial_capital,
        final_capital=final_capital,
        total_return=total_return,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate,
        max_drawdown=max_dd,
    )

    return {
        "initial_capital": result.initial_capital,
        "final_capital": result.final_capital,
        "total_return": result.total_return,
        "total_trades": result.total_trades,
        "winning_trades": result.winning_trades,
        "losing_trades": result.losing_trades,
        "win_rate": result.win_rate,
        "max_drawdown": result.max_drawdown,
    }

