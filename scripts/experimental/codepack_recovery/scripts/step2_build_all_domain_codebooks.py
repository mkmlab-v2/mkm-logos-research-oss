#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 2: 도메인 코드북 (DNA) 상주 시스템 구축

목적: 모든 도메인 코드북 사전 구축 및 배포 시스템 구축
- 도메인별 코드북 사전 구축 (1,540개 핵심 음절)
- 코드북 배포 시스템 구축 (수신 측 상주)
- 인덱스 기반 압축 강제 적용

수학 헌법 연계:
- 제7장 공식 7-3: 7.2배 최적화 계수
- 중복 엔트로피 제거: 37.9배 비효율 → 7.2배 효율

작성일: 2026-01-31
"""

import sys
from pathlib import Path
import logging

WORKSPACE_ROOT = Path("C:/workspace")
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "projects" / "mkm" / "mkm-backend-nitro" / "app" / "core"))

from mkm_domain_codebook_router import MKMDomainCodebookRouter, Domain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_all_domain_codebooks(force_rebuild: bool = False):
    """
    모든 도메인 코드북 구축
    
    Args:
        force_rebuild: 기존 코드북이 있어도 강제로 재구축 (기본값: False)
    """
    logger.info("=" * 80)
    logger.info("🏛️ Step 2: 도메인 코드북 (DNA) 상주 시스템 구축")
    logger.info("=" * 80)
    
    # 1. 라우터 초기화
    try:
        router = MKMDomainCodebookRouter(
            embedding_model="all-MiniLM-L6-v2",
            codebook_size_per_domain=10000  # 도메인당 코드북 크기
        )
        logger.info("✅ MKMDomainCodebookRouter 초기화 완료")
    except Exception as e:
        logger.error(f"❌ 초기화 실패: {e}")
        return False
    
    # 2. 코드북 디렉토리 생성
    codebook_dir = WORKSPACE_ROOT / "data" / "mkm_domain_codebooks"
    codebook_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📂 코드북 디렉토리: {codebook_dir}")
    
    # 3. 모든 도메인 코드북 구축
    results = {}
    all_domains = [Domain.SPIRIT, Domain.LOGIC, Domain.KNOWLEDGE, Domain.MATERIAL, Domain.TRADING, Domain.CODING]
    
    for domain in all_domains:
        logger.info(f"\n{'='*80}")
        logger.info(f"🔨 {domain.name} ({domain.value}) 도메인 코드북 구축 중...")
        logger.info(f"{'='*80}")
        
        try:
            # 코드북 구축
            codebook_result = router.build_domain_codebook(domain, force_rebuild=force_rebuild)
            
            if not codebook_result:
                logger.error(f"❌ {domain.name} 도메인 코드북 구축 실패")
                results[domain.value] = {"success": False, "error": "구축 실패"}
                continue
            
            # 코드북 크기 확인
            codebook_size = len(codebook_result.get("codebook", []))
            metadata_size = len(codebook_result.get("metadata", []))
            
            logger.info(f"✅ {domain.name} 도메인 코드북 구축 완료:")
            logger.info(f"  - 코드북 크기: {codebook_size}")
            logger.info(f"  - 메타데이터: {metadata_size}개")
            logger.info(f"  - 캐시 사용: {codebook_result.get('from_cache', False)}")
            
            # 코드북 저장
            filepath = codebook_dir / f"{domain.value}.bin"
            if router.save_domain_codebook(domain, filepath, include_text_mapping=False):
                logger.info(f"✅ 코드북 저장 완료: {filepath}")
                results[domain.value] = {
                    "success": True,
                    "codebook_size": codebook_size,
                    "metadata_size": metadata_size,
                    "filepath": str(filepath),
                    "from_cache": codebook_result.get("from_cache", False)
                }
            else:
                logger.error(f"❌ 코드북 저장 실패: {filepath}")
                results[domain.value] = {"success": False, "error": "저장 실패"}
                
        except Exception as e:
            logger.error(f"❌ {domain.name} 도메인 코드북 구축 중 오류: {e}")
            import traceback
            traceback.print_exc()
            results[domain.value] = {"success": False, "error": str(e)}
    
    # 4. 결과 요약
    logger.info("\n" + "=" * 80)
    logger.info("📊 도메인 코드북 구축 결과 요약")
    logger.info("=" * 80)
    
    success_count = sum(1 for r in results.values() if r.get("success", False))
    total_count = len(results)
    
    logger.info(f"총 도메인: {total_count}개")
    logger.info(f"구축 성공: {success_count}개 ({success_count/total_count*100:.1f}%)")
    logger.info(f"구축 실패: {total_count - success_count}개")
    
    for domain_code, result in results.items():
        if result.get("success"):
            logger.info(f"  ✅ {domain_code}: {result.get('metadata_size', 0)}개 항목")
        else:
            logger.error(f"  ❌ {domain_code}: {result.get('error', '알 수 없는 오류')}")
    
    logger.info("=" * 80)
    
    return success_count == total_count


def verify_codebook_residency():
    """
    코드북 상주 상태 검증
    
    Returns:
        검증 결과 딕셔너리
    """
    logger.info("\n" + "=" * 80)
    logger.info("🔍 코드북 상주 상태 검증")
    logger.info("=" * 80)
    
    codebook_dir = WORKSPACE_ROOT / "data" / "mkm_domain_codebooks"
    all_domains = [Domain.SPIRIT, Domain.LOGIC, Domain.KNOWLEDGE, Domain.MATERIAL, Domain.TRADING, Domain.CODING]
    
    verification_results = {}
    
    for domain in all_domains:
        filepath = codebook_dir / f"{domain.value}.bin"
        
        if filepath.exists():
            file_size = filepath.stat().st_size
            logger.info(f"✅ {domain.name} ({domain.value}): {filepath.name} ({file_size:,} bytes)")
            verification_results[domain.value] = {
                "exists": True,
                "filepath": str(filepath),
                "size": file_size
            }
        else:
            logger.warning(f"⚠️ {domain.name} ({domain.value}): 코드북 파일 없음")
            verification_results[domain.value] = {
                "exists": False,
                "filepath": str(filepath)
            }
    
    # 라우터에서 코드북 로드 테스트
    try:
        router = MKMDomainCodebookRouter(
            embedding_model="all-MiniLM-L6-v2",
            codebook_size_per_domain=10000
        )
        
        loaded_count = 0
        for domain in all_domains:
            filepath = codebook_dir / f"{domain.value}.bin"
            if filepath.exists():
                if router.load_domain_codebook(domain, filepath, load_text_mapping=False):
                    metadata_size = len(router.domain_metadata.get(domain, []))
                    logger.info(f"✅ {domain.name} 코드북 로드 성공: {metadata_size}개 항목")
                    loaded_count += 1
                else:
                    logger.warning(f"⚠️ {domain.name} 코드북 로드 실패")
        
        logger.info(f"\n📊 코드북 로드 결과: {loaded_count}/{len(all_domains)}개 도메인")
        verification_results["load_test"] = {
            "loaded_count": loaded_count,
            "total_count": len(all_domains),
            "success_rate": loaded_count / len(all_domains) * 100
        }
        
    except Exception as e:
        logger.error(f"❌ 코드북 로드 테스트 실패: {e}")
        verification_results["load_test"] = {"error": str(e)}
    
    logger.info("=" * 80)
    
    return verification_results


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Step 2: 도메인 코드북 (DNA) 상주 시스템 구축")
    parser.add_argument("--force-rebuild", action="store_true", help="기존 코드북 강제 재구축")
    parser.add_argument("--verify-only", action="store_true", help="코드북 상주 상태만 검증")
    
    args = parser.parse_args()
    
    if args.verify_only:
        # 검증만 수행
        verify_codebook_residency()
    else:
        # 코드북 구축
        success = build_all_domain_codebooks(force_rebuild=args.force_rebuild)
        
        if success:
            logger.info("\n✅ 모든 도메인 코드북 구축 완료")
            # 검증 수행
            verify_codebook_residency()
        else:
            logger.error("\n❌ 일부 도메인 코드북 구축 실패")
            return 1
    
    return 0


if __name__ == "__main__":
    exit(main())



















