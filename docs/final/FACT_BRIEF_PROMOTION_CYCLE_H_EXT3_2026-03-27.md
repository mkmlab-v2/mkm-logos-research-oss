# FACT Brief - Promotion Cycle H_ext3

## 문서 메타

- 날짜: 2026-03-27
- 작성자: Cursor Local Engineer
- 대상 범위: DSS/Apocrypha insight -> candidate rule promotion readiness
- 기준 SSOT:
  - `reports/constitution/command_center_fusion_progress_20260327.md`
  - `reports/constitution/candidate_rules_export_command_center_followup_20260327_h_ext3.json`
  - `reports/constitution/candidate_rules_delta_h_vs_h_ext3_20260327.json`

---

## Executive One-Liner

- 결론 한 줄: H_ext3에서 권위 준비도 READY를 달성했고, 승격 후보 3개는 `full_eval`/`embedding_batch` 양 경로에서 게이트 회귀 없이 안정적으로 검증되었다.

---

## [FACT] 확인된 사실

- [x] Hebrew-priority manifest 실행 후 blocker 지표가 회복되었다.
  - 근거: `projects/dss-4d-ingest/outputs/apocrypha_quality_report_pilot_manifest_ext3_hebrew_priority.json`
  - 수치: `hebrew_primary_tokens=1024`, `translation_proxy_ratio=0.718759`
- [x] 권위 준비도가 `BLOCKED`에서 `READY`로 전환되었다.
  - 근거: `projects/dss-4d-ingest/outputs/authority_readiness_command_center_followup_20260327_h_ext3.json`
- [x] 후보 규칙 3개의 승격 상태가 `PILOT -> CANDIDATE_FOR_PROMOTION`으로 변경되었다.
  - 근거: `reports/constitution/candidate_rules_delta_h_vs_h_ext3_20260327.json`
- [x] 승격 이후 `full_eval`과 `embedding_batch` 모두 `gate=GO`를 유지했다.
  - 근거:
    - `reports/constitution/command_center_fusion_progress_20260327.md`
    - `reports/constitution/promoted_candidates_ab_verification_20260327.md`

> 규칙: 재현 가능한 코드/로그/문서 근거가 없는 내용은 FACT에 넣지 않는다.

---

## [HYPO] 검증 가설

- [x] 가설 H1: Hebrew-priority 입력 확대로 권위 준비도 임계값을 통과할 수 있다.
  - 검증 방법: ext3 manifest 실행 후 quality/authority JSON 비교
  - 실패 기준: `hebrew_primary_tokens < 500` 또는 `translation_proxy_ratio > 0.8`
  - 성공 기준: authority readiness `READY`
- [x] 가설 H2: 승격 후보 적용 후에도 intake 게이트가 비열화로 유지된다.
  - 검증 방법: `full_eval` + `embedding_batch` 연속 실행
  - 실패 기준: `gate != GO` 또는 `health != HEALTHY`
  - 성공 기준: 양 경로 모두 `intake_cycle=OK`, `gate=GO`

> 규칙: HYPO는 반드시 측정 가능한 검증 계획을 동반한다.

---

## [STRAT] 전략 및 의사결정

- [x] 전략 S1: blocker 해소 전까지는 후보를 `PILOT`로 유지한다.
- [x] 전략 S2: blocker 해소 즉시 `CANDIDATE_FOR_PROMOTION`으로 전환하되, dual-path 검증을 필수로 수행한다.
- [x] 전략 S3: 승격 판정은 항상 원격 CI 성공 run id와 함께 고정한다.

> 규칙: STRAT은 방향 제시이며, 구현 완료 선언 문구를 포함하지 않는다.

---

## 최소 실행 순서 (3-Step)

1. `pilot_manifest_ext3_hebrew_priority.json` 실행 및 quality 리포트 생성
2. `authority_readiness` 재평가 및 candidate export/delta 산출
3. `full_eval` + `embedding_batch` 검증 후 원격 CI success 고정

---

## 승격 판정 체크리스트

- [x] 코드 import/호출 경로 연결 확인
- [x] 테스트 재현 통과 확인
- [x] 리포트 지표 개선 또는 비열화 확인
- [x] SSOT 갱신 완료

---

## 첨부 아티팩트

- 코드 변경 파일:
  - `reports/constitution/command_center_fusion_progress_20260327.md`
  - `reports/constitution/promoted_candidates_ab_verification_20260327.md`
  - `docs/final/SSH_RUNID_LATEST_PROMPT_2026-03-27.md`
- 테스트 명령:
  - `python scripts/run_fusion_intake_cycle.py --workload full_eval --skip-sync`
  - `python scripts/run_fusion_intake_cycle.py --workload embedding_batch --skip-sync`
- 리포트 경로:
  - `reports/constitution/candidate_rules_export_command_center_followup_20260327_h_ext3.json`
  - `reports/constitution/candidate_rules_delta_h_vs_h_ext3_20260327.json`
  - `reports/constitution/promoted_candidates_ab_verification_20260327.md`
- 비교표/요약표:
  - `reports/constitution/candidate_rules_delta_h_vs_h_ext3_20260327.md`
