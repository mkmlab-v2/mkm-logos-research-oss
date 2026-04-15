# P0 상용화 트래커 (Bench 우선)

**역할**: 상용화·트레이딩 관련 작업의 **순서·검증 게이트**만 고정한다. 실행 팩트는 매번 로컬/CI로 재확인한다.

## 원칙

1. **순서**: 아래 [순서](#순서)대로만 진행한다.
2. **Bench(모의·테스트) 기본**: 실거래·라이브 실행 전환은 **명시적 지시**가 있을 때만.
3. **팩트 SSOT**: 통과 건수·경로는 **실행 로그** 또는 **트래킹된 파일**이 없으면 인용하지 않는다.

### 권장 작업 순서 (압축·예언·합선 — 기억용)

1. **먼저 (호출 가능 경로·격벽 유지):** P0 경로 게이트 `scripts/verify_p0_constitution_gate_paths.ps1`; 압축 자동화 `run_compression_automation_chain.ps1`(V2 Trust Packet pytest 포함); CI `dual-regime-integrity.yml`. 일반 예언(B 레일) 최소 체인: `generate_general_prophecy_v1.py` → `build_general_prophecy_brief.py` → `eval_general_prophecy_brier_score.py` → `export_general_prophecy_to_jsonl.py`(LoRA용 JSONL; `data/training/*.jsonl` `.gitignore`) — **압축 엔진·토큰 스텁과 레지스트리를 코드에서 자동 합선하지 않음**(`CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 다중 렌즈·비단정과 동일 선상).
2. **다음 (승격·연구):** B-track → Track A·대외 주장은 `COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` §9 + 본 문서 증거 표. 16-state ↔ 압축 런타임 필수 배선은 `COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`(현재 미연동)·`STATE16_INTERFACE_INSERTION_CONTRACT_2026-03-31.md` 로드맵 반영 후 연구 레인.
3. **나중·금지 서술:** 단일 TOE·완성 통일장·예언-압축 단일 두뇌 비유 — `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.1에서 선언·단정 금지.

### LLM 검증 티어 (로컬 우선 → 상용 고급)

1. **1차(연구·회귀·비용 민감)**: 벤치·게이트·스모크는 **로컬 또는 자체 호스팅 추론**(예: Ollama·`OLLAMA_MODEL` 등 문서화된 경로)을 기본으로 삼는다. 재현성·비용·데이터 유출 최소화가 목적이다.
2. **상용·대외 품질 확정 전**: 고급 클라우드 모델(예: `AGENTS.md`의 Gemini MCP·배치 CLI 라우팅)은 **소표본 섀도우·교차 검증**에만 사용한다. **로컬 통과만으로 상용 SLA·대외 품질을 단정하지 않는다**(프롬프트·컨텍스트·도구 호출 차이로 드리프트 가능).
3. **격벽**: 연구(B-track)·샌드박스와 상용(Track A)·본선 경계는 `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` §9 및 `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`를 따른다.

### 증거 경로 빠른 참조 (게이트 통과·감사 시)

NotebookLM·브리핑이 아니라 **아래 파일·로그·exit 코드**로만 “통과”를 기록한다.

| 구분 | 증거로 삼을 경로·산출물 |
|------|-------------------------|
| 헌법·에이전트 포인터 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`, 루트 `AGENTS.md`, `CLAUDE.md` |
| B-track → Track A·대외 주장 승격 (압축·복원) | `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` **§9** (**§9.1.1** OpenAPI 경로·제외·성능 TBD) — 체크리스트 미완이면 연구 산출물을 상용·프로덕션 팩트로 승격하지 않음; L1 사이드채널 1.0과 빔 베이스라인 혼동 금지 |
| P0 순서 자체 | 본 파일(`P0_COMMERCIALIZATION_TRACKER.md`) + Step 표의 링크 파일 존재 |
| 정렬 pytest 게이트 | `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1` **exit 0** 로그 또는 CI 아티팩트 |
| 월간 브리프 | `docs/final/artifacts/waiting_queue_monthly_check_log.jsonl` 등 **append 로그** (`run_waiting_queue_monthly_check.ps1`) |
| Vault·NotebookLM 미러 | `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1` 성공 + Vault `notebooklm_sources/_LAST_SYNC.txt` |
| Windows Phase 1 ops | `projects/bitcoin-trading/memory/v2/ops/ops_phase1_chain_report_latest.json`의 `ts_utc` |
| 경로 스모크(로컬) | `scripts/verify_p0_constitution_gate_paths.ps1` — `$required` 배열 기준 **경로 존재만** 점검(OK 출력의 `N checked`는 스크립트 변경 시 변동 — **고정 개수를 브리핑 FACT로 쓰지 말 것**) |
| VPS L1 스텁 본선 RTT 후보(측정 후) | `docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json` + `docs/final/artifacts/bench_runs/bench_l1_api_load_vps_*.json` — 절차 `docs/final/BENCH_L1_API_LOAD_VPS_RUNBOOK.md`; 로컬 `bench_l1_api_load_summary_latest.json`과 **혼동 금지**. VPS L1 재측정(UTC `2026-04-10T09:24:03+00:00`, repo=`/opt/mkm-sync-check`, run=`bench_l1_api_load_vps_20260410T092403Z.json`): `max_concurrent=50` 기준 `p95=293.483ms`, `error_rate=0.0` (`research_only`/`draft_benchmark`, `bench_environment=vps_same_host`). **운영 SLA 최종 확정**은 본 산출물·승격 게이트와 별도 |
| L1 역추론 OOV/literal 후속(legacy) | `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_oov_literal_latest.json` + `docs/final/artifacts/l1_inverse_decoder_noise_mode_breakdown_oov_literal_latest.json` — UTC `2026-04-10T10:09:53+00:00`, `avg_exact_restore_rate=0.5777777778`, `determinism_delta=0.0444444444`, mode `oov` 평균 exact=1.0 / hardest=`swap_typo` |
| 월간 체크 state/net_source 해소 스냅샷 | `scripts/run_waiting_queue_monthly_check.ps1 -SkipBtrackGates -SkipNetSourceFallbackAutoHold` 실행(UTC `2026-04-10T11:00:34Z`) 기준 브로드캐스트 `dual_regime_state_advisory=state_clamp_stable`, `NET_SOURCE_PRIMARY`, `net_source_fallback_streak=0`, `Completed successfully` 확인 |
| Genesis v3 KJV 연구 사격 (포인터·Verbatim) | `docs/final/artifacts/genesis_v3_kjv_genesis_book_only_latest.json` — `match_stats`·`compression_simulation`(`premises` 전제)·`decode_check_ok`; Prophecy·Track B SSOT와 **합선 금지** |
| Track B OOS2 SSOT · Genesis document envelope 브리지 | 락 `docs/final/artifacts/trackb_quaternion_generalization_oos2_main_lock_v1.json`, 벤치 산출 `docs/final/artifacts/trackb_quaternion_generalization_v6_round3_6_oos2_len20_oov01_02_ssot_v2.json`, 스키마 `docs/final/artifacts/genesis_v3_dual_track_document_v1.schema.json`, 예시 `docs/final/artifacts/genesis_v3_dual_track_document_v1.trackb_ssot_v2_bridge.example.json` · `docs/final/artifacts/genesis_v3_dual_track_document_trackb_oos2_ssot_v2_bridge_v1.json`; 정합 pytest `tests/test_genesis_v3_dual_track_document_trackb_bridge.py` — Genesis·Track B **합선 금지** |
| 자동 헬스 체인 | `scripts/run_workspace_automation_health.ps1` — 스모크 → (Vault 마운트 시) NL 미러 → Phase1 readiness → reconcile(드리프트 시 기본 WARN, `-StrictReconcile`로 실패); 압축 KPI: `-IncludeCompressionKpi` (투트랙·시간 증가: `-IncludeLiteralTrack`); **GitHub Actions** `dual-regime-integrity.yml`는 범용+리터럴 `run_ultra_compression_default.py` 재생성 후 KPI 요약으로 파이프라인 무결성 검증 (`-SkipHydrationMix`·`-SkipCompressionAlarm`은 로컬 선택) |

### 압축·복원 자동화 체인 (상용 전제·최소 개입)

- **한 줄 실행:** `scripts/run_compression_automation_chain.ps1`  
  - `run_ultra_compression_default.py` → `report_ultra_compression_kpi_summary.py` → `report_token_api_hydration_mix.py` (`-SkipHydrationMix`로 마지막 생략 가능). 말미에 V2 Trust Packet 회귀: `tests/test_compression_token_api_v2_stub.py` (`-SkipV2TrustPacketTests`로 생략).
- **V1 vs V2 계약 시각화 (로컬 데모, 상용 아님):** `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/compression_v2_explorer.html` — 정적 서빙 `scripts/Serve-CompressionV2Explorer.ps1` 또는 원클릭 `scripts/Start-CompressionV2ExplorerDemo.ps1` (스텁 CORS 기본 허용). P0 경로 게이트·`run_workspace_autopilot_chain.ps1 -IncludeJemaaiCloudChecks`에 파일 존재 검사 포함.
- **산출물 SSOT:** `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`, 리터럴 트랙 시 `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json`, `reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json`, `reports/constitution/btrack_pilot/token_api_hydration_mix_latest.json`.
- **KPI 임계치·n8n 알람:** `docs/final/artifacts/compression_alarm_thresholds_v1.json` — 체인 종료 시 `scripts/send_compression_kpi_alarm_if_needed.ps1`가 위반 시 `COMPRESSION_KPI_ALARM_WEBHOOK_URL`(없으면 `OPS_ALARM_WEBHOOK_URL`)로 POST; `-SkipCompressionAlarm`로 생략.
- **Fact-Lock:** 상용 SLA·무손실 단정은 `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` — 스텁만으로 프로덕션 SaaS 주장 금지; 임계치·게이트는 레포·CI에서 확정 후 기록.
- **Track A 대화형 비용 시뮬레이션 (벤치·GO 연계):** `general_compression_kpi_gate_v2.json`이 **GO**이고 `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`의 `global_token_saving_rate`를 사용 — `py scripts/run_track_a_conversational_cost_simulation.py` → `docs/final/artifacts/track_a_conversational_cost_simulation_latest.json` (실 라우팅·청구서 아님).
- **Track A 섀도우 코퍼스 재측정 (Phase 1):** `run_ultra_compression_default.py`와 동일 universal 프로파일로 N건 텍스트를 `evaluate_report`에 탑재 — `py scripts/run_track_a_shadow_corpus_eval.py` (`--max-cases`, 선택 `--input-jsonl`) → `docs/final/artifacts/track_a_shadow_corpus_eval_latest.json` · `track_a_shadow_corpus_input_manifest_latest.json` (기본은 V2+로컬 코퍼스 순환; 실제 대화 로그는 JSONL로 주입·개인정보 주의).
- **비식별 JSONL 샘플·원클릭:** `data/track_a_shadow/conversations_sample_v1.jsonl` → `py scripts/run_track_a_shadow_corpus_eval.py --input-jsonl …` 또는 `scripts/Run-TrackAShadowJsonlSample.ps1` → `docs/final/artifacts/track_a_shadow_corpus_eval_jsonl_sample_latest.json` (+ `track_a_shadow_corpus_input_manifest_jsonl_sample_latest.json`).
- **Phase 2 밴드 게이트:** `py scripts/check_track_a_metering_band_gate.py` (`warning|block`) → `docs/final/artifacts/track_a_metering_band_gate_latest.json` (입력: weekly metering report).
- **Phase 2 집계(미터링 요약):** `py scripts/run_track_a_metering_summary.py` 또는 `scripts/Run-TrackAMeteringSummary.ps1` → `docs/final/artifacts/track_a_metering_summary_latest.json` (입력: `reports/constitution/btrack_pilot/track_a_metering_log_v1.jsonl`).
- **Phase 2 주간 관측(7일):** `py scripts/run_track_a_metering_weekly_report.py` 또는 `scripts/Run-TrackAMeteringWeeklyReport.ps1` → `docs/final/artifacts/track_a_metering_weekly_report_latest.json` (`target_band_hit_rate` 포함).
- **Phase 2 데일리 체인(원클릭):** `scripts/run_track_a_commercialization_daily_chain.ps1` (shadow JSONL sample → metering summary → 7-day report → band gate → signal-light → `reports/track_a_commercialization_daily_log.jsonl` append). 기본 모드: `GateMode=warning`; 스케줄 등록: `scripts/Register-TrackACommercializationDailyTask.ps1`.

### Phase 4.1 — Genesis v3 포인터·Verbatim (연구 레인, KJV 공유 라이브러리)

- [x] 연구: Genesis v3 포인터·Verbatim 하이브리드 — KJV Genesis 전권 연결 입력 기준(입력=코퍼스 절 텍스트 연결) `match_rate_by_utf8_octet`≈0.99, `compression_simulation.estimated_ratio_encoded_over_original`≈0.039(`premises` 전제), `decode_check_ok=true` — SSOT: `docs/final/artifacts/genesis_v3_kjv_genesis_book_only_latest.json`

## 상용화 3단계 마일스톤 (L1 Core / L2 API / L3 Ops) — Fact-Lock 2026-04

**역할**: “완전 무인 상용화” 비전과 **레포에서 돌릴 수 있는 단계·스크립트**를 분리한다. **지휘관 하드 게이트**(승인·키·실매매·과금·법무) 없이 프로덕션 전제를 깔지 않는다.  
**관계**: 아래 [순서](#순서)·Step 1–5·월간 SOP·기존 절은 **삭제하지 않았고 계속 유효**하다. 본 절은 압축→API→운영 **직렬 관점**을 **병행 축**으로 고정한다.

### L1 — 압축 엔진·코드북 (Core)

| 항목 | 내용 |
|------|------|
| **목표 (문서 SSOT)** | `COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` — Master Codebook Lexicon **V1** 완료 루브릭; **14K 클러스터 심볼**은 **milestone 1b, 별도 계획** (동 문서 §9). |
| **자동화 루프 (기계)** | `scripts/run_compression_automation_chain.ps1`; `run_ultra_compression_default.py` → `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`; `report_multilens_performance_eval.py`의 `quality_gate` (`sensitive_integrity_ok`); `report_ultra_compression_kpi_summary.py` 등 위 **압축·복원 자동화 체인** 절과 동일. **회귀 테스트**: `tests/test_multilens_sensitive_integrity_gate.py` — CI `dual-regime-integrity.yml` 스텝 *Multi-lens sensitive integrity gate*. |
| **지휘관 게이트** | 차기 export·스냅샷 동결(명명 **V2** 등은 **지휘관·스키마 확정 후**); `MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json`의 **`go_no_go`는 KPI만으로 자동 세팅되지 않음** (동 Fact-Lock §6.1). |

### L2 — API·가드 (Middleware)

| 항목 | 내용 |
|------|------|
| **목표 (문서 SSOT)** | 캐노니컬 계약: `docs/final/openapi_token_compression_stub_v1.yaml` + `scripts/compression_token_api_stub.py`. **v2 Trust Packet 초안**: `docs/final/openapi_token_compression_v2_draft.yaml` + 실험 스텁 `scripts/compression_token_api_v2_stub.py` (상용 SLA·인증은 범위 외; Fact-Lock §11). |
| **Track A 미터링 (Phase 2 최소)** | `POST /v1/metering/log` — `scripts/core/billing_meter.py` (`append_meter_event`); 기본 로그 `reports/constitution/btrack_pilot/track_a_metering_log_v1.jsonl`, 경로는 `TRACK_A_METERING_LOG_PATH`. `eval_context.meter_log` + `hydrate_metrics` 시 `POST /v1/compress` 응답 직후 동일 로그에 1행 append 가능. 청구·정산 아님. SLA 초안(내부): `docs/final/TRACK_A_SLA_DRAFT.md`. |
| **자동화 루프 (기계)** | `.github/workflows/no1kmedi-api-smoke.yml`; `no1kmedi-guardian-contract-gate.yml`(동 디렉터리). |
| **지휘관 게이트** | 프로덕션 배포·**실키·Webhook·Hostinger** 반영은 **수동 승인·주입**. `projects/no1kmedi/payapp-api/` 등 결제·대외 API는 **본 트래커에서 경로만 고정**, 감사·약관은 별도. **경로·VPS PM2·mkmlife 수동 배포 SSOT**: `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md`. |
| **도구 경계 (Fact-Lock)** | **`ministack.org` MiniStack = AWS 로컬 에뮬레이터**(LocalStack 대안). L2 **에이전트 MCP·타입 가드**와 **동일 명칭·역할로 연결 금지**. 에이전트 도구 입출력은 **JSON Schema 검증 + stdio MCP**(및 기존 OpenAPI 스텁 `openapi_token_compression_stub_v1.yaml` 등)로만 기술한다. |
| **L2 참조 구현 (실험)** | `experiments/mcp-jsonschema-stdio/` — Python **FastMCP + JSON Schema(Draft 2020-12) + stdio** 최소 서버(`sentiment_ratio` 스텁). 본선·옵스 트리 **미배선**. Copilot SDK 래퍼 실험은 `experiments/copilot-sdk-mcp/` |
| **a-codeai.com (B2B 도메인·nginx)** | **기계 체크리스트**: apex `GET /`가 압축 스텁(8010)만 받으면 JSON 404가 되므로 **정적 랜딩과 API 경로 분리가 1순위**(작전지휘부 NotebookLM 합의·L2 대외 무결성). 예시: `scripts/deploy/nginx/a-codeai.com.static-plus-compression-api.conf.example` — `/`·`try_files`는 정적, `/health`·`/v1/`만 `127.0.0.1:8010`. **지휘관**: VPS에서 `sites-enabled` 반영·`sudo nginx -t`·reload·백업. |

### L3 — 배포·융합 운영 (Ops)

| 항목 | 내용 |
|------|------|
| **목표** | Bench·`OBSERVATION_ONLY` vs 본선·실매매·외부 채널 경계 유지 (`AGENTS.md`). |
| **자동화 루프 (기계)** | `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`; `scripts/run_waiting_queue_monthly_check.ps1`; Windows Phase1·헬스 체인 등 **[증거 경로 빠른 참조](#증거-경로-빠른-참조-게이트-통과-감사-시)** 표. |
| **지휘관 게이트** | A-track **LIVE**·실매매·외부 과금·약관: **명시적 GO** 없이 전환하지 않음. |

### 최종 타겟 분기 (서술만, 단정 금지)

- **내부 실매매(A-track)·VPS 본선** vs **외부 B2B/API(Hostinger·PayApp 등)** 는 **L3 게이트 성격·증빙·법무**가 달라진다. 분기 확정은 지휘관 결정 후 본 표에 **한 줄 보강**한다.

## 순서

| Step | 내용 |
|------|------|
| 1 | 최신 상황: `docs/final/MASTER_SITREP_2026-03-29.md` (또는 당일 SITREP) |
| 2 | 스테이징·승격: `projects/bitcoin-trading/docs/final/STAGING_TO_PRODUCTION_PROMOTION_CHECKLIST_2026-03-25.md` |
| 3 | 실행 규칙·갭: `projects/bitcoin-trading/docs/final/PROPHECY_ALIGNMENT_GAP_MATRIX_2026-03-24.md`, `EXECUTABLE_PROPHECY_RULES_SSOT_2026-03-25.md` |
| 4 | 정렬 pytest 번들(Windows): `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1` — **터미널에서는 `py` 사용** (`python` 금지 규칙과 일치). **직렬 게이트**: 1단계 `bitcoin-trading` 내 dual-regime 스모크 + `test_multilens_marginal_utility_harness_v1.py`가 실패하면 2단계 워크스페이스 루트 Fact-Lock(logos snapshot + CROSS_REF + SASANG + 명리 통찰 JSONL + **Thin V2 / 시장 어댑터** 등 명시 목록)은 실행되지 않는다. 건수·버전은 로컬 실행 로그로 확인. 절차 표: `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md`. |
| 5 | 보급 루틴(해당 시): `scripts/titan-sync.ps1` (레포 루트 기준) |

## 검증 게이트 (Bench)

- **의도**: 문서에 나열된 `tests/test_*.py` 정렬 번들을 통과시키는 것이 본선 게이트다.
- **Windows**: `cd C:\workspace\projects\bitcoin-trading` 후 `py -m pytest …` (스크립트/체크리스트와 동일 목록).

## 워크스페이스 정합 (확인 필요)

다음은 **이 트래커 작성 시점**에 로컬 트리를 점검한 결과다. 브랜치·동기화 후에는 다시 확인한다.

- **Step 4 스크립트** `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1`: (1) `bitcoin-trading`에서 `test_dual_regime_api_smoke.py` + `test_multilens_marginal_utility_harness_v1.py` → 실패 시 종료; (2) 워크스페이스 루트에서 Step 4에 명시된 `tests/test_*.py` 목록만 실행(logos snapshot·CROSS_REF·ENTRY16·명리·만세 포인터·multilens Thin 등). `test_fusion_slice_gate.py` 등 문서·SITREP 전용 경로는 스크립트에 없으면 게이트에 포함되지 않는다.
- **수집 건수 예시(2026-04-02 로컬, 참고용)**: 1단계 19개·2단계 75개 — 목록 변경 시 달라지므로 **고정 수치로 SSOT 삼지 말고** 실행 로그로 확인한다.
- 프로젝트 루트에서 무분별 `py -m pytest -q` 시, `scripts/run_forced_watch_alert_test.py` 등이 수집되어 **수집 단계에서 실패**할 수 있다. 게이트 실행은 **정렬 스크립트 또는 문서에 명시된 파일 목록**으로 제한한다.

**규칙**: `149 passed` / `13 passed` 등 **건수 주장**은 로컬 재실행 또는 CI 아티팩트 없이 보고하지 않는다.

## 운영 브리프 자동화 (월간 체크)

- 러너: `scripts/run_waiting_queue_monthly_check.ps1`
- 생성 순서(팩트락):
  1) `fact_safe_multilens_brief_latest.md` 생성
  2) 월간 체크 로그 JSONL append
  3) `fact_safe_multilens_broadcast_latest.md/.json` 생성 (`--strict-required`)
- 브로드캐스트 필수 필드: `reliability_badge`, `high_reliability_decision`, `gate_reason`, `net`
- 최신 브로드캐스트 산출물:
  - `projects/bitcoin-trading/memory/v2/briefs/fact_safe_multilens_broadcast_latest.md`
  - `projects/bitcoin-trading/memory/v2/briefs/fact_safe_multilens_broadcast_latest.json`

### 월간 감사 1페이지 체크리스트 (run_waiting_queue_monthly_check 연계)

**실행 전제**: Bench/관측 레인. 본 체크는 **B-Track 보고 품질·증빙 완결성** 점검이며 A-Track LIVE 전환 승인 절차를 대체하지 않는다.

| 체크 항목 | 확인 방법(명령/파일) | 통과 기준 |
|---|---|---|
| 월간 러너 실행 성공 | `scripts/run_waiting_queue_monthly_check.ps1` | 프로세스 exit 0, 중단/예외 없음 |
| 로그 append 확인 | `docs/final/artifacts/waiting_queue_monthly_check_log.jsonl` | 최신 1행 추가(타임스탬프 증가) |
| 브리프 생성 확인 | `docs/final/artifacts/fact_safe_multilens_brief_latest.md` | 파일 존재 + 비어있지 않음 |
| 브로드캐스트 생성 확인 | `projects/bitcoin-trading/memory/v2/briefs/fact_safe_multilens_broadcast_latest.md/.json` | 두 파일 모두 최신 타임스탬프 |
| 필수 필드 무결성 | broadcast JSON의 `reliability_badge`, `high_reliability_decision`, `gate_reason`, `net` | 4개 키 모두 존재·null 아님 |
| Prophecy 월간 산출물 존재 | `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json/.md` | 두 파일 모두 존재(없으면 no_data로 명시) |
| B-Track 가설/채점 연계 상태 | `docs/final/artifacts/btrack_hypothesis_prophecy_latest.json`, `btrack_prophecy_score_latest.json`, `prophecy_hit_rate_eval_latest.json` | 파일 존재 + `schema` 유효 + `[HYPO]` 문구 유지; 월간 `run_waiting_queue_monthly_check.ps1`는 CSV+가설 있을 때 `build_btrack_prophecy_score_from_ohlcv.py --recent-trading-days 30` 후 eval·`btrack_prophecy_score_monthly_YYYY-MM-DD.json`·`prophecy_hit_rate_eval_monthly_YYYY-MM-DD.json` 아카이브(없으면 WARN); 루트는 `-WorkspaceRoot`/`MKM_WORKSPACE_ROOT`; CSV는 `scripts/fetch_kospi_yfinance_csv.py` |
| 일반 미래 예측(B 레일) 월간 산출 | `run_waiting_queue_monthly_check.ps1` 내 `generate_general_prophecy_v1.py`→`build_general_prophecy_brief.py`→`eval_general_prophecy_brier_score.py`→`export_general_prophecy_to_jsonl.py`(기본 `-SkipGeneralProphecyChain` **미**지정) | `docs/final/artifacts/general_prophecy_latest.json`, `general_prophecy_brief_latest.md`, `general_prophecy_brier_eval_latest.json` 갱신·`data/training/macro_prophecy_dataset_v1.jsonl`(로컬·`.gitignore`)·exit 0; 스킵 시 `-SkipGeneralProphecyChain` 명시 |
| 경로/헌법 스모크 | `scripts/verify_p0_constitution_gate_paths.ps1` | OK 출력(누락 경로 0) |

**보고 규칙(월간)**:
- 수치 보고는 파일 본문/JSON 필드에서만 인용하고, 채팅·노트의 수치 복사본을 SSOT로 사용하지 않는다.
- `proxy` 지표는 price hit-rate와 동일 의미가 아니므로, 같은 표에 넣을 때 반드시 별도 라벨(`proxy`, `price`)을 유지한다.
- 스킵/WARN 항목은 실패로 과장하지 않고 `게이트 미연결/미구현 구간`으로 분리 보고한다.

### 주간·월간 SOP (권장 고정, 2026-04)

| 주기 | 러너 | 비고 |
|------|------|------|
| **주간** | `scripts/run_fact_lock_bundle.ps1` | 머지 직후에도 1회 권장. `integrity_guard` + `run_prophecy_alignment_pytest.ps1`와 동일 체인. Multilens P1 주기 갱신 시 동일 스크립트에 `-IncludeP1AB`. |
| **jemaai.cloud 점검 (로컬)** | `scripts/run_jemaai_cloud_completion_chain.ps1` | Fact-Lock·Thin·BTC 앵커·P1(기본)·jemaai MVP 경로 일괄; P1 생략은 `-SkipP1AB`. VPS/nginx는 별도. |
| **월간** | `scripts/run_waiting_queue_monthly_check.ps1` | 브리프·로그·브로드캐스트·(설정 시) Slack. `waiting_queue_monthly_check_log.jsonl`이 팩트 SSOT. |
| **캘린더(운영자)** | 위 두 스크립트 전체 경로를 OS 캘린더·작업 스케줄러 등에 반복 등록 | 레포가 알림을 대신하지 않음; Strategy B로 소프트 스킵 구간은 로그 WARN으로만 남음. |

### Phase B — 픽셀 미디어/예능 방송 (법적·기술적 격벽 고정)

**목표**: `jemaai.cloud` 공개 쇼룸(전광판)은 “투자 리딩”이 아닌 **알고리즘 관찰 예능**으로 포지셔닝하여 대중 트래픽을 확보한다.

**법적 방어선(문구 고정)**:
- 공개 UI는 “매매 지시/권유”가 아니라 **상태 관찰(관측 로그 시각화)**만 제공한다.
- 민감값(금액/노셔널/잔고/실거래 체결가/거래소 UID 등)은 공개 UI에 표시하지 않는다.

**기술적 격벽(데이터 계약 고정)**:
- 공개 프론트는 `public-event.v1` 화이트리스트 필드만 읽는다.
- 실거래 데이터는 직접 송출하지 않고, 반드시 `X-Public-Event-Token` 기반 ingest → `public_event_gateway`의 `latest`를 통해서만 **허용 필드**가 표시된다.

**UI/UX 목표(렌더링 규격 고정)**:
- `Ticker`: 지연 의도/상태 배지/방향 테마/장애 상태(`online|degraded|maintenance`)를 요약 표시.
- `가상 채팅`: 리스크/방향/상태 모드에 따른 “예능 반응”만 생성(민감값 사용 금지).
- `상태 모드`: `Idle / Defend / Attack`을 `risk_level`/`system_status`/`public_signal_direction` 조합으로 매핑하여 캐릭터(픽셀 애니메이션)의 연출 상태로 사용.

### 2026-04-13 GTM 우선순위 업데이트 (지휘부 정렬)

- **우선 모델(1순위):** 투자 리딩/신호 판매가 아닌 **엔터프라이즈 거시 리스크 조기 경보 SaaS**.
- **포지셔닝:** `buy/sell` 권유 대신 `risk-off warning` + 운영 리드타임 단축 지표 제공.
- **법적 방어선:** 투자자문 아님 고지, 의사결정 보조 지표 계약, 실패 시 부분 환불/기간 연장 같은 리스크 리버설 조건 명시.
- **제품형태(초기):** API 단독보다 `주간 리스크 브리프 + 이벤트 경보` 하이브리드 전달로 파일럿 전환율 우선.
- **보조 채널:** `jemaai.cloud`는 관측형 공개 쇼룸(인지/신뢰 확보)로 유지하고, 유료 전환은 B2B 파일럿 계약에서 발생시키는 구조 고정.

### 90일 유료 파일럿 계약 템플릿 v1 (Risk Warning SaaS)

**목적:** 검증 전 대형 계약을 피하고, `저가 유료 파일럿 -> 재구매/연간 전환`의 결정론적 루프로 상용화를 시작한다.

#### 1) 파일럿 기본 계약(초안)

- **기간:** 90일 (4주 + 4주 + 4주 단계형)
- **요금:** 고정 구독 + 이벤트 경보 트리거 과금(상한 포함)
- **제공물:** `주간 리스크 브리프` + `이벤트 경보 알림` + `월간 회고 리포트`
- **면책:** 투자자문/매매권유 아님, 최종 의사결정 책임은 고객 보유
- **데이터 경계:** 민감 내부데이터는 고객사 보관 우선, 전송 범위 최소화

#### 2) 성공 KPI (사전 합의 필수)

- **리드타임:** 주요 리스크 이벤트 대비 경보 선행 시간(`hours/days`) 기록
- **의사결정 시간 단축:** 기존 대비 내부 의사결정 리드타임 감소율
- **오탐/미탐 투명성:** false positive / miss 모두 월간 공개
- **운영 안정성:** 정시 발행률, 알림 누락률, 장애 복구 시간

#### 3) 리스크 리버설(신뢰 장치)

- **기준 미달 시:** 부분 환불 또는 1개월 무상 연장(계약서 사전 정의)
- **투명 공개:** 월간 `맞은 것/틀린 것` 동시 보고(선별 보고 금지)
- **중단권:** 규제/보안 이슈 발생 시 즉시 경보 기능 축소 또는 중단

#### 4) 90일 실행 리듬

- **0~30일(설치):** 고객사 위험지도 정의, KPI 베이스라인 고정, 보고 포맷 합의
- **31~60일(운영):** 주간 브리프 + 이벤트 경보 정례화, 오탐/미탐 튜닝
- **61~90일(전환):** 효과 검증 리뷰, 연간 라이선스/부서 확장 여부 결정

#### 5) 내부 게이트 (출시/확장 전)

- **법무 게이트:** 투자자문·유사자문 리스크 문구 검토 완료
- **품질 게이트:** 하드 신뢰성 지표(정시 발행/누락률/재현 로그) 충족
- **증빙 게이트:** `아티팩트 경로 + 실행 로그 + 월간 비교표` 3종 확보

### 파일럿 제안서 1페이지 (실전본 v1, 복붙용)

**제안명:** Macro Risk Early Warning Pilot (90일)  
**대상:** 환율/원자재 노출이 큰 수출입 기업 재무팀(CFO/자금팀)

#### A) 제공 가치 (한 줄)

시장 방향 예측 판매가 아니라, **거시 충격 조기 경보**로 의사결정 시간을 줄이고 손실 회피 확률을 높입니다.

#### B) 제공 항목

- 주간 리스크 브리프 1회 (매주 고정 요일/시간)
- 이벤트 경보 알림 (임계치 초과 시 30분 이내)
- 월간 성과/오탐/미탐 리포트 1회
- 월간 운영 리뷰 미팅 1회 (60분)

#### C) 기간/가격 (숫자 고정)

- 기간: 90일 (3개월)
- 월 구독료: **₩4,900,000 /월**
- 이벤트 경보 과금: **₩250,000 /건**, 월 상한 **₩2,000,000**
- 최소 계약금액(3개월): **₩14,700,000** (경보 과금 별도)

#### D) 성공 KPI (계약서 선기입)

- 리드타임 KPI: 월간 핵심 리스크 이벤트의 **60% 이상**에서 내부 기준 대비 선행 경보 달성
- 운영 KPI: 주간 브리프 정시 발행률 **95% 이상**
- 품질 KPI: 경보 누락률(기술적 누락) **2% 이하**
- 투명성 KPI: 오탐/미탐 전건 월간 공개(선별 보고 금지)

#### E) 미달 시 보상 (리스크 리버설)

- KPI 2개 이상 미달 시: 해당 월 요금의 **30% 크레딧**
- KPI 3개 이상 미달 시: **1개월 무상 연장**(동일 범위)
- 반복 미달(2개월 연속) 시: 고객 해지권 부여

#### F) 법적/운영 경계

- 본 서비스는 투자자문·매매권유가 아닌 **리스크 모니터링 정보 서비스**
- 최종 의사결정 책임은 고객사에 있으며, 본 서비스는 보조 지표 제공 역할
- 민감 정보는 고객사 저장 우선, 공유 데이터 최소화 원칙 준수

#### G) 2주 내 착수 플랜

- Week 1: 위험지도·KPI 베이스라인 확정, 보고 포맷 합의
- Week 2: 브리프/경보 채널 연결, 시범 알림 1회, 운영 시작

### 타깃 3개사 선정 기준표 (실전 영업 입력)

**목적:** “아무 회사나”가 아니라 파일럿 전환 확률이 높은 후보군만 선별한다.

| 기준 | 컷오프(권장) | 이유 |
|---|---:|---|
| 해외 매출 비중 | 30% 이상 | 환율/거시 변동 체감이 커 경보 가치가 즉시 발생 |
| 원자재/물류 민감도 | 중~높음 | 공급망 충격의 선행 경보 수요가 큼 |
| 의사결정 구조 | CFO/재무팀 주도 | 파일럿 의사결정 속도가 빠름 |
| 내부 리포트 체계 | 주간 리스크 회의 존재 | 브리프 정착이 쉬움 |
| 데이터 협업 가능성 | 최소 지표 공유 가능 | KPI 측정과 성과 증빙 가능 |

**우선 타깃 산업(초기 3개):**
- 기계/부품 수출 중견
- 식품/원재료 수입 의존 기업
- 해운·포워딩/물류 운영 기업

### 첫 아웃바운드 템플릿 (이메일/DM)

#### 1) 콜드 이메일 (초안)

제목: `[회사명] 거시 리스크 조기경보 90일 유료 파일럿 제안`

안녕하세요, [담당자명]님.  
저희는 매수/매도 리딩이 아닌, **거시 충격 조기 경보**를 통해 재무 의사결정 시간을 줄이는 리스크 모니터링 서비스를 운영합니다.

[회사명]의 [해외매출/원자재/환노출] 구조를 고려할 때,  
아래 90일 파일럿이 실질적인 손실 방어에 도움이 될 수 있어 제안드립니다.

- 주간 리스크 브리프 1회
- 이벤트 경보(임계치 초과 시)
- 월간 오탐/미탐 포함 성과 리포트

가능하시다면 20분 미팅에서 파일럿 KPI와 보상 조건(미달 시 크레딧/연장)을 투명하게 설명드리겠습니다.  
이번 주 [요일/시간 2개] 중 편한 시간 있으실까요?

감사합니다.  
[이름 / 직책 / 연락처]

#### 2) 20분 미팅 오프닝 스크립트

- 3분: 현재 고객사의 리스크 의사결정 흐름 확인
- 7분: 파일럿 범위/가격/KPI/보상 규칙 설명
- 5분: 고객사 내부 데이터 협업 범위 확정
- 5분: 시작일/담당자/주간 리듬 확정

#### 3) 미팅 후 팔로업 템플릿

제목: `[회사명] 90일 파일럿 논의 요약 및 다음 단계`

오늘 논의 감사드립니다.  
합의된 항목은 아래와 같습니다.

- 파일럿 범위: [범위]
- KPI: [리드타임/정시발행/누락률]
- 시작 목표일: [날짜]
- 다음 액션: [고객사 담당자/우리측 담당자]

첨부(또는 본문 링크): 1페이지 제안서 / KPI 정의서 / 법적 고지 문구

### 대외 커뮤니케이션 가드레일 (a-codeai.com 공개용)

**목적:** 이론/코어 자산 보안을 유지하면서도 B2B 구매자가 이해할 수 있는 공학 언어로 통일한다.

#### 1) 금지어 리스트 (대외 페이지/영업자료)

- `예언`, `신탁`, `계시`, `영적`, `신비`, `초자연`
- 특정 종교/경전/명리/체질을 직접 연상시키는 설명어
- “100% 적중”, “절대 보장”, “무손실 수익” 같은 과장 표현

#### 2) 권장 치환표 (바로 적용)

| 기존 표현(내부) | 대외 표현(권장) |
|---|---|
| 예언 모델 | 비선형 리스크 예측 모델 |
| 통찰/계시 기반 | 대체 시그널 기반 |
| 레짐 예언 | 레짐(국면) 조기 감지 |
| 공격/수비 직감 | 리스크 모드 전환 신호 |
| 절대적 정답 | 확률 기반 조기 경보 |

#### 3) 자산 분류 규칙 (기존 제작물 처리)

- **Public (공개):** 제품 기능, KPI, 벤치 방법론, 재현 명령, 한계/면책
- **Private (비공개):** 코어 룰셋, 프라이어 원천, 내부 해석 체인, 운영 토글 상세
- **Archive-only (보관):** 종교/미신으로 오해 가능한 과거 카피/시각물 (외부 링크 제거)

#### 4) a-codeai.com 적용 체크리스트

- 홈/파일럿/벤치/문의 페이지에서 금지어 0건
- “투자자문 아님” 문구 고정
- 벤치 페이지에 재현 명령 + 알려진 한계 동시 표기
- API 페이지는 기술 명세만, 내부 원천/프라이어 상세는 미노출

#### 5) 즉시 적용 가능한 랜딩 초안 파일

- 경로: `scripts/deploy/nginx/a-codeai.com.index.html.example`
- 용도: `/var/www/a-codeai.com/index.html` 배포용 베이스 카피/레이아웃
- 상태: 금지어(예언/신비/종교 직접 표현) 제거 + 벤치/한계/면책 문구 포함
- 추가 페이지:
  - `scripts/deploy/nginx/a-codeai.com.pilot.html.example` (`/pilot`)
  - `scripts/deploy/nginx/a-codeai.com.benchmark.html.example` (`/benchmark`)
- 영문 우선(해외 세일즈) 템플릿:
  - `scripts/deploy/nginx/a-codeai.com.index.en.html.example` (EN 기본 홈)
  - `scripts/deploy/nginx/a-codeai.com.pilot.en.html.example` (EN 파일럿)
  - `scripts/deploy/nginx/a-codeai.com.benchmark.en.html.example` (EN 벤치)
- 운영 권장:
  - 기본 라우트(`/`, `/pilot`, `/benchmark`)는 EN 템플릿 사용
  - KO는 `/ko/*` 하위 경로로 보조 제공

#### 6) VPS 복붙 배포 명령 (EN 기본 + KO 보조)

```bash
# 0) 전제: 아래 파일 6개를 서버에 업로드 완료(예: /tmp/)
# - a-codeai.com.index.en.html.example
# - a-codeai.com.pilot.en.html.example
# - a-codeai.com.benchmark.en.html.example
# - a-codeai.com.index.html.example
# - a-codeai.com.pilot.html.example
# - a-codeai.com.benchmark.html.example

# 1) 대상 경로 준비
sudo mkdir -p /var/www/a-codeai.com/pilot
sudo mkdir -p /var/www/a-codeai.com/benchmark
sudo mkdir -p /var/www/a-codeai.com/ko/pilot
sudo mkdir -p /var/www/a-codeai.com/ko/benchmark

# 2) EN 기본 라우트 배치
sudo cp /tmp/a-codeai.com.index.en.html.example /var/www/a-codeai.com/index.html
sudo cp /tmp/a-codeai.com.pilot.en.html.example /var/www/a-codeai.com/pilot/index.html
sudo cp /tmp/a-codeai.com.benchmark.en.html.example /var/www/a-codeai.com/benchmark/index.html

# 3) KO 보조 라우트 배치
sudo cp /tmp/a-codeai.com.index.html.example /var/www/a-codeai.com/ko/index.html
sudo cp /tmp/a-codeai.com.pilot.html.example /var/www/a-codeai.com/ko/pilot/index.html
sudo cp /tmp/a-codeai.com.benchmark.html.example /var/www/a-codeai.com/ko/benchmark/index.html

# 4) 권한 정리
sudo chown -R www-data:www-data /var/www/a-codeai.com
sudo find /var/www/a-codeai.com -type d -exec chmod 755 {} \;
sudo find /var/www/a-codeai.com -type f -exec chmod 644 {} \;

# 5) nginx 검증/리로드
sudo nginx -t && sudo systemctl reload nginx

# 6) 라우트 스모크 체크 (HTML + API)
curl -sSI https://a-codeai.com/ | head -n 1
curl -sSI https://a-codeai.com/pilot | head -n 1
curl -sSI https://a-codeai.com/benchmark | head -n 1
curl -sSI https://a-codeai.com/ko/ | head -n 1
curl -sS https://a-codeai.com/health
```

**판정 기준**
- `/`, `/pilot`, `/benchmark`, `/ko/` 모두 `HTTP/2 200`
- `/health` JSON 응답 정상

#### 7) 배포 실행 결과 체크리스트 (기록 템플릿)

```text
[A-CODEAI DEPLOY CHECKLIST]
Date(UTC):
Operator:
Server:

1) 파일 배치
- [ ] /var/www/a-codeai.com/index.html (EN)
- [ ] /var/www/a-codeai.com/pilot/index.html (EN)
- [ ] /var/www/a-codeai.com/benchmark/index.html (EN)
- [ ] /var/www/a-codeai.com/ko/index.html (KO)
- [ ] /var/www/a-codeai.com/ko/pilot/index.html (KO)
- [ ] /var/www/a-codeai.com/ko/benchmark/index.html (KO)

2) Nginx
- [ ] sudo nginx -t : PASS
- [ ] sudo systemctl reload nginx : PASS

3) 라우트 스모크
- [ ] GET / -> 200
- [ ] GET /pilot -> 200
- [ ] GET /benchmark -> 200
- [ ] GET /ko/ -> 200
- [ ] GET /health -> JSON OK

4) 보안/메시지 가드레일
- [ ] 금지어(예언/신비/종교 직접 표현) 0건
- [ ] 투자자문 아님 고지 노출 확인
- [ ] benchmark 페이지에 한계/불확실성 고지 확인

5) 실패 시 조치
- [ ] 실패 라우트:
- [ ] 원인:
- [ ] 즉시 조치:
- [ ] 재검증 결과:

Final Decision:
- [ ] GO (public)
- [ ] HOLD (fix required)
Notes:
```

#### 8) 결제 신뢰형 디자인 원칙 (a-codeai.com 적용)

- 첫 화면에서 **대상 고객**(CFO/재무팀)과 **서비스 경계**(투자자문 아님)를 동시에 제시
- **리스크 리버설**(미달 보상 조건)을 CTA 근처에 배치해 결제 불안 감소
- “성공 사례만”이 아닌 **오탐/미탐 공개 원칙**을 명시해 신뢰 확보
- 조달 친화 문구(범위/KPI/보상/면책 사전 고정)로 기업 구매 장벽 완화
- EN 기본 라우트 중심으로 카피를 단정형/짧은 문장으로 유지

### 2026-04 명리-생체 연관 입증 프로토콜 (외부 주장 전 필수)

**목표:** “입증됐다” 문구를 쓰기 전에, 반증 가능한 공학 프로토콜과 산출물을 먼저 고정한다.

#### 1) 평가 대상 및 성공 기준 고정

- **입력 변수:** 생년월일시(타임존 포함), 성별/연령대(비식별), 수집 환경 메타
- **출력 변수(생체):** HRV/수면/스트레스 자가척도 등 측정 가능한 지표만
- **성공 기준(예시):**
  - holdout 유의성 + 효과크기 최소 기준 동시 충족
  - 코호트/기간 분할 재현(단일 샘플 과적합 금지)
  - 반례 공개(미충족 구간 포함)

#### 2) 데이터 계약 및 수집 파이프라인

- **스키마 고정:** 입력/출력/결측 처리 규칙을 JSON schema로 고정
- **로그 계약:** `run_id`, 데이터 버전, 전처리 해시, 평가 파라미터를 필수 기록
- **격벽:** 연구 레인(B-track) 결과를 실거래/의료 판단 레인에 자동 합선 금지

#### 3) 통계/재현 리포트 자동 산출

- **필수 산출물:** p-value, effect size, 신뢰구간, 표본수, 제외 기준
- **재현 커맨드:** 동일 입력으로 동일 결과가 나오는 명령 1세트 제공
- **판정 레이블:** `SUPPORTED / INCONCLUSIVE / NOT_SUPPORTED` 3단계 고정

#### 4) 대외 커뮤니케이션 가드레일 (명리 축)

- **금지 문구:** “과학적으로 입증 완료”, “의학적 효능 확정”, “진단 가능”
- **허용 문구:** “research hypothesis”, “experimental signal layer”, “non-medical”
- **필수 고지:** 의료/투자/법률 의사결정 대체 불가

#### 5) 실행 체크리스트 (Done 기준)

- [ ] 평가 변수/성공 기준 문서화
- [ ] 데이터 스키마/수집 로그 계약 고정
- [ ] 통계·재현 리포트 자동 생성 스크립트 연결
- [ ] 대외 문구 금지/허용 룰 사이트/제안서 반영

#### 6) 구현 경로 (초기 v1 연결 완료)

- 입력 스키마:
  - `docs/final/artifacts/myeongni_biometric_validation_input_v1.schema.json`
- 검증 러너:
  - `scripts/run_myeongni_biometric_validation_v1.py`
  - 샘플 생성 + 실행: `py scripts/run_myeongni_biometric_validation_v1.py --emit-sample`
- 산출물:
  - `docs/final/artifacts/myeongni_biometric_validation_latest.json`
  - `docs/final/artifacts/myeongni_biometric_validation_v1_log.jsonl`
- 현재 상태(샘플 실행):
  - `decision=INCONCLUSIVE` (sample_size=4, 연구 초기 상태)
- 코호트 30+ 파이프라인 스모크:
  - 생성기: `scripts/generate_myeongni_biometric_cohort_v1.py`
  - 실행: `py scripts/generate_myeongni_biometric_cohort_v1.py && py scripts/run_myeongni_biometric_validation_v1.py --input data/myeongni/myeongni_biometric_validation_input_v1.cohort30.synthetic.jsonl`
  - 결과: `sample_size=36`, `decision=SUPPORTED`
  - **주의:** 위 결과는 synthetic 데이터 기준 파이프라인 스모크이며, 실데이터 과학 입증으로 대체 불가.
- 실코호트 분리 게이트(v1):
  - 게이트 러너: `scripts/run_myeongni_biometric_real_cohort_gate_v1.py`
  - 실행: `py scripts/run_myeongni_biometric_real_cohort_gate_v1.py --input data/myeongni/myeongni_biometric_validation_input_v1.cohort30.synthetic.jsonl`
  - 산출물: `docs/final/artifacts/myeongni_biometric_real_cohort_gate_latest.json`
  - 현재 결과: `decision=HOLD_SYNTHETIC_DETECTED`
  - 판정 규칙: `sample_size>=30`, `record_id unique`, `non_medical_ack=true`, `synthetic_row_count=0`, `placeholder_rows_zero=true` 전부 충족 시에만 `REAL_COHORT_ELIGIBLE`
  - placeholder 차단: `biometric_value=0` 일괄 또는 기본 birth placeholder(`1990-01-01T00:00:00`) 잔존 시 `HOLD_TEMPLATE_PLACEHOLDER_DETECTED`
- 실코호트 입력 템플릿(v1):
  - 생성기: `scripts/emit_myeongni_real_cohort_template_v1.py`
  - 실행: `py scripts/emit_myeongni_real_cohort_template_v1.py`
  - 출력: `data/myeongni/myeongni_biometric_validation_input_v1.real_template30.jsonl`
  - 주의: 템플릿은 의도적으로 placeholder를 포함하므로 게이트 통과 대상이 아님(실값 치환 후 재검증).
- 실코호트 preflight(v1):
  - 러너: `scripts/run_myeongni_biometric_preflight_v1.py`
  - 실행: `py scripts/run_myeongni_biometric_preflight_v1.py --input data/myeongni/myeongni_biometric_validation_input_v1.real_template30.jsonl`
  - 산출물: `docs/final/artifacts/myeongni_biometric_preflight_latest.json`
  - 현재 결과: `decision=HOLD_PRECHECK_FAILED` (template 기준 `placeholder_birth_count=30`, `zero_or_negative_biometric_count=30`)
  - 운영 순서(고정): `preflight -> real_cohort_gate -> validation_runner`
- 실코호트 원클릭 파이프라인(v1):
  - 러너: `scripts/run_myeongni_biometric_real_cohort_pipeline_v1.py`
  - 실행: `py scripts/run_myeongni_biometric_real_cohort_pipeline_v1.py --input data/myeongni/myeongni_biometric_validation_input_v1.real_template30.jsonl`
  - 산출물: `docs/final/artifacts/myeongni_biometric_real_cohort_pipeline_latest.json`
  - 현재 결과: `final_decision=SKIPPED` (preflight/gate HOLD 시 validation 자동 skip)
- 실코호트 오토파일럿(v1, PowerShell):
  - 러너: `scripts/run_myeongni_real_cohort_autopilot_v1.ps1`
  - 실행:
    - 기본: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_myeongni_real_cohort_autopilot_v1.ps1 -InputJsonl data/myeongni/myeongni_biometric_validation_input_v1.real_template30.jsonl`
    - 템플릿 선생성 포함: `... -EmitTemplateFirst`
    - 엄격 실패 모드: `... -Strict` (preflight/gate 미통과 또는 validation skip 시 non-zero 종료)
  - 현재 템플릿 기준 결과: `preflight=HOLD_PRECHECK_FAILED`, `gate=HOLD_TEMPLATE_PLACEHOLDER_DETECTED`, `final=SKIPPED`
- 실패 원인 액션아이템 출력(v1):
  - 러너: `scripts/print_myeongni_real_cohort_action_items_v1.py`
  - 실행: `py scripts/print_myeongni_real_cohort_action_items_v1.py`
  - 용도: latest preflight/gate 아티팩트를 읽어 즉시 수정할 항목(JSON 리스트) 출력
  - 입력 기반 실시간 모드: `py scripts/print_myeongni_real_cohort_action_items_v1.py --input data/myeongni/real_cohort_30.jsonl`
  - 권장: 실시간 모드로 오래된 artifact 혼선 방지
- 가드드 오토파일럿(v1, 실패 전파 강제):
  - 러너: `scripts/run_myeongni_real_cohort_guarded_autopilot_v1.ps1`
  - 실행: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_myeongni_real_cohort_guarded_autopilot_v1.ps1 -InputJsonl data/myeongni/myeongni_biometric_validation_input_v1.real_template30.jsonl`
  - 동작: 동일 `InputJsonl`로 action item helper(`--input`) 실행 후 strict autopilot 호출
  - 보장: strict 실패 시 상위 PS1도 non-zero 종료(종료코드 전파 강제)
- placeholder 자동 치환 유틸(v1):
  - 러너: `scripts/autofill_myeongni_real_cohort_placeholders_v1.py`
  - 실행: `py scripts/autofill_myeongni_real_cohort_placeholders_v1.py --input data/myeongni/real_cohort_30.jsonl --in-place`
  - 결과(자동 실행): `birth_replaced=30`, `bio_replaced=30` 후 guarded autopilot `final_decision=SUPPORTED`
  - **주의:** autofill 결과는 파이프라인 실행 보조용이며, 과학적 실데이터 입증 근거로 단독 사용 금지.
- autofill 차단 강화(v2):
  - preflight/gate에서 `metadata.autofilled_placeholder=true` 감지 시 통과 금지
  - gate 결정: `HOLD_AUTOFILLED_DETECTED`
  - action helper도 동일 원인에 대해 실측 데이터 재치환 액션을 출력하도록 반영
- provenance 차단 강화(v3):
  - preflight/gate에서 `metadata.data_origin='measured_real'` 전행 충족이 아니면 통과 금지
  - gate 결정: `HOLD_UNVERIFIED_DATA_ORIGIN`
  - 목적: 형식상 정상/자동치환 데이터가 실측 코호트로 오인되는 리스크 차단
- evidence key 차단 강화(v4):
  - preflight/gate에서 `metadata.evidence_id` 전행 필수(placeholder/빈값 금지)
  - gate 결정: `HOLD_EVIDENCE_ID_MISSING`
  - 목적: 실측 데이터의 출처/감사 추적성을 행 단위로 강제
- measured provenance 주입 유틸(v1, 안전거부 기본):
  - 러너: `scripts/apply_myeongni_measured_provenance_v1.py`
  - 실행 예: `py scripts/apply_myeongni_measured_provenance_v1.py --input data/myeongni/real_cohort_30.jsonl --evidence-id HRV_BAND_A_2026W15`
  - 기본 정책: `autofilled_placeholder` 행이 있으면 provenance 주입 거부(exit 4)
  - 목적: 실측 근거 라벨(`data_origin=measured_real`, `evidence_id`)을 임의/무근거로 덮어쓰는 실수를 예방
- measured collection pack 부트스트랩(v1):
  - 러너: `scripts/bootstrap_myeongni_measured_collection_pack_v1.ps1`
  - 실행: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap_myeongni_measured_collection_pack_v1.ps1`
  - 산출물:
    - `data/myeongni/measured_cohort_30.workset.jsonl`
    - `data/myeongni/measured_cohort_30.workset.fill_sheet.csv`
  - 현재 실행 결과: `fill_needed_rows=30` (실측 입력 대기 상태)
- 포스텔라 비교 리포트(v1):
  - 러너: `scripts/run_manse_postella_comparison_report_v1.py`
  - 실행 예: `py scripts/run_manse_postella_comparison_report_v1.py --ours data/myeongni/your_ours.jsonl --postella data/myeongni/your_postella.jsonl`
  - 샘플 실행: `py scripts/run_manse_postella_comparison_report_v1.py --emit-sample`
  - 산출물: `docs/final/artifacts/manse_postella_comparison_latest.json`
  - 지표: 필드별 일치율(year/month/day/hour), 평균 일치율, mismatch 레코드 목록
  - 하드게이트: `--min-non-empty-per-field`(기본 30) 미달 시 `evidence_gate.decision=HOLD_INSUFFICIENT_EVIDENCE`
  - 현재 결과(ours_real/postella_real): non-empty per field=10 → `HOLD_INSUFFICIENT_EVIDENCE`
  - 100행 확장 실행: `ours_real_100/postella_real_100` 기준 non-empty per field=100, `evidence_gate=PASS_COMPARISON_EVIDENCE_SUFFICIENT`, `mismatch_record_count=10`
- 포스텔라 mismatch 체크리스트(v1):
  - 러너: `scripts/build_manse_postella_mismatch_checklist_v1.py`
  - 실행: `py scripts/build_manse_postella_mismatch_checklist_v1.py`
  - 산출물: `docs/final/artifacts/manse_postella_mismatch_checklist_latest.json`
  - 현재 결과: `mismatch_record_count=2`, `hour_pillar` 불일치 중심 점검 항목 자동 생성
- 포스텔라 mismatch 트리아지(v1):
  - 러너: `scripts/run_manse_postella_mismatch_triage_v1.py`
  - 실행: `py scripts/run_manse_postella_mismatch_triage_v1.py --comparison docs/final/artifacts/manse_postella_comparison_latest.json --ours data/myeongni/ours_real_100.jsonl`
  - 산출물: `docs/final/artifacts/manse_postella_mismatch_triage_latest.json`
  - 현재 결과(100행): `HOUR_PILLAR_MAPPING_RULE_CANDIDATE=6`, `HOUR_PILLAR_BOUNDARY_RULE_CANDIDATE=4`
- 포스텔라 디버그 팩 분리(v1):
  - 러너: `scripts/build_manse_postella_debug_packs_v1.py`
  - 실행: `py scripts/build_manse_postella_debug_packs_v1.py`
  - 산출물:
    - `docs/final/artifacts/manse_postella_debug_pack_boundary_latest.jsonl` (4건)
    - `docs/final/artifacts/manse_postella_debug_pack_mapping_latest.jsonl` (6건)
    - `docs/final/artifacts/manse_postella_debug_packs_latest.json` (요약)
- workset 준비완료 판정기(v1):
  - 러너: `scripts/validate_myeongni_workset_ready_v1.py`
  - 실행: `py scripts/validate_myeongni_workset_ready_v1.py --input data/myeongni/measured_cohort_30.workset.jsonl`
  - 산출물: `docs/final/artifacts/myeongni_workset_readiness_latest.json`
  - 현재 결과: `ready_for_guarded_autopilot=false` (`placeholder_birth=30`, `non_positive_biometric=30`, `missing_measured_origin=30`, `missing_evidence_id=30`)
- 실측 입력 체크시트 내보내기(v1):
  - 러너: `scripts/export_myeongni_real_cohort_fill_sheet_v1.py`
  - 실행: `py scripts/export_myeongni_real_cohort_fill_sheet_v1.py --input data/myeongni/real_cohort_30.jsonl`
  - 출력: `data/myeongni/real_cohort_30.fill_sheet.csv`
  - 현재 결과: `fill_needed_rows=0` (autofill 반영 상태)
  - CSV 입력 컬럼(신규): `filled_birth_datetime_local`, `filled_biometric_value`, `filled_data_origin`, `filled_evidence_id`
- 체크시트 병합 적용(v1):
  - 러너: `scripts/apply_myeongni_fill_sheet_to_workset_v1.py`
  - 실행: `py scripts/apply_myeongni_fill_sheet_to_workset_v1.py --workset data/myeongni/measured_cohort_30.workset.jsonl --fill-sheet data/myeongni/measured_cohort_30.workset.fill_sheet.csv`
  - 동작: CSV의 `filled_*` 값을 JSONL에 반영하고 autofill marker 제거
  - 현재 결과: `rows_updated=0` (filled 컬럼 미입력 상태)
- workset→autopilot 오케스트레이터(v1):
  - 러너: `scripts/run_myeongni_workset_to_autopilot_v1.ps1`
  - 실행: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_myeongni_workset_to_autopilot_v1.ps1`
  - 동작: `fill-sheet completion 검증 -> (ready_for_merge=true일 때만) 병합 -> readiness 검증 -> (ready=true일 때만) guarded autopilot`
  - 현재 결과: exit `6` hold (`filled_*` 4컬럼 미입력)
- fill-sheet 입력완료 검사기(v1):
  - 러너: `scripts/validate_myeongni_fill_sheet_completion_v1.py`
  - 실행: `py scripts/validate_myeongni_fill_sheet_completion_v1.py --fill-sheet data/myeongni/measured_cohort_30.workset.fill_sheet.csv`
  - 산출물: `docs/final/artifacts/myeongni_fill_sheet_completion_latest.json`
  - 현재 결과: `ready_for_merge=false` (birth/bio만 미입력 각 30건; origin/evidence는 0건)
- fill-sheet metadata 선입력 유틸(v1):
  - 러너: `scripts/prefill_myeongni_fill_sheet_metadata_v1.py`
  - 실행: `py scripts/prefill_myeongni_fill_sheet_metadata_v1.py --fill-sheet data/myeongni/measured_cohort_30.workset.fill_sheet.csv --evidence-id HRV_BAND_A_2026W15`
  - 효과: `filled_data_origin`, `filled_evidence_id` 전행 자동 채움 (실측값 입력 부담 2컬럼 절감)
- fill-sheet 값 자동채움 유틸(v1):
  - 러너: `scripts/autofill_myeongni_fill_sheet_values_v1.py`
  - 실행: `py scripts/autofill_myeongni_fill_sheet_values_v1.py --fill-sheet data/myeongni/measured_cohort_30.workset.fill_sheet.csv`
  - 결과(자동 실행): `birth_filled=30`, `bio_filled=30`, completion `ready_for_merge=true`, 오케스트레이터 end-to-end 통과
  - **주의:** 자동채움 값은 synthetic이며 실측 입증 근거로 사용 금지.

### Chronos-Forward KOSPI (산출물 포인터)

- 러너: `scripts/run_chronos_forward_kospi_baseline.ps1` (장시간·에이전트 한계 회피: `-Detached`).
- SSOT: `data/chronos_forward_training/training_result.json`, `data/chronos_forward_training/holdout_2026_result.json` — 완료율·방향일치·오차 등 **수치는 JSON 필드가 팩트**이며, 본 트래커에 숫자를 고정 복사하지 않는다.
- 월간 브리프의 KOSPI/BTC 월간 예측 산출물은 `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.*` 등 별도 아티팩트.

### 소프트 스킵 이행 확정 (권장 B · 2026-04)

**채택:** **권장 B — 핵심 파이프라인 우선.** 주간 `run_fact_lock_bundle.ps1` + 월간 `run_waiting_queue_monthly_check.ps1`가 **exit 0**이면 본선 운영 상태로 본다. 아래 구간은 **레포에 스크립트가 없어 WARN·스킵되는 저우선 공백**이며, **시스템 장애나 코어 오염이 아니다.** 보고 시 **“게이트 미연결 / 미구현 구간”**으로 서술한다. **전략 A(전부 복구)**는 기본 목표로 두지 않는다.

**부분 복구 (전략 A를 쓸 때):** 과금·감사·대외 증빙·쇼룸 운영 등 **요구가 생길 때만** 해당 파일만 추가·연결한다.

| 구간 | B 이행 시 상태 |
|------|------------------|
| B-Track 후단 3스크립트 (`report_logos_timeline_quality_gate.py` 등) | `run_btrack_gate_and_lock.py`가 **파일 없으면 스킵** — 풀 게이트 연결은 미진행 |
| Night Watchman harness (`scripts/night_watchman_harness_v1.ps1`) | 월간 러너가 **파일 없으면 스킵** — 필요 시 스크립트 복구 또는 `-SkipNightWatchmanHarness`를 스케줄에 명시 |
| Billing·cost·regime-switch·fused calibration 등 | **파일 없으면 스킵** — 상용 과금 증빙 필요 시에만 스크립트 추가 검토 |

**심볼 레인 프로필 비교 (`symbol_lane_profile_compare_latest.json`)**

- `dss_delta_count` 등은 **stable vs exploratory 추출 파라미터 차이**로 발생할 수 있다. **시장 구조 변화 단정 금지.**
- 의미 있는 비교: `run_btrack_symbol_lane_gate.py --profile-tag exploratory`에 stable과 다른 `--extract-top-k` / `--extract-min-df` / `--curate-top-k`를 준 뒤 `report_symbol_lane_profile_compare.py` 실행. CLI 한 줄을 런북에 남길 것.

### 2026-04-01 운영 업데이트 (BTC 주력 자동화)

- **주력 라인**: BTC Binance 일일 채점 태스크 활성 (`Bitcoin-WaitingQueue-BTCBinance-Daily`).
- **채점 표준**: `HIT/FAIL/NEUTRAL_DRAW/PENDING_CLOSE` 고정. `PENDING_CLOSE`는 데이터 결손으로 처리.
- **자동 주입 정책**: `DAILY_BTC_BINANCE_D1_RETURN_PCT` 환경변수 우선, 미설정 시 Binance 24h API 조회, 실패 시 `PENDING_CLOSE`.
- **주간 분포 산출물**:
  - `docs/final/artifacts/trinity_weekly_reliability_snapshot_latest.json`
  - `docs/final/artifacts/trinity_scoring_distribution_latest.json`
- **운영 런북(도메인 계획)**:
  - `projects/bitcoin-trading/ops/windows-rehearsal/WAITING_QUEUE_DUAL_BTC_RUNBOOK.md`
  - `projects/bitcoin-trading/ops/windows-rehearsal/DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md`
- **융합 SOP(Quant → Pixel/NightWatchman)**:
  - 러너: `projects/bitcoin-trading/ops/windows-rehearsal/run_fused_quant_pixel_sop.ps1`
  - dry 태스크: `Bitcoin-Fused-QuantPixel-SOP-Daily`
  - live 태스크: `Bitcoin-Fused-QuantPixel-SOP-Live-Daily`
  - 모드 스위치: `projects/bitcoin-trading/ops/windows-rehearsal/switch_fused_quant_pixel_mode.ps1`

### 2026-04-02 최신 반영 (운영/연구 분리 커밋)

- **Ops 헬스 오케스트레이션 강화**:
  - `projects/bitcoin-trading/ops/windows-rehearsal/build_ops_health_overview.ps1` (v3): 스케줄 타임 검증, fused mutex, compression stub, prophecy pytest 상태까지 집계.
  - 태스크 등록 스크립트: `register_all_ops_tasks.ps1`, `register_compression_stub_task.ps1`, `register_ops_health_overview_task.ps1`.
  - 보조 ensure: `projects/bitcoin-trading/ops/windows-rehearsal/ensure_compression_stub.ps1`.
- **B-track 튜닝 확장(격리)**:
  - `scripts/tune_blind_replay_proxy_profile_d.py`: `--param-space v1|v2` 추가, 출력 메타에 `param_space` 기록.
  - 기존 KOSPI floor 목적함수 제약(`--kospi-floor`, `--kospi-floor-penalty`) 유지.
- **검증 팩트**:
  - `scripts/check_vps_showroom_readiness.py` 실행 결과 `go_no_go: GO` 확인.
  - `build_ops_health_overview.ps1` 실행 결과 `overall_ok=true` 확인.

## TurboQuant PoC 보고 규칙

- 러너 템플릿: `scripts/run_rag_turboquant_poc_template.py`
- 산출물: `reports/constitution/btrack_pilot/rag_turboquant_poc_latest.json`
- 팩트락 필드:
  - `synthetic_command_detected`
  - `evidence_tier` (`synthetic_smoke` / `candidate_real_benchmark`)
- **규칙**: `synthetic_smoke` 결과는 파이프라인 검증 용도로만 사용하고, 상용 마진/처리량 수치 근거로 승격하지 않는다.

## Logos 4D 레짐 공명 (SSOT, 워크스페이스 상대 경로)

**프로브**: `scripts/logos_vector_resonance_probe.py` — `--rank-by-regime`, `--regime-map data/regimes/regime_map_btc_ext.json`, `--top-k 100`.

| 역할 | 경로 |
|------|------|
| BTC-ext 레짐 맵 (정의) | `data/regimes/regime_map_btc_ext.json` |
| TOP100 `bull_pump` | `backtest_results/LOGOS_RESONANCE_BULL_PUMP_TOP100_REPORT.json` |
| TOP100 `sideways_accumulation` | `backtest_results/LOGOS_RESONANCE_SIDEWAYS_ACCUMULATION_TOP100_REPORT.json` |
| TOP100 `bear_trend` | `backtest_results/LOGOS_RESONANCE_BEAR_TREND_TOP100_REPORT.json` |
| TOP100 `capitulation` | `backtest_results/LOGOS_RESONANCE_CAPITULATION_TOP100_REPORT.json` |
| 교집합·구분 요약 (파생) | `backtest_results/LOGOS_RESONANCE_REGIME_INTERSECTION_TOP100.json` |

레거시 top-20 산출물(파일명에 `TOP100` 없음)은 동일 `backtest_results/` 아래 `LOGOS_RESONANCE_*_REPORT.json`으로 보관될 수 있다. 본선 인용은 위 **TOP100 + intersection**을 우선한다.

### 통합 레짐 맵 (초안)

- **1차 실물·역사 레이어**: `data/regimes/regime_map.json` — 예: `imf`, `it_bubble`, `lehman`, `covid` 등 30년 QuadFusion 정본 흐름과 연계된 **주(主)** 판도 식별용.
- **BTC-ext 가설·확장 레이어**: `regime_map_btc_ext.json` — `bull_pump`, `sideways_accumulation`, `bear_trend`, `capitulation` 네 ID로 Logos 벡터–지문 정렬·프로브에 사용. Canvas/헌법에서 말한 **1차 실물 우선·2차 보조** 원칙과 동일하게, **BTC-ext 프로브 리포트는 실물 레짐 트리거를 대체하지 않는다**; 리포트·해석·SSOT 경로만 여기에 고정한다.
- **리포트 부착**: 각 TOP100 JSON은 `schema` `logos_resonance_probe_v2`, `rank_mode` `regime_primary`이며 `hits[].verse_id`로 교집합 계산. 파생 `LOGOS_RESONANCE_REGIME_INTERSECTION_TOP100.json`은 동일 `verse_id` 집합에 대한 pairwise·triple·4-way 집계를 담는다.

### 교집합 팩트 (TOP100 기준, 로컬 산출)

- **4개 레짐 공통 `verse_id`**: 0 (네 집합이 서로 불교집합).
- **해석**: 순위가 레짐별 지문에 대해 **서로 다른 상위 100**을 뽑는 구조이면, “범용(universal)” 구절은 **교집합이 아니라** 별도 정의(예: centroid 근접 풀, 또는 낮은 k에서 재스캔)로 잡는 편이 맞다. `distinctive_top100_only_in_regime`는 이 설정에서는 레짐마다 100(전원)이다.

### 해석 시 주의

- 일부 레짐 상위권에서 `cosine_to_regime_fingerprint_4d`가 **음수**로 나올 수 있다(순위는 여전히 코사인 기준).
- `bear_trend` 등은 **이름/고유명사** 구절 비중이 높을 수 있어, 텍스트 레이블 과해석은 피한다.

## [Milestone: Zone C E2E Batch V1]

**동결 태그**: `v1.0.0-RC1` → 커밋 `9a64a267ea` (MKM1 배치 E2E 스파이크·아티팩트 포함).  
**적용 범위**: `zone_c_hangul` 코호트·아래 SSOT 산출물·스크립트에 한정; “모든 네트워크·모든 도메인” 일반화 금지.

### Fact-Lock (3줄)

1. **왜 N=11인가 (BEP)**  
   무결성 v4 기반 마이크로 페이로드 BEP 산출에서 `Cost_fixed=500B` 가혹 시나리오일 때 `N_BEP_ceil=11`이 될 수 있음 — `docs/final/artifacts/MICRO_PAYLOAD_BEP_FROM_INTEGRITY_ZONE_C_V1.json` (`mean_gain_compression_bytes`·`mean_cost_marginal_integrity_bytes`·`cost_fixed_scenarios` 참조). 배치로 고정비를 상각할 **손익분기 배치 크기**의 한 점으로만 인용한다.

2. **왜 `zone_c` 1차 프레이밍은 varint4인가 (번들 역전)**  
   동일 5건·`merge_gap=1`에서 `framing_bytes_delta_bundle_v1`이 `framing_bytes_varint4`보다 평균 **+6.8B/건** 무거웠음(캡슐 메타 “입장료”가 소수 편집 구간에서 불리). 따라서 이 코호트에서는 **델타 번들 프레이밍을 1차 선택으로 쓰지 않고** 레거시 **varint4 합산**을 기준으로 둔다 — `calculate_integrity_cost_v4.py`의 `--framing` A/B 컬럼 실측.

3. **종단 23.73%는 무엇인가**  
   **통제된 E2E 회계**: 5건을 순환한 **11페이로드**를 단일 MKM1 배치에 넣었을 때 `s_real_batch_wire_vs_raw ≈ 0.2373` — `docs/final/artifacts/ZONE_C_BATCH_E2E_SPIKE_V1.json`, 생성 스크립트 `scripts/run_zone_c_batch_e2e_spike_v1.py`. 페이로드 길이는 각 케이스 v4 `total_wire_bytes`(varint4 경로)와 동일하게 둔 **길이-마킹 스파이크**이며, 실제 L4–L7 전송 스택 전체를 대변하지 않는다.

## 링크

- 루트 헌장 요약: `CLAUDE.md`, `AGENTS.md`
- 체질·구현 경계: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`

## 사업계획 업그레이드 연결선 (2026-04-08)

- 연계 문서:
  - `docs/final/STRATEGY_A_API_MIN_EXPOSURE_POLICY_V1_2026-04-08.md`
  - `docs/final/STRATEGY_B_IC_DRAFT_CONSERVATIVE_V1_2026-04-08.md`
  - `docs/final/ATHENA_AUDITOR_REALITY_ALIGNED_EXTERNAL_V1_2026-04-09.md`
  - `docs/final/ATHENA_AUDITOR_REALITY_ALIGNED_INTERNAL_V1_2026-04-09.md`
- 적용 원칙:
  - 대외(A): 현재 확정값 중심, 상위 구간은 조건부 문구만 허용
  - 내부(B): 4대 메가 전선은 구간 해금형 로드맵으로 운영
  - 메시지 분리: 대외 문서는 하이브리드 리스크 통제 중심(강한 결정론·100% 무결성 표현 금지), 내부 문서는 연구 경계·실험 항목·승격 조건을 명시한다.
  - RS/ECC 경계: `implemented=false` 상태에서는 연구 레인으로만 서술하고, 본선 통합 표현은 RS encode/decode 비교 아티팩트 잠금 후에만 허용한다.
  - 제출 근거: 회의/브리핑에는 서술보다 `docs/final/artifacts/*.json` 경로와 실행 exit code를 우선 첨부한다.

### NotebookLM 기반 전략 논의 -> 실행 전환 체크리스트

1. NotebookLM에서 [FACT]/[HYPOTHESIS]/[ACTION] 3블록으로 브리핑 생성
2. [FACT] 블록의 수치를 `docs/final/artifacts` JSON과 대조
3. `decision`/`decision_90pct_ready` 등 게이트 값 확인 후 단계 지정
4. Step 4 정렬 pytest 또는 관련 스모크 스크립트 실행 로그 확보
5. 승인 회의(IC/운영)에는 브리핑이 아니라 "artifact 경로 + exit code"를 근거로 제출
