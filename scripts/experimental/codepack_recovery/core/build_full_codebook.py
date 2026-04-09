#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전체 성경 데이터로 코드북 재구축"""

import sys
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from tools.core.mkm_domain_codebook_router import MKMDomainCodebookRouter, Domain

print("=" * 80)
print("📖 S 도메인 코드북 전체 재구축 (31,103개 구절)")
print("=" * 80)
print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

try:
    router = MKMDomainCodebookRouter()
    
    # 데이터 로드 확인
    print("🔄 데이터 로드 확인 중...")
    texts_data = router.load_domain_data(Domain.SPIRIT)
    print(f"✅ 데이터 로드 완료: {len(texts_data)}개 구절")
    
    if len(texts_data) < 30000:
        print(f"⚠️ 경고: 예상보다 적은 데이터입니다 (목표: 31,103개, 현재: {len(texts_data)}개)")
        # 자동 진행 (사용자 입력 없이)
        print("자동으로 진행합니다...")
    
    print()
    print("🔄 코드북 재구축 시작 (force_rebuild=True)...")
    print("   ⚠️ 기존 코드북을 덮어씁니다!")
    print()
    
    start_time = datetime.now()
    
    # 전체 데이터로 코드북 재구축
    result = router.build_domain_codebook(Domain.SPIRIT, force_rebuild=True)
    
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    
    print()
    print("=" * 80)
    print(f"✅ 코드북 재구축 완료!")
    print(f"   - 소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    print(f"   - 코드북 크기: {result.get('size', 0)}개")
    print(f"   - 메타데이터 개수: {len(router.domain_metadata.get(Domain.SPIRIT, []))}개")
    print(f"   - 캐시 사용: {result.get('from_cache', False)}")
    print("=" * 80)
    
except KeyboardInterrupt:
    print("\n⚠️ 사용자에 의해 중단됨")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

