# P1 압축 API 파일럿 전환 체크리스트 v1

**역할:** `Track C` 축 A(압축·토큰 절감 API) **파일럿 전환** 직전·직후에 감사·재현 가능한 **경로·exit code·JSON**만 고정한다. 기획·브리핑 단독 주장은 금지한다.  
**상위 SSOT:** `docs/final/P0_COMMERCIALIZATION_TRACKER.md` (L1/L2·Track A 체인), `docs/final/MKM_PROMOTION_GATE_CHECKLIST_B_TO_A_C_V1.md` (G0~G12), `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` (`§3.7`, `§9` External Messaging, **`§11` 세일즈 킷**), `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`.

**Frozen pointer:** 2026-05-02 초안 — 개정 시 본문 상단에 `Revised:` 한 줄과 근거를 남긴다.

---

## 0) 승격·합선 방지 (필수)

| 항목 | 요구 |
|------|------|
| **B → A/C 승격 증빙** | `docs/final/MKM_PROMOTION_GATE_CHECKLIST_B_TO_A_C_V1.md`의 **G0~G12** 각 항목에 대해 호출 가능 스크립트·워크플로·증거 아티팩트로 통과를 입증한다. |
| **Bleed-over 금지** | 연구(B-track)·비결정론 벤치 산출을 파일럿 라우팅·과금·대외 SLA와 **무분별 합선하지 않는다**. |

---

## 1) 대외·세일즈 동결 전제 (DoD) — `TRACK_C` §11

파일럿 GO 전 **세일즈 킷 기준 경로**가 레포에 존재하고, 랜딩·API 카피가 **동결 버전**으로 식별 가능해야 한다.

| 구분 | 경로 (SSOT) |
|------|-------------|
| 세일즈킷 루트 | `docs/final/artifacts/mkm_ai_sales_kit_v1/` |
| 랜딩 카피 (a-codeai.com 등 연동 원칙과 정합) | `docs/final/artifacts/mkm_ai_sales_kit_v1/MKM_AI_LANDING_COPY_V1.md` |
| API 브랜딩 브리지 (계약 비파괴) | `docs/final/artifacts/mkm_ai_sales_kit_v1/MKM_AI_API_BRANDING_BRIDGE_V1.md` |
| 숫자·문구 가드 | `docs/final/artifacts/mkm_ai_sales_kit_v1/MKM_AI_FACTSAFE_NUMBERS_V1.md` |
| 세일즈킷 구조 레지스트리 | `docs/final/artifacts/mkm_ai_sales_kit_v1/MKM_AI_SALES_KIT_STRUCTURE_V1.json` |

**상태 (2026-05-02):** §11 나열 파일이 `docs/final/artifacts/mkm_ai_sales_kit_v1/` 에 반영됨. 카피·수치는 **동결 버전** 식별(커밋·`MKM_AI_SALES_KIT_STRUCTURE_V1.json`의 `frozen_pointer_utc`) 후 파일럿 보고에 인용한다. 존재 여부만으로 “성능·SLA 완료”를 단정하지 않는다.

**법무·대외 문구:** `TRACK_C` §1 Fact-Locked Baseline, §9 External Messaging — 투자조언·수익 보장·무손실 단정 금지.

---

## 2) 파일럿 핵심 목표 · 증거 매핑

### 2.1 토큰 이코노미 (절감률·비용 시뮬)

| 목표 | 실행·산출 (예시) | 비고 |
|------|------------------|------|
| 압축 KPI·글로벌 절감률 | `scripts/run_compression_automation_chain.ps1` → `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` (`global_token_saving_rate` 등) | `P0` 압축 자동화 체인 |
| Track A 대화 비용 시뮬 (벤치) | `general_compression_kpi_gate_v2.json` **GO** + 위 리포트의 `global_token_saving_rate` → `py scripts/run_track_a_conversational_cost_simulation.py` → `docs/final/artifacts/track_a_conversational_cost_simulation_latest.json` | 실 청구서 아님 |
| 섀도우 코퍼스 | `py scripts/run_track_a_shadow_corpus_eval.py` → `docs/final/artifacts/track_a_shadow_corpus_eval_latest.json` | 고객별 패턴은 JSONL 주입 시 개인정보·동의 범위 준수 |
| 미터링 로그 | `POST /v1/metering/log` → `reports/constitution/btrack_pilot/track_a_metering_log_v1.jsonl` (환경변수 `TRACK_A_METERING_LOG_PATH` 등) | `P0` L2 |

### 2.2 지연 시간 안정화 (P95)

| 목표 | 실행·산출 | 비고 |
|------|-----------|------|
| L1 RTT 벤치 (드래프트) | `py scripts/bench_l1_api_load.py` → `docs/final/artifacts/bench_l1_api_load_latest.json` (로컬) | `research_only` / draft; SLA 최종은 별 게이트 |
| VPS 동일 절차 | `docs/final/BENCH_L1_API_LOAD_VPS_RUNBOOK.md`, 산출 `docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json` 등 | 로컬 `bench_l1_api_load_summary_latest.json`과 혼동 금지 (`P0` 증거 표) |

### 2.3 복원 품질 (`reconstruction_fidelity_jaccard`)

| 목표 | 실행·산출 | 비고 |
|------|-----------|------|
| 집계 경로 | `scripts/report_multilens_performance_eval.py` — 케이스별·평균 `avg_reconstruction_fidelity_jaccard` 등 (`CONSTITUTION` Multilens eval 행) | 감사 로그는 **결정론적 재실행 로그 + JSON 필드**로 남긴다 |
| API 스텁 계약 | `scripts/compression_token_api_stub.py` + `docs/final/openapi_token_compression_stub_v1.yaml` | 회귀: `py -m pytest tests/test_compression_token_api_stub.py` |

---

## 3) 운영 연계 (Chain of Custody)

| 단계 | 경로·조건 |
|------|-----------|
| **멀티렌즈 P1 프로파일 (본선 갱신)** | `AGENTS.md`에 명시: `py scripts/run_multilens_p1_production_chain.py` 또는 `scripts/Run-MultilensP1ProductionChain.ps1`; `--dry-run` / `--json-plan`으로 계획만 확인 가능. 산출 예: `docs/final/artifacts/MULTILENS_P1_AB_*_V1.json`, `MULTILENS_P1_AB_FINAL_SELECTION_V1.json` (`CONSTITUTION` 표). **레포에 스크립트가 없으면** 경로 존재를 `verify_p0_constitution_gate_paths.ps1` 등으로 확인하고, 미배치 구간으로 보고한다. |
| **압축 토큰 API 스텁** | `scripts/compression_token_api_stub.py` — `GET /health`, `POST /v1/compress`, `POST /v1/expand`, 미터링 연계는 `P0` L2. |
| **OpenAPI 회귀** | `tests/test_compression_token_api_stub.py` 통과 (G7과 정합). |
| **미터링·알람** | 압축 KPI 알람: `docs/final/artifacts/compression_alarm_thresholds_v1.json`; 웹훅 `COMPRESSION_KPI_ALARM_WEBHOOK_URL` 또는 폴백 `OPS_ALARM_WEBHOOK_URL` (`P0`, `CONSTITUTION`). 체인 말미: `scripts/send_compression_kpi_alarm_if_needed.ps1` (`run_compression_automation_chain.ps1` 연계 시). |
| **일일 상용화 체인 (선택)** | `scripts/run_track_a_commercialization_daily_chain.ps1` — shadow → metering summary → weekly report → band gate (`P0` Phase 2). |

---

## 4) 로컬 스모크 (파일럿 전 최소)

워크스페이스 루트 `C:\workspace`에서 실행한다.

| # | 명령 | 통과 기준 |
|---|------|-----------|
| S1 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_p0_constitution_gate_paths.ps1` | **exit 0** |
| S2 | `py -m pytest tests/test_compression_token_api_stub.py -q` | **전부 통과** |
| S3 (권장) | `py -m pytest tests/test_bench_l1_api_load.py -q` | 부하 벤치 스크립트 회귀 시 |
| S4 (권장) | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_workspace_automation_health.ps1` (시간 여유 시 `-IncludeCompressionKpi`) | 스모크·정합 요약 확인 |

**본 체크리스트 작성 시점 로컬 결과(참고, SSOT 아님):** S1 exit 0 (경로 개수는 `verify_p0_constitution_gate_paths.ps1` 출력 참조); S2 스텁 테스트 전부 통과.

---

## 5) 파일럿 완료 정의 (DoD 요약)

- [ ] **§11** 세일즈 킷 경로 중 본 문서 §1 표가 **존재·동결**되어 있다.
- [ ] **G0~G12** 증빙이 감사 가능한 형태로 확보되었다.
- [ ] 토큰 이코노미·P95·`reconstruction_fidelity_jaccard` 관련 **산출 JSON·로그 경로**가 파일럿 리포트에 명시되었다.
- [ ] `COMPRESSION_KPI_ALARM_WEBHOOK_URL` 또는 `OPS_ALARM_WEBHOOK_URL` 중 파일럿 환경에 **유효한 알림 채널**이 설정되었다 (해당 체인 사용 시).
- [ ] 실매매·외부 과금·LIVE 승격은 **`MKM_PROMOTION_GATE_CHECKLIST` G12 및 지휘관 GO** 없이 진행하지 않는다.

---

## 보조 참조

| 항목 | 경로 |
|------|------|
| a-codeai.com 정적+API 분리 예시 | `scripts/deploy/nginx/a-codeai.com.static-plus-compression-api.conf.example` (`P0` L2) |
| Track A SLA 초안 | `docs/final/TRACK_A_SLA_DRAFT.md` |
