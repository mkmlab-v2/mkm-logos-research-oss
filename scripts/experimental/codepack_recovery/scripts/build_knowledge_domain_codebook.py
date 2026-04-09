#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💰 KNOWLEDGE 도메인 코드북 구축 스크립트

목적: 투자/금융 데이터를 벡터화하여 K.bin 코드북 생성
- FileBasedMemory finance_market, finance_core 컬렉션 활용
- 투자 용어 및 금융 패턴 포함
- 지식/공학 관련 텍스트 벡터화

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
    logger.info("💰 KNOWLEDGE 도메인 코드북 구축 시작")
    logger.info("=" * 70)
    logger.info("\n목표: 투자/금융 데이터 벡터화")
    logger.info("소스: FileBasedMemory finance_market + finance_core")
    logger.info("")
    
    # 1. MKMDomainCodebookRouter 초기화
    logger.info("🔧 MKMDomainCodebookRouter 초기화 중...")
    router = MKMDomainCodebookRouter(
        embedding_model="all-MiniLM-L6-v2",
        codebook_size_per_domain=10000  # K 도메인에 맞게 조정 가능
    )
    logger.info("✅ MKMDomainCodebookRouter 초기화 완료")
    
    # 2. KNOWLEDGE 도메인 데이터 로드
    logger.info("\n💰 KNOWLEDGE 도메인 데이터 로드 중...")
    knowledge_data = router.load_domain_data(Domain.KNOWLEDGE)
    if not knowledge_data:
        logger.error("❌ KNOWLEDGE 도메인 데이터를 로드할 수 없습니다.")
        return False
    
    logger.info(f"✅ KNOWLEDGE 도메인 데이터 로드: {len(knowledge_data)}개 패턴")
    
    # 데이터 소스 분석
    finance_count = sum(1 for _, tag in knowledge_data if "finance" in tag.lower() or "market" in tag.lower() or "투자" in tag.lower() or "금융" in tag.lower())
    investment_count = sum(1 for _, tag in knowledge_data if "investment" in tag.lower() or "stock" in tag.lower() or "주식" in tag.lower())
    memory_count = sum(1 for _, tag in knowledge_data if "memory" in tag.lower())
    
    logger.info(f"  - 금융/시장: {finance_count}개")
    logger.info(f"  - 투자/주식: {investment_count}개")
    logger.info(f"  - FileBasedMemory: {memory_count}개")
    logger.info(f"  - 기타: {len(knowledge_data) - finance_count - investment_count - memory_count}개")
    
    # 데이터 부족 경고
    if len(knowledge_data) < 100:
        logger.warning(f"⚠️ 데이터가 부족합니다 (현재: {len(knowledge_data)}개)")
        logger.warning("⚠️ FileBasedMemory에서 추가 데이터를 로드하거나 샘플 데이터를 사용합니다.")
    
    # 3. KNOWLEDGE 도메인 코드북 구축
    logger.info("\n🔨 KNOWLEDGE 도메인 코드북 구축 중...")
    logger.info("  (이 작업은 시간이 걸릴 수 있습니다...)")
    try:
        codebook_result = router.build_domain_codebook(Domain.KNOWLEDGE)
        if not codebook_result:
            logger.error("❌ KNOWLEDGE 도메인 코드북 구축 실패")
            return False
        
        logger.info(f"✅ KNOWLEDGE 도메인 코드북 구축 완료")
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
        filepath = codebook_dir / "K.bin"
        router.save_domain_codebook(Domain.KNOWLEDGE, filepath)
        
        # 파일 크기 확인
        file_size_kb = filepath.stat().st_size / 1024
        file_size_mb = file_size_kb / 1024
        logger.info(f"✅ KNOWLEDGE 도메인 코드북 저장 완료: {filepath}")
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
        test_router.load_domain_codebook(Domain.KNOWLEDGE, filepath)
        
        if test_router.domain_codebooks.get(Domain.KNOWLEDGE) is None:
            logger.error("❌ 코드북 로드 테스트 실패: 코드북이 로드되지 않았습니다.")
            return False
        logger.info(f"✅ 코드북 로드 테스트 성공")
        logger.info(f"  - 코드북 벡터 수: {len(test_router.domain_codebooks[Domain.KNOWLEDGE])}")
        
        # 도메인 감지 테스트
        test_queries = [
            "What is EPS in stock market?",
            "주식 시장에서 EPS는 무엇인가?",
            "투자 전략",
            "금융 시장 분석",
        ]
        
        logger.info("\n🔍 도메인 감지 테스트:")
        all_correct = True
        for query in test_queries:
            detected_domain = test_router.detect_domain(query)
            is_correct = detected_domain == Domain.KNOWLEDGE
            status = "✅" if is_correct else "❌"
            logger.info(f"  {status} '{query}' → {detected_domain.value} (예상: K)")
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
    logger.info("✅ KNOWLEDGE 도메인 코드북 구축 완료")
    logger.info("=" * 70)
    logger.info(f"\n📊 최종 통계:")
    logger.info(f"  - 로드된 패턴: {len(knowledge_data):,}개")
    logger.info(f"  - 코드북 벡터: {len(codebook_result.get('codebook', []))}개")
    logger.info(f"  - 파일 크기: {file_size_mb:.2f} MB")
    logger.info(f"  - 저장 위치: {filepath}")
    logger.info("")
    
    return True

if __name__ == "__main__":
    if main():
        logger.info("\n✅ KNOWLEDGE 도메인 코드북 구축 성공!")
        logger.info("\n다음 단계:")
        logger.info("  1. M (Material) 도메인 코드북 구축")
        logger.info("  2. 전체 MoE 구조 통합 테스트")
    else:
        logger.error("\n❌ KNOWLEDGE 도메인 코드북 구축 실패")

