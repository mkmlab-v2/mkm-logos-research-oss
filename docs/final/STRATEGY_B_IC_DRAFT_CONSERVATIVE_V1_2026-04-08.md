# 전략 B(내부 IC) 보수 운용 결재본 v1

## 0) 문서 성격

- 구분: 내부 투자위원회(IC) 전용, 대외 배포 금지
- 목적: Strategy B(내부 운용) 우선 레인을 팩트 기반으로 승인/통제
- 원칙: 비전 서술 금지, artifact 기반 현재 성능과 게이트만 사용

## 1) 현재 팩트 스냅샷

기준 artifact:
- `docs/final/artifacts/general_compression_ab_result_summary_v1.json`
- `docs/final/artifacts/general_compression_kpi_gate_v2.json`
- `docs/final/artifacts/general_compression_90pct_failure_taxonomy_v1.json`
- `docs/final/artifacts/general_compression_external_claims_whitelist_v1.json`

현재 수치:
- 절감률(treatment): `0.4012345679` (약 40.1%)
- 복원 정합성(Jaccard): `0.6710029493`
- 민감 무결성: `1.0` (해당 run 기준 violation 없음)
- KPI 게이트: `GO`
- 90% 고압축 준비도: `NO_GO`

## 2) IC 판단 명제(보수형)

- 승인 대상은 "완전 자율 운영"이 아니라 "하드락 기반 내부 운용 자동화"다.
- 성능 주장은 `40.1%` 및 `0.6710` 범위의 현재 검증값으로 제한한다.
- 문구 원칙: "무조건 보장" 대신 "검증 조건 기반 관측값"으로만 표현한다.
- 90% 고압축은 연구 항목으로만 유지하며 운영 레인에서 사용 금지한다.

## 3) 운용 가드레일

- 하드락 승인제:
  - 자금 집행, 리스크 한도 변경, 전략 파라미터 승격은 IC 또는 운영자 승인 후 적용
- 게이트 규칙:
  - `general_compression_kpi_gate`가 `NO_GO`로 하향되면 확대/승격 즉시 중단
  - 90% 프로파일은 `decision_90pct_ready=GO` 근거 확보 전 금지
- 레인 분리:
  - 연구(B-track) 결과의 본선 자동 합선 금지

## 4) 킬스위치 기준(운영 필수)

- 품질 킬스위치: 품질 지표가 내부 승인 하한 미달 상태로 연속 관측될 때
- 리스크 킬스위치: 손실/슬리피지/집행 오류가 IC 승인 한도 초과 시
- 인프라 킬스위치: 데이터 stale, 반복 실패, 모니터링 공백 발생 시

## 5) 주간 IC 리포트 항목

- 모델: saving/jaccard 드리프트(앵커: `0.4012`, `0.6710`), 게이트 상태
- 리스크: 손실 구간, 슬리피지 초과 건수, 킬스위치 이벤트
- 운영: 실패 건수, 복구 시간, 재현성 유지 여부

## 6) 금지 문구 및 금지 동작

- 금지 문구:
  - "완전 자율 운영 완료"
  - "항상 우월"
  - "100% 무손실 확정"
- 금지 동작:
  - 연구 결과 자동 승격
  - 승인 없는 본선 파라미터 변경
  - 90% 고압축 프로파일의 운영 반영

## 7) 근거 매핑

| ID | 항목 | 근거 경로 | 확인값 |
|---|---|---|---|
| B-1 | 절감률 40.1% | `docs/final/artifacts/general_compression_ab_result_summary_v1.json` | `global_token_saving_rate=0.4012345679` |
| B-2 | Jaccard 0.6710 | `docs/final/artifacts/general_compression_ab_result_summary_v1.json` | `avg_reconstruction_fidelity_jaccard=0.6710029493` |
| B-3 | KPI 게이트 GO | `docs/final/artifacts/general_compression_kpi_gate_v2.json` | `decision=GO` |
| B-4 | 90% 미준비 | `docs/final/artifacts/general_compression_90pct_failure_taxonomy_v1.json` | `decision_90pct_ready=NO_GO` |
| B-5 | 과장 금지 패턴 | `docs/final/artifacts/general_compression_external_claims_whitelist_v1.json` | `banned_patterns` |

## 8) 4대 메가 전선 로드맵 (내부 IC용, 조건부)

- 본 절은 비전 문구가 아니라 "조건부 사업 전개 순서"를 고정한다.
- 공통 원칙: 각 전선은 선행 게이트(품질, 보안, 재현성) 통과 전까지 "연구/PoC" 상태로 유지한다.

### 8.1 전선 정의

1. AI 인프라/GPU 메모리 승수(라이선스)
2. 에이전트 장기기억 코어(Long-term Memory Core)
3. 온디바이스/극저대역 통신(Edge/Extreme Comms)
4. 금융 실시간 문맥 압축 운용(Internal Quant)

### 8.2 구간별 해금 규칙 (운영 단정 금지)

- 40%+ (현재): 4번 전선의 내부 효율 개선/관측 운용만 허용
- 65%+: 3번 전선 PoC 착수 검토(온디바이스 벤치, 전력/지연/복원률)
- 85%+: 1번 전선 PoC 착수 검토(VRAM 절감 실측, 공급자 협의 자료)
- 90%+: 2번 전선 PoC 착수 검토(장기기억 코어), 단 `decision_90pct_ready=GO` 전에는 운영 금지

### 8.3 NotebookLM 논의 운영 프로토콜

- 목적: IC 논의 속도 향상(브리핑), 의사결정 근거는 artifact로 고정(팩트락)
- 입력 소스: `docs/NotebookLM_sources_manifest.md`의 A 궤적 우선, B 궤적은 가설 레이어로 분리
- 출력 규칙:
  - [FACT] 현재 수치/게이트
  - [HYPOTHESIS] 시장 확장 시나리오
  - [ACTION] 다음 검증 실험과 종료 조건
- 금지: NotebookLM 요약만으로 승인 결론 확정
