#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""코드북 구축 (진행 상황 출력)"""

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
print("📖 S 도메인 코드북 구축 (진행 상황 출력)")
print("=" * 80)
print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

try:
    router = MKMDomainCodebookRouter()
    
    print("🔄 코드북 구축 시작...")
    start_time = datetime.now()
    
    router.build_domain_codebook(Domain.SPIRIT)
    
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    
    print()
    print("=" * 80)
    print(f"✅ 코드북 구축 완료!")
    print(f"   - 소요 시간: {elapsed:.1f}초")
    print(f"   - 구절 수: {len(router.domain_metadata[Domain.SPIRIT])}개")
    print(f"   - 코드북 크기: {len(router.domain_codebooks.get(Domain.SPIRIT, []))}개")
    print("=" * 80)
    
except KeyboardInterrupt:
    print("\n⚠️ 사용자에 의해 중단됨")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

