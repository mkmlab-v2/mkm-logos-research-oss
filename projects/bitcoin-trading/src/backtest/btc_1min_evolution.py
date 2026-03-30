#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ Bitcoin 1분봉 자율 진화 엔진

비트코인 1분봉 데이터를 사용한 자율 진화 훈련
- 1분봉 데이터 수집
- 결정적 구간 탐지
- 재귀적 정제 (Recursive Refinement)
- 가중치 자동 조정

작성일: 2026-02-14
버전: v1.0
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
import json
import time

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(workspace_root / "scripts"))

# 모듈 import
try:
    from src.strategy.crypto_nitro_live_strategy import CryptoNitroLiveStrategy
    from tools.core.financial_sovereign_harness import FinancialSovereignHarness
    from src.data.bitcoin_4d_mapper import Bitcoin4DMapper
    STRATEGY_AVAILABLE = True
except ImportError as e:
    STRATEGY_AVAILABLE = False
    logger.warning(f"⚠️ 전략 모듈 import 실패: {e}")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BTC1MinEvolution:
    """
    비트코인 1분봉 자율 진화 엔진
    
    목표: 매매 타점의 정밀도를 85% 이상으로 고정
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        initial_capital: float = 10000.0,
        leverage: int = 2,
        lookforward_minutes: int = 60  # 1시간 후 결과 검증
    ):
        """
        Args:
            symbol: 거래 심볼
            initial_capital: 초기 자본
            leverage: 레버리지
            lookforward_minutes: 결과 검증 시간 (분)
        """
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.lookforward_minutes = lookforward_minutes
        
        # Financial Sovereign Harness 초기화
        self.harness = None
        try:
            codebook_path = workspace_root / "projects" / "bitcoin-trading" / "data" / "btc_1min_codebook.json"
            self.harness = FinancialSovereignHarness(codebook_path=str(codebook_path))
            logger.info("✅ Financial Sovereign Harness 초기화 완료 (1분봉 진화용)")
        except Exception as e:
            logger.warning(f"⚠️ Financial Sovereign Harness 초기화 실패: {e}")
        
        # 진화 결과 추적
        self.evolution_results = {
            "total_iterations": 0,
            "success_count": 0,
            "failure_count": 0,
            "success_rate": 0.0,
            "total_profit": 0.0,
            "weight_adjustments": 0,
            "iterations": []
        }
        
        logger.info("✅ BTC 1분봉 자율 진화 엔진 초기화 완료")
    
    def load_1min_data(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        1분봉 데이터 수집
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 최대 데이터 개수
        
        Returns:
            1분봉 데이터 DataFrame
        """
        try:
            # Binance 공개 API로 1분봉 데이터 수집
            import requests
            
            # 시작 타임스탬프 (밀리초)
            start_ts = int(start_date.timestamp() * 1000)
            end_ts = int(end_date.timestamp() * 1000)
            
            all_data = []
            current_ts = start_ts
            
            while current_ts < end_ts and len(all_data) < limit:
                try:
                    url = f"https://api.binance.com/api/v3/klines"
                    params = {
                        "symbol": self.symbol,
                        "interval": "1m",
                        "startTime": current_ts,
                        "endTime": min(current_ts + 1000 * 60 * 1000, end_ts),  # 최대 1000개씩
                        "limit": 1000
                    }
                    
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        all_data.extend(data)
                        current_ts = data[-1][0] + 1  # 다음 시작점
                        time.sleep(0.1)  # API 레이트 리밋 방지
                    else:
                        logger.warning(f"⚠️ API 호출 실패: {response.status_code}")
                        break
                        
                except Exception as e:
                    logger.error(f"❌ 데이터 수집 실패: {e}")
                    break
            
            if not all_data:
                logger.warning("⚠️ 데이터가 없습니다.")
                return pd.DataFrame()
            
            # DataFrame 변환
            df = pd.DataFrame(all_data, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume", "trades", "taker_buy_base",
                "taker_buy_quote", "ignore"
            ])
            
            # 데이터 타입 변환
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # 인덱스 설정
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"✅ 1분봉 데이터 수집 완료: {len(df)}개 (기간: {start_date} ~ {end_date})")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 1분봉 데이터 수집 실패: {e}")
            return pd.DataFrame()
    
    def detect_critical_points(
        self,
        data: pd.DataFrame,
        min_interval_minutes: int = 60  # 최소 간격 (분)
    ) -> List[datetime]:
        """
        결정적 구간 탐지 (1분봉 데이터)
        
        Args:
            data: 1분봉 데이터
            min_interval_minutes: 최소 간격 (분)
        
        Returns:
            결정적 구간 리스트
        """
        try:
            if len(data) < 100:
                return []
            
            # 변동성 계산 (롤링 윈도우)
            data['volatility'] = data['close'].pct_change().rolling(60).std()  # 1시간 롤링
            
            # 변동성이 높은 시점 탐지 (상위 10%)
            threshold = data['volatility'].quantile(0.9)
            high_volatility_points = data[data['volatility'] >= threshold].index.tolist()
            
            # 최소 간격 필터링
            critical_points = []
            last_point = None
            
            for point in high_volatility_points:
                if last_point is None:
                    critical_points.append(point)
                    last_point = point
                else:
                    # 최소 간격 확인
                    if (point - last_point).total_seconds() >= min_interval_minutes * 60:
                        critical_points.append(point)
                        last_point = point
            
            logger.info(f"✅ 결정적 구간 탐지 완료: {len(critical_points)}개")
            
            return critical_points
            
        except Exception as e:
            logger.error(f"❌ 결정적 구간 탐지 실패: {e}")
            return []
    
    def run_evolution_loop(
        self,
        data: pd.DataFrame,
        critical_points: List[datetime],
        max_iterations: int = 100
    ) -> Dict[str, Any]:
        """
        자율 진화 루프 실행
        
        Args:
            data: 1분봉 데이터
            critical_points: 결정적 구간 리스트
            max_iterations: 최대 반복 횟수
        
        Returns:
            진화 결과
        """
        try:
            iterations = min(len(critical_points), max_iterations)
            
            logger.info(f"🚀 자율 진화 루프 시작: {iterations}회 반복")
            
            for i, critical_point in enumerate(critical_points[:iterations]):
                logger.info(f"\n📊 진화 반복 {i+1}/{iterations}")
                logger.info(f"   시점: {critical_point}")
                
                # 1. 위상 소환 및 매매 집행
                signal_result = self._invoke_signal(data, critical_point)
                
                if not signal_result:
                    logger.warning(f"⚠️ 신호 생성 실패 (반복 {i+1})")
                    continue
                
                # 2. 결과 검증 (Back-to-Future Verification)
                verification_result = self._verify_result(
                    data, critical_point, signal_result, self.lookforward_minutes
                )
                
                # 3. 자율 조정
                if verification_result.get("profit", 0) < 0:
                    # 손실 발생 시 가중치 조정
                    self._adjust_weights(
                        failed_vector=signal_result.get("vector_4d", {}),
                        actual_result=verification_result,
                        reason="Market Constitution Violation"
                    )
                    self.evolution_results["weight_adjustments"] += 1
                    self.evolution_results["failure_count"] += 1
                else:
                    self.evolution_results["success_count"] += 1
                
                # 결과 기록
                iteration_result = {
                    "iteration": i + 1,
                    "timestamp": critical_point.isoformat(),
                    "signal": signal_result.get("signal"),
                    "confidence": signal_result.get("confidence"),
                    "profit": verification_result.get("profit", 0),
                    "success": verification_result.get("profit", 0) >= 0
                }
                self.evolution_results["iterations"].append(iteration_result)
                self.evolution_results["total_iterations"] += 1
                self.evolution_results["total_profit"] += verification_result.get("profit", 0)
            
            # 성공률 계산
            if self.evolution_results["total_iterations"] > 0:
                self.evolution_results["success_rate"] = (
                    self.evolution_results["success_count"] / 
                    self.evolution_results["total_iterations"]
                )
            
            logger.info("\n" + "=" * 80)
            logger.info("🏛️ 자율 진화 완료")
            logger.info("=" * 80)
            logger.info(f"총 반복 횟수: {self.evolution_results['total_iterations']}회")
            logger.info(f"성공 횟수: {self.evolution_results['success_count']}회")
            logger.info(f"실패 횟수: {self.evolution_results['failure_count']}회")
            logger.info(f"성공률: {self.evolution_results['success_rate']:.2%}")
            logger.info(f"총 수익: ${self.evolution_results['total_profit']:.2f}")
            logger.info(f"가중치 조정 횟수: {self.evolution_results['weight_adjustments']}회")
            
            return self.evolution_results
            
        except Exception as e:
            logger.error(f"❌ 자율 진화 루프 실패: {e}")
            return self.evolution_results
    
    def _invoke_signal(
        self,
        data: pd.DataFrame,
        current_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """신호 생성 (위상 소환)"""
        try:
            if not STRATEGY_AVAILABLE:
                return None
            
            # 현재 시점까지의 데이터만 사용
            blind_data = data[data.index <= current_time].copy()
            
            if len(blind_data) < 100:
                return None
            
            # 전략 초기화
            strategy = CryptoNitroLiveStrategy(
                symbol=self.symbol,
                initial_capital=self.initial_capital,
                leverage=self.leverage,
                use_great_trunk_filter=True,
                binance_client=None,
                harness_instance=self.harness  # 공유 하네스 인스턴스
            )
            strategy.price_data = blind_data.copy()
            
            # 현재 가격
            current_price = blind_data['close'].iloc[-1]
            
            # 신호 생성
            signal_data = strategy.calculate_trading_signal(
                current_price=current_price,
                current_time=current_time
            )
            
            # 4D 벡터 추출
            vector_4d = signal_data.get("sovereign_vector", {})
            if not vector_4d:
                vector_4d = {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
            
            return {
                "signal": signal_data.get("signal", "HOLD"),
                "confidence": signal_data.get("confidence", 0.0),
                "vector_4d": vector_4d,
                "signal_id": signal_data.get("signal_id"),
                "price": current_price
            }
            
        except Exception as e:
            logger.error(f"❌ 신호 생성 실패: {e}")
            return None
    
    def _verify_result(
        self,
        data: pd.DataFrame,
        current_time: datetime,
        signal_result: Dict[str, Any],
        lookforward_minutes: int
    ) -> Dict[str, Any]:
        """결과 검증 (Back-to-Future Verification)"""
        try:
            # 미래 시점 계산
            future_time = current_time + timedelta(minutes=lookforward_minutes)
            
            # 미래 데이터 조회
            future_data = data[data.index > current_time]
            if len(future_data) == 0:
                return {"profit": 0, "price_change": 0}
            
            # 가장 가까운 미래 시점
            future_idx = future_data.index[future_data.index <= future_time]
            if len(future_idx) == 0:
                # lookforward_minutes 내에 데이터가 없으면 가장 가까운 데이터 사용
                future_idx = future_data.index[:1]
            
            future_price = future_data.loc[future_idx[0], 'close']
            current_price = signal_result.get("price", 0)
            
            if current_price == 0:
                return {"profit": 0, "price_change": 0}
            
            # 가격 변화율
            price_change = (future_price - current_price) / current_price
            
            # 신호에 따른 수익 계산
            signal = signal_result.get("signal", "HOLD")
            if signal == "BUY":
                profit = price_change * self.initial_capital * self.leverage
            elif signal == "SELL":
                profit = -price_change * self.initial_capital * self.leverage
            else:
                profit = 0
            
            return {
                "profit": profit,
                "price_change": price_change,
                "current_price": current_price,
                "future_price": future_price
            }
            
        except Exception as e:
            logger.error(f"❌ 결과 검증 실패: {e}")
            return {"profit": 0, "price_change": 0}
    
    def _adjust_weights(
        self,
        failed_vector: Dict[str, float],
        actual_result: Dict[str, Any],
        reason: str = "Market Constitution Violation"
    ):
        """가중치 조정 (자율 진화)"""
        try:
            # 실패 패턴 기록
            # TODO: 더 정교한 가중치 조정 알고리즘 구현
            logger.debug(f"가중치 조정: {reason}, 벡터: {failed_vector}")
            
        except Exception as e:
            logger.warning(f"⚠️ 가중치 조정 실패: {e}")
    
    def save_results(self, output_path: Optional[Path] = None):
        """진화 결과 저장"""
        try:
            if output_path is None:
                output_path = workspace_root / "projects" / "bitcoin-trading" / "data" / "btc_1min_evolution_results.json"
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.evolution_results, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"✅ 진화 결과 저장 완료: {output_path}")
            
        except Exception as e:
            logger.error(f"❌ 진화 결과 저장 실패: {e}")


if __name__ == "__main__":
    # 테스트 실행
    evolution = BTC1MinEvolution(
        symbol="BTCUSDT",
        initial_capital=10000.0,
        leverage=2,
        lookforward_minutes=60
    )
    
    # 최근 7일 데이터 수집
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    logger.info("📊 1분봉 데이터 수집 중...")
    data = evolution.load_1min_data(start_date, end_date, limit=10000)
    
    if len(data) > 0:
        # 결정적 구간 탐지
        logger.info("🔍 결정적 구간 탐지 중...")
        critical_points = evolution.detect_critical_points(data, min_interval_minutes=60)
        
        if len(critical_points) > 0:
            # 자율 진화 루프 실행
            logger.info("🚀 자율 진화 루프 시작...")
            results = evolution.run_evolution_loop(data, critical_points, max_iterations=10)
            
            # 결과 저장
            evolution.save_results()
        else:
            logger.warning("⚠️ 결정적 구간이 없습니다.")
    else:
        logger.warning("⚠️ 데이터가 없습니다.")

