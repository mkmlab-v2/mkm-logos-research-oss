# 전략 A 제한형 API 최소노출 정책 v1 (대외용 확정본)

## 0) 목적 및 범위

- 목적: 대외/API 사업화 시 성능 주장을 과장 없이 통제하고, 엔진 IP 노출을 최소화한다.
- 범위: 모든 대외/파트너 대상 텍스트 압축 API 커뮤니케이션 및 운영 정책.
- 원칙: 본 문서의 수치/문구는 지정 artifact로 재현 가능한 항목만 사용한다.

## 1) 대외 허용 주장(allowed claims)

- "본 실험 조건에서 treatment가 baseline 대비 토큰 절감률과 복원 품질 게이트를 동시에 충족했습니다."
- "재현 가능한 결과: saving 0.2963 -> 0.4012, jaccard 0.5531 -> 0.6710."
- 설명형 보강 문구(허용): "고품질 텍스트 압축", "비용 효율 개선", "관측 레인 기준 결과"

근거:
- `docs/final/artifacts/general_compression_ab_result_summary_v1.json`
- `docs/final/artifacts/general_compression_kpi_gate_v2.json`
- `docs/final/artifacts/general_compression_external_claims_whitelist_v1.json`

## 2) 대외 금지 주장(banned claims)

- "항상 우수"
- "100% 무손실 확정"
- "XX% 개선 확정"
- "Zero-Hallucination 보장"
- "완전 자율 운영 사령관"
- "90% 고압축 상용 준비 완료"

근거:
- `docs/final/artifacts/general_compression_external_claims_whitelist_v1.json`
- `docs/final/artifacts/general_compression_90pct_failure_taxonomy_v1.json` (`decision_90pct_ready=NO_GO`)

## 3) 제품 포지셔닝(대외 문안 고정)

- 제품 정의: "본 실험 조건에서 비용 절감과 복원 품질 게이트를 동시 충족한 제한형 텍스트 압축 API"
- 의무 고지: "observation lane only", "실거래 아님", "외부 독립 재현 필요"
- 보장 문구 금지: "최소 XX% 무조건 보장" 형태 문구 사용 금지
- 금지: 자율 운영, 내부 전략 엔진, 투자판단 자동화와 연결되는 표현

## 4) 최소 노출 아키텍처 원칙

- 서버 단독 처리 원칙: 입력 -> 서버 처리 -> 결과 반환
- 클라이언트 측 복원 로직/중간표현 배포 금지
- 내부 산출물(좌표/상태/코드북 힌트) 외부 노출 금지

## 5) 운영 및 보안 게이트

- Gate 1: `general_compression_kpi_gate_v2.json`가 `GO`일 것
- Gate 2: 인증/권한/테넌트 격리/로그 최소화 정책 점검 통과
- Gate 3: 법무/컴플라이언스 문구 승인
- Gate 4: 키 유출/어뷰징 시나리오 대응 리허설 완료

## 6) 변경관리

- 대외 문구 변경 전 필수:
  - artifact 수치 갱신
  - whitelist 재검토
  - 정책 이력 업데이트
- 노출면 증가 변경은 보안 리뷰 승인 전 반영 금지

## 7) 근거 매핑

| ID | 주장/규칙 | 근거 경로 | 확인값 |
|---|---|---|---|
| A-1 | saving 0.2963 -> 0.4012 | `docs/final/artifacts/general_compression_ab_result_summary_v1.json` | baseline/treatment saving |
| A-2 | jaccard 0.5531 -> 0.6710 | `docs/final/artifacts/general_compression_ab_result_summary_v1.json` | baseline/treatment jaccard |
| A-3 | 현재 KPI 게이트 GO | `docs/final/artifacts/general_compression_kpi_gate_v2.json` | `decision=GO` |
| A-4 | banned claims 집합 | `docs/final/artifacts/general_compression_external_claims_whitelist_v1.json` | `banned_patterns` |
| A-5 | 90% 고압축 미준비 | `docs/final/artifacts/general_compression_90pct_failure_taxonomy_v1.json` | `decision_90pct_ready=NO_GO` |

## 8) 단계형 시장 커뮤니케이션 가이드 (대외)

- 본 절은 "시장 확장 비전"을 말할 때 과장·오해를 막기 위한 문안 가이드다.
- 원칙: 현재 구간은 "관측 기반 API/운영 효율"만 확정 문구로 사용하고, 상위 구간은 조건부 가능성으로만 서술한다.

### 8.1 구간별 허용 표현

- 40%+ (현재): "비용 효율 개선형 텍스트 압축 API", "관측 레인 기준 검증값"
- 65%+ (조건부): "온디바이스 적용 가능성 탐색", "추가 검증 필요"
- 85%+ (조건부): "인프라 절감 잠재력 검토", "벤치 확장 예정"
- 90%+ (조건부): "장기 연구 가설", "상용 준비 단정 금지"

### 8.2 대외 금지 표현(추가)

- "새로운 물리 법칙 발견"
- "VRAM 10배 확정 보장"
- "AGI 무한 기억 상용 완료"
- "국방/우주 통신 즉시 적용 가능"

### 8.3 NotebookLM 브리핑 연동 규칙 (대외용)

- NotebookLM 요약은 "브리핑 초안"으로만 사용하고, 최종 대외 문구는 artifact 재검증 후 확정한다.
- 브리핑 본문에는 반드시 "observation lane only", "independent replication required"를 포함한다.
- 내부 고유 이론명/매핑명은 대외본에서 일반 용어로 치환한다.
