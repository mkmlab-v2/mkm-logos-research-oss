# Map-Factory PoC v1 One-Pager (Fact-Safe)

## 1) Purpose

본 문서는 Genesis v3 기반 Map-Factory PoC의 의사결정용 기준서다.  
목표는 "범용 텍스트 압축"이 아니라, 반복 문구가 많은 B2B 도메인에서 무손실 복원과 비용 시뮬레이션 효율을 동시에 검증하는 것이다.  
모든 수치는 `premises` 기반 시뮬레이션이며 실제 과금/VRAM 절감을 자동 보증하지 않는다.

## 2) Current Verified State (as of 2026-04-08)

근거 아티팩트: `docs/final/artifacts/comparison_summary_latest.json`

- Integrity:
  - `integrity_guarantee_flag=true`
  - 포함 배치 기준 `decode_check_ok=true` 유지
- Theology cross-map (KJV/NIV/ESV):
  - 자기 맵 정합 시 `match_rate_by_utf8_octet` 약 `0.69~0.74`
  - 교차 맵은 `0.0`
- Multi-domain PoC (it/finance/api):
  - `aligned_eval_a_avg_match_rate_by_utf8_octet=0.6217916`
  - `negative_eval_b_all_zero_hit=true`
  - `kjv_cross_baseline_all_zero_hit=true`
- Auto-map:
  - 최근 probe 기준 `map_selected`와 `fallback_verbatim_only` 분기 확인
  - 0-hit 입력은 threshold 규칙으로 fallback 처리

## 3) Target KPI (PoC Gate)

KPI는 모두 아티팩트 재현 가능한 값으로만 선언한다.

- Core quality
  - `decode_check_ok=true` (배치 전 항목)
  - 0-hit 입력에서 `decision=fallback_verbatim_only`
- Matching effectiveness
  - 정합 eval(`eval_a`)에서 `match_rate_by_utf8_octet >= 0.55` (도메인별)
  - 비정합 eval(`eval_b`)에서 `match_rate_by_utf8_octet = 0.0` 유지
- Route stability
  - threshold sweep(`0.01/0.03/0.05/0.1`)에서 도메인 정합 입력 `map_selected` 유지
  - 비정합 입력(arXiv류) `fallback_verbatim_only` 유지

## 4) Out of Scope (Explicit Exclusions)

- 일반 뉴스/일상 대화/오픈 도메인 텍스트를 단일 맵으로 고효율 압축하는 주장
- 시뮬레이션 수치를 API billing, wire-byte, VRAM 절감으로 직접 환산하는 주장
- 단일 패스에서 다중 맵을 동시에 포인터 최적화하는 기능 (현 스캐폴드 미구현)

## 5) Data Sovereignty & Integrity

- Map 격리 원칙:
  - 도메인별 코퍼스는 분리 보관(예: `it_terms_v1.json`, `finance_terms_v1.json`, `api_policy_v1.json`)
- Unknown-safe 원칙:
  - 최고 매칭률이 threshold 미만이면 `best_map=null` + `fallback_verbatim_only`
- 무손실 원칙:
  - 비정합 구간은 억지 매칭하지 않고 verbatim 처리
  - 결과 해석은 배치 범위의 `decode_check_ok`로만 한정

## 6) B2B Onboarding Flow (Map-Factory v1)

1. Scope lock
   - 고객 도메인 문서 범위 확정(약관/API/정책 등)
2. Corpus build
   - 도메인 반복 문구를 isomorphic JSON 코퍼스로 변환
3. Split eval
   - train/eval 분리(`eval_a` partial-match, `eval_b` non-match)로 과적합 방지
4. Route registration
   - auto-map 후보군에 도메인 맵 등록, threshold 정책 적용
5. Acceptance
   - KPI 게이트 통과 시 도입, 미달 시 fallback-only 정책 유지

## 7) Immediate Mitigations / Next Actions

- Single-map limitation mitigation
  - 혼합 문서는 현재 단일맵으로 일부 구간만 포인터 이득, 나머지는 verbatim 처리
  - 차기 과제: multi-corpus pointer envelope 설계 검토
- Operational hardening
  - `run_genesis_v3_auto_map_chain.py`를 단일 진입점으로 사용
  - 실행 후 `comparison_summary_latest.json` 갱신을 기본 경로로 유지
- Claim discipline
  - 외부 문구는 `premises_global_note` 경계 문장을 반드시 동반

## 8) Fact-Safe Claim Template (External)

"본 결과는 지정된 입력·코퍼스·premises 조건의 시뮬레이션 관측값이며,  
배치 범위에서 무손실 복원(`decode_check_ok`)과 fallback 동작을 확인했다.  
실제 요금/VRAM 절감은 별도 계측·계약 조건에서 검증되어야 한다."
