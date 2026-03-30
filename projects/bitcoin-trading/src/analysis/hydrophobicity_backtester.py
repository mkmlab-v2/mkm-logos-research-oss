#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 소수성 필터 백테스트 시스템 (Hydrophobicity Backtester)

목적: "소수성 필터"를 장착한 상태로 과거 폭락장 백테스트
- 2008 금융위기 (리먼 쇼크)
- 2020 코로나 폭락
- 소수성 필터 적용 전/후 성과 비교

작성일: 2026-01-18
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import json

# 워크스페이스 루트
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "projects" / "bitcoin-trading" / "src" / "analysis"))

# yfinance for historical data
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("⚠️ yfinance가 설치되지 않았습니다. pip install yfinance 실행 필요", file=sys.stderr)
    yf = None

# PhaseSpaceNowcaster import
try:
    from phase_space_nowcaster import PhaseSpaceNowcaster, DIVINE_CENTROID, ACTUAL_BIBLE_AVERAGE
    NOWCASTER_AVAILABLE = True
except ImportError as e:
    NOWCASTER_AVAILABLE = False
    print(f"⚠️ PhaseSpaceNowcaster를 찾을 수 없습니다: {e}", file=sys.stderr)

# Sovereign Core Constants import
try:
    from tools.core.sovereign_core_constants import (
        TAEYANGIN_RARITY_WEIGHTS,
        get_taeyangin_rarity_weight
    )
    CONSTANTS_AVAILABLE = True
except ImportError:
    CONSTANTS_AVAILABLE = False
    print("⚠️ Sovereign Core Constants를 찾을 수 없습니다", file=sys.stderr)


class FinancialCrisisEvent:
    """금융 위기 이벤트 정의"""
    
    def __init__(
        self,
        name: str,
        start_date: str,
        end_date: str,
        crash_date: str,
        symbols: List[str],
        vix_peak_date: Optional[str] = None,
        vix_peak_value: Optional[float] = None
    ):
        """
        Args:
            name: 이벤트 이름
            start_date: 데이터 수집 시작일 (YYYY-MM-DD)
            end_date: 데이터 수집 종료일 (YYYY-MM-DD)
            crash_date: 실제 붕괴 시작일 (YYYY-MM-DD)
            symbols: 분석할 종목 리스트
            vix_peak_date: VIX 최고치 날짜 (선택적)
            vix_peak_value: VIX 최고치 값 (선택적)
        """
        self.name = name
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.crash_date = datetime.strptime(crash_date, "%Y-%m-%d")
        self.symbols = symbols
        self.vix_peak_date = datetime.strptime(vix_peak_date, "%Y-%m-%d") if vix_peak_date else None
        self.vix_peak_value = vix_peak_value


class HydrophobicityBacktester:
    """
    소수성 필터 백테스트 시스템
    
    원리:
    - 소수성이 극대화된 종목 = 보호막 안의 화(火) 에너지가 응축된 종목
    - 이 종목들은 "예언적 사건"이 일어날 가능성이 높음
    - 과거 폭락장에서 소수성 필터가 실제로 위기를 감지했는지 검증
    """
    
    def __init__(self, domain: str = "stock_volatile"):
        """
        Args:
            domain: 도메인 (stock_volatile, stock_stable, human 등)
        """
        self.domain = domain
        self.nowcaster = None
        if NOWCASTER_AVAILABLE:
            try:
                self.nowcaster = PhaseSpaceNowcaster(enable_unified_engine=True)
            except Exception as e:
                print(f"⚠️ PhaseSpaceNowcaster 초기화 실패: {e}", file=sys.stderr)
    
    def backtest_crisis_event(
        self,
        event: FinancialCrisisEvent,
        lookback_days: int = 30,
        enable_hydrophobicity_filter: bool = True
    ) -> Dict[str, Any]:
        """
        위기 이벤트 백테스트
        
        Args:
            event: 금융 위기 이벤트
            lookback_days: 붕괴 전 경고 기간 (일)
            enable_hydrophobicity_filter: 소수성 필터 활성화 여부
        
        Returns:
            백테스트 결과
        """
        if not YFINANCE_AVAILABLE:
            return {"error": "yfinance가 설치되지 않았습니다"}
        
        if not self.nowcaster:
            return {"error": "PhaseSpaceNowcaster를 초기화할 수 없습니다"}
        
        print(f"\n🔍 {event.name} 백테스트 시작...", file=sys.stderr)
        print(f"   기간: {event.start_date.date()} ~ {event.end_date.date()}", file=sys.stderr)
        print(f"   붕괴일: {event.crash_date.date()}", file=sys.stderr)
        
        # 붕괴 전 경고 기간
        warning_start = event.crash_date - timedelta(days=lookback_days)
        warning_end = event.crash_date
        
        # 일별 데이터 수집 및 분석
        daily_results = []
        warnings_detected = []
        
        current_date = warning_start
        while current_date <= event.end_date:
            try:
                # 해당 날짜의 데이터 수집
                daily_data = self._collect_daily_data(current_date, event.symbols)
                
                if daily_data:
                    # 4D 벡터 계산
                    vector_4d = self._calculate_4d_vector(daily_data)
                    
                    # PhaseSpaceNowcaster 업데이트
                    self.nowcaster.update_phase_vector(vector_4d, timestamp=current_date)
                    
                    # 나우캐스팅 리포트 생성
                    vix_value = daily_data.get("vix", None)
                    report = self.nowcaster.get_nowcasting_report(vix_value=vix_value)
                    
                    # 소수성 필터 적용 (선택적)
                    if enable_hydrophobicity_filter:
                        # 체질 점수 추정 (백테스트용)
                        taeyang_score = self._estimate_taeyang_score_from_vector(vector_4d, vix_value)
                        constitution_scores = {
                            "태양인": taeyang_score,
                            "태음인": 0.0,
                            "소양인": 0.0,
                            "소음인": 0.0
                        }
                        
                        # 화기운 분석
                        fire_analysis = self.nowcaster._detect_explosive_energy(
                            vector_4d,
                            constitution_scores
                        )
                        hydrophobicity_level = fire_analysis.get("hydrophobicity_level", 0.0)
                        is_explosive = fire_analysis.get("is_explosive", False)
                    else:
                        hydrophobicity_level = 0.0
                        is_explosive = False
                        fire_analysis = {}
                    
                    # 위기 신호 판정
                    crisis_level = report.get("crisis_level", "HOLD")
                    distance = report.get("nowcasting", {}).get("distance_to_centroid", 0.0)
                    
                    # 경고 감지
                    is_warning = (
                        crisis_level in ["SELL", "EMERGENCY_SELL"] or
                        (enable_hydrophobicity_filter and is_explosive) or
                        (enable_hydrophobicity_filter and hydrophobicity_level >= 0.7)
                    )
                    
                    if is_warning:
                        warnings_detected.append({
                            "date": current_date.isoformat(),
                            "crisis_level": crisis_level,
                            "distance": distance,
                            "vix": vix_value,
                            "hydrophobicity_level": hydrophobicity_level,
                            "is_explosive": is_explosive,
                            "days_before_crash": (event.crash_date - current_date).days
                        })
                    
                    daily_results.append({
                        "date": current_date.isoformat(),
                        "vector_4d": vector_4d,
                        "crisis_level": crisis_level,
                        "distance": distance,
                        "vix": vix_value,
                        "hydrophobicity_level": hydrophobicity_level,
                        "is_explosive": is_explosive
                    })
            
            except Exception as e:
                print(f"⚠️ {current_date.date()} 데이터 처리 실패: {e}", file=sys.stderr)
            
            current_date += timedelta(days=1)
        
        # 결과 분석
        early_warnings = [w for w in warnings_detected if w["days_before_crash"] > 0]
        on_time_warnings = [w for w in warnings_detected if w["days_before_crash"] == 0]
        late_warnings = [w for w in warnings_detected if w["days_before_crash"] < 0]
        
        # 성공률 계산
        success_rate = 0.0
        if early_warnings:
            success_rate = len(early_warnings) / len(warnings_detected) if warnings_detected else 0.0
        
        # 평균 조기 경보 일수
        avg_early_warning_days = 0.0
        if early_warnings:
            avg_early_warning_days = sum(w["days_before_crash"] for w in early_warnings) / len(early_warnings)
        
        return {
            "event_name": event.name,
            "crash_date": event.crash_date.isoformat(),
            "total_days_analyzed": len(daily_results),
            "warnings_detected": len(warnings_detected),
            "early_warnings": len(early_warnings),
            "on_time_warnings": len(on_time_warnings),
            "late_warnings": len(late_warnings),
            "success_rate": success_rate,
            "avg_early_warning_days": avg_early_warning_days,
            "warnings": warnings_detected,
            "daily_results": daily_results[:10],  # 처음 10개만 반환 (전체는 너무 큼)
            "hydrophobicity_filter_enabled": enable_hydrophobicity_filter
        }
    
    def _collect_daily_data(
        self,
        date: datetime,
        symbols: List[str]
    ) -> Optional[Dict[str, Any]]:
        """일별 데이터 수집"""
        if not yf:
            return None
        
        try:
            data = {}
            
            # VIX 데이터 수집
            try:
                vix_ticker = yf.Ticker("^VIX")
                vix_hist = vix_ticker.history(start=date, end=date + timedelta(days=1))
                if not vix_hist.empty:
                    data["vix"] = float(vix_hist["Close"].iloc[0])
            except:
                data["vix"] = None
            
            # 종목별 데이터 수집
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(start=date, end=date + timedelta(days=1))
                    if not hist.empty:
                        data[symbol] = {
                            "open": float(hist["Open"].iloc[0]),
                            "high": float(hist["High"].iloc[0]),
                            "low": float(hist["Low"].iloc[0]),
                            "close": float(hist["Close"].iloc[0]),
                            "volume": float(hist["Volume"].iloc[0])
                        }
                except:
                    pass
            
            return data if data else None
        
        except Exception as e:
            print(f"⚠️ {date.date()} 데이터 수집 실패: {e}", file=sys.stderr)
            return None
    
    def _calculate_4d_vector(self, daily_data: Dict[str, Any]) -> Dict[str, float]:
        """일별 데이터로부터 4D 벡터 계산"""
        # VIX 기반 S 차원 (공포)
        vix_value = daily_data.get("vix", None)
        if vix_value is not None:
            vix_normalized = max(0.0, min(1.0, (vix_value - 10) / 70))
            s_value = max(0.1, min(0.4, 0.4 - vix_normalized * 0.3))
        else:
            s_value = 0.25
        
        # 가격 변동성 기반 L 차원 (논리)
        price_changes = []
        for symbol, price_data in daily_data.items():
            if symbol != "vix" and isinstance(price_data, dict):
                change = (price_data["close"] - price_data["open"]) / price_data["open"]
                price_changes.append(abs(change))
        
        if price_changes:
            avg_volatility = sum(price_changes) / len(price_changes)
            l_value = max(0.1, min(0.4, 0.25 - avg_volatility * 0.5))
        else:
            l_value = 0.25
        
        # 거래량 기반 K 차원 (지식)
        volumes = []
        for symbol, price_data in daily_data.items():
            if symbol != "vix" and isinstance(price_data, dict):
                volumes.append(price_data.get("volume", 0))
        
        if volumes:
            total_volume = sum(volumes)
            volume_heat = min(total_volume / 1e10, 0.15)
            k_value = max(0.1, min(0.4, 0.25 + volume_heat))
        else:
            k_value = 0.25
        
        # 가격 수준 기반 M 차원 (물질)
        prices = []
        for symbol, price_data in daily_data.items():
            if symbol != "vix" and isinstance(price_data, dict):
                prices.append(price_data["close"])
        
        if prices:
            avg_price = sum(prices) / len(prices)
            m_value = max(0.1, min(0.4, 0.25 + min(avg_price / 100000, 0.1)))
        else:
            m_value = 0.25
        
        # 정규화
        total = s_value + l_value + k_value + m_value
        if total > 0:
            return {
                "S": s_value / total,
                "L": l_value / total,
                "K": k_value / total,
                "M": m_value / total
            }
        else:
            return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    
    def _estimate_taeyang_score_from_vector(
        self,
        vector_4d: Dict[str, float],
        vix_value: Optional[float] = None
    ) -> float:
        """
        4D 벡터로부터 태양인 점수 추정
        
        원리:
        - S 차원이 높을수록, S-M 괴리가 클수록 태양인 가능성 높음
        - VIX가 낮을 때 S가 높으면 태양인 (소수성 패턴)
        
        Returns:
            태양인 점수 (0.0 ~ 1.0)
        """
        s_value = vector_4d.get("S", 0.25)
        m_value = vector_4d.get("M", 0.25)
        
        # S-M 괴리 (태양인 특징: S 높음, M 낮음)
        s_m_gap = abs(s_value - m_value)
        
        # S 차원 높음 (태양인 특징)
        s_score = max(0.0, (s_value - 0.25) / 0.25)  # 0.25 기준으로 정규화
        
        # VIX가 낮을 때 S가 높으면 태양인 (소수성 패턴)
        vix_bonus = 0.0
        if vix_value is not None and vix_value < 20:
            # VIX가 낮은데 S가 높으면 소수성 패턴
            if s_value > 0.3:
                vix_bonus = 0.3
        
        # 종합 점수
        taeyang_score = (
            s_score * 0.4 +
            s_m_gap * 0.3 +
            vix_bonus * 0.3
        )
        
        return min(1.0, max(0.0, taeyang_score))
    
    def compare_with_without_filter(
        self,
        event: FinancialCrisisEvent,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        소수성 필터 적용 전/후 성과 비교
        
        Returns:
            비교 결과
        """
        # 필터 없이 백테스트
        result_without = self.backtest_crisis_event(
            event,
            lookback_days=lookback_days,
            enable_hydrophobicity_filter=False
        )
        
        # 필터 적용하여 백테스트
        result_with = self.backtest_crisis_event(
            event,
            lookback_days=lookback_days,
            enable_hydrophobicity_filter=True
        )
        
        return {
            "event_name": event.name,
            "without_filter": result_without,
            "with_filter": result_with,
            "improvement": {
                "warnings_increase": result_with.get("warnings_detected", 0) - result_without.get("warnings_detected", 0),
                "success_rate_change": result_with.get("success_rate", 0.0) - result_without.get("success_rate", 0.0),
                "avg_early_warning_days_change": result_with.get("avg_early_warning_days", 0.0) - result_without.get("avg_early_warning_days", 0.0)
            }
        }


def main():
    """메인 실행 함수"""
    print("🏛️ 소수성 필터 백테스트 시스템", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    
    if not YFINANCE_AVAILABLE:
        print("❌ yfinance가 설치되지 않았습니다. pip install yfinance 실행 필요", file=sys.stderr)
        return
    
    if not NOWCASTER_AVAILABLE:
        print("❌ PhaseSpaceNowcaster를 찾을 수 없습니다", file=sys.stderr)
        return
    
    backtester = HydrophobicityBacktester(domain="stock_volatile")
    
    # 2008 금융위기 이벤트
    event_2008 = FinancialCrisisEvent(
        name="2008 금융위기 (리먼 쇼크)",
        start_date="2008-09-01",
        end_date="2008-12-31",
        crash_date="2008-09-15",
        symbols=["SPY", "QQQ"],
        vix_peak_date="2008-10-24",
        vix_peak_value=79.1
    )
    
    # 2020 코로나 폭락 이벤트
    event_2020 = FinancialCrisisEvent(
        name="2020 코로나 폭락",
        start_date="2020-02-01",
        end_date="2020-04-30",
        crash_date="2020-03-09",
        symbols=["SPY", "QQQ"],
        vix_peak_date="2020-03-16",
        vix_peak_value=82.7
    )
    
    # 백테스트 실행
    events = [event_2008, event_2020]
    results = []
    
    for event in events:
        print(f"\n📊 {event.name} 백테스트 실행 중...", file=sys.stderr)
        
        # 필터 적용 전/후 비교
        comparison = backtester.compare_with_without_filter(event, lookback_days=30)
        results.append(comparison)
        
        # 결과 출력
        print(f"\n✅ {event.name} 결과:", file=sys.stderr)
        print(f"   필터 없이: 경고 {comparison['without_filter'].get('warnings_detected', 0)}개, 성공률 {comparison['without_filter'].get('success_rate', 0.0):.1%}", file=sys.stderr)
        print(f"   필터 적용: 경고 {comparison['with_filter'].get('warnings_detected', 0)}개, 성공률 {comparison['with_filter'].get('success_rate', 0.0):.1%}", file=sys.stderr)
        print(f"   개선: 경고 +{comparison['improvement']['warnings_increase']}개, 성공률 {comparison['improvement']['success_rate_change']:+.1%}p", file=sys.stderr)
    
    # 종합 결과
    print("\n" + "=" * 80, file=sys.stderr)
    print("🏛️ 종합 결과", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    
    for result in results:
        print(f"\n{result['event_name']}:", file=sys.stderr)
        print(f"  필터 없이 성공률: {result['without_filter'].get('success_rate', 0.0):.1%}", file=sys.stderr)
        print(f"  필터 적용 성공률: {result['with_filter'].get('success_rate', 0.0):.1%}", file=sys.stderr)
        print(f"  개선: {result['improvement']['success_rate_change']:+.1%}p", file=sys.stderr)
    
    # JSON 출력
    print("\n" + "=" * 80)
    print(json.dumps(results, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()

