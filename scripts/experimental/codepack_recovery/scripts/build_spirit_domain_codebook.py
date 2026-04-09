#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📖 SPIRIT 도메인 코드북 구축 스크립트

목적: 성경 구절 31,102개를 벡터화하여 S.bin 코드북 생성
- KJV, NASB, NIV 통합 (English Trinity)
- FileBasedMemory 우선 사용
- JSON 파일 Fallback

작성일: 2026-01-22
Operation: Neuro-Router (경로 A: 전인적 MoE 완성)
"""

import sys
from pathlib import Path
import logging
import numpy as np
import json

# 경로 설정
WORKSPACE_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "tools" / "core"))
sys.path.insert(0, str(WORKSPACE_ROOT / "tools"))

# Import (경로 문제 해결)
try:
    from tools.core.mkm_domain_codebook_router import MKMDomainCodebookRouter, Domain
except ImportError:
    try:
        from mkm_domain_codebook_router import MKMDomainCodebookRouter, Domain
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "core"))
        from mkm_domain_codebook_router import MKMDomainCodebookRouter, Domain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 70)
    logger.info("📖 SPIRIT 도메인 코드북 구축 시작")
    logger.info("=" * 70)
    logger.info("\n목표: 성경 구절 31,102개 벡터화")
    logger.info("소스: KJV + NASB + NIV (English Trinity)")
    logger.info("")
    
    # 1. MKMDomainCodebookRouter 초기화
    logger.info("🔧 MKMDomainCodebookRouter 초기화 중...")
    router = MKMDomainCodebookRouter(
        embedding_model="all-MiniLM-L6-v2",
        codebook_size_per_domain=31000  # 목표: 31,103개 구절 모두 포함 (GPU 사용)
    )
    logger.info("✅ MKMDomainCodebookRouter 초기화 완료")
    
    # 2. SPIRIT 도메인 데이터 로드
    logger.info("\n📖 SPIRIT 도메인 데이터 로드 중...")
    spirit_data = router.load_domain_data(Domain.SPIRIT)
    if not spirit_data:
        logger.error("❌ SPIRIT 도메인 데이터를 로드할 수 없습니다.")
        return False
    
    logger.info(f"✅ SPIRIT 도메인 데이터 로드: {len(spirit_data)}개 패턴")
    
    # 데이터 소스 분석
    kjv_count = sum(1 for _, tag in spirit_data if "kjv" in tag.lower())
    nasb_count = sum(1 for _, tag in spirit_data if "nasb" in tag.lower())
    niv_count = sum(1 for _, tag in spirit_data if "niv" in tag.lower())
    memory_count = sum(1 for _, tag in spirit_data if "memory" in tag.lower() or "logos" in tag.lower())
    
    logger.info(f"  - KJV 구절: {kjv_count}개")
    logger.info(f"  - NASB 구절: {nasb_count}개")
    logger.info(f"  - NIV 구절: {niv_count}개")
    logger.info(f"  - FileBasedMemory: {memory_count}개")
    logger.info(f"  - 기타: {len(spirit_data) - kjv_count - nasb_count - niv_count - memory_count}개")
    
    # 목표 31,102개 확인
    if len(spirit_data) < 1000:
        logger.warning(f"⚠️ 데이터가 부족합니다 (목표: 31,102개, 현재: {len(spirit_data)}개)")
        logger.warning("⚠️ FileBasedMemory 또는 JSON 파일에서 추가 데이터를 로드하세요.")
    elif len(spirit_data) >= 31000:
        logger.info(f"✅ 목표 달성: {len(spirit_data):,}개 구절 (목표: 31,102개)")
    else:
        logger.info(f"📊 현재: {len(spirit_data):,}개 구절 (목표: 31,102개, {((len(spirit_data)/31002)*100):.1f}%)")
    
    # 3. SPIRIT 도메인 코드북 구축
    logger.info("\n🔨 SPIRIT 도메인 코드북 구축 중...")
    logger.info("  (이 작업은 시간이 걸릴 수 있습니다...)")
    logger.info("  (force_rebuild=True로 강제 재구축)")
    try:
        codebook_result = router.build_domain_codebook(Domain.SPIRIT, force_rebuild=True)
        if not codebook_result:
            logger.error("❌ SPIRIT 도메인 코드북 구축 실패")
            return False
        
        logger.info(f"✅ SPIRIT 도메인 코드북 구축 완료")
        logger.info(f"  - 코드북 크기: {len(codebook_result.get('codebook', []))}")
        logger.info(f"  - 메타데이터: {len(codebook_result.get('metadata', []))}개")
    except Exception as e:
        logger.error(f"❌ 코드북 구축 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. 코드북 저장
    codebook_dir = WORKSPACE_ROOT / "data" / "mkm_domain_codebooks"
    codebook_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        filepath = codebook_dir / "S.bin"
        router.save_domain_codebook(Domain.SPIRIT, filepath)
        
        # 파일 크기 확인
        file_size_kb = filepath.stat().st_size / 1024
        file_size_mb = file_size_kb / 1024
        logger.info(f"✅ SPIRIT 도메인 코드북 저장 완료: {filepath}")
        logger.info(f"  - 파일 크기: {file_size_mb:.2f} MB ({file_size_kb:.2f} KB)")
    except Exception as e:
        logger.error(f"❌ 코드북 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 코드북 로드 테스트 및 도메인 감지 테스트
    logger.info("\n🔍 코드북 로드 테스트 중...")
    try:
        test_router = MKMDomainCodebookRouter()
        test_router.load_domain_codebook(Domain.SPIRIT, filepath)
        
        if test_router.domain_codebooks.get(Domain.SPIRIT) is None:
            logger.error("❌ 코드북 로드 테스트 실패: 코드북이 로드되지 않았습니다.")
            return False
        logger.info(f"✅ 코드북 로드 테스트 성공")
        logger.info(f"  - 코드북 벡터 수: {len(test_router.domain_codebooks[Domain.SPIRIT])}")
        
        # 도메인 감지 테스트
        test_queries = [
            "What does the Bible say about love?",
            "하나님의 사랑은 무엇인가?",
            "예수님의 가르침",
            "성경의 구원",
        ]
        
        logger.info("\n🔍 도메인 감지 테스트:")
        all_correct = True
        for query in test_queries:
            detected_domain = test_router.detect_domain(query)
            is_correct = detected_domain == Domain.SPIRIT
            status = "✅" if is_correct else "❌"
            logger.info(f"  {status} '{query}' → {detected_domain.value} (예상: S)")
            if not is_correct:
                all_correct = False
        
        if not all_correct:
            logger.warning("⚠️ 일부 도메인 감지 테스트 실패 (정확도 개선 필요)")
        else:
            logger.info("✅ 도메인 감지 정확도 확인")

    except Exception as e:
        logger.error(f"❌ 코드북 로드 또는 도메인 감지 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    logger.info("\n" + "=" * 70)
    logger.info("✅ SPIRIT 도메인 코드북 구축 완료")
    logger.info("=" * 70)
    logger.info(f"\n📊 최종 통계:")
    logger.info(f"  - 로드된 구절: {len(spirit_data):,}개")
    logger.info(f"  - 코드북 벡터: {len(codebook_result.get('codebook', []))}개")
    logger.info(f"  - 파일 크기: {file_size_mb:.2f} MB")
    logger.info(f"  - 저장 위치: {filepath}")
    logger.info("")
    
    return True

if __name__ == "__main__":
    if main():
        logger.info("\n✅ SPIRIT 도메인 코드북 구축 성공!")
        logger.info("\n다음 단계:")
        logger.info("  1. L (Logic) 도메인 코드북 구축")
        logger.info("  2. K (Knowledge) 도메인 코드북 구축")
        logger.info("  3. M (Material) 도메인 코드북 구축")
        logger.info("  4. 전체 MoE 구조 통합 테스트")
    else:
        logger.error("\n❌ SPIRIT 도메인 코드북 구축 실패")

