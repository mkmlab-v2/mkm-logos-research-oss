#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 금화교역 감지기 파라미터 최적화 시스템

손절/익절 비율, 진입 조건, T_transition 임계값 최적화

작성일: 2026-01-21
목적: 승률 60-75%, 수익 팩터 1.5 이상 달성
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
import json
import logging
from itertools import product

# 워크스페이스 루트
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
BITCOIN_TRADING_ROOT = Path(__file__).parent.parent.parent
SRC_ROOT = BITCOIN_TRADING_ROOT / "src"

sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(BITCOIN_TRADING_ROOT))
sys.path.insert(0, str(SRC_ROOT))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# GeumHwaDetector import
try:
    from src.strategy.geum_hwa_detector import GeumHwaDetector
    DETECTOR_AVAILABLE = True
except ImportError:
    try:
        from strategy.geum_hwa_detector import GeumHwaDetector
        DETECTOR_AVAILABLE = True
    except ImportError:
        DETECTOR_AVAILABLE = False
        logger.error("⚠️ GeumHwaDetector를 찾을 수 없습니다.")

# 백테스터 import
try:
    from src.analysis.geum_hwa_backtester import GeumHwaBacktester
    BACKTESTER_AVAILABLE = True
except ImportError:
    try:
        from analysis.geum_hwa_backtester import GeumHwaBacktester
        BACKTESTER_AVAILABLE = True
    except ImportError:
        BACKTESTER_AVAILABLE = False
        logger.error("⚠️ GeumHwaBacktester를 찾을 수 없습니다.")


class GeumHwaParameterOptimizer:
    """금화교역 감지기 파라미터 최적화 클래스"""
    
    def __init__(
        self,
        constitution: str = "TY",
        initial_capital: float = 1000.0
    ):
        """
        Args:
            constitution: 체질 (TY, TE, SE, SY)
            initial_capital: 초기 자본
        """
        if not DETECTOR_AVAILABLE or not BACKTESTER_AVAILABLE:
            raise ImportError("필요한 모듈을 찾을 수 없습니다.")
        
        self.constitution = constitution
        self.initial_capital = initial_capital
        self.results = []
    
    def optimize_parameters(
        self,
        df: pd.DataFrame,
        stop_loss_range: Tuple[float, float, float] = (0.03, 0.07, 0.01),  # 3% ~ 7%, 1% 간격
        take_profit_range: Tuple[float, float, float] = (0.08, 0.15, 0.01),  # 8% ~ 15%, 1% 간격
        min_indicators_range: Tuple[int, int] = (1, 3),  # 최소 지표 개수 1~3
        position_size: float = 0.3
    ) -> Dict[str, Any]:
        """
        파라미터 그리드 서치 최적화
        
        Args:
            df: 백테스트 데이터
            stop_loss_range: 손절 비율 범위 (min, max, step)
            take_profit_range: 익절 비율 범위 (min, max, step)
            min_indicators_range: 최소 지표 개수 범위 (min, max)
            position_size: 포지션 크기
        
        Returns:
            최적 파라미터 및 결과
        """
        logger.info("🔍 파라미터 최적화 시작...")
        
        # 파라미터 그리드 생성
        stop_loss_values = np.arange(
            stop_loss_range[0],
            stop_loss_range[1] + stop_loss_range[2],
            stop_loss_range[2]
        )
        take_profit_values = np.arange(
            take_profit_range[0],
            take_profit_range[1] + take_profit_range[2],
            take_profit_range[2]
        )
        min_indicators_values = range(
            min_indicators_range[0],
            min_indicators_range[1] + 1
        )
        
        total_combinations = len(stop_loss_values) * len(take_profit_values) * len(min_indicators_values)
        logger.info(f"   총 {total_combinations}개 조합 테스트 예정")
        
        best_result = None
        best_score = -np.inf
        
        # 그리드 서치
        for i, (stop_loss, take_profit, min_indicators) in enumerate(
            product(stop_loss_values, take_profit_values, min_indicators_values)
        ):
            if (i + 1) % 10 == 0:
                logger.info(f"   진행: {i + 1}/{total_combinations} ({100 * (i + 1) / total_combinations:.1f}%)")
            
            # 백테스트 실행
            result = self._run_backtest_with_params(
                df=df,
                stop_loss=stop_loss,
                take_profit=take_profit,
                min_indicators=min_indicators,
                position_size=position_size
            )
            
            if result is None:
                continue
            
            # 점수 계산 (승률 * 수익 팩터 * (1 - 최대 낙폭))
            win_rate = result.get('win_rate', 0.0)
            profit_factor = result.get('profit_factor', 0.0)
            max_drawdown = result.get('max_drawdown_pct', 1.0) / 100.0
            
            # 목표: 승률 60-75%, 수익 팩터 1.5 이상
            score = win_rate * profit_factor * (1.0 - max_drawdown)
            
            result['score'] = score
            result['stop_loss'] = stop_loss
            result['take_profit'] = take_profit
            result['min_indicators'] = min_indicators
            
            self.results.append(result)
            
            # 최적 결과 업데이트
            if score > best_score:
                best_score = score
                best_result = result
        
        logger.info(f"✅ 최적화 완료: {len(self.results)}개 결과")
        
        return {
            'best_params': {
                'stop_loss': best_result['stop_loss'],
                'take_profit': best_result['take_profit'],
                'min_indicators': best_result['min_indicators'],
                'position_size': position_size
            },
            'best_result': best_result,
            'all_results': self.results
        }
    
    def _run_backtest_with_params(
        self,
        df: pd.DataFrame,
        stop_loss: float,
        take_profit: float,
        min_indicators: int,
        position_size: float
    ) -> Dict[str, Any]:
        """
        특정 파라미터로 백테스트 실행
        
        Args:
            df: 백테스트 데이터
            stop_loss: 손절 비율
            take_profit: 익절 비율
            min_indicators: 최소 지표 개수
            position_size: 포지션 크기
        
        Returns:
            백테스트 결과
        """
        try:
            # 백테스터 생성
            backtester = GeumHwaBacktester(
                constitution=self.constitution,
                initial_capital=self.initial_capital,
                commission_rate=0.001
            )
            
            # GeumHwaDetector에 최소 지표 개수 설정 (임시)
            # 실제로는 detect_geum_hwa_transition 함수를 수정해야 함
            # 여기서는 백테스터의 run_backtest에 파라미터 전달
            
            # 백테스트 실행
            results = backtester.run_backtest(
                df=df,
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                min_indicators=min_indicators  # 추가 파라미터
            )
            
            return results
        
        except Exception as e:
            logger.warning(f"⚠️ 백테스트 실패 (stop_loss={stop_loss}, take_profit={take_profit}, min_indicators={min_indicators}): {e}")
            return None
    
    def print_optimization_results(self, optimization_result: Dict[str, Any]):
        """최적화 결과 출력"""
        print("\n" + "="*80)
        print("🏛️ 금화교역 감지기 파라미터 최적화 결과")
        print("="*80)
        
        best_params = optimization_result['best_params']
        best_result = optimization_result['best_result']
        
        print(f"\n📊 최적 파라미터:")
        print(f"  손절 비율: {best_params['stop_loss']*100:.1f}%")
        print(f"  익절 비율: {best_params['take_profit']*100:.1f}%")
        print(f"  최소 지표 개수: {best_params['min_indicators']}개")
        print(f"  포지션 크기: {best_params['position_size']*100:.0f}%")
        
        print(f"\n📈 최적 성과:")
        print(f"  총 수익률: {best_result.get('total_return_pct', 0.0):.2f}%")
        print(f"  승률: {best_result.get('win_rate', 0.0)*100:.2f}%")
        print(f"  수익 팩터: {best_result.get('profit_factor', 0.0):.2f}")
        print(f"  최대 낙폭: {best_result.get('max_drawdown_pct', 0.0):.2f}%")
        print(f"  총 거래 횟수: {best_result.get('total_trades', 0)}회")
        print(f"  점수: {best_result.get('score', 0.0):.4f}")
        
        # 상위 5개 결과 출력
        sorted_results = sorted(
            self.results,
            key=lambda x: x.get('score', 0.0),
            reverse=True
        )[:5]
        
        print(f"\n🏆 상위 5개 결과:")
        for i, result in enumerate(sorted_results, 1):
            print(f"\n  {i}. 손절={result['stop_loss']*100:.1f}%, 익절={result['take_profit']*100:.1f}%, "
                  f"지표={result['min_indicators']}개")
            print(f"     승률={result.get('win_rate', 0.0)*100:.2f}%, "
                  f"수익팩터={result.get('profit_factor', 0.0):.2f}, "
                  f"점수={result.get('score', 0.0):.4f}")
        
        print("\n" + "="*80)


def main():
    """메인 함수"""
    print("🏛️ 금화교역 감지기 파라미터 최적화 시스템")
    print("="*80)
    
    # 최적화기 생성
    optimizer = GeumHwaParameterOptimizer(
        constitution="TY",  # 태양인
        initial_capital=1000.0
    )
    
    # 데이터 로드
    print("\n📥 데이터 로드 중...")
    backtester = GeumHwaBacktester(
        constitution="TY",
        initial_capital=1000.0
    )
    
    # CSV 파일에서 데이터 로드
    data_dir = BITCOIN_TRADING_ROOT / "data"
    csv_file = data_dir / "BTCUSDT_1h.csv"
    
    if not csv_file.exists():
        print(f"❌ 데이터 파일을 찾을 수 없습니다: {csv_file}")
        print("   먼저 download_binance_data.py를 실행하세요.")
        sys.exit(1)
    
    df = pd.read_csv(csv_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"✅ 데이터 로드 완료: {len(df)}개 캔들")
    print(f"   기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")
    
    # 파라미터 최적화 실행
    print("\n🚀 파라미터 최적화 실행 중...")
    print("   (이 작업은 시간이 걸릴 수 있습니다)")
    
    # Phase 2-2: 손절/익절 비율 재최적화 (고밀도 사격 모드)
    # 목표: 수익 팩터 1.5 이상, 승률 60-75%
    optimization_result = optimizer.optimize_parameters(
        df=df,
        stop_loss_range=(0.02, 0.03, 0.005),  # 2% ~ 3%, 0.5% 간격
        take_profit_range=(0.12, 0.15, 0.01),  # 12% ~ 15%, 1% 간격
        min_indicators_range=(2, 2),  # 최소 지표 개수 2개 (고정, A등급 상전이 세팅)
        position_size=0.3
    )
    
    # 결과 출력
    optimizer.print_optimization_results(optimization_result)
    
    # 결과 저장
    output_dir = BITCOIN_TRADING_ROOT / "backtest_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"parameter_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # JSON 직렬화 가능한 형태로 변환
    results_json = {
        'best_params': optimization_result['best_params'],
        'best_result': {
            k: v for k, v in optimization_result['best_result'].items()
            if k not in ['equity_curve', 'trades']
        },
        'top_5_results': [
            {
                k: v for k, v in result.items()
                if k not in ['equity_curve', 'trades']
            }
            for result in sorted(
                optimizer.results,
                key=lambda x: x.get('score', 0.0),
                reverse=True
            )[:5]
        ]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_json, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 결과 저장: {output_file}")
    print("\n✅ 최적화 완료!")


if __name__ == "__main__":
    main()

