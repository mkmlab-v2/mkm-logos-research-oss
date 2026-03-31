#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
표준 만세력 우선 사용 시스템 v2
- Swiss Ephemeris 우선 사용 (표준 만세력과 100% 일치 목표)
- AstroBaziEngine 보조 검증
- PerfectManseryeok Fallback

작성일: 2026-01-30
"""

import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from typing import Dict, Any, Optional

# 로거 설정
logger = logging.getLogger(__name__)

# Swiss Ephemeris (최우선)
SWISSEPH_AVAILABLE = False
try:
    from scripts.manseryeok_swiss_ephemeris_integration import SwissEphemerisManseryeok
    SWISSEPH_AVAILABLE = True
except ImportError:
    SWISSEPH_AVAILABLE = False
    print("⚠️ 경고: Swiss Ephemeris를 사용할 수 없습니다.")

# AstroBaziEngine (보조)
ASTRO_BAZI_AVAILABLE = False
try:
    from scripts.astro_bazi_engine import AstroBaziEngine
    ASTRO_BAZI_AVAILABLE = True
except ImportError:
    ASTRO_BAZI_AVAILABLE = False

# PerfectManseryeok (Fallback)
PERFECT_MANSERYEOK_AVAILABLE = False
try:
    from scripts.manseryeok_perfect_final import PerfectManseryeok
    PERFECT_MANSERYEOK_AVAILABLE = True
except ImportError:
    PERFECT_MANSERYEOK_AVAILABLE = False


def calculate_saju_standard_first_v2(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    longitude: Optional[float] = None,
    is_male: bool = True,
    verify: bool = True
) -> Dict[str, Any]:
    """
    표준 만세력 우선 사용 시스템 v2
    
    우선순위:
    1. Swiss Ephemeris (최우선, 표준 만세력과 100% 일치 목표)
    2. AstroBaziEngine (보조 검증)
    3. PerfectManseryeok (Fallback)
    
    Args:
        year: 연도
        month: 월
        day: 일
        hour: 시
        minute: 분
        longitude: 경도 (기본값: 서울 126.9780)
        is_male: 남성 여부
        verify: 교차 검증 여부
        
    Returns:
        사주 8자 결과 + 검증 정보
    """
    if longitude is None:
        longitude = 126.9780  # 서울
    
    results = {}
    primary_result = None
    primary_method = None
    
    # 1. Swiss Ephemeris 시도 (최우선)
    if SWISSEPH_AVAILABLE:
        try:
            swiss_engine = SwissEphemerisManseryeok()
            swiss_result = swiss_engine.calculate_saju_8ja(
                year, month, day, hour, minute, longitude, is_male
            )
            results['swiss_ephemeris'] = swiss_result
            primary_result = swiss_result
            primary_method = 'swiss_ephemeris'
            logger.debug("✅ Swiss Ephemeris 계산 성공")
        except Exception as e:
            logger.warning(f"⚠️ Swiss Ephemeris 계산 실패: {e}")
            results['swiss_ephemeris'] = {'error': str(e)}
    
    # 2. AstroBaziEngine 시도 (보조)
    if ASTRO_BAZI_AVAILABLE and verify:
        try:
            astro_engine = AstroBaziEngine()
            birth_kst = datetime(year, month, day, hour, minute, 0)
            astro_result = astro_engine.generate_precision_bazi(
                birth_kst, longitude=longitude, is_male=is_male
            )
            results['astro_bazi'] = astro_result
            if primary_result is None:
                primary_result = astro_result
                primary_method = 'astro_bazi'
            import logging
            logger = logging.getLogger(__name__)
            logger.debug("✅ AstroBaziEngine 계산 성공")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ AstroBaziEngine 계산 실패: {e}")
            results['astro_bazi'] = {'error': str(e)}
    
    # 3. PerfectManseryeok Fallback
    if PERFECT_MANSERYEOK_AVAILABLE and primary_result is None:
        try:
            perfect_engine = PerfectManseryeok()
            perfect_result = perfect_engine.calculate_full_saju_perfect(
                year=year,
                month=month,
                day=day,
                hour=hour,
                is_solar=True,
                is_male=is_male
            )
            results['perfect_manseryeok'] = perfect_result
            primary_result = perfect_result
            primary_method = 'perfect_manseryeok'
            print("✅ PerfectManseryeok 계산 성공")
        except Exception as e:
            print(f"⚠️ PerfectManseryeok 계산 실패: {e}")
            results['perfect_manseryeok'] = {'error': str(e)}
    
    if primary_result is None:
        raise ValueError("만세력 계산 엔진을 사용할 수 없습니다.")
    
    # 4. 교차 검증 (여러 방법으로 계산한 경우)
    verification = None
    if verify and len(results) > 1:
        verification = compare_results(results)
        if verification['all_match']:
            logger.debug("✅ 모든 계산 방법이 일치합니다.")
        else:
            # 경고 메시지를 로그 레벨로 변경 (표준 출력 대신)
            logger.warning("⚠️ 계산 결과 불일치 (Swiss Ephemeris가 우선 사용됨)")
            for diff in verification['differences']:
                logger.debug(f"  - {diff}")
    
    # 5. 최종 결과 반환
    final_result = primary_result.copy()
    final_result['calculation_method'] = primary_method
    final_result['all_results'] = results
    if verification:
        final_result['verification'] = verification
    
    return final_result


def compare_results(results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    여러 계산 결과 비교
    
    Args:
        results: 계산 결과 딕셔너리
        
    Returns:
        검증 결과
    """
    verification = {
        'all_match': True,
        'differences': []
    }
    
    # 사주 8자 추출
    saju_dict = {}
    for method, result in results.items():
        if 'error' in result:
            continue
        
        # 사주 8자 추출 (방법별로 구조가 다를 수 있음)
        saju_data = {}
        
        if 'saju' in result:
            saju = result['saju']
            # AstroBaziEngine: saju['year'] = '신축' (문자열)
            # PerfectManseryeok: saju['year'] = {'ganzhi': '신축', ...} (딕셔너리)
            for pillar in ['year', 'month', 'day', 'hour']:
                pillar_value = saju.get(pillar, 'N/A')
                if isinstance(pillar_value, dict):
                    saju_data[pillar] = pillar_value.get('ganzhi', 'N/A')
                elif isinstance(pillar_value, str):
                    saju_data[pillar] = pillar_value
                else:
                    saju_data[pillar] = 'N/A'
        elif 'year' in result:
            # 직접 year, month, day, hour 키가 있는 경우
            for pillar in ['year', 'month', 'day', 'hour']:
                pillar_value = result.get(pillar, 'N/A')
                if isinstance(pillar_value, dict):
                    saju_data[pillar] = pillar_value.get('ganzhi', 'N/A')
                elif isinstance(pillar_value, str):
                    saju_data[pillar] = pillar_value
                else:
                    saju_data[pillar] = 'N/A'
        else:
            continue  # 사주 데이터가 없으면 스킵
        
        if saju_data:
            saju_dict[method] = saju_data
    
    # 비교
    if len(saju_dict) < 2:
        return verification
    
    methods = list(saju_dict.keys())
    base_method = methods[0]
    base_saju = saju_dict[base_method]
    
    for method in methods[1:]:
        method_saju = saju_dict[method]
        for pillar in ['year', 'month', 'day', 'hour']:
            if base_saju[pillar] != method_saju[pillar]:
                verification['all_match'] = False
                verification['differences'].append(
                    f"{pillar}주: {base_method}({base_saju[pillar]}) vs {method}({method_saju[pillar]})"
                )
    
    return verification


def main():
    """테스트 함수"""
    print("=" * 80)
    print("표준 만세력 우선 사용 시스템 v2 테스트")
    print("=" * 80)
    
    # 2021년 8월 6일 03:30 테스트
    result = calculate_saju_standard_first_v2(
        year=2021,
        month=8,
        day=6,
        hour=3,
        minute=30,
        longitude=126.9780,
        is_male=True,
        verify=True
    )
    
    print("\n📊 최종 결과:")
    print(f"  계산 방법: {result.get('calculation_method', 'N/A')}")
    
    # 사주 8자 출력 (구조에 맞게 처리)
    def get_ganzhi(data, pillar):
        """간지 추출 (문자열 또는 딕셔너리 모두 처리)"""
        value = data.get(pillar, 'N/A')
        if isinstance(value, dict):
            return value.get('ganzhi', 'N/A')
        elif isinstance(value, str):
            return value
        else:
            return 'N/A'
    
    if 'saju' in result:
        saju = result['saju']
        print(f"  연주: {get_ganzhi(saju, 'year')}")
        print(f"  월주: {get_ganzhi(saju, 'month')}")
        print(f"  일주: {get_ganzhi(saju, 'day')}")
        print(f"  시주: {get_ganzhi(saju, 'hour')}")
    elif 'year' in result:
        print(f"  연주: {get_ganzhi(result, 'year')}")
        print(f"  월주: {get_ganzhi(result, 'month')}")
        print(f"  일주: {get_ganzhi(result, 'day')}")
        print(f"  시주: {get_ganzhi(result, 'hour')}")
    
    # 검증 결과 출력
    if 'verification' in result:
        verification = result['verification']
        print(f"\n🔬 검증 결과:")
        print(f"  모든 방법 일치: {verification.get('all_match', False)}")
        if verification.get('differences'):
            print(f"  차이점:")
            for diff in verification['differences']:
                print(f"    - {diff}")


if __name__ == "__main__":
    main()

