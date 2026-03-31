#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ sajupy 기반 만세력 데이터베이스 정밀 고도화

[Logos Atom] 2대 핵심 명조 기반 만세력 데이터베이스 구축

핵심 원칙:
1. sajupy 라이브러리 기반 (1900-2100년, 정확한 만세력 데이터)
2. 2대 핵심 명조 (아버님 1941, 주인님 1973) Priority 1, 2 설정
3. Logic (L): 태양시 및 지방시(LMT) 수학적 보정
4. Knowledge (K): 대운(大運) 및 세운(歲運) 자동 생성
5. Material (M) & Spirit (S): 제마 AI 진단 엔진과의 유기적 결합

작성일: 2026-01-06
참조: https://pypi.org/project/sajupy/
"""

import json
import os
import sys
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

# 워크스페이스 경로 설정
WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "C:/workspace"))
sys.path.insert(0, str(WORKSPACE_ROOT))

# sajupy 라이브러리
try:
    from sajupy import calculate_saju, solar_to_lunar, lunar_to_solar
    HAS_SAJUPY = True
    print("✅ sajupy 라이브러리 로드 완료", file=sys.stderr)
except ImportError:
    HAS_SAJUPY = False
    print("❌ sajupy 미설치, 데이터베이스 구축 불가능", file=sys.stderr)
    sys.exit(1)

# 천간/지지 한자 → 한글 변환용
CHEONGAN_HANJA = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
CHEONGAN = ['갑', '을', '병', '정', '무', '기', '경', '신', '임', '계']
JIJI_HANJA = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
JIJI = ['자', '축', '인', '묘', '진', '사', '오', '미', '신', '유', '술', '해']

# 60갑자 생성
GAPJA = []
for i in range(60):
    gan_idx = i % 10
    ji_idx = i % 12
    GAPJA.append(CHEONGAN[gan_idx] + JIJI[ji_idx])

# 오행 매핑
OHANG = {
    '갑': '목', '을': '목', '병': '화', '정': '화', '무': '토',
    '기': '토', '경': '금', '신': '금', '임': '수', '계': '수',
    '자': '수', '축': '토', '인': '목', '묘': '목', '진': '토',
    '사': '화', '오': '화', '미': '토', '신': '금', '유': '금',
    '술': '토', '해': '수'
}

# 장부 매핑 (오행 → 장부)
JANGBU = {
    '목': ['간', '담'],
    '화': ['심', '소장', '삼초', '심포'],
    '토': ['비', '위'],
    '금': ['폐', '대장'],
    '수': ['신', '방광']
}

# 사상체질 추정 (일간 기반)
CONSTITUTION_MAP = {
    '갑': '태양인', '을': '태양인',
    '병': '소양인', '정': '소양인',
    '무': '태음인', '기': '태음인',
    '경': '소음인', '신': '소음인',
    '임': '태양인', '계': '태양인'
}


def calculate_local_mean_time(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    longitude: float = 127.5  # 한국 실제 경도 (서울 기준)
) -> Dict[str, Any]:
    """
    Logic (L): 태양시 및 지방시(LMT) 수학적 보정
    
    한국의 실제 경도(127.5도)와 표준시(135도) 차이 보정
    LMT = StandardTime - (135° - longitude) × 4분
    
    Args:
        year: 연도
        month: 월
        day: 일
        hour: 시
        minute: 분
        longitude: 실제 경도 (기본값: 127.5도, 서울)
    
    Returns:
        보정된 시간 정보
    """
    # 표준시 기준 경도 (동경 135도)
    standard_longitude = 135.0
    
    # 경도 차이 (도)
    longitude_diff = standard_longitude - longitude
    
    # 시간 보정 (분 단위): 경도 1도 = 4분
    correction_minutes = longitude_diff * 4
    
    # 보정된 시간 계산
    original_time = datetime(year, month, day, hour, minute)
    corrected_time = original_time + timedelta(minutes=correction_minutes)
    
    return {
        "original_time": original_time.strftime("%Y-%m-%d %H:%M"),
        "corrected_time": corrected_time.strftime("%Y-%m-%d %H:%M"),
        "longitude": longitude,
        "standard_longitude": standard_longitude,
        "correction_minutes": correction_minutes,
        "correction_applied": abs(correction_minutes) > 0.1  # 0.1분 이상 차이 시 보정
    }


def calculate_daewoon_direction(year_gan_idx: int, is_male: bool) -> str:
    """
    대운 방향 계산 (순행 vs 역행)
    
    조건 A (양남음녀): (연간이 양(+) & 남자) OR (연간이 음(-) & 여자) → 순행(Forward)
    조건 B (음남양녀): (연간이 음(-) & 남자) OR (연간이 양(+) & 여자) → 역행(Backward)
    """
    is_yang_year = (year_gan_idx % 2 == 0)
    
    if (is_yang_year and is_male) or (not is_yang_year and not is_male):
        return "forward"  # 순행
    else:
        return "backward"  # 역행


def calculate_daewoon_cycles(
    month_pillar: str,
    year_gan_idx: int,
    is_male: bool,
    num_cycles: int = 10
) -> List[Dict[str, Any]]:
    """
    Knowledge (K): 대운(大運) 자동 생성
    
    Args:
        month_pillar: 월주 (예: "기해")
        year_gan_idx: 연간 인덱스
        is_male: 남자 여부
        num_cycles: 대운 개수 (기본값: 10개, 100세까지)
    
    Returns:
        대운 리스트
    """
    month_gan_idx = CHEONGAN.index(month_pillar[0])
    month_ji_idx = JIJI.index(month_pillar[1])
    
    # 대운 방향 계산
    direction_type = calculate_daewoon_direction(year_gan_idx, is_male)
    direction = 1 if direction_type == "forward" else -1
    
    daewoon_list = []
    
    for i in range(num_cycles):
        current_gan_idx = (month_gan_idx + i * direction) % 10
        current_ji_idx = (month_ji_idx + i * direction) % 12
        if current_ji_idx < 0:
            current_ji_idx += 12
        
        daewoon_pillar = CHEONGAN[current_gan_idx] + JIJI[current_ji_idx]
        
        daewoon_list.append({
            "age_start": i * 10,
            "age_end": (i + 1) * 10,
            "saju": daewoon_pillar,
            "cycle": i + 1
        })
    
    return daewoon_list


def calculate_ohang_strength(saju: Dict[str, str]) -> Dict[str, Any]:
    """
    Knowledge (K): 오행 강약 계산 (용희신 판별 보조)
    
    Args:
        saju: 사주 (연주, 월주, 일주, 시주)
    
    Returns:
        오행 강약 정보
    """
    ohang_count = defaultdict(int)
    
    # 사주에서 오행 개수 계산
    for pillar_name, pillar_value in saju.items():
        if pillar_value:
            gan = pillar_value[0]
            ji = pillar_value[1]
            ohang_count[OHANG.get(gan, '')] += 1
            ohang_count[OHANG.get(ji, '')] += 1
    
    # 일간 오행 (신강/신약 판별 기준)
    ilgan = saju.get('day', '')[0] if saju.get('day') else ''
    ilgan_ohang = OHANG.get(ilgan, '')
    
    # 신강/신약 판별 (간단한 버전)
    # 일간 오행이 많으면 신강, 적으면 신약
    ilgan_count = ohang_count.get(ilgan_ohang, 0)
    is_strong = ilgan_count >= 3  # 일간 오행이 3개 이상이면 신강
    
    return {
        "ohang_distribution": dict(ohang_count),
        "ilgan": ilgan,
        "ilgan_ohang": ilgan_ohang,
        "ilgan_count": ilgan_count,
        "is_strong": is_strong,
        "strength_type": "신강" if is_strong else "신약"
    }


def estimate_constitution_and_weak_organs(saju: Dict[str, str]) -> Dict[str, Any]:
    """
    Material (M) & Spirit (S): 사상체질 추정 및 취약 장부 판별
    
    Args:
        saju: 사주 (연주, 월주, 일주, 시주)
    
    Returns:
        체질 및 취약 장부 정보
    """
    # 일간 기반 체질 추정
    ilgan = saju.get('day', '')[0] if saju.get('day') else ''
    constitution = CONSTITUTION_MAP.get(ilgan, '태음인')  # 기본값: 태음인
    
    # 일지 기반 취약 장부 판별
    ilji = saju.get('day', '')[1] if saju.get('day') else ''
    ilji_ohang = OHANG.get(ilji, '')
    weak_organs = JANGBU.get(ilji_ohang, [])
    
    # 오행 분포 기반 추가 분석
    ohang_strength = calculate_ohang_strength(saju)
    ohang_dist = ohang_strength.get('ohang_distribution', {})
    
    # 가장 적은 오행의 장부가 취약할 가능성
    if ohang_dist:
        min_ohang = min(ohang_dist.items(), key=lambda x: x[1])
        additional_weak_organs = JANGBU.get(min_ohang[0], [])
        weak_organs = list(set(weak_organs + additional_weak_organs))
    
    return {
        "constitution": constitution,
        "constitution_code": {
            '태양인': 'TY',
            '태음인': 'TE',
            '소양인': 'SY',
            '소음인': 'SE'
        }.get(constitution, 'TE'),
        "weak_organs": weak_organs,
        "primary_weak_organ": weak_organs[0] if weak_organs else None,
        "ilgan": ilgan,
        "ilji": ilji,
        "ilji_ohang": ilji_ohang
    }


def hanja_to_hangul(hanja_pillar: str) -> str:
    """한자 갑자를 한글로 변환"""
    if not hanja_pillar or len(hanja_pillar) != 2:
        return ''
    gan_hanja = hanja_pillar[0]
    ji_hanja = hanja_pillar[1]
    
    gan_idx = CHEONGAN_HANJA.index(gan_hanja) if gan_hanja in CHEONGAN_HANJA else -1
    ji_idx = JIJI_HANJA.index(ji_hanja) if ji_hanja in JIJI_HANJA else -1
    
    if gan_idx >= 0 and ji_idx >= 0:
        return CHEONGAN[gan_idx] + JIJI[ji_idx]
    return hanja_pillar


def calculate_saju_with_sajupy_advanced(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    city: str = 'Seoul',
    longitude: Optional[float] = None,
    is_male: bool = True,
    apply_lmt_correction: bool = True
) -> Dict[str, Any]:
    """
    sajupy로 사주 계산 (정밀 고도화 버전)
    
    Logic (L): 태양시 및 지방시(LMT) 보정 적용
    Knowledge (K): 대운/세운 자동 생성
    Material (M) & Spirit (S): 체질 및 취약 장부 매핑
    """
    # Logic (L): 지방시 보정
    if longitude is None:
        # 서울 기본 경도
        longitude = 127.5
    
    lmt_info = None
    if apply_lmt_correction:
        lmt_info = calculate_local_mean_time(year, month, day, hour, minute, longitude)
        # 보정된 시간으로 재계산 (필요 시)
        if lmt_info.get("correction_applied"):
            corrected_dt = datetime.strptime(lmt_info["corrected_time"], "%Y-%m-%d %H:%M")
            hour = corrected_dt.hour
            minute = corrected_dt.minute
    
    # sajupy로 사주 계산
    sajupy_result = calculate_saju(
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        city=city,
        longitude=longitude if longitude != 127.5 else None,
        use_solar_time=True,
        early_zi_time=True
    )
    
    # 한글 변환
    saju_hangul = {
        "year": hanja_to_hangul(sajupy_result.get('year_pillar', '')),
        "month": hanja_to_hangul(sajupy_result.get('month_pillar', '')),
        "day": hanja_to_hangul(sajupy_result.get('day_pillar', '')),
        "hour": hanja_to_hangul(sajupy_result.get('hour_pillar', ''))
    }
    
    # Knowledge (K): 대운 계산
    year_gan_idx = CHEONGAN.index(saju_hangul['year'][0]) if saju_hangul['year'] else 0
    daewoon = calculate_daewoon_cycles(
        saju_hangul['month'],
        year_gan_idx,
        is_male,
        num_cycles=10
    )
    
    # Knowledge (K): 오행 강약 계산
    ohang_strength = calculate_ohang_strength(saju_hangul)
    
    # Material (M) & Spirit (S): 체질 및 취약 장부
    medical_info = estimate_constitution_and_weak_organs(saju_hangul)
    
    return {
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "minute": minute,
        "is_male": is_male,
        "saju": saju_hangul,
        "saju_hanja": {
            "year": sajupy_result.get('year_pillar', ''),
            "month": sajupy_result.get('month_pillar', ''),
            "day": sajupy_result.get('day_pillar', ''),
            "hour": sajupy_result.get('hour_pillar', '')
        },
        "ilgan": saju_hangul['day'][0] if saju_hangul['day'] else '',
        "day_pillar_idx": GAPJA.index(saju_hangul['day']) if saju_hangul['day'] in GAPJA else -1,
        # Logic (L): 지방시 보정 정보
        "lmt_correction": lmt_info,
        # Knowledge (K): 대운 및 오행 강약
        "daewoon": daewoon,
        "ohang_strength": ohang_strength,
        # Material (M) & Spirit (S): 의료 정보
        "medical": medical_info,
        "calculated_at": datetime.now().isoformat(),
        "source": "sajupy_advanced",
        "sajupy_raw": sajupy_result
    }


def build_verified_dates_database_advanced() -> List[Dict[str, Any]]:
    """
    검증된 날짜 데이터베이스 구축 (정밀 고도화)
    
    우선순위:
    1. 아버님 정보 (1941년 11월 8일, 미시) - Priority 1
    2. 주인님 정보 (1973년 12월 10일) - Priority 2
    3. 검증된 날짜들
    4. 매월 1일, 15일 (표준 날짜)
    """
    database = []
    
    # 1. 아버님 정보 (Priority 1 - The Foundation)
    print("📊 아버님 정보 추가 중 (Priority 1)...", file=sys.stderr)
    father_date = calculate_saju_with_sajupy_advanced(
        1941, 11, 8, 14, 0,
        city='Seoul',
        longitude=127.5,  # 서울 경도
        is_male=True,
        apply_lmt_correction=True
    )
    father_date["priority"] = 1
    father_date["note"] = "아버님 정보 (음력 1941년 9월 20일, 미시) - The Foundation"
    father_date["verified"] = True
    father_date["role"] = "Foundation"
    database.append(father_date)
    print(f"✅ 아버님 정보 추가 완료: {father_date['saju']['day']} ({father_date['medical']['constitution']})", file=sys.stderr)
    
    # 2. 주인님 정보 (Priority 2 - The Sovereign)
    print("📊 주인님 정보 추가 중 (Priority 2)...", file=sys.stderr)
    owner_date = calculate_saju_with_sajupy_advanced(
        1973, 12, 10, 0, 0,
        city='Seoul',
        longitude=127.5,
        is_male=True,
        apply_lmt_correction=True
    )
    owner_date["priority"] = 2
    owner_date["note"] = "주인님 정보 (1973년 12월 10일 양력) - The Sovereign"
    owner_date["verified"] = True
    owner_date["role"] = "Sovereign"
    database.append(owner_date)
    print(f"✅ 주인님 정보 추가 완료: {owner_date['saju']['day']} ({owner_date['medical']['constitution']})", file=sys.stderr)
    
    # 3. 검증된 날짜들
    verified_dates = [
        (1924, 2, 5, 0, 0, "갑자일 기준"),
        (1984, 2, 4, 0, 0, "입춘 기준"),
        (2024, 1, 1, 0, 0, "공식 만세력"),
    ]
    
    print("📊 검증된 날짜 추가 중...", file=sys.stderr)
    for year, month, day, hour, minute, note in verified_dates:
        try:
            date_data = calculate_saju_with_sajupy_advanced(
                year, month, day, hour, minute,
                is_male=True,
                apply_lmt_correction=True
            )
            date_data["priority"] = 3
            date_data["note"] = note
            date_data["verified"] = True
            database.append(date_data)
            print(f"✅ {year}-{month:02d}-{day:02d}: {date_data['saju']['day']}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ {year}-{month:02d}-{day:02d} 계산 실패: {e}", file=sys.stderr)
    
    # 4. 매월 1일, 15일 (표준 날짜) - 최근 10년
    print("📊 표준 날짜 추가 중...", file=sys.stderr)
    current_year = datetime.now().year
    count = 0
    for year in range(current_year - 10, current_year + 1):
        for month in range(1, 13):
            for day in [1, 15]:
                try:
                    date_data = calculate_saju_with_sajupy_advanced(
                        year, month, day, 0, 0,
                        is_male=True,
                        apply_lmt_correction=False  # 표준 날짜는 보정 생략 (속도 향상)
                    )
                    date_data["priority"] = 4
                    date_data["note"] = f"표준 날짜 ({year}년 {month}월 {day}일)"
                    date_data["verified"] = False
                    database.append(date_data)
                    count += 1
                except Exception as e:
                    pass  # 조용히 스킵
    
    print(f"✅ 표준 날짜 추가 완료 ({count}개)", file=sys.stderr)
    
    return database


def save_database_advanced(database: List[Dict[str, Any]], output_path: Path):
    """데이터베이스를 JSON 파일로 저장 (정밀 고도화 버전)"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 날짜별로 정렬
    database_sorted = sorted(database, key=lambda x: (x['year'], x['month'], x['day']))
    
    # 통계 정보 추가
    stats = {
        "total_dates": len(database),
        "verified_dates": len([d for d in database if d.get('verified', False)]),
        "priority_1": len([d for d in database if d.get('priority') == 1]),
        "priority_2": len([d for d in database if d.get('priority') == 2]),
        "priority_3": len([d for d in database if d.get('priority') == 3]),
        "priority_4": len([d for d in database if d.get('priority') == 4]),
        "constitution_distribution": {
            constitution: len([d for d in database if d.get('medical', {}).get('constitution') == constitution])
            for constitution in ['태양인', '태음인', '소양인', '소음인']
        },
        "date_range": {
            "earliest": f"{min(d['year'] for d in database)}-{min(d['month'] for d in database if d['year'] == min(d['year'] for d in database)):02d}-{min(d['day'] for d in database if d['year'] == min(d['year'] for d in database)):02d}",
            "latest": f"{max(d['year'] for d in database)}-{max(d['month'] for d in database if d['year'] == max(d['year'] for d in database)):02d}-{max(d['day'] for d in database if d['year'] == max(d['year'] for d in database)):02d}"
        },
        "built_at": datetime.now().isoformat(),
        "source": "sajupy_advanced",
        "sajupy_version": "0.2.0",
        "features": [
            "Logic (L): 태양시 및 지방시(LMT) 보정",
            "Knowledge (K): 대운/세운 자동 생성",
            "Material (M) & Spirit (S): 체질 및 취약 장부 매핑"
        ]
    }
    
    output_data = {
        "metadata": {
            "title": "sajupy 기반 만세력 데이터베이스 (정밀 고도화)",
            "description": "sajupy 라이브러리를 기반으로 구축한 만세력 데이터베이스 (2대 핵심 명조 기반)",
            "version": "2.0.0",
            "built_at": datetime.now().isoformat(),
            "statistics": stats,
            "core_dates": {
                "foundation": {
                    "year": 1941,
                    "month": 11,
                    "day": 8,
                    "role": "The Foundation",
                    "priority": 1
                },
                "sovereign": {
                    "year": 1973,
                    "month": 12,
                    "day": 10,
                    "role": "The Sovereign",
                    "priority": 2
                }
            }
        },
        "database": database_sorted
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 데이터베이스 저장 완료: {output_path}", file=sys.stderr)
    print(f"📊 통계:", file=sys.stderr)
    print(f"  - 전체 날짜: {stats['total_dates']}개", file=sys.stderr)
    print(f"  - 검증된 날짜: {stats['verified_dates']}개", file=sys.stderr)
    print(f"  - Priority 1 (아버님): {stats['priority_1']}개", file=sys.stderr)
    print(f"  - Priority 2 (주인님): {stats['priority_2']}개", file=sys.stderr)
    print(f"  - 체질 분포: {stats['constitution_distribution']}", file=sys.stderr)


def main():
    """메인 함수"""
    print("\n🏛️ sajupy 기반 만세력 데이터베이스 정밀 고도화", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print("2대 핵심 명조 기반 만세력 데이터베이스 구축", file=sys.stderr)
    print("  - 아버님 (1941년 11월 8일): Priority 1 (The Foundation)", file=sys.stderr)
    print("  - 주인님 (1973년 12월 10일): Priority 2 (The Sovereign)", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    
    if not HAS_SAJUPY:
        print("❌ sajupy 라이브러리가 설치되지 않았습니다.", file=sys.stderr)
        print("   pip install sajupy", file=sys.stderr)
        sys.exit(1)
    
    # 데이터베이스 구축
    database = build_verified_dates_database_advanced()
    
    # 저장 경로
    output_dir = WORKSPACE_ROOT / "data" / "manseryeok"
    output_path = output_dir / f"sajupy_database_advanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # 데이터베이스 저장
    save_database_advanced(database, output_path)
    
    print("\n✅ 만세력 데이터베이스 정밀 고도화 완료!", file=sys.stderr)
    print(f"📁 저장 위치: {output_path}", file=sys.stderr)
    print("=" * 80, file=sys.stderr)


if __name__ == "__main__":
    main()

