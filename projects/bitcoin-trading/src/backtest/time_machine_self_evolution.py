#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ Time-Machine Self-Evolution Engine (시공간 자율 진화 엔진)

10년치 과거 데이터를 사용하여 재귀적 정제(Recursive Refinement)를 통해
모델의 판단 기준 자체를 진화시키는 시스템.

핵심 원리:
1. 위상 소환: 명리 위상(λ)에 따라 매매 집행
2. 결과 검증: 실제 결과와 대조하여 Hallucination 포착
3. 자율 조정: 실패한 구간의 4D 벡터 상수 재조정
4. 반복 진화: 수정된 로직으로 다음 시점 매매 수행

작성일: 2026-02-14
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import logging
import time
from collections import defaultdict

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent
bitcoin_trading_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(workspace_root / "scripts"))
sys.path.insert(0, str(bitcoin_trading_root))
sys.path.insert(0, str(bitcoin_trading_root / "src"))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 전략 클래스 import
STRATEGY_AVAILABLE = False
try:
    from src.strategy.crypto_nitro_live_strategy import CryptoNitroLiveStrategy
    STRATEGY_AVAILABLE = True
except ImportError:
    try:
        from strategy.crypto_nitro_live_strategy import CryptoNitroLiveStrategy
        STRATEGY_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"⚠️ CryptoNitroLiveStrategy를 import할 수 없습니다: {e}")

# Financial Sovereign Harness import
HARNESS_AVAILABLE = False
try:
    from tools.core.financial_sovereign_harness import FinancialSovereignHarness
    HARNESS_AVAILABLE = True
except ImportError:
    try:
        import sys
        tools_path = workspace_root / "tools" / "core"
        if tools_path.exists():
            sys.path.insert(0, str(tools_path.parent.parent))
        from tools.core.financial_sovereign_harness import FinancialSovereignHarness
        HARNESS_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"⚠️ FinancialSovereignHarness를 import할 수 없습니다: {e}")

# 명리 컨트롤러 import
MYEONGRI_AVAILABLE = False
try:
    from tools.core.myeongri_controller import MyeongriController
    MYEONGRI_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ MyeongriController를 import할 수 없습니다.")


class ModelOptimizer:
    """
    🏛️ 모델 최적화 엔진
    
    실패한 구간의 4D 벡터 상수를 재조정하여 자율 진화
    """
    
    def __init__(self):
        """초기화"""
        # 실패 패턴 추적
        self.failure_patterns = defaultdict(list)  # vector_4d -> [실패 사례들]
        self.success_patterns = defaultdict(list)  # vector_4d -> [성공 사례들]
        
        # 가중치 조정 히스토리
        self.weight_adjustments = []
        
        logger.info("✅ Model Optimizer 초기화 완료")
    
    def adjust_weights(
        self,
        failed_vector: Dict[str, float],
        actual_result: Dict[str, Any],
        reason: str = "Market Constitution Violation"
    ) -> Dict[str, float]:
        """
        가중치 자동 조정
        
        Args:
            failed_vector: 실패한 4D 벡터
            actual_result: 실제 결과
            reason: 실패 이유
        
        Returns:
            조정된 가중치
        """
        # 실패 패턴 기록
        self.failure_patterns[json.dumps(failed_vector, sort_keys=True)].append({
            "vector": failed_vector,
            "result": actual_result,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        # 가중치 조정 로직 (간단한 예시)
        # 실제로는 더 정교한 알고리즘 필요
        adjusted_weights = {
            "S": failed_vector.get("S", 0.25),
            "L": failed_vector.get("L", 0.25),
            "K": failed_vector.get("K", 0.25),
            "M": failed_vector.get("M", 0.25)
        }
        
        # 실패 원인에 따른 가중치 조정
        if "Market Constitution Violation" in reason:
            # 시장 체질 위반 시 해당 차원 가중치 감소
            if actual_result.get("actual_direction") == "UP" and failed_vector.get("S", 0.25) > 0.3:
                adjusted_weights["S"] = max(0.1, adjusted_weights["S"] * 0.9)
            elif actual_result.get("actual_direction") == "DOWN" and failed_vector.get("S", 0.25) < 0.2:
                adjusted_weights["S"] = min(0.4, adjusted_weights["S"] * 1.1)
        
        self.weight_adjustments.append({
            "original": failed_vector,
            "adjusted": adjusted_weights,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.debug(f"🔧 가중치 조정: {failed_vector} → {adjusted_weights} (이유: {reason})")
        
        return adjusted_weights
    
    def record_success(
        self,
        success_vector: Dict[str, float],
        actual_result: Dict[str, Any]
    ):
        """
        성공 패턴 기록
        
        Args:
            success_vector: 성공한 4D 벡터
            actual_result: 실제 결과
        """
        self.success_patterns[json.dumps(success_vector, sort_keys=True)].append({
            "vector": success_vector,
            "result": actual_result,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        최적화 통계 반환
        
        Returns:
            통계 정보
        """
        total_failures = sum(len(cases) for cases in self.failure_patterns.values())
        total_successes = sum(len(cases) for cases in self.success_patterns.values())
        
        return {
            "total_failures": total_failures,
            "total_successes": total_successes,
            "failure_patterns_count": len(self.failure_patterns),
            "success_patterns_count": len(self.success_patterns),
            "weight_adjustments_count": len(self.weight_adjustments),
            "success_rate": total_successes / (total_failures + total_successes) if (total_failures + total_successes) > 0 else 0.0
        }


class TimeMachineSelfEvolution:
    """
    🏛️ Time-Machine Self-Evolution Engine
    
    10년치 과거 데이터를 사용하여 재귀적 정제를 통해 모델 진화
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        initial_capital: float = 10000.0,
        leverage: int = 2,
        start_year: int = 2016,
        end_year: int = 2026
    ):
        """
        Args:
            symbol: 거래 심볼
            initial_capital: 초기 자본
            leverage: 레버리지
            start_year: 시작 연도 (10년 전)
            end_year: 종료 연도
        """
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.start_year = start_year
        self.end_year = end_year
        
        # Financial Sovereign Harness 초기화
        self.harness = None
        if HARNESS_AVAILABLE:
            try:
                codebook_path = workspace_root / "projects" / "bitcoin-trading" / "data" / "evolution_codebook.json"
                codebook_path.parent.mkdir(parents=True, exist_ok=True)
                self.harness = FinancialSovereignHarness(codebook_path=str(codebook_path))
                logger.info("✅ Financial Sovereign Harness 초기화 완료 (진화 훈련용)")
            except Exception as e:
                logger.warning(f"⚠️ Financial Sovereign Harness 초기화 실패: {e}")
        
        # 명리 컨트롤러 초기화
        self.myeongri_controller = None
        if MYEONGRI_AVAILABLE:
            try:
                config_path = workspace_root / "projects" / "bitcoin-trading" / "config" / "trading_config.yaml"
                if config_path.exists():
                    import yaml
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    
                    myeongri_config = config.get("myeongri", {})
                    if myeongri_config.get("enabled", False):
                        self.myeongri_controller = MyeongriController(
                            birth_year=myeongri_config.get("birth_year", 1990),
                            birth_month=myeongri_config.get("birth_month", 1),
                            birth_day=myeongri_config.get("birth_day", 1),
                            birth_hour=myeongri_config.get("birth_hour", 0),
                            is_solar=myeongri_config.get("is_solar", False),
                            is_male=myeongri_config.get("is_male", True)
                        )
                        logger.info("✅ 명리 컨트롤러 Phase 2 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ 명리 컨트롤러 초기화 실패: {e}")
        
        # 모델 최적화 엔진 초기화
        self.optimizer = ModelOptimizer()
        
        logger.info("✅ Time-Machine Self-Evolution Engine 초기화 완료")
        logger.info(f"   기간: {start_year}년 ~ {end_year}년 (약 {end_year - start_year}년)")
    
    def download_10_year_data(
        self,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        10년치 과거 데이터 다운로드
        
        Args:
            interval: 시간 간격
        
        Returns:
            가격 데이터 DataFrame
        """
        logger.info("📥 10년치 과거 데이터 다운로드 중...")
        logger.info(f"   심볼: {self.symbol}")
        logger.info(f"   간격: {interval}")
        logger.info(f"   기간: {self.start_year}년 ~ {self.end_year}년")
        
        try:
            import requests
            
            # Binance 공개 API 엔드포인트
            url = "https://api.binance.com/api/v3/klines"
            
            # 날짜 범위 계산
            start_date = datetime(self.start_year, 1, 1)
            end_date = datetime(self.end_year, 2, 14)  # 현재까지
            
            # 시작 시간 (밀리초)
            start_time = int(start_date.timestamp() * 1000)
            end_time = int(end_date.timestamp() * 1000)
            
            all_klines = []
            current_start = start_time
            limit = 1000  # Binance API 최대 제한
            
            logger.info(f"   시작: {start_date.strftime('%Y-%m-%d')}")
            logger.info(f"   종료: {end_date.strftime('%Y-%m-%d')}")
            
            # 배치로 데이터 다운로드
            batch_count = 0
            while current_start < end_time:
                params = {
                    'symbol': self.symbol,
                    'interval': interval,
                    'startTime': current_start,
                    'endTime': end_time,
                    'limit': limit
                }
                
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                klines = response.json()
                
                if not klines:
                    break
                
                all_klines.extend(klines)
                batch_count += 1
                
                # 다음 배치 시작 시간
                current_start = klines[-1][6] + 1  # close_time + 1ms
                
                # 진행 상황 출력
                progress = (current_start - start_time) / (end_time - start_time) * 100
                print(f"   진행: {progress:.1f}% ({len(all_klines)}개 캔들, {batch_count}배치)", end='\r')
                
                # API Rate Limit 방지
                time.sleep(0.1)
            
            logger.info("")  # 줄바꿈
            
            if not all_klines:
                logger.error("❌ 데이터를 다운로드할 수 없습니다.")
                return pd.DataFrame()
            
            # DataFrame 생성
            df = pd.DataFrame(all_klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # 날짜 컬럼 변환
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('date', inplace=True)
            
            # 숫자 형식 변환
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
                df[col] = df[col].astype(float)
            
            # 중복 제거 및 정렬
            df = df.drop_duplicates(subset=['timestamp'])
            df = df.sort_index()
            
            logger.info(f"✅ 10년치 데이터 다운로드 완료: {len(df)}개 캔들")
            logger.info(f"   기간: {df.index[0]} ~ {df.index[-1]}")
            logger.info(f"   가격 범위: ${df['low'].min():.2f} ~ ${df['high'].max():.2f}")
            
            # 데이터 저장
            data_dir = workspace_root / "projects" / "bitcoin-trading" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            data_file = data_dir / f"{self.symbol}_{interval}_10years.csv"
            df.to_csv(data_file)
            logger.info(f"💾 데이터 저장: {data_file}")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 데이터 다운로드 실패: {e}")
            return pd.DataFrame()
    
    def find_critical_points(
        self,
        historical_data: pd.DataFrame,
        min_interval_days: int = 7
    ) -> List[datetime]:
        """
        결정적 구간(Critical Points) 찾기
        
        Args:
            historical_data: 과거 데이터
            min_interval_days: 최소 간격 (일)
        
        Returns:
            결정적 구간 시점 리스트
        """
        critical_points = []
        
        # 변동성이 큰 시점 찾기
        if len(historical_data) < 30:
            return critical_points
        
        # 일일 변동률 계산
        historical_data['daily_return'] = historical_data['close'].pct_change()
        historical_data['volatility'] = historical_data['daily_return'].rolling(30).std()
        
        # 변동성이 높은 시점 (상위 10%)
        volatility_threshold = historical_data['volatility'].quantile(0.9)
        
        # 결정적 구간 추출
        last_point = None
        for idx, row in historical_data.iterrows():
            if pd.isna(row['volatility']):
                continue
            
            if row['volatility'] >= volatility_threshold:
                if last_point is None or (idx - last_point).days >= min_interval_days:
                    critical_points.append(idx)
                    last_point = idx
        
        logger.info(f"✅ 결정적 구간 {len(critical_points)}개 발견")
        
        return critical_points
    
    def evolve_ten_years(
        self,
        historical_data: pd.DataFrame,
        max_iterations: int = 1000,
        lookforward_days: int = 7
    ) -> Dict[str, Any]:
        """
        10년 자율 진화 실행
        
        Args:
            historical_data: 10년치 과거 데이터
            max_iterations: 최대 반복 횟수
            lookforward_days: 미래 데이터 일수 (검증용)
        
        Returns:
            진화 결과
        """
        logger.info("=" * 80)
        logger.info("🏛️ Time-Machine Self-Evolution 시작")
        logger.info("=" * 80)
        logger.info(f"최대 반복 횟수: {max_iterations}회")
        logger.info(f"검증 기간: {lookforward_days}일")
        
        # 결정적 구간 찾기
        critical_points = self.find_critical_points(historical_data)
        
        if len(critical_points) == 0:
            logger.error("❌ 결정적 구간을 찾을 수 없습니다.")
            return {}
        
        # 반복 횟수 제한 (결정적 구간 수와 최대 반복 횟수 중 작은 값)
        iterations = min(len(critical_points), max_iterations)
        
        results = []
        evolution_history = []
        
        for i, current_time in enumerate(critical_points[:iterations]):
            logger.info(f"\n📊 진화 반복 {i+1}/{iterations}")
            logger.info(f"   시점: {current_time.strftime('%Y-%m-%d')}")
            
            try:
                # 1. 위상 소환 및 매매 집행
                signal_result = self._invoke_signal(historical_data, current_time)
                
                if not signal_result:
                    continue
                
                # 2. 결과 검증 (Back-to-Future Verification)
                verification_result = self._verify_result(
                    historical_data,
                    current_time,
                    signal_result,
                    lookforward_days
                )
                
                # 3. 자율 진화: 손실 발생 시 가중치 자동 보정
                if verification_result.get("profit", 0) < 0:
                    adjusted_weights = self.optimizer.adjust_weights(
                        failed_vector=signal_result.get("vector_4d", {}),
                        actual_result=verification_result,
                        reason="Market Constitution Violation"
                    )
                    
                    evolution_history.append({
                        "iteration": i + 1,
                        "timestamp": current_time.isoformat(),
                        "action": "adjust_weights",
                        "original_vector": signal_result.get("vector_4d", {}),
                        "adjusted_vector": adjusted_weights,
                        "reason": "Market Constitution Violation"
                    })
                else:
                    # 성공 패턴 기록
                    self.optimizer.record_success(
                        success_vector=signal_result.get("vector_4d", {}),
                        actual_result=verification_result
                    )
                
                # 결과 저장
                results.append({
                    "iteration": i + 1,
                    "timestamp": current_time.isoformat(),
                    "signal": signal_result,
                    "verification": verification_result,
                    "evolution": evolution_history[-1] if evolution_history else None
                })
                
                # 진행 상황 로깅 (10회마다)
                if (i + 1) % 10 == 0:
                    success_count = sum(1 for r in results if r.get("verification", {}).get("profit", 0) >= 0)
                    success_rate = success_count / len(results) * 100
                    logger.info(f"   진행: {i+1}/{iterations}, 성공률: {success_rate:.1f}%")
                
                # API Rate Limit 방지
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ 진화 반복 {i+1} 실패: {e}")
                continue
        
        # 종합 결과 계산
        total_iterations = len(results)
        success_count = sum(1 for r in results if r.get("verification", {}).get("profit", 0) >= 0)
        total_profit = sum(r.get("verification", {}).get("profit", 0) for r in results)
        
        optimizer_stats = self.optimizer.get_statistics()
        
        summary = {
            "total_iterations": total_iterations,
            "success_count": success_count,
            "failure_count": total_iterations - success_count,
            "success_rate": success_count / total_iterations if total_iterations > 0 else 0.0,
            "total_profit": total_profit,
            "optimizer_stats": optimizer_stats,
            "evolution_history": evolution_history,
            "results": results[-100:] if len(results) > 100 else results  # 최근 100개만
        }
        
        logger.info("=" * 80)
        logger.info("🏛️ 자율 진화 완료")
        logger.info("=" * 80)
        logger.info(f"총 반복 횟수: {total_iterations}회")
        logger.info(f"성공 횟수: {success_count}회")
        logger.info(f"실패 횟수: {total_iterations - success_count}회")
        logger.info(f"성공률: {summary['success_rate']:.2%}")
        logger.info(f"총 수익: ${total_profit:,.2f}")
        logger.info(f"가중치 조정 횟수: {optimizer_stats['weight_adjustments_count']}회")
        
        return summary
    
    def _invoke_signal(
        self,
        historical_data: pd.DataFrame,
        current_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        위상 소환 및 매매 집행
        
        Args:
            historical_data: 전체 과거 데이터
            current_time: 현재 시점
        
        Returns:
            신호 결과
        """
        try:
            # 현재 시점 이전 데이터만 사용
            current_idx = historical_data.index.searchsorted(current_time)
            if current_idx >= len(historical_data):
                current_idx = len(historical_data) - 1
            
            blind_data = historical_data.iloc[:current_idx + 1].copy()
            
            if len(blind_data) < 30:
                return None
            
            # 전략 초기화
            strategy = CryptoNitroLiveStrategy(
                symbol=self.symbol,
                initial_capital=self.initial_capital,
                leverage=self.leverage,
                use_great_trunk_filter=True,
                binance_client=None
            )
            strategy.price_data = blind_data.copy()
            
            # 하네스 인스턴스 공유
            if self.harness and hasattr(strategy, 'harness'):
                strategy.harness = self.harness
            
            # 현재 가격
            current_price = blind_data['close'].iloc[-1]
            
            # 명리 위상(λ) 계산
            lambda_constraint = None
            if self.myeongri_controller:
                try:
                    target_year = current_time.year
                    target_month = current_time.month
                    
                    timing_result = self.myeongri_controller.judge_timing(
                        prescription_type="trading",
                        current_year=target_year,
                        current_month=target_month
                    )
                    
                    lambda_constraint = {
                        "is_optimal_timing": timing_result.get("is_optimal_timing", False),
                        "energy_mode": timing_result.get("energy_mode", "unknown"),
                        "priority": timing_result.get("priority", 0.5)
                    }
                except Exception as e:
                    logger.debug(f"명리 위상 계산 실패: {e}")
            
            # 신호 생성
            signal_data = strategy.calculate_trading_signal(
                current_price=current_price,
                current_time=current_time
            )
            
            # 4D 벡터 추출 (신호 데이터에서)
            vector_4d = signal_data.get("sovereign_vector", {})
            if not vector_4d:
                vector_4d = {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
            
            return {
                "signal": signal_data.get("signal", "HOLD"),
                "confidence": signal_data.get("confidence", 0.0),
                "vector_4d": vector_4d,
                "lambda_constraint": lambda_constraint,
                "signal_id": signal_data.get("signal_id"),
                "price": current_price
            }
            
        except Exception as e:
            logger.error(f"❌ 신호 생성 실패: {e}")
            return None
    
    def _verify_result(
        self,
        historical_data: pd.DataFrame,
        current_time: datetime,
        signal_result: Dict[str, Any],
        lookforward_days: int = 7
    ) -> Dict[str, Any]:
        """
        결과 검증 (Back-to-Future Verification)
        
        Args:
            historical_data: 전체 과거 데이터
            current_time: 현재 시점
            signal_result: 신호 결과
            lookforward_days: 미래 데이터 일수
        
        Returns:
            검증 결과
        """
        try:
            # 현재 시점 이후 데이터
            current_idx = historical_data.index.searchsorted(current_time)
            if current_idx >= len(historical_data):
                return {"profit": 0, "actual_direction": "FLAT"}
            
            future_end_idx = min(current_idx + lookforward_days, len(historical_data))
            future_data = historical_data.iloc[current_idx + 1:future_end_idx]
            
            if len(future_data) == 0:
                return {"profit": 0, "actual_direction": "FLAT"}
            
            # 실제 가격 변동
            current_price = signal_result.get("price", 0)
            future_price = future_data['close'].iloc[-1]
            price_change = (future_price - current_price) / current_price
            
            # 실제 방향
            actual_direction = "UP" if price_change > 0 else "DOWN" if price_change < 0 else "FLAT"
            
            # 수익 계산 (간단한 로직)
            signal = signal_result.get("signal", "HOLD")
            profit = 0.0
            
            if signal == "BUY" and actual_direction == "UP":
                profit = price_change * self.initial_capital * 0.3  # 자본의 30% 투자
            elif signal == "SELL" and actual_direction == "DOWN":
                profit = abs(price_change) * self.initial_capital * 0.3
            elif signal == "HOLD":
                profit = 0.0
            else:
                profit = -abs(price_change) * self.initial_capital * 0.3  # 손실
            
            return {
                "profit": profit,
                "price_change": price_change,
                "actual_direction": actual_direction,
                "current_price": current_price,
                "future_price": future_price
            }
            
        except Exception as e:
            logger.error(f"❌ 결과 검증 실패: {e}")
            return {"profit": 0, "actual_direction": "FLAT"}
    
    def save_results(self, results: Dict[str, Any], output_file: Optional[str] = None):
        """
        결과 저장
        
        Args:
            results: 진화 결과
            output_file: 출력 파일 경로
        """
        if output_file is None:
            output_file = workspace_root / "projects" / "bitcoin-trading" / "data" / "evolution_results.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"✅ 진화 결과 저장 완료: {output_path}")


if __name__ == "__main__":
    # 10년 자율 진화 실행
    logger.info("=" * 80)
    logger.info("🏛️ Time-Machine Self-Evolution Engine")
    logger.info("=" * 80)
    
    # 진화 엔진 초기화
    evolution_engine = TimeMachineSelfEvolution(
        symbol="BTCUSDT",
        initial_capital=10000.0,
        leverage=2,
        start_year=2016,
        end_year=2026
    )
    
    # 10년치 데이터 다운로드 또는 로드
    data_file = workspace_root / "projects" / "bitcoin-trading" / "data" / "BTCUSDT_1d_10years.csv"
    
    if data_file.exists():
        logger.info("📥 기존 10년치 데이터 로드 중...")
        historical_data = pd.read_csv(data_file, index_col='date', parse_dates=True)
        logger.info(f"✅ 데이터 로드 완료: {len(historical_data)}개 캔들")
    else:
        logger.info("📥 10년치 데이터 다운로드 중...")
        historical_data = evolution_engine.download_10_year_data(interval="1d")
    
    if len(historical_data) > 0:
        # 10년 자율 진화 실행
        logger.info("\n🚀 10년 자율 진화 시작 (최대 1,000회 반복)")
        results = evolution_engine.evolve_ten_years(
            historical_data,
            max_iterations=1000,
            lookforward_days=7
        )
        
        if results:
            evolution_engine.save_results(results)
            logger.info("\n✅ 10년 자율 진화 완료!")
    else:
        logger.error("❌ 과거 데이터가 없습니다.")

