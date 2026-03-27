# no1kmedi 복구/고도화 작업리스트 (2026-03-27, Fact-Locked)

## 문서 메타

- 날짜: 2026-03-27
- 목적: no1kmedi 복구/고도화 작업의 완료 근거를 팩트 기반으로 고정하고 운영 승격 리스크를 통제
- 기준 문서:
  - `docs/final/FACT_LOCK_BRIEF_2026-03-27.md`
  - `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`

---

## Executive One-Liner

- 본 문서는 no1kmedi의 복구/고도화 작업을 "문서-코드 정합 + 모델 이중화 + 데이터 성숙화 + 계약 테스트" 축으로 완료 추적하고, 승격은 검증 증거가 있을 때만 허용한다.

---

## [FACT] 고정 전제

- 현재 작업은 운영 경로를 유지한 채 신뢰성/가시성/데이터 품질을 단계적으로 강화하는 목적이다.
- `MODEL_PROVIDER` 기반 라우팅과 Vertex→Local fallback은 운영 안정성 핵심 경로다.
- Guardian API는 파싱 실패 대비 안전 fallback이 필요하다.
- 데이터 확장 결과는 생성량뿐 아니라 분포/중복/품질 검증 결과로 함께 판정해야 한다.

## [HYPO] 실험 가설

- provider 이중화와 fallback 적용으로 장애 상황에서도 핵심 API 가용성을 유지할 수 있다.
- 멀티도메인 균형 데이터와 자동 품질 검증을 결합하면 학습 데이터 신뢰도를 높일 수 있다.

## [STRAT] 운영 전략

- 기능 추가보다 운영 안정성 경로(라우팅/fallback/계약 테스트)를 우선 고정한다.
- 데이터 증량은 단계별(Phase A/B/C)로 진행하고 매 단계 검증 리포트를 남긴다.
- 완료 표시는 코드/워크플로우/리포트 3점 증거가 있을 때만 확정한다.

---

## 판정 규칙 (강제)

- Go: 문서-코드 정합, provider 전환, fallback 동작, 계약 테스트, 데이터 품질 검증을 모두 충족
- No-Go/Hold: 핵심 API 복구 미확인, 검증 리포트 누락, 데이터 품질 실패 시 보류
- 모든 결론 문구는 [FACT]/[HYPO]/[STRAT] 중 하나로 라벨링한다.

---

## 상세 실행 로그

기준: 현재 구현 상태를 유지하면서 운영 신뢰성, 문서 정합성, 모델 이중화, 데이터 성숙도를 순차 개선한다.

## 실행 순서

- [x] 1) 현황 재점검: 코드/문서/CI 실제 상태 재확인
- [x] 2) 문서-코드 정합화: "완전 온디바이스" 표현을 "현재/목표"로 분리
- [x] 3) 모델 라우팅 도입: `MODEL_PROVIDER=vertex|local|hybrid` 추가
- [x] 4) Guardian API fallback: Vertex 실패 시 Local 자동 전환
- [x] 5) 응답 강건성: JSON 파싱 실패 시 안전 fallback 응답
- [x] 6) 운영 가시성: provider/route 기준 에러 로그 표준화
- [x] 7) 데이터 성숙화: codebook training records 확장 계획 수립
- [x] 8) CI 확대: guardian 핵심 API 계약 테스트 추가
- [x] 9) Phase A 데이터 증량: training records 200건 생성/검증/export
- [x] 10) Phase B 데이터 증량: training records 1000건 생성/검증/export + 분포 리포트
- [x] 11) 도메인 불균형 해소: 4도메인 균등 1000건 생성 + KPI 충족 확인
- [x] 12) Phase C 확장: 멀티도메인 5000건 생성/검증/export
- [x] 13) 중복/품질 자동검증: 해시 중복 검사 + 품질 리포트 자동화
- [x] 14) 학습연결 스모크 러너: E2E 파이프라인 단일 실행 스크립트 추가
- [x] 15) CI 스모크 게이트: PR에서 학습 파이프라인 스모크 자동 실행
- [x] 16) 비합성 검증셋: 실문장 24건 추가 및 코드북 정합 검사 자동화
- [x] 17) 스모크 강화: E2E 실행에 real-sample validation 단계 통합

## 완료 기준 (DoD)

- 문서와 실제 실행 경로가 모순되지 않는다.
- `MODEL_PROVIDER` 설정만으로 provider 전환이 가능하다.
- Vertex 장애 시 Local fallback이 동작한다.
- 최소 1개 guardian API에서 파싱 실패 복구가 확인된다.
- 다음 단계용 데이터 확장/테스트 TODO가 문서화되어 있다.

## 진행 로그

- 2026-03-27: 1) 현황 재점검 완료 (코드북 검증 통과, training export 1건 확인)
- 2026-03-27: 2)~5) 반영 완료 (`ai-provider` 라우터 추가, guardian/partner chat API fallback 적용)
- 2026-03-27: 6) 반영 완료 (API 응답 `meta/provider_meta`에 provider/fallback 상태 포함)
- 2026-03-27: 7) 반영 완료 (`NO1KMEDI_TRAINING_DATA_EXPANSION_PLAN_2026-03-27.md` 생성)
- 2026-03-27: 8) 반영 완료 (`scripts/validate_no1kmedi_guardian_contracts.py`, `.github/workflows/no1kmedi-guardian-contract-gate.yml` 추가)
- 2026-03-27: 9) 반영 완료 (`scripts/generate_phaseA_training_codebook.py`로 200건 생성, schema 검증 통과, `master_codebook_training_phaseA_200.jsonl` export)
- 2026-03-27: 10) 반영 완료 (`master_codebook_dual_track.phaseB_1000.json`, `master_codebook_training_phaseB_1000.jsonl`, 분포 리포트 생성)
- 2026-03-27: 11) 반영 완료 (`scripts/generate_multidomain_training_codebook.py`, 멀티도메인 1000건/분포 25% 균등 확인)
- 2026-03-27: 12) 반영 완료 (`master_codebook_dual_track.multidomain_5000.json`, `master_codebook_training_multidomain_5000.jsonl` 생성)
- 2026-03-27: 13) 반영 완료 (`scripts/validate_training_jsonl_quality.py`, 품질 리포트 pass=True / duplicate=0 확인)
- 2026-03-27: 14) 반영 완료 (`scripts/run_master_codebook_training_smoke.py`, local smoke 500 실행 통과)
- 2026-03-27: 15) 반영 완료 (`.github/workflows/master-codebook-training-smoke-gate.yml` 추가)
- 2026-03-27: 16) 반영 완료 (`data/constitution/master_codebook_real_validation_samples.jsonl`, `scripts/validate_master_codebook_real_samples.py` 추가)
- 2026-03-27: 17) 반영 완료 (smoke runner/CI에 real-sample validation 통합, local_smoke_real_500 통과)

---

## 병렬 전선 운영 추가안 (2026-03-27, this chat)

### 목적

- 본 채팅창을 한의학/의학/금융 보조 전선으로 고정하고, DSS/외경 + 원어/문화 주력 전선과 충돌 없이 병렬 운용한다.

### 전선 분리 규칙

- 주력 전선(별도 창): DSS 복원, 외경, 원어/문화/문헌비평 관련 변경만 수행.
- 보조 전선(본 창): no1kmedi 및 의학/금융 관련 리서치/검증/게이트 안정화 작업만 수행.
- 교차 반영은 "증거 아티팩트(리포트/테스트 로그/변경 파일 목록)"가 있을 때만 수행.
- 동일 파일 동시 수정 금지(LOCK/UNLOCK 규칙 적용).

### 이번 창 즉시 실행 체크리스트

- [x] M1) 의학/한의학/금융 공통 KPI 3개 확정(안정성, 재현성, 품질지표).
- [x] M2) no1kmedi 관련 다음 우선 과제 1건 선정 후 단일 PR 범위로 고정.
- [x] M3) 주력 전선과 교차 가능한 용어 사전(원어/문화 ↔ 의학/금융) 초안 작성.
- [x] M4) 본 창 변경 파일 목록/검증 명령/리스크 Top3를 주기적으로 기록.

### Merge Gate 추가 조건

- [x] G1) 보조 전선 변경이 DSS 주력 경로 파일을 건드리지 않았음을 `git diff --name-only`로 확인.
- [x] G2) 보조 전선 테스트/스모크를 재현 가능한 단일 명령으로 제시.
- [x] G3) [FACT]/[HYPO]/[STRAT] 라벨 규칙 유지 확인.

### 병렬 전선 로그

- 2026-03-27: 보조 전선 계획 문서 생성 (`docs/final/MED_FIN_HAN_PARALLEL_FRONTLINE_PLAN_2026-03-27.md`)
- 2026-03-27: M1/M2 완료 처리 (KPI 확정 + 단일 우선 과제 `MFH-P1` 고정)
- 2026-03-27: 재현 검증 명령 실행 완료
  - `python scripts/validate_no1kmedi_guardian_contracts.py`
  - `python scripts/run_master_codebook_training_smoke.py --count 50 --prefix mfh_smoke`
  - 결과: contract pass / smoke pass / real sample matched 24/24
- 2026-03-27: 교차 용어 사전 초안 생성 (`docs/final/ORIGINAL_LANGUAGE_MED_FIN_GLOSSARY_DRAFT_2026-03-27.md`)
- 2026-03-27: Cycle 3 주기 기록 반영
  - changed files:
    - `docs/final/NO1KMEDI_RECOVERY_TASKLIST_2026-03-27.md`
    - `docs/final/MED_FIN_HAN_PARALLEL_FRONTLINE_PLAN_2026-03-27.md`
    - `docs/final/ORIGINAL_LANGUAGE_MED_FIN_GLOSSARY_DRAFT_2026-03-27.md`
  - verification commands:
    - `python scripts/validate_no1kmedi_guardian_contracts.py`
    - `python scripts/run_master_codebook_training_smoke.py --count 50 --prefix mfh_smoke`
  - risks top3: 대규모 변경셋 중첩/용어사전 동기화 지연/원격 CI 괴리
- 2026-03-27: Cycle 4 원격 증거 수집 단계 HOLD
  - `git remote -v` 결과 remote 미설정
  - 조치: remote 연결된 메인 워크스페이스에서 workflow dispatch 수행 필요
- 2026-03-27: Cycle 5 핸드오프 패키지 생성
  - `docs/final/MFH_REMOTE_CI_HANDOFF_2026-03-27.md`
  - 포함: guardian/smoke gate 원격 dispatch 명령 + PASS 기준 + GO/HOLD 보고 템플릿
- 2026-03-27: Cycle 6 결과 수집 템플릿 생성
  - `docs/final/MFH_REMOTE_CI_CYCLE6_RESULTS_2026-03-27.md`
  - 포함: run_id/url/conclusion 기록 슬롯 + GO/HOLD 판정 + 실패 요약 템플릿
- 2026-03-27: Cycle 6 원격 실행 결과 수집 완료 (HOLD)
  - guardian run: `23647646169` (failure)
  - smoke run: `23647647632` (failure)
  - 공통 실패 원인: 원격 default branch에서 `scripts/*.py` 대상 파일 미존재 (`can't open file`)
