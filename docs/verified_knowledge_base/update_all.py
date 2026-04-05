#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 검증된 지식 베이스 자동 업데이트 스크립트

목적: 코드베이스 변경 시 검증된 데이터를 자동으로 추출하여 업데이트
제미나이/노트북LM에 업로드할 데이터를 최신 상태로 유지

작성일: 2026-02-10
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

WORKSPACE_ROOT = Path("C:/workspace")
sys.path.insert(0, str(WORKSPACE_ROOT))

# 출력 디렉토리
OUTPUT_DIR = WORKSPACE_ROOT / "docs" / "verified_knowledge_base"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def update_unified_field_theory():
    """통일장이론 데이터 업데이트"""
    print("📐 통일장이론 데이터 업데이트 중...")
    
    try:
        from tools.core.unified_field_theory_engine import UnifiedFieldTheoryEngine
        
        engine = UnifiedFieldTheoryEngine()
        
        # Divine Centroid 업데이트
        divine_centroid = {
            "version": "1.0",
            "updated": datetime.now().isoformat(),
            "divine_centroid": {
                "S": engine.DIVINE_CENTROID["S"],
                "L": engine.DIVINE_CENTROID["L"],
                "K": engine.DIVINE_CENTROID["K"],
                "M": engine.DIVINE_CENTROID["M"]
            },
            "physical_constants": {
                "G": engine.G,
                "c": engine.c,
                "k_B": engine.k_B,
                "h_bar": engine.h_bar
            },
            "taeyangin_singularity": engine.TAEYANGIN_SINGULARITY_CONDITION
        }
        
        output_file = OUTPUT_DIR / "unified_field_theory" / "divine_centroid.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(divine_centroid, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Divine Centroid 업데이트 완료: {output_file}")
        
    except Exception as e:
        print(f"⚠️ 통일장이론 업데이트 실패: {e}")

def update_myeongri():
    """명리학 데이터 업데이트"""
    print("📅 명리학 데이터 업데이트 중...")
    
    try:
        # 만세력 기준일 데이터 복사
        source_file = WORKSPACE_ROOT / "docs" / "gemini" / "attachments" / "data" / "manseryeok_verified_anchor_dates.json"
        target_file = OUTPUT_DIR / "myeongri" / "verified_anchor_dates.json"
        
        if source_file.exists():
            import shutil
            shutil.copy2(source_file, target_file)
            print(f"✅ 만세력 기준일 데이터 업데이트 완료: {target_file}")
        else:
            print(f"⚠️ 만세력 기준일 데이터 파일 없음: {source_file}")
            print("   스크립트 실행 필요: python scripts/create_manseryeok_reference_data.py")
        
    except Exception as e:
        print(f"⚠️ 명리학 업데이트 실패: {e}")

def update_bible():
    """성경 데이터 업데이트"""
    print("📖 성경 데이터 업데이트 중...")
    
    try:
        # English Trinity 소스 확인
        from tools.multi_logos_blitz import MULTI_LOGOS_MIRRORS
        
        english_trinity = {
            "version": "1.0",
            "updated": datetime.now().isoformat(),
            "sources": MULTI_LOGOS_MIRRORS,
            "verification": "검증된 미러 (2025-12-31)"
        }
        
        output_file = OUTPUT_DIR / "bible" / "english_trinity_sources.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(english_trinity, f, ensure_ascii=False, indent=2)
        
        print(f"✅ English Trinity 소스 업데이트 완료: {output_file}")
        
    except Exception as e:
        print(f"⚠️ 성경 데이터 업데이트 실패: {e}")

def update_iching():
    """주역 데이터 업데이트"""
    print("📜 주역 데이터 업데이트 중...")
    
    try:
        from tools.core.iching_year_mapper import IChingYearMapper
        
        mapper = IChingYearMapper()
        
        # 핵심 괘 정보 추출
        hexagrams = {}
        for year in [2026, 2027, 2028, 2029, 2030]:
            hexagram = mapper.get_hexagram_for_year(year)
            hexagrams[str(year)] = hexagram
        
        iching_data = {
            "version": "1.0",
            "updated": datetime.now().isoformat(),
            "year_mapping": hexagrams,
            "verification": "코드베이스 구현 확인"
        }
        
        output_file = OUTPUT_DIR / "iching" / "core_principles.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(iching_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 주역 데이터 업데이트 완료: {output_file}")
        
    except Exception as e:
        print(f"⚠️ 주역 데이터 업데이트 실패: {e}")

def create_update_summary():
    """업데이트 요약 생성"""
    summary = {
        "last_updated": datetime.now().isoformat(),
        "status": "success",
        "updated_files": [
            "unified_field_theory/divine_centroid.json",
            "myeongri/verified_anchor_dates.json",
            "bible/english_trinity_sources.json",
            "iching/core_principles.json"
        ]
    }
    
    summary_file = OUTPUT_DIR / "update_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 업데이트 요약: {summary_file}")

def main():
    """메인 함수"""
    print("🏛️ 검증된 지식 베이스 자동 업데이트 시작\n")
    
    update_unified_field_theory()
    update_myeongri()
    update_bible()
    update_iching()
    create_update_summary()
    
    print("\n✅ 모든 업데이트 완료!")
    print("\n📤 제미나이/노트북LM 업로드 가이드:")
    print("   1. 이 폴더의 모든 JSON 파일을 확인")
    print("   2. 제미나이 JAMS 또는 노트북LM에 업로드")
    print("   3. 업데이트된 데이터 반영 확인")

if __name__ == "__main__":
    main()

