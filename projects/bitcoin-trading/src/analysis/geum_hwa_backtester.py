#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 금화교역 감지기 백테스트 시스템 (Geum-Hwa Detector Backtester)

Phase 1 & 2 완료 후 새로운 수식과 임계값 검증
544편 논문 분석 기반 정확한 수식 적용

작성일: 2026-01-21
목적: 금화교역 스나이핑 알고리즘의 실전 성능 검증
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import json
import logging

# 워크스페이스 루트
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
BITCOIN_TRADING_ROOT = Path(__file__).parent.parent.parent
SRC_ROOT = Path(__file__).parent.parent

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
    except ImportError as e:
        DETECTOR_AVAILABLE = False
        logger.error(f"⚠️ GeumHwaDetector를 찾을 수 없습니다: {e}")

# Binance API import
try:
    from src.api.binance_client import BinanceClient
    BINANCE_AVAILABLE = True
except ImportError:
    try:
        from api.binance_client import BinanceClient
        BINANCE_AVAILABLE = True
    except ImportError as e:
        BINANCE_AVAILABLE = False
        logger.warning(f"⚠️ BinanceClient를 찾을 수 없습니다: {e}")


class GeumHwaBacktester:
    """
    🏛️ 금화교역 감지기 백테스트 시스템
    
    과거 데이터를 사용하여 새로운 수식과 임계값의 성능을 검증합니다.
    """
    
    def __init__(
        self,
        constitution: str = "TY",
        initial_capital: float = 1000.0,
        commission_rate: float = 0.001  # 0.1% 수수료
    ):
        """
        Args:
            constitution: 체질 (TY: 태양인, 기본값)
            initial_capital: 초기 자본금 (USDT)
            commission_rate: 거래 수수료율
        """
        if not DETECTOR_AVAILABLE:
            raise ImportError("GeumHwaDetector를 import할 수 없습니다.")
        
        # 백테스트에서는 위상 공명 팩트체크 비활성화 (벡터 추정이 단순함)
        self.detector = GeumHwaDetector(constitution=constitution, enable_phase_resonance=False)
        self.constitution = constitution
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        
        # 백테스트 상태
        self.capital = initial_capital
        self.position = 0.0  # 포지션 크기 (USDT)
        self.entry_price = 0.0
        self.trades = []
        self.equity_curve = []
        
        # 성능 지표
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.max_drawdown = 0.0
        self.peak_capital = initial_capital
        
    def load_historical_data(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1h",
        start_date: str = None,
        end_date: str = None,
        days: int = 30
    ) -> pd.DataFrame:
        """
        과거 데이터 로드 (Binance API 또는 CSV 파일)
        
        Args:
            symbol: 거래 심볼
            interval: 시간 간격 (1h, 4h, 1d 등)
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            days: 시작 날짜로부터 며칠 전 데이터 (start_date가 None일 때)
        
        Returns:
            DataFrame with columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        """
        # 먼저 CSV 파일 확인 (다운로드 스크립트로 생성된 파일)
        data_dir = BITCOIN_TRADING_ROOT / "data"
        csv_file = data_dir / f"{symbol}_{interval}.csv"
        
        if csv_file.exists():
            logger.info(f"📥 CSV 파일에서 데이터 로드: {csv_file}")
            df = pd.read_csv(csv_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            logger.info(f"✅ 데이터 로드 완료: {len(df)}개 캔들")
            logger.info(f"   기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")
            return df
        
        try:
            if BINANCE_AVAILABLE:
                # Binance API로 데이터 로드
                client = BinanceClient()
                
                if end_date is None:
                    end_date = datetime.now()
                else:
                    end_date = datetime.strptime(end_date, "%Y-%m-%d")
                
                if start_date is None:
                    start_date = end_date - timedelta(days=days)
                else:
                    start_date = datetime.strptime(start_date, "%Y-%m-%d")
                
                # Binance API 호출
                klines = client.get_klines(
                    symbol=symbol,
                    interval=interval,
                    start_time=int(start_date.timestamp() * 1000),
                    end_time=int(end_date.timestamp() * 1000)
                )
                
                # DataFrame 변환
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                # 타입 변환
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['open'] = df['open'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['close'] = df['close'].astype(float)
                df['volume'] = df['volume'].astype(float)
                
                return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            else:
                # CSV 파일로부터 로드 (대안)
                csv_path = WORKSPACE_ROOT / "projects" / "bitcoin-trading" / "data" / f"{symbol}_{interval}.csv"
                if csv_path.exists():
                    df = pd.read_csv(csv_path)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    return df
                else:
                    raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {csv_path}")
        
        except Exception as e:
            logger.error(f"⚠️ 과거 데이터 로드 실패: {e}")
            # 샘플 데이터 생성 (테스트용)
            logger.warning("샘플 데이터를 생성합니다...")
            return self._generate_sample_data(days=days)
    
    def _generate_sample_data(self, days: int = 30) -> pd.DataFrame:
        """샘플 데이터 생성 (테스트용)"""
        dates = pd.date_range(end=datetime.now(), periods=days*24, freq='1H')
        
        # 랜덤 워크 + 트렌드
        np.random.seed(42)
        price = 50000.0
        prices = []
        volumes = []
        
        for i in range(len(dates)):
            # 가격 변화 (랜덤 워크 + 약한 트렌드)
            change = np.random.normal(0, 0.01) + 0.0001
            price *= (1 + change)
            prices.append(price)
            
            # 거래량 (가격 변동성과 연관)
            volume = np.random.uniform(100, 1000) * abs(change) * 10
            volumes.append(volume)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
            'close': prices,
            'volume': volumes
        })
        
        return df
    
    def run_backtest(
        self,
        df: pd.DataFrame,
        position_size: float = 0.3,  # 자본금의 30%
        stop_loss: float = 0.05,  # 5% 손절
        take_profit: float = 0.10,  # 10% 익절
        min_indicators: Optional[int] = None  # 최소 지표 개수 (None이면 체질별 기본값 사용)
    ) -> Dict[str, Any]:
        """
        백테스트 실행
        
        Args:
            df: 과거 데이터 DataFrame
            position_size: 포지션 크기 비율 (0.0 ~ 1.0)
            stop_loss: 손절 비율
            take_profit: 익절 비율
        
        Returns:
            백테스트 결과 딕셔너리
        """
        logger.info(f"🚀 백테스트 시작: {len(df)}개 캔들, 초기 자본: ${self.initial_capital:.2f}")
        
        # 초기화
        self.capital = self.initial_capital
        self.position = 0.0
        self.entry_price = 0.0
        self.trades = []
        self.equity_curve = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.max_drawdown = 0.0
        self.peak_capital = self.initial_capital
        
        # 최소 윈도우 크기 확인
        min_window = max(30, 20 + 5 + 1)  # IEG 계산을 위한 최소 윈도우
        if len(df) < min_window:
            logger.warning(f"⚠️ 데이터가 부족합니다 (최소 {min_window}개 필요)")
            return self._get_results()
        
        # 백테스트 루프
        for i in range(min_window, len(df)):
            current_data = df.iloc[:i+1]
            current_price = current_data['close'].iloc[-1]
            current_volume = current_data['volume'].iloc[-1]
            
            # 가격 시리즈와 거래량 시리즈
            price_series = current_data['close']
            volume_series = current_data['volume']
            
            # 4D 벡터 생성 (간단한 추정)
            # 실제로는 증류 엔진을 사용해야 하지만, 백테스트에서는 간단한 추정 사용
            vector_4d = self._estimate_vector_4d(current_data)
            
            # 금화교역 감지
            try:
                result = self.detector.detect_geum_hwa_transition(
                    price_series=price_series,
                    volume_series=volume_series,
                    vector_4d=vector_4d,
                    window=20,
                    min_indicators=min_indicators
                )
                
                t_transition = result.get("t_transition", 0.0)
                sniping_signal = result.get("sniping_signal", "HOLD")
                transition_detected = result.get("transition_detected", False)
                
                # 포지션 관리
                if self.position > 0:
                    # 포지션이 있을 때: 손절/익절 체크
                    profit_pct = (current_price - self.entry_price) / self.entry_price
                    
                    if profit_pct <= -stop_loss:
                        # 손절
                        self._close_position(current_price, "STOP_LOSS", profit_pct)
                    elif profit_pct >= take_profit:
                        # 익절
                        self._close_position(current_price, "TAKE_PROFIT", profit_pct)
                    elif sniping_signal == "SELL" and transition_detected:
                        # 금화교역 신호로 청산
                        self._close_position(current_price, "GEUM_HWA_SELL", profit_pct)
                
                elif sniping_signal == "BUY" and transition_detected:
                    # 진입 신호
                    if self.capital > 0:
                        self._open_position(current_price, position_size, t_transition)
                
                # 자본 업데이트
                current_equity = self.capital + (self.position * current_price if self.position > 0 else 0)
                self.equity_curve.append({
                    'timestamp': current_data['timestamp'].iloc[-1],
                    'equity': current_equity,
                    'capital': self.capital,
                    'position': self.position,
                    'price': current_price,
                    't_transition': t_transition
                })
                
                # 최대 낙폭 업데이트
                if current_equity > self.peak_capital:
                    self.peak_capital = current_equity
                else:
                    drawdown = (self.peak_capital - current_equity) / self.peak_capital
                    if drawdown > self.max_drawdown:
                        self.max_drawdown = drawdown
            
            except Exception as e:
                logger.warning(f"⚠️ 백테스트 루프 오류 (인덱스 {i}): {e}")
                continue
        
        # 최종 포지션 청산
        if self.position > 0:
            final_price = df['close'].iloc[-1]
            profit_pct = (final_price - self.entry_price) / self.entry_price
            self._close_position(final_price, "FINAL_CLOSE", profit_pct)
        
        return self._get_results()
    
    def _estimate_vector_4d(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        4D 벡터 추정 (백테스트용 간단한 추정)
        
        실제로는 증류 엔진을 사용해야 하지만, 백테스트에서는 간단한 추정 사용
        """
        recent = df.tail(20)
        
        # S (Spirit): 가격 모멘텀
        momentum = (recent['close'].iloc[-1] - recent['close'].iloc[0]) / recent['close'].iloc[0]
        S = max(0.0, min(1.0, 0.25 + momentum * 2))
        
        # L (Logic): 변동성
        volatility = recent['close'].std() / recent['close'].mean()
        L = max(0.0, min(1.0, 0.25 + volatility * 10))
        
        # K (Knowledge): 거래량 추세
        volume_trend = (recent['volume'].iloc[-1] - recent['volume'].mean()) / recent['volume'].mean()
        K = max(0.0, min(1.0, 0.25 + volume_trend * 0.5))
        
        # M (Material): 가격 위치 (고점 대비)
        price_position = (recent['close'].iloc[-1] - recent['low'].min()) / (recent['high'].max() - recent['low'].min())
        M = max(0.0, min(1.0, 0.25 + (price_position - 0.5) * 0.5))
        
        # 정규화
        total = S + L + K + M
        if total > 0:
            return {
                "S": S / total,
                "L": L / total,
                "K": K / total,
                "M": M / total
            }
        else:
            return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    
    def _open_position(self, price: float, position_size: float, t_transition: float):
        """포지션 진입"""
        position_value = self.capital * position_size
        self.position = position_value / price
        self.entry_price = price
        self.capital -= position_value
        
        logger.debug(f"📈 진입: 가격=${price:.2f}, 포지션={self.position:.6f} BTC, T_transition={t_transition:.3f}")
    
    def _close_position(self, price: float, reason: str, profit_pct: float):
        """포지션 청산"""
        if self.position <= 0:
            return
        
        position_value = self.position * price
        commission = position_value * self.commission_rate
        net_value = position_value - commission
        
        self.capital += net_value
        
        # 거래 기록
        trade = {
            'entry_price': self.entry_price,
            'exit_price': price,
            'profit_pct': profit_pct,
            'profit_usdt': net_value - (self.position * self.entry_price),
            'reason': reason,
            'position_size': self.position
        }
        self.trades.append(trade)
        
        # 통계 업데이트
        self.total_trades += 1
        if profit_pct > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        self.total_profit += trade['profit_usdt']
        
        logger.info(
            f"📉 청산 ({reason}): "
            f"가격=${price:.2f}, 수익률={profit_pct*100:.2f}%, "
            f"수익=${trade['profit_usdt']:.2f}"
        )
        
        # 포지션 초기화
        self.position = 0.0
        self.entry_price = 0.0
    
    def _get_results(self) -> Dict[str, Any]:
        """백테스트 결과 반환"""
        final_equity = self.capital + (self.position * self.equity_curve[-1]['price'] if self.position > 0 and self.equity_curve else self.capital)
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # 승률 계산 (0.0 ~ 1.0 범위)
        win_rate = (self.winning_trades / self.total_trades) if self.total_trades > 0 else 0.0
        
        avg_profit = np.mean([t['profit_pct'] for t in self.trades]) if self.trades else 0.0
        avg_loss = np.mean([t['profit_pct'] for t in self.trades if t['profit_pct'] < 0]) if any(t['profit_pct'] < 0 for t in self.trades) else 0.0
        
        profit_factor = abs(sum(t['profit_usdt'] for t in self.trades if t['profit_usdt'] > 0) / 
                          sum(t['profit_usdt'] for t in self.trades if t['profit_usdt'] < 0)) if any(t['profit_usdt'] < 0 for t in self.trades) else float('inf')
        
        return {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'total_profit': self.total_profit,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'avg_profit_pct': avg_profit * 100,
            'avg_loss_pct': avg_loss * 100,
            'profit_factor': profit_factor,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown * 100,
            'constitution': self.constitution,
            'equity_curve': self.equity_curve,
            'trades': self.trades
        }
    
    def print_results(self, results: Dict[str, Any]):
        """백테스트 결과 출력"""
        print("\n" + "="*80)
        print("🏛️ 금화교역 감지기 백테스트 결과")
        print("="*80)
        print(f"\n📊 기본 통계:")
        print(f"  초기 자본: ${results['initial_capital']:.2f}")
        print(f"  최종 자산: ${results['final_equity']:.2f}")
        print(f"  총 수익률: {results['total_return_pct']:.2f}%")
        print(f"  총 수익: ${results['total_profit']:.2f}")
        
        print(f"\n📈 거래 통계:")
        print(f"  총 거래 횟수: {results['total_trades']}회")
        print(f"  승리 거래: {results['winning_trades']}회")
        print(f"  손실 거래: {results['losing_trades']}회")
        print(f"  승률: {results['win_rate']*100:.2f}%")
        
        if results['total_trades'] > 0:
            print(f"  평균 수익률: {results['avg_profit_pct']:.2f}%")
            if results['avg_loss_pct'] < 0:
                print(f"  평균 손실률: {results['avg_loss_pct']:.2f}%")
            print(f"  수익 팩터: {results['profit_factor']:.2f}")
        
        print(f"\n🛡️ 리스크 지표:")
        print(f"  최대 낙폭: {results['max_drawdown_pct']:.2f}%")
        
        print(f"\n🏛️ 체질 정보:")
        print(f"  체질: {results['constitution']}")
        if results['constitution'] == "TY":
            print(f"  태양인 보정 계수 적용: α = 1.2")
        
        print("\n" + "="*80)


def main():
    """메인 함수"""
    print("🏛️ 금화교역 감지기 백테스트 시스템")
    print("="*80)
    
    # 백테스터 생성
    backtester = GeumHwaBacktester(
        constitution="TY",  # 태양인
        initial_capital=1000.0,
        commission_rate=0.001
    )
    
    # 과거 데이터 로드
    print("\n📥 과거 데이터 로드 중...")
    try:
        df = backtester.load_historical_data(
            symbol="BTCUSDT",
            interval="1h",
            days=30  # 최근 30일
        )
        print(f"✅ 데이터 로드 완료: {len(df)}개 캔들")
        print(f"   기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")
    except Exception as e:
        logger.error(f"❌ 데이터 로드 실패: {e}")
        print("⚠️ 샘플 데이터로 진행합니다...")
        df = backtester.load_historical_data(days=30)
    
    # 백테스트 실행
    print("\n🚀 백테스트 실행 중...")
    results = backtester.run_backtest(
        df=df,
        position_size=0.3,  # 자본금의 30%
        stop_loss=0.05,  # 5% 손절
        take_profit=0.10  # 10% 익절
    )
    
    # 결과 출력
    backtester.print_results(results)
    
    # 결과 저장
    output_path = WORKSPACE_ROOT / "projects" / "bitcoin-trading" / "backtest_results" / f"geum_hwa_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # JSON 직렬화 가능한 형태로 변환
    results_json = {
        **{k: v for k, v in results.items() if k not in ['equity_curve', 'trades']},
        'equity_curve': [
            {
                'timestamp': str(eq['timestamp']),
                'equity': float(eq['equity']),
                'capital': float(eq['capital']),
                'position': float(eq['position']),
                'price': float(eq['price']),
                't_transition': float(eq['t_transition'])
            }
            for eq in results['equity_curve']
        ],
        'trades': [
            {
                'entry_price': float(t['entry_price']),
                'exit_price': float(t['exit_price']),
                'profit_pct': float(t['profit_pct']),
                'profit_usdt': float(t['profit_usdt']),
                'reason': t['reason'],
                'position_size': float(t['position_size'])
            }
            for t in results['trades']
        ]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results_json, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 결과 저장: {output_path}")
    print("\n✅ 백테스트 완료!")


if __name__ == "__main__":
    main()

