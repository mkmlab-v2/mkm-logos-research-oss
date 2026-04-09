# Track A Repositioning Memo v1 (Fact-Safe)

## 1) Executive Decision

Track A의 1차 가치 제안을 "LLM API 토큰 요금 절감 엔진"에서 "무결성 라우팅 + 도메인 격리 + fallback 안전장치" 중심으로 재정의한다.  
본압축(backend compression)은 파이썬 매칭 엔진 단독이 아니라 **Zstd native dictionary 경로**를 우선 채택한다.  
Genesis 멀티맵 스캐폴드는 압축 백엔드 대체가 아니라, 라우팅/정합성 검증 레인으로 역할을 명확히 분리한다.

## 2) Why This Pivot (Measured Evidence)

근거 아티팩트: `docs/final/artifacts/tracka_vs_zstd_native_bench_latest.json`

- 입력: `benchmark_tracka_10mb_input.txt` (약 10MB, 합성 반복 데이터)
- 비교 결과(동일 입력):
  - `tracka_multimap_plus_zstd3`: ratio `0.00043258`, multimap encode `2120.025 ms`
  - `zstd_native_level3_no_dict`: ratio `0.00023317`, `0.988 ms`
  - `zstd_native_level3_with_trained_dict`: ratio `0.00016155`, dict train `9.282 ms`, compress `1.273 ms`

해석: 본 벤치에서는 Zstd native(dictionary training 포함)가 압축률·속도 모두 우위다.  
따라서 Track A의 핵심 차별점을 "압축 알고리즘 자체"가 아닌 "도메인 분리/라우팅/무결성 통제"로 두는 것이 합리적이다.

## 3) What Track A Keeps (Core Moat)

- **Domain isolation:** 코퍼스(맵) 분리 운영으로 이종 데이터 오염 방지
- **Auto-map governance:** threshold 기반 `map_selected` / `fallback_verbatim_only`
- **Lossless integrity:** `decode_check_ok` 중심의 무손실 검증 체계
- **Operational artifacts:** summary/probe/route/bench JSON로 재현 가능한 감사 추적

## 4) What Track A Drops (Claim Discipline)

- "우리 파이썬 멀티맵 압축기가 범용 압축기 대비 항상 우월" 주장을 중단한다.
- 시뮬레이션 수치를 API billing, wire-byte, VRAM 절감으로 자동 환산하는 문구를 금지한다.
- 단일 샘플 최고 수치를 제품 일반 성능으로 표현하지 않는다.

## 5) Updated Product Posture

Track A를 다음 2-레이어로 정의한다.

1. **Control Plane (our moat):**
   - 도메인 맵 등록, 라우팅, 정책(임계치/격벽), fallback 제어, 감사 로그
2. **Compression Plane (replaceable backend):**
   - 우선순위: Zstd native dictionary
   - 필요 시 backend 교체 가능(고정 벤더 종속 회피)

## 6) Immediate Next Actions (72h)

1. 도메인별 실데이터 3세트(IT/Finance/API)로 동일 벤치 재실행
2. `run_genesis_v3_auto_map_chain.py`에 Zstd native dictionary 경로 옵션 추가
3. `comparison_summary_latest.json`에 backend 비교 섹션 추가
4. 대외 문구를 `prophecy_external_claim_onepager_safe_v1.txt` 규칙에 맞게 일괄 교정

## 7) Fact-Safe Boundary

본 메모의 수치는 지정 아티팩트·지정 입력에 한정된 관측값이다.  
상용 계약, 과금 절감, 인프라 절감 주장에는 별도 고객 데이터 실측과 계약 범위 정의가 필요하다.
