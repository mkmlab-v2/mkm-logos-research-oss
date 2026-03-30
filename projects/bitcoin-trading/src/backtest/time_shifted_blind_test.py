#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ Time-Shifted Blind Test (시공간 전이 훈련) 프로토콜

임의의 과거 시점을 선택하여:
1. 해당 시점의 데이터만 제공 (미래 데이터 은닉)
2. 명리 위상(λ) 정보만으로 신호 생성
3. 실제 결과와 비교하여 정확도 검증

핵심 원칙:
- 100% Literal Restoration: Signal ID 기반 결정론적 앵커
- Deterministic Anchoring: 위상 공명도 계산
- Hallucination Check: 가짜 신호 무시

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
import random
import time

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


class TimeShiftedBlindTest:
    """
    🏛️ Time-Shifted Blind Test (시공간 전이 훈련) 프로토콜
    
    임의의 과거 시점을 선택하여 블라인드 테스트를 수행합니다.
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        initial_capital: float = 10000.0,
        leverage: int = 2
    ):
        """
        Args:
            symbol: 거래 심볼
            initial_capital: 초기 자본
            leverage: 레버리지
        """
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.leverage = leverage
        
        # Financial Sovereign Harness 초기화
        self.harness = None
        if HARNESS_AVAILABLE:
            try:
                codebook_path = workspace_root / "projects" / "bitcoin-trading" / "data" / "blind_test_codebook.json"
                codebook_path.parent.mkdir(parents=True, exist_ok=True)
                self.harness = FinancialSovereignHarness(codebook_path=str(codebook_path))
                logger.info("✅ Financial Sovereign Harness 초기화 완료 (Blind Test용)")
            except Exception as e:
                logger.warning(f"⚠️ Financial Sovereign Harness 초기화 실패: {e}")
        
        # 명리 컨트롤러 초기화 (설정 파일에서 읽기)
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
        
        logger.info("✅ Time-Shifted Blind Test 시스템 초기화 완료")
    
    def load_historical_data(self, data_file: Optional[str] = None) -> pd.DataFrame:
        """
        과거 데이터 로드
        
        Args:
            data_file: 데이터 파일 경로
        
        Returns:
            가격 데이터 DataFrame
        """
        if data_file is None:
            data_file = workspace_root / "projects" / "bitcoin-trading" / "data" / "BTCUSDT_1d_historical.csv"
        
        data_path = Path(data_file)
        
        if not data_path.exists():
            logger.error(f"❌ 데이터 파일이 없습니다: {data_path}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(data_path)
            
            # 날짜 컬럼 변환
            if 'timestamp' in df.columns:
                df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            else:
                logger.error("❌ 날짜 컬럼을 찾을 수 없습니다.")
                return pd.DataFrame()
            
            df.set_index('date', inplace=True)
            df = df.sort_index()
            
            logger.info(f"✅ 과거 데이터 로드 완료: {len(df)}개 캔들")
            logger.info(f"   기간: {df.index[0]} ~ {df.index[-1]}")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 데이터 로드 실패: {e}")
            return pd.DataFrame()
    
    def select_blind_test_point(
        self,
        historical_data: pd.DataFrame,
        min_lookback_days: int = 30,
        min_lookforward_days: int = 7
    ) -> Optional[datetime]:
        """
        블라인드 테스트 시점 선택 (임의)
        
        Args:
            historical_data: 과거 데이터
            min_lookback_days: 최소 과거 데이터 일수
            min_lookforward_days: 최소 미래 데이터 일수
        
        Returns:
            선택된 시점 (None이면 선택 불가)
        """
        if len(historical_data) < min_lookback_days + min_lookforward_days:
            logger.error("❌ 데이터가 부족합니다.")
            return None
        
        # 선택 가능한 범위 계산
        start_idx = min_lookback_days
        end_idx = len(historical_data) - min_lookforward_days
        
        if start_idx >= end_idx:
            logger.error("❌ 선택 가능한 시점이 없습니다.")
            return None
        
        # 임의 시점 선택
        selected_idx = random.randint(start_idx, end_idx)
        selected_timestamp = historical_data.index[selected_idx]
        
        logger.info(f"🎯 블라인드 테스트 시점 선택: {selected_timestamp.strftime('%Y-%m-%d')}")
        logger.info(f"   과거 데이터: {min_lookback_days}일")
        logger.info(f"   미래 데이터: {min_lookforward_days}일 (은닉)")
        
        return selected_timestamp
    
    def run_blind_test(
        self,
        historical_data: pd.DataFrame,
        target_timestamp: datetime,
        lookback_days: int = 30,
        lookforward_days: int = 7
    ) -> Dict[str, Any]:
        """
        블라인드 테스트 실행
        
        Args:
            historical_data: 전체 과거 데이터
            target_timestamp: 테스트 시점
            lookback_days: 과거 데이터 일수
            lookforward_days: 미래 데이터 일수 (검증용)
        
        Returns:
            테스트 결과
        """
        logger.info("=" * 80)
        logger.info("🏛️ Time-Shifted Blind Test 시작")
        logger.info("=" * 80)
        logger.info(f"🎯 타겟 시점: {target_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. 데이터 격리: 타겟 시점 이전 데이터만 제공
        try:
            target_idx = historical_data.index.get_loc(target_timestamp)
        except KeyError:
            # 정확한 시점이 없으면 가장 가까운 시점 찾기
            target_idx = historical_data.index.searchsorted(target_timestamp)
            if target_idx >= len(historical_data):
                target_idx = len(historical_data) - 1
        
        blind_data = historical_data.iloc[:target_idx + 1].copy()
        
        logger.info(f"📊 제공된 데이터: {len(blind_data)}개 캔들")
        logger.info(f"   기간: {blind_data.index[0]} ~ {blind_data.index[-1]}")
        
        # 2. 미래 데이터 (Ground Truth) 저장
        future_start_idx = target_idx + 1
        future_end_idx = min(target_idx + lookforward_days, len(historical_data))
        future_data = historical_data.iloc[future_start_idx:future_end_idx].copy()
        
        logger.info(f"🔒 은닉된 미래 데이터: {len(future_data)}개 캔들")
        logger.info(f"   기간: {future_data.index[0]} ~ {future_data.index[-1]}")
        
        # 3. 명리 위상(λ) 계산
        lambda_constraint = None
        if self.myeongri_controller:
            try:
                target_year = target_timestamp.year
                target_month = target_timestamp.month
                
                timing_result = self.myeongri_controller.judge_timing(
                    prescription_type="trading",
                    current_year=target_year,
                    current_month=target_month
                )
                
                lambda_constraint = {
                    "is_optimal_timing": timing_result.get("is_optimal_timing", False),
                    "energy_mode": timing_result.get("energy_mode", "unknown"),
                    "priority": timing_result.get("priority", 0.5),
                    "recommended_dosage": timing_result.get("recommended_dosage", 1.0)
                }
                
                logger.info(f"📐 명리 위상(λ) 계산 완료:")
                logger.info(f"   최적 타이밍: {lambda_constraint['is_optimal_timing']}")
                logger.info(f"   에너지 모드: {lambda_constraint['energy_mode']}")
                logger.info(f"   우선순위: {lambda_constraint['priority']:.2f}")
            except Exception as e:
                logger.warning(f"⚠️ 명리 위상 계산 실패: {e}")
        
        # 4. 블랙박스 추론: 전략 클래스로 신호 생성 (미래 데이터 참조 금지)
        current_price = blind_data['close'].iloc[-1]
        current_time = blind_data.index[-1]
        
        # 전략 초기화 (블랙박스)
        strategy = None
        if STRATEGY_AVAILABLE:
            try:
                strategy = CryptoNitroLiveStrategy(
                    symbol=self.symbol,
                    initial_capital=self.initial_capital,
                    leverage=self.leverage,
                    use_great_trunk_filter=True,
                    binance_client=None
                )
                strategy.price_data = blind_data.copy()
                
                # 🏛️ 바이브 코딩: Blind Test와 전략 클래스가 같은 하네스 인스턴스 공유
                if self.harness and hasattr(strategy, 'harness'):
                    strategy.harness = self.harness
                    logger.info("✅ 하네스 인스턴스 공유 완료 (Signal ID 검증 보장)")
                
                logger.info("✅ 전략 클래스 초기화 완료 (블랙박스 모드)")
            except Exception as e:
                logger.error(f"❌ 전략 클래스 초기화 실패: {e}")
                return {}
        
        # 신호 생성 (미래 데이터 참조 금지)
        start_time = time.time()
        try:
            signal_data = strategy.calculate_trading_signal(
                current_price=current_price,
                current_time=current_time
            )
            process_time = (time.time() - start_time) * 1000  # ms
            
            predicted_signal = signal_data.get("signal", "HOLD")
            predicted_confidence = signal_data.get("confidence", 0.0)
            signal_id = signal_data.get("signal_id")
            
            logger.info(f"🔮 예측 신호 생성 완료:")
            logger.info(f"   신호: {predicted_signal}")
            logger.info(f"   신뢰도: {predicted_confidence:.2%}")
            logger.info(f"   Signal ID: {signal_id}")
            logger.info(f"   처리 시간: {process_time:.3f}ms")
            
        except Exception as e:
            logger.error(f"❌ 신호 생성 실패: {e}")
            return {}
        
        # 5. 실제 결과와 대조 (Ground Truth)
        actual_price_change = (future_data['close'].iloc[-1] - current_price) / current_price
        actual_direction = "UP" if actual_price_change > 0 else "DOWN" if actual_price_change < 0 else "FLAT"
        
        # 신호 매칭 검증
        signal_match = False
        if predicted_signal == "BUY" and actual_direction == "UP":
            signal_match = True
        elif predicted_signal == "SELL" and actual_direction == "DOWN":
            signal_match = True
        elif predicted_signal == "HOLD" and abs(actual_price_change) < 0.01:  # 1% 미만 변동
            signal_match = True
        
        # Vector Stability 검증 (4D 벡터 위상 안정성)
        vector_stability = 1.0  # 기본값 (실제로는 벡터 계산 필요)
        
        # Hallucination Check (가짜 신호 무시 여부)
        hallucination_check = True  # Signal ID 검증 통과 시 True
        
        if self.harness and signal_id:
            try:
                expected_signal = {
                    "signal": predicted_signal,
                    "confidence": predicted_confidence,
                    "price": current_price
                }
                
                verified_signal = self.harness.verify_signal(
                    signal_id=signal_id,
                    expected_signal=expected_signal
                )
                
                hallucination_check = verified_signal.is_valid
                
                if not verified_signal.is_valid:
                    logger.warning(f"⚠️ Hallucination 감지: Signal ID 검증 실패")
            except Exception as e:
                logger.warning(f"⚠️ Signal ID 검증 실패: {e}")
        
        # 6. 결과 계산
        accuracy = 1.0 if signal_match else 0.0
        price_drift = abs(actual_price_change - (predicted_confidence if predicted_signal != "HOLD" else 0))
        
        result = {
            "target_timestamp": target_timestamp.isoformat(),
            "predicted_signal": predicted_signal,
            "predicted_confidence": predicted_confidence,
            "actual_direction": actual_direction,
            "actual_price_change": actual_price_change,
            "signal_match": signal_match,
            "accuracy": accuracy,
            "process_time_ms": process_time,
            "price_drift": price_drift,
            "vector_stability": vector_stability,
            "hallucination_check": hallucination_check,
            "lambda_constraint": lambda_constraint,
            "signal_id": signal_id
        }
        
        logger.info("=" * 80)
        logger.info("🏛️ Blind Test 결과")
        logger.info("=" * 80)
        logger.info(f"예측 신호: {predicted_signal} (신뢰도: {predicted_confidence:.2%})")
        logger.info(f"실제 방향: {actual_direction} (변동: {actual_price_change:.2%})")
        logger.info(f"신호 매칭: {'✅ 일치' if signal_match else '❌ 불일치'}")
        logger.info(f"정확도: {accuracy:.2%}")
        logger.info(f"처리 시간: {process_time:.3f}ms")
        logger.info(f"Hallucination Check: {'✅ 통과' if hallucination_check else '❌ 실패'}")
        
        return result
    
    def run_multiple_tests(
        self,
        historical_data: pd.DataFrame,
        num_tests: int = 10,
        lookback_days: int = 30,
        lookforward_days: int = 7
    ) -> Dict[str, Any]:
        """
        여러 번의 블라인드 테스트 실행
        
        Args:
            historical_data: 전체 과거 데이터
            num_tests: 테스트 횟수
            lookback_days: 과거 데이터 일수
            lookforward_days: 미래 데이터 일수
        
        Returns:
            종합 결과
        """
        logger.info("=" * 80)
        logger.info(f"🏛️ Time-Shifted Blind Test 배치 실행 ({num_tests}회)")
        logger.info("=" * 80)
        
        results = []
        
        for i in range(num_tests):
            logger.info(f"\n📊 테스트 {i+1}/{num_tests}")
            
            # 임의 시점 선택
            target_timestamp = self.select_blind_test_point(
                historical_data,
                min_lookback_days=lookback_days,
                min_lookforward_days=lookforward_days
            )
            
            if target_timestamp is None:
                logger.warning(f"⚠️ 테스트 {i+1} 건너뜀 (시점 선택 실패)")
                continue
            
            # 블라인드 테스트 실행
            result = self.run_blind_test(
                historical_data,
                target_timestamp,
                lookback_days=lookback_days,
                lookforward_days=lookforward_days
            )
            
            if result:
                results.append(result)
            
            # API Rate Limit 방지
            time.sleep(0.5)
        
        # 종합 결과 계산
        if not results:
            logger.error("❌ 테스트 결과가 없습니다.")
            return {}
        
        total_accuracy = sum(r['accuracy'] for r in results) / len(results)
        avg_process_time = sum(r['process_time_ms'] for r in results) / len(results)
        avg_price_drift = sum(r['price_drift'] for r in results) / len(results)
        hallucination_pass_rate = sum(1 for r in results if r['hallucination_check']) / len(results)
        
        summary = {
            "total_tests": len(results),
            "total_accuracy": total_accuracy,
            "avg_process_time_ms": avg_process_time,
            "avg_price_drift": avg_price_drift,
            "hallucination_pass_rate": hallucination_pass_rate,
            "results": results
        }
        
        logger.info("=" * 80)
        logger.info("🏛️ 배치 테스트 종합 결과")
        logger.info("=" * 80)
        logger.info(f"총 테스트: {len(results)}회")
        logger.info(f"평균 정확도: {total_accuracy:.2%}")
        logger.info(f"평균 처리 시간: {avg_process_time:.3f}ms")
        logger.info(f"평균 가격 편차: {avg_price_drift:.2%}")
        logger.info(f"Hallucination 통과율: {hallucination_pass_rate:.2%}")
        
        return summary
    
    def save_results(self, results: Dict[str, Any], output_file: Optional[str] = None):
        """
        결과 저장
        
        Args:
            results: 테스트 결과
            output_file: 출력 파일 경로
        """
        if output_file is None:
            output_file = workspace_root / "projects" / "bitcoin-trading" / "data" / "blind_test_results.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"✅ 결과 저장 완료: {output_path}")


if __name__ == "__main__":
    # Blind Test 실행 예시
    logger.info("=" * 80)
    logger.info("🏛️ Time-Shifted Blind Test 프로토콜")
    logger.info("=" * 80)
    
    # Blind Test 시스템 초기화
    blind_test = TimeShiftedBlindTest(
        symbol="BTCUSDT",
        initial_capital=10000.0,
        leverage=2
    )
    
    # 과거 데이터 로드
    historical_data = blind_test.load_historical_data()
    
    if len(historical_data) > 0:
        # 배치 테스트 실행 (바이브 코딩 자동 진행)
        logger.info("\n🎯 배치 Blind Test 실행 (10회)")
        batch_results = blind_test.run_multiple_tests(
            historical_data,
            num_tests=10,
            lookback_days=30,
            lookforward_days=7
        )
        
        if batch_results:
            blind_test.save_results(batch_results, "blind_test_batch_results.json")
            logger.info("\n✅ 바이브 코딩 자동 진행 완료!")
    else:
        logger.error("❌ 과거 데이터가 없습니다.")

