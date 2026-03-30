#!/usr/bin/env python3
"""
현실 기반 실행 모델링

백테스트와 실전 간의 괴리를 최소화하기 위한 정교한 실행 모델:
- 동적 슬리피지 모델링 (제곱근 법칙)
- 거래소 수수료 구조 반영
- 지연 시간 시뮬레이션
- Almgren-Chriss 최적 집행 경로
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, Any
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RealityExecutionModel:
    """
    현실 기반 실행 모델
    
    백테스트와 실전 간의 괴리를 최소화하기 위한 정교한 실행 모델
    """
    
    # 바이낸스 수수료 구조 (2025년 기준)
    FEE_STRUCTURE = {
        "VIP0": {"taker": 0.0010, "maker": 0.0010},  # 0.10%
        "VIP1": {"taker": 0.0009, "maker": 0.0008},  # 0.09% / 0.08%
        "VIP2": {"taker": 0.0008, "maker": 0.0006},  # 0.08% / 0.06%
        "VIP3": {"taker": 0.0007, "maker": 0.0004},  # 0.07% / 0.04%
        "VIP4": {"taker": 0.0006, "maker": 0.0003},  # 0.06% / 0.03%
        "VIP5": {"taker": 0.0005, "maker": 0.0002},  # 0.05% / 0.02%
        "VIP6": {"taker": 0.0004, "maker": 0.0001},  # 0.04% / 0.01%
    }
    
    def __init__(
        self,
        vip_level: str = "VIP0",
        latency_ms: int = 100,
        use_optimal_execution: bool = True
    ):
        """
        Args:
            vip_level: VIP 등급 (기본값: VIP0)
            latency_ms: 지연 시간 (밀리초, 기본값: 100ms)
            use_optimal_execution: 최적 집행 경로 사용 여부 (Almgren-Chriss)
        """
        self.vip_level = vip_level
        self.latency_ms = latency_ms
        self.use_optimal_execution = use_optimal_execution
        
        # 수수료 설정
        fee_config = self.FEE_STRUCTURE.get(vip_level, self.FEE_STRUCTURE["VIP0"])
        self.taker_fee = fee_config["taker"]
        self.maker_fee = fee_config["maker"]
        
        logger.info(
            f"✅ 실행 모델 초기화: "
            f"VIP={vip_level}, "
            f"Taker={self.taker_fee:.4%}, "
            f"Maker={self.maker_fee:.4%}, "
            f"지연시간={latency_ms}ms"
        )
    
    def calculate_slippage(
        self,
        trade_size: float,
        daily_volume: float,
        volatility: float,
        order_type: str = "market"
    ) -> float:
        """
        동적 슬리피지 계산 (제곱근 법칙)
        
        공식: Cost ≈ σ × √(Trade Size / Daily Volume)
        
        Args:
            trade_size: 거래 크기 (USDT)
            daily_volume: 일일 거래량 (USDT)
            volatility: 시장 변동성 (ATR 기반, 0.0-1.0)
            order_type: 주문 타입 ("market" 또는 "limit")
        
        Returns:
            슬리피지 비율 (0.0-1.0)
        """
        if daily_volume <= 0:
            logger.warning("⚠️ 일일 거래량이 0 이하입니다, 기본 슬리피지 사용")
            return 0.001  # 기본 0.1%
        
        # 제곱근 법칙
        volume_ratio = trade_size / daily_volume
        slippage_base = volatility * np.sqrt(volume_ratio)
        
        # 시장 주문은 슬리피지 증가, 지정가 주문은 감소
        if order_type == "market":
            slippage_multiplier = 1.5  # 시장 주문은 50% 추가 슬리피지
        else:  # limit
            slippage_multiplier = 0.5  # 지정가 주문은 50% 감소
        
        slippage = slippage_base * slippage_multiplier
        
        # 최소/최대 제한
        slippage = max(0.0001, min(slippage, 0.01))  # 0.01% ~ 1%
        
        logger.debug(
            f"💧 슬리피지 계산: "
            f"거래 크기={trade_size:.2f}, "
            f"일일 거래량={daily_volume:.2f}, "
            f"변동성={volatility:.2%}, "
            f"슬리피지={slippage:.4%}"
        )
        
        return slippage
    
    def calculate_total_cost(
        self,
        trade_size: float,
        price: float,
        daily_volume: float,
        volatility: float,
        order_type: str = "market",
        is_maker: bool = False
    ) -> Dict[str, float]:
        """
        총 거래 비용 계산 (수수료 + 슬리피지)
        
        Args:
            trade_size: 거래 크기 (USDT)
            price: 거래 가격
            daily_volume: 일일 거래량 (USDT)
            volatility: 시장 변동성
            order_type: 주문 타입
            is_maker: Maker 주문 여부 (True: 리베이트, False: Taker 수수료)
        
        Returns:
            거래 비용 정보 딕셔너리
        """
        # 1. 수수료 계산
        fee_rate = self.maker_fee if is_maker else self.taker_fee
        fee_cost = trade_size * fee_rate
        
        # 2. 슬리피지 계산
        slippage_rate = self.calculate_slippage(
            trade_size, daily_volume, volatility, order_type
        )
        slippage_cost = trade_size * slippage_rate
        
        # 3. 총 비용
        total_cost = fee_cost + slippage_cost
        total_cost_ratio = total_cost / trade_size
        
        result = {
            "fee_cost": fee_cost,
            "fee_rate": fee_rate,
            "slippage_cost": slippage_cost,
            "slippage_rate": slippage_rate,
            "total_cost": total_cost,
            "total_cost_ratio": total_cost_ratio,
            "effective_price": price * (1 + total_cost_ratio) if order_type == "market" else price
        }
        
        logger.debug(
            f"💰 거래 비용: "
            f"수수료={fee_cost:.4f} ({fee_rate:.4%}), "
            f"슬리피지={slippage_cost:.4f} ({slippage_rate:.4%}), "
            f"총 비용={total_cost:.4f} ({total_cost_ratio:.4%})"
        )
        
        return result
    
    def simulate_latency(
        self,
        current_price: float,
        price_data: pd.DataFrame,
        latency_ms: int = None
    ) -> float:
        """
        지연 시간 시뮬레이션
        
        주문 전송 → 매칭 엔진 도달까지의 지연 시간 동안 가격 변동 반영
        
        Args:
            current_price: 현재 가격
            price_data: 가격 데이터 (최근 N개 캔들)
            latency_ms: 지연 시간 (밀리초, None이면 self.latency_ms 사용)
        
        Returns:
            지연 시간 반영된 가격
        """
        if latency_ms is None:
            latency_ms = self.latency_ms
        
        if len(price_data) < 2:
            # 데이터 부족 시 현재 가격 반환
            return current_price
        
        # 지연 시간 동안의 평균 가격 변동률 계산
        recent_returns = price_data['close'].pct_change().dropna()
        
        if len(recent_returns) == 0:
            return current_price
        
        # 지연 시간을 고려한 가격 변동 시뮬레이션
        # 100ms = 약 0.1초, 1분 캔들 기준 0.1/60 = 0.00167
        time_ratio = latency_ms / 60000.0  # 1분 캔들 기준
        
        # 최근 변동성 기반 가격 변동 추정
        avg_volatility = recent_returns.std()
        price_change = avg_volatility * np.sqrt(time_ratio) * np.random.randn()
        
        adjusted_price = current_price * (1 + price_change)
        
        logger.debug(
            f"⏱️ 지연 시간 시뮬레이션: "
            f"지연시간={latency_ms}ms, "
            f"가격 변동={price_change:.4%}, "
            f"조정 가격={adjusted_price:.2f}"
        )
        
        return adjusted_price
    
    def calculate_optimal_execution_path(
        self,
        total_size: float,
        current_price: float,
        volatility: float,
        daily_volume: float,
        urgency: float = 0.5
    ) -> Dict[str, Any]:
        """
        Almgren-Chriss 최적 집행 경로 계산
        
        Args:
            total_size: 총 거래 크기 (USDT)
            current_price: 현재 가격
            volatility: 시장 변동성
            daily_volume: 일일 거래량
            urgency: 긴급도 (0.0-1.0, 높을수록 빠른 집행)
        
        Returns:
            최적 집행 경로 정보
        """
        # Almgren-Chriss 모델의 단순화된 버전
        # 실제로는 더 복잡한 최적화 문제를 풀어야 하지만,
        # 여기서는 근사치를 계산
        
        # 일시적 충격 (Temporary Impact)
        # 천천히 매매하면 줄일 수 있음
        temp_impact = volatility * np.sqrt(total_size / daily_volume)
        
        # 영구적 충격 (Permanent Impact)
        # 나의 매매로 인한 균형 가격 이동
        perm_impact = 0.1 * temp_impact  # 영구적 충격은 일시적 충격의 10%
        
        # 최적 집행 시간 (긴급도에 따라 조정)
        # 긴급도가 높으면 빠른 집행 (TWAP/VWAP), 낮으면 천천히 집행
        if urgency > 0.7:
            execution_time_minutes = 1  # 1분 내 집행
            execution_type = "aggressive"
        elif urgency > 0.4:
            execution_time_minutes = 5  # 5분 내 집행 (TWAP)
            execution_type = "twap"
        else:
            execution_time_minutes = 15  # 15분 내 집행 (VWAP)
            execution_type = "vwap"
        
        # 예상 총 비용
        expected_slippage = temp_impact + perm_impact
        expected_cost = total_size * (expected_slippage + self.taker_fee)
        
        result = {
            "execution_type": execution_type,
            "execution_time_minutes": execution_time_minutes,
            "temporary_impact": temp_impact,
            "permanent_impact": perm_impact,
            "expected_slippage": expected_slippage,
            "expected_cost": expected_cost,
            "urgency": urgency
        }
        
        logger.info(
            f"📊 최적 집행 경로: "
            f"타입={execution_type}, "
            f"집행 시간={execution_time_minutes}분, "
            f"예상 슬리피지={expected_slippage:.4%}, "
            f"예상 총 비용={expected_cost:.4f}"
        )
        
        return result
    
    def apply_execution_costs(
        self,
        entry_price: float,
        exit_price: float,
        position_size: float,
        daily_volume: float,
        volatility: float,
        is_long: bool = True
    ) -> Dict[str, float]:
        """
        진입/청산 시 실행 비용 적용
        
        Args:
            entry_price: 진입 가격
            exit_price: 청산 가격
            position_size: 포지션 크기 (USDT)
            daily_volume: 일일 거래량
            volatility: 시장 변동성
            is_long: 롱 포지션 여부
        
        Returns:
            실행 비용이 반영된 손익 정보
        """
        # 1. 진입 비용
        entry_costs = self.calculate_total_cost(
            position_size, entry_price, daily_volume, volatility,
            order_type="market", is_maker=False
        )
        
        # 2. 청산 비용
        exit_costs = self.calculate_total_cost(
            position_size, exit_price, daily_volume, volatility,
            order_type="market", is_maker=False
        )
        
        # 3. 총 비용
        total_execution_cost = entry_costs["total_cost"] + exit_costs["total_cost"]
        
        # 4. 손익 계산
        if is_long:
            gross_pnl = position_size * ((exit_price - entry_price) / entry_price)
        else:  # SHORT
            gross_pnl = position_size * ((entry_price - exit_price) / entry_price)
        
        net_pnl = gross_pnl - total_execution_cost
        
        result = {
            "gross_pnl": gross_pnl,
            "entry_cost": entry_costs["total_cost"],
            "exit_cost": exit_costs["total_cost"],
            "total_execution_cost": total_execution_cost,
            "net_pnl": net_pnl,
            "execution_cost_ratio": total_execution_cost / position_size,
            "net_return": net_pnl / position_size
        }
        
        logger.info(
            f"💰 실행 비용 적용: "
            f"총 비용={total_execution_cost:.4f} ({result['execution_cost_ratio']:.4%}), "
            f"순손익={net_pnl:.4f} ({result['net_return']:.4%})"
        )
        
        return result

