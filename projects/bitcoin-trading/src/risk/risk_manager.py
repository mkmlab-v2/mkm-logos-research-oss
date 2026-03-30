#!/usr/bin/env python3
"""
리스크 관리 시스템

보명지주 시스템 통합:
- Max Drawdown 22% 제어
- 일일 손실 한도 (3-5%)
- 포지션 크기 자동 조정
"""
import logging
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime
import numpy as np

from .kelly_criterion_calculator import KellyCriterionCalculator
from .regime_risk_policy import get_regime_risk_level
from ..monitoring.alert_manager import AlertManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RiskManager:
    """
    리스크 관리 시스템
    
    보명지주 시스템 통합:
    - Max Drawdown 22% 제어
    - 일일 손실 한도 (3-5%)
    - 포지션 크기 자동 조정
    """
    
    def __init__(
        self,
        initial_capital: float = 1000.0,
        max_drawdown: float = 0.22,  # 22%
        max_daily_loss: float = 0.05,  # 5%
        max_position_size: float = 0.3,  # 30% (정상 모드 기준 상한)
        stop_loss_ratio: float = 0.02,  # 2%
        take_profit_ratio: float = 0.06,  # 6% (손익비 1:3 달성)
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None
    ):
        """
        Args:
            initial_capital: 초기 자본 (USDT)
            max_drawdown: 최대 낙폭 (22%)
            max_daily_loss: 일일 최대 손실 (5%)
            max_position_size: 최대 포지션 크기 (30%)
            stop_loss_ratio: 손절 비율 (2%)
            take_profit_ratio: 익절 비율 (6%, 손익비 1:3)
            telegram_bot_token: 텔레그램 봇 토큰
            telegram_chat_id: 텔레그램 채팅 ID
        """
        self.initial_capital = initial_capital
        self.max_drawdown = max_drawdown
        # 일일 손실 한도는 매크로/보명지주 시스템에서 동적으로 축소될 수 있으므로
        # 기준 값과 현재 값을 분리해서 보관한다.
        self.base_max_daily_loss = max_daily_loss
        self.max_daily_loss = max_daily_loss
        # 정상 모드 기준 최대 포지션 비율 저장 (보명지주 시스템의 기준 비율)
        self.base_max_position_size = max_position_size
        # 현재 적용 중인 최대 포지션 비율 (위험 모드에서 일시적으로 축소 가능)
        self.max_position_size = max_position_size
        self.stop_loss_ratio = stop_loss_ratio
        self.take_profit_ratio = take_profit_ratio
        
        # 상태 추적
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        
        # Kelly Criterion 계산기
        self.kelly_calculator = KellyCriterionCalculator()
        
        # 거래 통계 (Kelly Criterion 계산용)
        self.trade_history = []  # {"win": bool, "pnl_ratio": float}
        
        # Alert Manager 초기화
        self.alert_manager = AlertManager(
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id
        )

        # 보명지주 시스템 단계 상태
        # - False: 정상 모드 (풀 리스크 허용 범위 내)
        # - True: 포지션 축소 모드 (낙폭이 한도의 80% 이상일 때)
        self.emergency_mode = False

        # 🏛️ PTA (Proverbs Trading Algorithm) 설정
        self.use_proverbs_rules = True
        self.pta_max_position_per_trade = 0.02  # P1: 망령되이 얻은 재물 방지 (2%)
        self.pta_cross_verification_required = True  # P2: 지략이 많으면 평안
        self.pta_leverage_limit = 1.0  # P4: 빚진 자는 종이 됨

    def apply_macro_regime(
        self,
        macro_risk_level: float,
        min_factor: float = 0.3
    ) -> None:
        """
        매크로 레짐(예: KOSPI 블랙수요일, 환율/에너지 쇼크)을 반영해
        기본 리스크 한도를 보수적으로 축소한다.

        Args:
            macro_risk_level: 0.0~1.0 범위의 매크로 리스크 스코어
            min_factor: 축소 하한 계수 (0.3이면 기준의 최소 30%까지 축소)
        """
        try:
            level = float(macro_risk_level)
        except (TypeError, ValueError):
            logger.warning(f"⚠️ 매크로 레짐 레벨 변환 실패: {macro_risk_level}, 적용 생략")
            return

        # 0.0~1.0 범위로 클램핑
        level = max(0.0, min(1.0, level))

        # 위험이 높을수록 (level↑) 리스크 한도 축소 (factor↓)
        factor = max(min_factor, 1.0 - level)

        old_max_pos = self.max_position_size
        old_daily_loss = self.max_daily_loss

        # 포지션 상한과 일일 손실 한도를 동적으로 축소
        self.max_position_size = self.base_max_position_size * factor
        self.max_daily_loss = self.base_max_daily_loss * factor

        logger.info(
            "🛡️ 매크로 레짐 적용: macro_risk_level=%.2f, "
            "max_position_size %.1f%% → %.1f%%, "
            "max_daily_loss %.2f%% → %.2f%%",
            level,
            old_max_pos * 100,
            self.max_position_size * 100,
            old_daily_loss * 100,
            self.max_daily_loss * 100,
        )

    def apply_regime_policy(
        self,
        primary_regime: Optional[str],
        divine_distance: Optional[float],
    ) -> None:
        """
        레짐·0.25 기반 리스크 정책 적용 (1차 실물 레짐 + Divine Distance만 사용).
        2차 성경 레짐은 리스크/포지션에 사용하지 않음.
        """
        level = get_regime_risk_level(primary_regime, divine_distance)
        
        # 🏛️ PTA P2 적용: BCL_index가 위험 수준이면 강제로 리스크 레벨 상향
        if self.use_proverbs_rules:
            try:
                # 최신 BCL index 로드 (파일 시스템 연동 가정)
                import json
                with open("c:/workspace/data/bcl_global_current.json", "r") as f:
                    bcl_data = json.load(f)
                    bcl_val = bcl_data.get("bcl_index", 0.0)
                    if bcl_val >= 0.5:
                        logger.warning(f"🏛️ PTA P2 Alert: BCL_index({bcl_val:.4f}) 위험 수준. 리스크 레벨 강제 조정.")
                        level = max(level, 0.8) # 위험 시 강제 0.8 리스크 적용
            except Exception:
                pass
                
        self.apply_macro_regime(level)
    
    def reset_daily_pnl(self):
        """일일 손익 리셋 (자정)"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
            logger.info("✅ 일일 손익 리셋")
    
    def update_capital(self, current_balance: float):
        """자본 업데이트"""
        self.current_capital = current_balance
        
        # 최고 자본 업데이트
        if current_balance > self.peak_capital:
            self.peak_capital = current_balance
    
    def calculate_drawdown(self) -> float:
        """현재 낙폭 계산"""
        if self.peak_capital > 0:
            drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
            return drawdown
        return 0.0
    
    def check_drawdown_limit(self) -> bool:
        """낙폭 한도 확인"""
        drawdown = self.calculate_drawdown()
        # 2단계: 보명지주 최종 방어선 – 거래 완전 중단 (전략 레이어 점검 모드)
        if drawdown >= self.max_drawdown:
            logger.warning(f"⚠️ 낙폭 한도 초과: {drawdown:.2%} >= {self.max_drawdown:.2%}")
            # 포지션 축소 모드 유지 + 신규 거래 차단
            self.emergency_mode = True
            # 보수적으로 최대 포지션 비율을 절반으로 고정
            self.max_position_size = min(self.max_position_size, self.base_max_position_size * 0.5)
            asyncio.create_task(
                self.alert_manager.alert_risk_warning(
                    warning_type="MAX_DRAWDOWN",
                    current_value=drawdown * 100,
                    threshold=self.max_drawdown * 100,
                    message_detail=(
                        "현재 낙폭이 최대 한도에 도달했습니다. "
                        "신규 거래를 중단하고 전략/시장 구조를 재점검해야 합니다."
                    )
                )
            )
            return False
        # 1단계: 포지션 축소 모드 진입 (한도의 80% 이상에서 공격성 낮추기)
        elif drawdown >= self.max_drawdown * 0.8:  # 80% 경고
            if not self.emergency_mode:
                logger.warning(
                    f"⚠️ 낙폭 경고: {drawdown:.2%} (한도: {self.max_drawdown:.2%}) – "
                    f"포지션 축소 모드 진입 (max_position_size {self.max_position_size:.1%} → "
                    f"{self.base_max_position_size * 0.5:.1%})"
                )
            else:
                logger.warning(
                    f"⚠️ 낙폭 경고 유지: {drawdown:.2%} (한도: {self.max_drawdown:.2%}) – "
                    "포지션 축소 모드 지속"
                )

            # 1단계에서는 신규 거래는 허용하되 포지션 규모를 강제로 축소
            self.emergency_mode = True
            # 정상 모드 기준의 50%로 상한 축소 (예: 30% → 15%)
            self.max_position_size = min(self.max_position_size, self.base_max_position_size * 0.5)

            asyncio.create_task(
                self.alert_manager.alert_risk_warning(
                    warning_type="MAX_DRAWDOWN",
                    current_value=drawdown * 100,
                    threshold=self.max_drawdown * 100,
                    message_detail=(
                        "낙폭이 한도의 80%에 도달했습니다. "
                        "포지션 비중을 줄이고 시장을 관망하는 단계로 진입합니다."
                    )
                )
            )
        else:
            # 낙폭이 충분히 회복되면 포지션 상한과 모드 상태를 정상 모드로 복원
            if self.emergency_mode and drawdown <= self.max_drawdown * 0.5:
                logger.info(
                    f"✅ 낙폭 회복 감지: {drawdown:.2%} (한도: {self.max_drawdown:.2%}) – "
                    f"포지션 상한 {self.max_position_size:.1%} → "
                    f"{self.base_max_position_size:.1%} (정상 모드 복원)"
                )
                self.max_position_size = self.base_max_position_size
                self.emergency_mode = False
        return True
    
    def check_daily_loss_limit(self) -> bool:
        """일일 손실 한도 확인"""
        self.reset_daily_pnl()
        
        daily_loss_ratio = abs(self.daily_pnl) / self.initial_capital if self.daily_pnl < 0 else 0.0
        if daily_loss_ratio >= self.max_daily_loss:
            logger.warning(f"⚠️ 일일 손실 한도 초과: {daily_loss_ratio:.2%} >= {self.max_daily_loss:.2%}")
            asyncio.create_task(
                self.alert_manager.alert_risk_warning(
                    warning_type="DAILY_LOSS_LIMIT",
                    current_value=daily_loss_ratio * 100,
                    threshold=self.max_daily_loss * 100,
                    message_detail=f"일일 손실이 한도에 도달했습니다. 거래가 중단됩니다."
                )
            )
            return False
        elif daily_loss_ratio >= self.max_daily_loss * 0.8:  # 80% 경고
            logger.warning(f"⚠️ 일일 손실 경고: {daily_loss_ratio:.2%} (한도: {self.max_daily_loss:.2%})")
            asyncio.create_task(
                self.alert_manager.alert_risk_warning(
                    warning_type="DAILY_LOSS_LIMIT",
                    current_value=daily_loss_ratio * 100,
                    threshold=self.max_daily_loss * 100,
                    message_detail=f"일일 손실이 한도의 80%에 도달했습니다. 주의가 필요합니다."
                )
            )
        return True
    
    def calculate_liquidity_density(
        self,
        recent_volume: float,
        avg_volume: float = None
    ) -> float:
        """
        유동성 밀도 계산 (슬리피지 보정용)
        
        Args:
            recent_volume: 최근 거래량 (24시간)
            avg_volume: 평균 거래량 (30일, None이면 recent_volume 사용)
        
        Returns:
            유동성 밀도 (0.0 ~ 1.0, 높을수록 유동성 좋음)
        """
        try:
            if avg_volume is None:
                avg_volume = recent_volume
            
            if avg_volume <= 0:
                return 0.5  # 기본값 (중간 유동성)
            
            # 거래량 비율 계산
            volume_ratio = recent_volume / avg_volume
            
            # 유동성 밀도 정규화 (0.0 ~ 1.0)
            # 거래량이 평균의 50% 미만이면 낮은 유동성
            if volume_ratio < 0.5:
                liquidity_density = 0.3  # 낮은 유동성
            elif volume_ratio < 0.8:
                liquidity_density = 0.6  # 중간 유동성
            else:
                liquidity_density = 1.0  # 높은 유동성
            
            return liquidity_density
        except Exception as e:
            logger.warning(f"⚠️ 유동성 밀도 계산 실패: {e}, 기본값 0.5 사용")
            return 0.5
    
    def calculate_slippage_adjustment(
        self,
        liquidity_density: float
    ) -> float:
        """
        슬리피지 보정 배율 계산
        
        Args:
            liquidity_density: 유동성 밀도 (0.0 ~ 1.0)
        
        Returns:
            슬리피지 보정 배율 (0.9 ~ 1.0, 낮을수록 포지션 축소)
        """
        try:
            # 유동성이 낮을수록 포지션 축소 (최대 10% 축소)
            # liquidity_density = 0.3 (낮음) → 0.9배 (10% 축소)
            # liquidity_density = 0.6 (중간) → 0.95배 (5% 축소)
            # liquidity_density = 1.0 (높음) → 1.0배 (축소 없음)
            slippage_multiplier = 0.9 + (liquidity_density * 0.1)
            
            return slippage_multiplier
        except Exception as e:
            logger.warning(f"⚠️ 슬리피지 보정 계산 실패: {e}, 기본값 1.0 사용")
            return 1.0
    
    def calculate_position_size(
        self,
        current_price: float,
        signal_confidence: float = 0.5,
        recent_volume: float = None,
        avg_volume: float = None,
        use_kelly: bool = True,
        current_volatility: float = None,
        win_rate: float = None,
        avg_win: float = None,
        avg_loss: float = None,
        vector_4d: Optional[Dict[str, float]] = None
    ) -> float:
        """
        포지션 크기 계산 (Kelly Criterion + 슬리피지 보정)
        
        MKM12 수학 헌법 v4.0 준수:
        - Divine Centroid (0.25 평형) 신뢰도 보정 적용
        
        Args:
            current_price: 현재 가격
            signal_confidence: 신호 신뢰도 (0.0 ~ 1.0)
            recent_volume: 최근 거래량 (24시간, 슬리피지 보정용)
            avg_volume: 평균 거래량 (30일, 슬리피지 보정용)
            use_kelly: Kelly Criterion 사용 여부 (기본값: True)
            current_volatility: 현재 변동성 (ATR 기반, Kelly 조정용)
            win_rate: 승률 (Kelly 계산용, None이면 거래 통계에서 계산)
            avg_win: 평균 수익률 (Kelly 계산용, None이면 거래 통계에서 계산)
            avg_loss: 평균 손실률 (Kelly 계산용, None이면 거래 통계에서 계산)
            vector_4d: 4D 벡터 (Divine Centroid 보정용, 선택적)
        
        Returns:
            포지션 크기 (USDT)
        """
        try:
            # Kelly Criterion 기반 포지션 크기 계산
            if use_kelly and len(self.trade_history) >= 10:
                # 거래 통계에서 승률 및 손익비 계산
                if win_rate is None or avg_win is None or avg_loss is None:
                    wins = [t for t in self.trade_history if t.get("win", False)]
                    losses = [t for t in self.trade_history if not t.get("win", False)]
                    
                    if len(wins) > 0 and len(losses) > 0:
                        win_rate = len(wins) / len(self.trade_history)
                        avg_win = np.mean([t["pnl_ratio"] for t in wins])
                        avg_loss = abs(np.mean([t["pnl_ratio"] for t in losses]))
                    else:
                        # 통계 부족 시 기본값 사용
                        win_rate = 0.45
                        avg_win = self.take_profit_ratio
                        avg_loss = self.stop_loss_ratio
                else:
                    # 파라미터가 제공된 경우 사용
                    pass
                
                # 변동성 기본값
                if current_volatility is None:
                    current_volatility = 0.02  # 기본 2%
                
                # Kelly Criterion 최적 포지션 크기 계산
                # MKM12 수학 헌법 v4.0 준수: Divine Centroid 보정 적용
                kelly_result = self.kelly_calculator.calculate_optimal_position_size(
                    win_rate=win_rate,
                    avg_win=avg_win,
                    avg_loss=avg_loss,
                    current_volatility=current_volatility,
                    signal_confidence=signal_confidence,
                    kelly_fraction=0.25,  # Quarter-Kelly (보수적)
                    max_position_size=self.max_position_size,
                    vector_4d=vector_4d  # Divine Centroid 보정용
                )
                
                base_position_ratio = kelly_result["final_position_size"]
                logger.info(f"📊 Kelly Criterion 포지션 비율: {base_position_ratio:.2%}")
            else:
                # Kelly Criterion 미사용 또는 통계 부족 시 기존 방식
                base_position_ratio = self.max_position_size
                logger.info(f"📊 기본 포지션 비율 사용: {base_position_ratio:.2%}")
            
            # 기본 포지션 크기
            base_position = self.current_capital * base_position_ratio
            
            # 🎯 정확도 기반 포지션 크기 명시적 증가 (신뢰도에 비례)
            confidence_multiplier = 0.5 + (signal_confidence * 1.0)  # 0.5배 ~ 1.5배
            # 예: confidence 0.9 → 1.4배, confidence 0.5 → 1.0배
            confidence_adjusted_position = base_position * confidence_multiplier
            
            if signal_confidence >= 0.85:
                logger.info(
                    f"🚀 정확도 기반 포지션 크기 증가: 신뢰도 {signal_confidence:.2%} → "
                    f"포지션 크기 {confidence_multiplier:.2f}배 "
                    f"(${base_position:.2f} → ${confidence_adjusted_position:.2f})"
                )
            
            # 낙폭 기반 조정 (낙폭이 클수록 포지션 축소)
            drawdown = self.calculate_drawdown()
            drawdown_multiplier = max(0.5, 1.0 - drawdown / self.max_drawdown)
            adjusted_position = confidence_adjusted_position * drawdown_multiplier
            
            # 🏛️ 아테나 제안: 슬리피지 보정 (유동성 밀도 기반)
            if recent_volume is not None:
                liquidity_density = self.calculate_liquidity_density(recent_volume, avg_volume)
                slippage_multiplier = self.calculate_slippage_adjustment(liquidity_density)
                adjusted_position *= slippage_multiplier
                
                if liquidity_density < 0.5:
                    logger.info(
                        f"💧 슬리피지 보정 적용: 유동성 밀도 {liquidity_density:.2f}, "
                        f"포지션 {slippage_multiplier:.1%}로 축소"
                    )
            
            # 최소 포지션 크기 (10 USDT)
            min_position = 10.0
            final_position = max(min_position, adjusted_position)

            # 🏛️ PTA P1 적용: 단일 거래 최대 비중 제한 (2%)
            if self.use_proverbs_rules:
                pta_limit = self.current_capital * self.pta_max_position_per_trade
                if final_position > pta_limit:
                    logger.info(f"🏛️ PTA P1 Restriction: 포지션 축소 (${final_position:.2f} → ${pta_limit:.2f}) - Gradient Rule 적용")
                    final_position = pta_limit
            
            return final_position
        except Exception as e:
            logger.error(f"❌ 포지션 크기 계산 실패: {e}")
            return self.current_capital * 0.1  # 기본 10%
    
    def calculate_stop_loss(self, entry_price: float, position_side: str = "LONG") -> float:
        """
        손절 가격 계산
        
        Args:
            entry_price: 진입 가격
            position_side: 포지션 방향 ("LONG" 또는 "SHORT")
        
        Returns:
            손절 가격
        """
        if position_side == "LONG":
            return entry_price * (1 - self.stop_loss_ratio)
        else:  # SHORT
            return entry_price * (1 + self.stop_loss_ratio)
    
    def calculate_take_profit(self, entry_price: float, position_side: str = "LONG") -> float:
        """
        익절 가격 계산
        
        Args:
            entry_price: 진입 가격
            position_side: 포지션 방향 ("LONG" 또는 "SHORT")
        
        Returns:
            익절 가격
        """
        if position_side == "LONG":
            return entry_price * (1 + self.take_profit_ratio)
        else:  # SHORT
            return entry_price * (1 - self.take_profit_ratio)
    
    def can_trade(self) -> bool:
        """거래 가능 여부 확인"""
        # 낙폭 한도 확인
        if not self.check_drawdown_limit():
            return False
        
        # 일일 손실 한도 확인
        if not self.check_daily_loss_limit():
            return False
        
        return True
    
    def update_pnl(self, pnl: float, entry_capital: float = None):
        """
        손익 업데이트
        
        Args:
            pnl: 손익 (USDT)
            entry_capital: 진입 시 자본 (Kelly 통계용, None이면 현재 자본 사용)
        """
        self.daily_pnl += pnl
        self.current_capital += pnl
        
        # 최고 자본 업데이트
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        # 거래 통계 업데이트 (Kelly Criterion용)
        if entry_capital is not None and entry_capital > 0:
            pnl_ratio = pnl / entry_capital
            trade_record = {
                "win": pnl > 0,
                "pnl_ratio": abs(pnl_ratio)
            }
            self.trade_history.append(trade_record)
            
            # 최근 100개 거래만 유지 (메모리 효율)
            if len(self.trade_history) > 100:
                self.trade_history = self.trade_history[-100:]
        
        logger.info(f"💰 손익 업데이트: {pnl:.2f} USDT (일일: {self.daily_pnl:.2f} USDT, 총 자본: {self.current_capital:.2f} USDT)")
        
        # 큰 손익 발생 시 알림 (5% 이상) - 간단한 메시지로 전송
        if abs(pnl) >= self.initial_capital * 0.05:
            pnl_ratio = pnl / self.initial_capital
            message = f"💰 큰 손익 발생: {pnl:+.2f} USDT ({pnl_ratio:+.2%})"
            asyncio.create_task(self.alert_manager.send_telegram(message))


