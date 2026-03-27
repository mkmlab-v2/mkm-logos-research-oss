# SSH Cursor Prompt: run_id latest 자동 분리 마감 (Fact-Locked)

## 문서 메타

- 날짜: 2026-03-27
- 작성 목적: attribution 리포트의 run 혼합 오염 방지 및 운영 코어 상태 검증
- 기준 SSOT:
  - `docs/final/FACT_LOCK_BRIEF_2026-03-27.md`
  - `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`

---

## Executive One-Liner

- `--run-id latest` 기반 단일 run 집계를 표준화하고, 코어 외 모듈 비활성 상태를 함께 검증한다.

---

## [FACT] 확인된 실행 요구사항

- attribution 요약 스크립트는 `--run-id latest`를 지원해야 한다.
- 출력 파일명은 `run_id`를 포함해 run 간 합산 오염을 방지해야 한다.
- 운영 코어는 `Basic/BCL/PMI`를 기본 활성 대상으로 확인하고, `Quaternion/JEMA-12/TimeXer`는 기본 OFF를 유지해야 한다.
- 보고 시 수정 파일/실행 명령/생성 파일 경로를 필수 첨부한다.
- 운영 승격 선언은 `3점 검증(코드 연결 + 재현 테스트 + 지표 개선/비열화)` 충족 전까지 금지한다.

---

## [HYPO] 검증 가설

- H1: `--run-id latest` 적용 시 복수 run 혼합 집계가 제거된다.
  - 검증: latest 요약의 decision 수 vs 해당 run raw JSONL 레코드 수 일치 여부 확인
  - 실패 기준: decision 수 불일치 또는 latest run 식별 실패
  - 성공 기준: decision 수 일치 및 리포트 1건 정상 생성

- H2: 운영 코어 외 모듈이 기본 실행에서 비활성 상태를 유지한다.
  - 검증: 실행 로그/컴포넌트 상태 리포트에서 모듈 상태 확인
  - 실패 기준: `Quaternion/JEMA-12/TimeXer` 중 1개 이상 active
  - 성공 기준: 대상 모듈 모두 inactive 또는 failed(비활성 운영 상태)

---

## [STRAT] 운영 전략

- 안정 운영 우선: 코어 3개(`Basic/BCL/PMI`)를 기준선으로 고정한다.
- 실험 통제: 코어 외 모듈 동시 ON 실험은 금지하고, 단독 A/B만 허용한다.
- 재현성 우선: 실행 커맨드와 산출 경로를 항상 함께 남긴다.
- 확정/비확정 분리: 실험 결과는 `[HYPO]`, 3점 검증 완료 건만 `[FACT]`로 승격한다.

---

## 최소 실행 순서 (3-Step)

1) 옵트인/옵트아웃 상태 고정
- 기본 모드에서 `Basic/BCL/PMI` 활성, `Quaternion/JEMA-12/TimeXer` 비활성 상태를 전제한다.

2) 고정 검증 실행
- 표준 모드 1회 실행 후 `--run-id latest` 요약 생성.
- latest run 기준 decision 수 일치 여부를 점검한다.

3) 증거 기반 판정
- 리포트 지표와 컴포넌트 상태를 기준으로 PASS/FAIL 판정.
- PASS 시 산출물 첨부, FAIL 시 원인(식별 실패/모듈 활성/수치 불일치) 기록.

---

## 실행 커맨드 (예시)

```powershell
# 1) 표준 모드 실행
python scripts/run_oos_backtest.py --mode standard

# 2) latest run 자동 감지 기반 요약
python scripts/summarize_decision_attribution.py --run-id latest

# 3) 컴포넌트 상태 리포트(경로는 환경에 맞게 조정)
python scripts/generate_component_status_report.py --log-file /tmp/oos_with_trace_standard.log
```

---

## 성공 조건 (PASS 기준)

- `--run-id latest` 실행 성공 및 리포트 1개 생성
- 리포트에 다음 지표 모두 포함:
  - total decisions
  - gate change ratio
  - BCL interventions (risk_down/neutral)
  - PMI interventions (risk_down)
- 컴포넌트 상태에서 `Basic/BCL/PMI` active 확인
- `Quaternion/JEMA-12/TimeXer`는 inactive/failed 확인
- 보고 첨부 3종:
  - 수정 파일 목록
  - 실행 커맨드
  - 생성 파일 경로

---

## 최신 원격 실행 포인터 (2026-03-27)

- repo: `mkmlab-v2/mkm-destiny-ai-41e38ec6`
- workflow: `Frontline Release Check`
- latest run id: `23646409745`
- conclusion: `success`
- URL: `https://github.com/mkmlab-v2/mkm-destiny-ai-41e38ec6/actions/runs/23646409745`

재확인:

```powershell
gh run view 23646409745 --repo mkmlab-v2/mkm-destiny-ai-41e38ec6 --json status,conclusion,workflowName,url
```
