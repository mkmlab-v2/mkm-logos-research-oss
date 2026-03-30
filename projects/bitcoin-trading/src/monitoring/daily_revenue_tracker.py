#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💰 일일 수익 추적 시스템

목적: 일일 수익률, 자산 증가율, PnL 추적
- 일일 수익률 계산
- 자산 증가율 모니터링
- 기술 정합성 지표 통합

작성일: 2026-02-08
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class DailyRevenueMetrics:
    """일일 수익 지표"""
    date: str
    daily_pnl: float
    daily_return: float  # 일일 수익률 (%)
    current_capital: float
    initial_capital: float
    asset_growth_rate: float  # 자산 증가율 (%)
    total_trades: int
    winning_trades: int
    win_rate: float
    peak_capital: float
    max_drawdown: float
    technical_compliance: float  # 기술 정합성 점수 (0-1)


class DailyRevenueTracker:
    """일일 수익 추적 시스템"""
    
    def __init__(self, data_dir: Path = None):
        """초기화"""
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data" / "revenue_tracking"
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.metrics_file = self.data_dir / "daily_metrics.json"
        self.history_file = self.data_dir / "revenue_history.json"
        
        # 일일 메트릭 로드
        self.daily_metrics = self._load_daily_metrics()
        self.revenue_history = self._load_revenue_history()
    
    def _load_daily_metrics(self) -> Dict[str, Any]:
        """일일 메트릭 로드"""
        if self.metrics_file.exists():
            try:
                return json.loads(self.metrics_file.read_text(encoding='utf-8'))
            except Exception as e:
                logger.warning(f"⚠️ 일일 메트릭 로드 실패: {e}")
        return {
            "current_date": datetime.now().strftime('%Y-%m-%d'),
            "daily_pnl": 0.0,
            "daily_return": 0.0,
            "current_capital": 0.0,
            "initial_capital": 0.0,
            "asset_growth_rate": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "win_rate": 0.0,
            "peak_capital": 0.0,
            "max_drawdown": 0.0,
            "technical_compliance": 1.0
        }
    
    def _load_revenue_history(self) -> List[Dict[str, Any]]:
        """수익 히스토리 로드"""
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text(encoding='utf-8'))
            except Exception as e:
                logger.warning(f"⚠️ 수익 히스토리 로드 실패: {e}")
        return []
    
    def _save_daily_metrics(self):
        """일일 메트릭 저장"""
        try:
            self.metrics_file.write_text(
                json.dumps(self.daily_metrics, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as e:
            logger.error(f"❌ 일일 메트릭 저장 실패: {e}")
    
    def _save_revenue_history(self):
        """수익 히스토리 저장"""
        try:
            self.history_file.write_text(
                json.dumps(self.revenue_history, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as e:
            logger.error(f"❌ 수익 히스토리 저장 실패: {e}")
    
    def update_daily_pnl(
        self,
        pnl: float,
        current_capital: float,
        initial_capital: float,
        total_trades: int = 0,
        winning_trades: int = 0,
        peak_capital: float = None,
        max_drawdown: float = None,
        technical_compliance: float = 1.0
    ):
        """일일 PnL 업데이트"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # 날짜 변경 확인
        if self.daily_metrics.get("current_date") != current_date:
            # 이전 날짜 데이터를 히스토리에 저장
            if self.daily_metrics.get("current_date"):
                self.revenue_history.append(self.daily_metrics.copy())
                # 최근 90일만 유지
                if len(self.revenue_history) > 90:
                    self.revenue_history = self.revenue_history[-90:]
                self._save_revenue_history()
            
            # 새 날짜 초기화
            self.daily_metrics = {
                "current_date": current_date,
                "daily_pnl": 0.0,
                "daily_return": 0.0,
                "current_capital": current_capital,
                "initial_capital": initial_capital,
                "asset_growth_rate": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "win_rate": 0.0,
                "peak_capital": peak_capital or current_capital,
                "max_drawdown": max_drawdown or 0.0,
                "technical_compliance": technical_compliance
            }
        
        # 일일 PnL 누적
        self.daily_metrics["daily_pnl"] += pnl
        self.daily_metrics["current_capital"] = current_capital
        self.daily_metrics["initial_capital"] = initial_capital
        
        # 일일 수익률 계산
        if initial_capital > 0:
            self.daily_metrics["daily_return"] = (
                (current_capital - initial_capital) / initial_capital * 100
            )
        
        # 자산 증가율 계산
        if initial_capital > 0:
            self.daily_metrics["asset_growth_rate"] = (
                (current_capital - initial_capital) / initial_capital * 100
            )
        
        # 거래 통계 업데이트
        if total_trades > 0:
            self.daily_metrics["total_trades"] = total_trades
            self.daily_metrics["winning_trades"] = winning_trades
            if total_trades > 0:
                self.daily_metrics["win_rate"] = (winning_trades / total_trades) * 100
        
        # Peak Capital 업데이트
        if peak_capital is not None:
            if peak_capital > self.daily_metrics.get("peak_capital", 0):
                self.daily_metrics["peak_capital"] = peak_capital
        
        # Max Drawdown 업데이트
        if max_drawdown is not None:
            if max_drawdown > self.daily_metrics.get("max_drawdown", 0):
                self.daily_metrics["max_drawdown"] = max_drawdown
        
        # 기술 정합성 업데이트
        self.daily_metrics["technical_compliance"] = technical_compliance
        
        # 저장
        self._save_daily_metrics()
        
        logger.info(
            f"💰 일일 수익 업데이트: "
            f"PnL={self.daily_metrics['daily_pnl']:.2f} USDT, "
            f"수익률={self.daily_metrics['daily_return']:.2f}%, "
            f"자산 증가율={self.daily_metrics['asset_growth_rate']:.2f}%"
        )
    
    def get_daily_metrics(self) -> Dict[str, Any]:
        """일일 메트릭 조회"""
        return self.daily_metrics.copy()
    
    def get_revenue_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """수익 히스토리 조회"""
        return self.revenue_history[-days:] if days > 0 else self.revenue_history
    
    def get_summary(self) -> Dict[str, Any]:
        """요약 통계"""
        current = self.get_daily_metrics()
        history = self.get_revenue_history(30)
        
        # 30일 평균 수익률
        avg_daily_return = 0.0
        if history:
            avg_daily_return = sum(
                day.get("daily_return", 0.0) for day in history
            ) / len(history)
        
        # 총 수익률
        total_return = current.get("asset_growth_rate", 0.0)
        
        return {
            "current_date": current.get("current_date"),
            "daily_pnl": current.get("daily_pnl", 0.0),
            "daily_return": current.get("daily_return", 0.0),
            "current_capital": current.get("current_capital", 0.0),
            "initial_capital": current.get("initial_capital", 0.0),
            "asset_growth_rate": current.get("asset_growth_rate", 0.0),
            "total_return": total_return,
            "avg_daily_return_30d": avg_daily_return,
            "total_trades": current.get("total_trades", 0),
            "win_rate": current.get("win_rate", 0.0),
            "max_drawdown": current.get("max_drawdown", 0.0),
            "technical_compliance": current.get("technical_compliance", 1.0),
            "history_days": len(history)
        }

