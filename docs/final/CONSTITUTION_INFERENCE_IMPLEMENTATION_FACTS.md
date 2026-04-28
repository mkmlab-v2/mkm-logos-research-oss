# Constitution / Inference — 구현 팩트 (SSOT)

**작성일**: 2026-03-29  
**최종 갱신**: 2026-04-27 — SSOT 정합 복구(Drift pruning): 현행 운영 레일 중심으로 P0 경로 게이트를 재정렬하고, 비활성/미배포 체인은 필수 게이트에서 제외. **이전 갱신**: 2026-04-18 — §1.1.1 `[VISION]` 예언 성능 우선·국방 서사 `research_only` 격리; OHLCV 30일 패널 재실행(best_delta **-4.8%**)·`prophecy_overlay_prior_threshold_recommended_latest.json`·`prophecy_prior_threshold_sweep_summary_latest.json`; `eval_prophecy_hit_rate_v1.py --run-mode price`; CI `prophecy-restoration-spike-smoke.yml`.
**이전 갱신**: 2026-04-14 §2 B-track `4d_to_ohaeng`·human regime audit 스파이크 행; §3.4.1 Postella; 2026-04-13 §1.2 AE-2 KOSPI.  
**목적**: “기획·NotebookLM·헌법 문서만 보고 구현됨”이라고 단정하지 않도록, **호출 가능한 경로**와 **검증 상태**를 한곳에 고정한다.

> **정합성 메모 (2026-04-27):** 문서에 남아 있는 일부 historical/연구 레일 경로는 참고 이력일 수 있다. 운영 필수 여부 판정은 `scripts/verify_p0_constitution_gate_paths.ps1`의 current required 목록을 우선한다. 미존재 경로는 복구 승인 전까지 필수 게이트로 간주하지 않는다.

**갱신 (2026-04-28):** §16 `scripts/run_aramaic_mvp_chain_v1.ps1` 후반 `[35/37]`–`[37/37]`(제출 증거 번들·제출 초안·카메라레디 JSON) 및 동 단계 스크립트·pytest 경로를 `verify_p0_constitution_gate_paths.ps1` 필수 목록에 포함. 추가로 `scripts/run_two_track_submission_pack_v1.ps1`로 동 세 단계만 단독 실행 가능(선행 산출 없으면 exit 2). CI: `.github/workflows/dual-regime-integrity.yml`에 제출 팩 빌더 회귀 pytest 3종 단계 포함(PR paths에 동 스크립트·테스트 경로 추가). **`scripts/extract_aramaic_core_corpus_v1.py`**는 `verse_decoded_v2.jsonl`에서 정경 아람어 구간을 추출하는 체인 1단계 구현이며 회귀는 `tests/test_extract_aramaic_core_corpus_v1.py`(동 워크플로 단계 및 P0 목록 포함).

**갱신 (2026-04-21):** §8.1 Bio Sasang×논문 SNP **경계 팩트** 및 조인 게이트 `scripts/spec_bio_sample_paper_snp_join_gate_v1.py` 추가. 유전자명–체질 고정 매핑 표는 **본 문서 FACT 본문에 등재하지 않음** (`[HYPO]`·연구 노트 전용). 동 절 관련 스크립트·`bio_measured_labels_paper_snp_sidecar_v1.json`·매핑 템플릿 CSV는 `scripts/verify_p0_constitution_gate_paths.ps1` 필수 목록에 포함. CI 스모크: `.github/workflows/bio-paper-snp-sidecar-smoke.yml`·`tests/test_bio_paper_snp_join_chain_smoke_v1.py`·`tests/test_run_bio_paper_snp_sidecar_export_and_apply_v1_cli.py`·`tests/test_run_bio_epmc_catalog_and_label_merge_v1_cli.py`; 동일 pytest는 `dual-regime-integrity.yml`에도 포함(PR paths에 Bio SNP 경로 추가). 매핑 선행 점검: `scripts/check_bio_paper_snp_mapping_coverage_v1.py`. 로컬 헬스 선택: `scripts/run_workspace_automation_health.ps1 -IncludeBioPaperSnpJoinSmoke`. Windows 래퍼: `scripts/Run-BioPaperSnpSidecarExportAndApply.ps1`.

**갱신 (2026-04-22 — Pre-News 레일):** `scripts/build_pre_news_snapshot_v1.py` → `docs/final/artifacts/pre_news_snapshot_latest.json`; 스키마 `docs/final/schemas/pre_news_snapshot_v1.schema.json`; `scripts/pre_news_dual_regime_adapter_v1.py`·`scripts/dry_run_pre_news_dual_regime_v1.py` → `docs/final/artifacts/pre_news_dual_regime_bridge_latest.json`; 벤치 입력 `docs/final/artifacts/pre_news_bench_inputs_latest.json`(선택); `scripts/send_pre_news_bridge_stub_telegram_v1.py`(루트 `.env` 병합·`TELEGRAM_*` 없으면 skip); `scripts/evolve_pre_news_bench_inputs_v1.py`(자동 제안·자동 적용 금지)·`scripts/run_ssh_shadow_pre_news_chain_v1.ps1`(원격 shadow 실행/회수); `scripts/run_pre_news_morning_chain_v1.ps1`·`scripts/register_pre_news_morning_chain_task.ps1`; `scripts/run_daily_prophecy_then_pre_news_v1.ps1`; **로컬 단일 24h 운영 래퍼** `scripts/run_local_24h_ops_chain_v1.ps1`·`scripts/register_local_24h_ops_chain_task.ps1`·`scripts/run_local_min_verification_5lines_v1.ps1`; **모드 전환 가드** `scripts/alert_local_trading_mode_transition_v1.py` (`reports/local_trading_mode_guard_state.json`); **주간 후보 검토 패킷** `scripts/run_pre_news_weekly_candidate_review_v1.py`·`scripts/register_pre_news_weekly_candidate_review_task.ps1` (`docs/final/artifacts/pre_news_weekly_candidate_review_latest.json`); 감사 `reports/pre_news_morning_chain_log.jsonl`·`reports/local_trading_min_verification_latest.json`. **실매매·본선 주문 자동 합선 없음.**

**갱신 (2026-04-28 — Hybrid Pointer Router 상용 PoC 체인):** §19~§27에 `GO/WATCH/HOLD` 라벨·순효율 민감도·운영 권장영역·routing decision/runtime config/shadow daily report/alert/guard/guard drill 및 B2B SLA·카피덱·PoC 체크리스트 추가. 기본 정책은 조건부 주장(artifact-bound)과 자동 강등(`HOLD_POINTER_ROUTE` → `track_a_primary`) 고정.

---

## 1. 검증 범위

- **포함**: 저장소 내 실제 파일 경로, 스모크/단위 테스트에서 참조되는 심볼.
- **제외**: 다른 브랜치·미커밋 로컬 전용 파일·외부 Vault만 존재하는 산출물 (경로만 “확인 필요”로 표기).

### 1.2 압축·해석 파이프라인 Fact-Lock (혼선 방지 SSOT)

| 항목 | 경로 | 비고 |
|------|------|------|
| Compression Interpretation Fact-Lock | `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` | 12AI(파일럿)·코드북 샤드·압축 엔진·다중렌즈 역할 분리, 16상 연동 상태(미완) 고정; HTTP v2 Trust Packet 초안은 §11; **파일럿 대외 톤** §10에 L1 연구 와이어 `POST /v1/research/l1_side_channel/wire` 경계(§2 표와 정합) |
| B-track → Track A promotion (compression lane) | `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` §9 (§9.1.1 승격 범위·OpenAPI 경로 표·성능 잠금 절차) | 연구 산출물 승격 전 체크리스트·격벽(L1 하네스 vs 빔·Jaccard SSOT 등); `P0_COMMERCIALIZATION_TRACKER.md` 증거 표 교차 참조 |
| Two-track compression SLA (Track A/B) | `docs/final/COMPRESSION_SLA_POLICY_V1.md` | 범용 vs 리터럴 프로필·산출 경로·헬스/손실 리포트·웹훅은 `active_kpi`(Track A)만; `run_ultra_compression_default.py --mode literal`, `literal_kpi`, CI 범용+리터럴 재생성 스텝 |
| HTTP v2 Trust Packet (OpenAPI + stub) | `docs/final/openapi_token_compression_v2_draft.yaml` | FastAPI: `scripts/compression_token_api_v2_stub.py` — `POST /v2/compress`, `POST /v2/expand`; 압축 경로는 `evaluate_report` + 도메인 라우터(초안 명칭 `GlobalPivotCompressionPipeline` 대체). 본문 `emit_semantic_pointer: true` 시 `residual_meta.mk_stub_v2.semantic_pointer`(`schema: semantic_pointer_v1`, `evaluate_report` 가산). 계약 회귀: `tests/test_compression_token_api_v2_stub.py::test_openapi_v2_contract_has_emit_semantic_pointer`. 상용 SLA 아님. §11 |
| Master codebook lexicon V1 export | `scripts/export_master_codebook_v1.py` | 아톰+Strong+MorphHB 시드 조인 산출; 루브릭은 동 COMPRESSION 문서 §9 |
| Master codebook lexicon V1 → multilens route join (bridge) | `scripts/core/master_codebook_lexicon_v1_bridge.py` | `evaluate_report(..., use_master_codebook_lexicon_v1=True)` 시 원문 토큰과 `normalized_form` 교집합으로 must_keep 보강; 4D·샤드 정책 대체 아님. 호출부: `report_multilens_performance_eval.py`, ultra/P1 러너·벤치·압축 스텁 |
| Multilens eval `semantic_pointer` (가산 채널) | `scripts/report_multilens_performance_eval.py` | CLI `--emit-semantic-pointer` / `evaluate_report(..., emit_semantic_pointer=True)` — 케이스별 `semantic_pointer`(`schema: semantic_pointer_v1`), `compression_metrics.semantic_pointer_channel`; `avg_reconstruction_fidelity_jaccard`·`global_token_saving_rate` 집계 경로 불변. 회귀: `tests/test_multilens_performance_eval_report.py` |
| State16 Insertion Contract | `docs/final/STATE16_INTERFACE_INSERTION_CONTRACT_2026-03-31.md` | 16상 인터페이스 삽입 지점/입출력/오류/단계적 게이트 명세 (런타임 강제 아님) |
| AE-2 KOSPI 구조 엔트로피 스파이크 v1 | `scripts/spike_kospi_structural_entropy_v1.py` → `docs/final/artifacts/spike_kospi_kld_v1.json` (합성 기본); `--mode csv`+`research/market_data/kospi_daily_external_yf.csv` → `spike_kospi_kld_v1_real.json` (JSON에 `csv_source_health`: 행 수·수익률 쌍·스킵 카운트·기간); `scripts/spike_kospi_structural_entropy_compare_v1.py` → `docs/final/artifacts/spike_kospi_kld_v1_compare.json` | **관측·연구 전용** — 멀티렌즈 토큰 압축·Track A 승격·`evaluate_report` 본선과 자동 합선 없음; blind replay 코스피 그리드와 별도 레일 (`COMPRESSION_RESTORATION_EVOLUTION_INDEX_V1.md` §2 2026-04-13). 회귀: `tests/test_spike_kospi_structural_entropy_v1.py`, `tests/test_spike_kospi_structural_entropy_compare_v1.py`. |

### 1.1 엔지니어링 정체성 (Multi-Lens · 단일 방정식 비단정)

**폐기(선언·단정 금지):** 성경·명리·시장·외경·DSS 등을 **물리 만물이론(TOE)급 단일 방정식**으로 이미 합선·구현했다는 서술. 기획서·NotebookLM·수사만으로 **“통일장 완성”**을 코드에 대입하지 않는다.

**채택(Fact-Lock):**

- **다중 렌즈:** 로고스(정경 코어), 명리(B-track 실험), 레짐·PSI(실물 1차) 등은 **각각의 스키마·경로**로 두고, 필요 시 **교차 참조·관측 리포트**로만 맞춘다.
- **격벽:** §4 평행 코퍼스, §3 명리 분리, §2.1 dual-regime(16상 캡 미연동)을 **합선 방지**의 기본으로 둔다.
- **UFT·통일장 라벨:** `tools/core/unified_field_theory_engine*.py` 등은 **§10 경로 팩트**로만 인용한다. **호출 가능한 `.py`·테스트**가 없으면 “구현됨”으로 말하지 않는다(본 문서 상단 목적과 동일).

### 1.1.1 [VISION] 예언 성능 우선·대외 도메인 사례 격리 (2026-04-18)

대외용 ‘국방 제안·지원사업’ 서사는 **`research_only` 도메인 연구 사례**로만 유지하고, 시스템 우선순위 서술은 **예언(Prophecy) 성능·재현 가능한 채점**으로 맞춘다. B-track 기반 개입의 **성패 판정**은 `prophecy_hit_rate_eval_report_v2` 및 동일 채점기 위의 **적중률 델타**(또는 `run_prophecy_restoration_spike.py` 등 **AB 오버레이 스파이크 산출**)로만 논한다; 델타가 음수인 것도 **유효한 관측**이며 정책·임계값 스윕 비교의 입력이 된다. 명리·로고스 등 B-track 산출물은 Prior·실험 입력으로만 쓰고, **§1.1 TOE 비단정·§8 Promotion Loop·격벽** 없이 A-track·실매매 파이프라인에 합선하지 않는다. 다축 브리지·라우팅 보조와 토큰 압축 경로의 **역할 분업**은 기존 표·§2 경로 팩트를 따르며, 본 절은 구현 행을 중복하지 않는다.

---

## 2. Dual-regime / 레짐 융합 (실물 쪽, 1차 레짐)

| 항목 | 경로 | 비고 |
|------|------|------|
| Dual-regime 평가 모듈 | `projects/bitcoin-trading/src/integration/dual_regime_api.py` | `evaluate_dual_regime_and_market_shock` 등 Python API; **이 파일 단독으로는 FastAPI 앱이 아니다** (HTTP 래퍼는 별도 서비스/스크립트에 둔다). 선택 인자 ``state_provenance``에 ``source_track: B``(``scripts/core/track_source_guard.py``)가 오면 명리 방어 클램프에 ``state_id``를 적용하지 않음(bulkhead). 실매매 쪽은 ``crypto_nitro_live_strategy``가 ``signal_data``/``risk_assessment``의 ``source_track``을 전달. JSONL 상위 키 ``source_track``로 Track A 로더 거부: ``assert_track_a_json_row_allowed``. |
| Track A/B JSONL (Sovereign iterator) | `scripts/core/sovereign_jsonl.py` | `iter_jsonl_dict_rows` — `track_context` A면 행마다 `assert_track_a_json_row_allowed`, B면 연구 입력용(가드 생략). 파일럿: `report_symbol_numeric_injection` B-context. 회귀: `tests/test_sovereign_jsonl.py`. |
| 소버린 토큰 절감 스파이크 v1 | `scripts/spike_sovereign_token_saving.py` → `docs/final/artifacts/derived/spike_sovereign_token_saving_latest.json` | 코드북 용어(최대 16개)를 ``<S00>``..``<S15>``로 치환 후 tiktoken(o200k_base) 또는 바이트 프록시로 대비; B-track. 회귀: ``tests/test_spike_sovereign_token_saving_v1.py``. |
| 샤드 어휘 소버린 효율 스파이크 | `scripts/spike_sovereign_vocab_efficiency.py` → `docs/final/artifacts/derived/spike_sovereign_vocab_efficiency_latest.json` | ``codebook/shards/zone_*.json``에서 수집한 용어로 **다어구**를 구성, 플레이스홀더 토큰 수보다 **baseline 토큰 수가 큰 구문만** 매핑 후 tiktoken 대비; B-track. 회귀: ``tests/test_sovereign_efficiency.py``. |
| 토큰 압축 API (스텁 v1) | `scripts/compression_token_api_stub.py` | FastAPI: `POST /v1/compress`, `POST /v1/expand`, `GET /health`. **연구 레인(additive):** `POST /v1/research/l1_side_channel/wire` — L1 사이드 채널 최소 페이로드를 `scripts/l1_side_channel_wire_codec.py`(`encode_adaptive_msgpack` 등)로 적응형 와이어 인코딩·base64 반환; **HTTP 503**: (1) 런타임에 msgpack 미설치, (2) 내부 `msgpack_payload_bytes`가 `None`(pack 불가). 응답에 `api_contract_version`; `eval_context.hydrate_metrics` 없으면 `compression_metrics` null(라우터만). **enterprise 티어**에서 `hydrate_live_eval` 시 `evaluate_report`(선택 `eval_context.emit_semantic_pointer` → 응답 `semantic_pointer` `semantic_pointer_v1`) 시도·실패 시 `integrity_flags.hydration_live_eval_failed` 가능. **public 티어(Track B·literal KPI 추정)**는 동일 요청 시 `hydrate_live_eval_suppressed`로 라이브 경로 차단. **expand는 원문 에코**. 회귀: `tests/test_compression_token_api_stub.py`(OpenAPI 경로 포함·와이어 라운드트립·`test_public_tier_bulkhead_never_calls_live_eval_even_when_requested`·`test_openapi_v1_semantic_pointer_contract_fields`). 대외 설명 SSOT: `COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` §10 + `openapi_token_compression_stub_v1.yaml` description. |
| 토큰 압축 스텁 부하 벤치 (§9.2 draft SLA) | `scripts/bench_l1_api_load.py` → `docs/final/artifacts/bench_l1_api_load_latest.json` | stdlib `urllib` 스레드 풀; **클라이언트 RTT** p50/p95/p99. 서버 RSS는 동일 호스트 `--server-pid`+`psutil` 선택. `research_only`/`draft_benchmark`; FACT 승격은 플레이북 9.2 절차. dry-run 회귀: `tests/test_bench_l1_api_load.py`. |
| OpenAPI (압축 스텁) | `docs/final/openapi_token_compression_stub_v1.yaml` | HTTP 계약(SSOT); `info.version` **1.1.1+** (예시 문서만 PATCH). `mode_live` 요청 예시 텍스트는 기본 `COMPRESSION_API_LIVE_EVAL_MIN_TOKENS`(12, 스텁 `TOKEN_RE` 토큰 수) 이상. EvalContext(`emit_semantic_pointer`)·HydrationHints·CompressionMetrics·CompressResponse(`semantic_pointer`) 스키마 포함. **v1.1.0** 에 `POST /v1/research/l1_side_channel/wire` 추가; 스키마 `L1SideChannelWireRequest` / `L1SideChannelWireResponse`, 응답 `schema_version` 예시 `l1_side_channel_wire_stub_v1`. 상용 SLA·인증은 범위 외. |
| 정책 SSOT | `data/regimes/regime_fusion_policy.json` | 워크스페이스 상대 경로로 로드 |
| 보조 정책 | `data/regimes/dual_regime_policy.json` | 존재 확인됨 |
| 레짐 맵 | `data/regimes/regime_map.json` | 존재 확인됨 |
| B-track 4D→레짐 이론 오버레이 스파이크 | `scripts/build_4d_to_ohaeng_theory_aligned_regime_overlay_spike.py` → 기본 `docs/final/artifacts/4d_to_ohaeng_regime_labeled_with_theory_regime_v1.jsonl` | 행 `vector_4d`와 레짐 맵 `fingerprint.unified_4d_vector` 코사인 → `regime_id_theory_v1` 등; 경로명 `ohaeng`은 파이프라인 라벨(전통 오행 1:1 매핑 단정 아님). 연구·[HYPO] |
| B-track 4D→ohaeng NotebookLM 권장 풀체인 스파이크 | `scripts/run_4d_to_ohaeng_notebooklm_recommended_full_chain_spike.py` | 포인터 `docs/final/artifacts/4d_to_ohaeng_notebooklm_merge_inputs_recommended_v1.json`; merge·holdout·스냅샷·게이트·선택 이론 오버레이(`--no-theory-overlay` 가능). 실매매·A-track 자동 합선 금지 |
| Human regime audit 측정 스파이크 | `scripts/run_human_regime_audit_measurement_chain_spike.py` → `docs/final/artifacts/human_regime_audit_measurement_run_latest.json` | `scripts/fill_human_regime_audit_llm_spike.py`로 휴리스틱/Gemini 자동 라벨·프록시 비교; Gemini는 `google.genai` `HttpOptions.timeout`이 **밀리초**(초×1000·최소 10s); 루트 `.env`는 기동 시 로드·기존 env 미덮어씀. 회귀: `tests/test_fill_human_regime_audit_llm_heuristic_spike.py`, `tests/test_fill_human_regime_audit_gemini_retry_spike.py` |
| 성경 2차 레짐 | `data/regimes/biblical_regime_matrix.json` | 헌법: 보조 레이어 |

### 2.1 Dual-regime 평가 하이브리드 (연속 캡 · 이산 임계 · 16상 미연동)

`projects/bitcoin-trading/src/integration/dual_regime_api.py`의 `evaluate_dual_regime_and_market_shock` 팩트:

- **연속(실수):** `stress`, `risk_multiplier_cap`; 선택적 로고스 브리지에서 `resonance`·조정 캡.
- **이산/임계:** `psi_thresholds`(warning/crisis), `market_shock_confirmed`, `veto_triggered`; `resonance_count`는 4D 축이 중립(0.25)에서 벗어난 개수(0–4 정수).
- **명리 16상(B-track):** `state_id`로 캡을 분기하지 않음. `get_myeongni_16_state_experiment_ssot`는 **경로·메타**만 노출하며, 16상 실험 JSONL·스키마는 **캡 합선 전** Fact-Lock(§3.1)과 동일 정책.

**정체성:** 단일 “통일장 방정식”으로 모든 도메인을 합선했다고 단정하지 않는다. 레짐·로고스·명리는 **별 모듈·별 격벽**을 유지하고, 본 절은 **벤치용 dual-regime 조합기**의 실제 동작만 기술한다.

---

## 3. 명리(Myeongri) 분리 네임스페이스 (거래 그래프와 합선 방지)

| 항목 | 경로 | 비고 |
|------|------|------|
| 명리 전용 ledger 접두어 | `projects/bitcoin-trading/ops/v2/memory/decision_ledger.py` | `MYEONGRI_LEDGER_PREFIX`, `append_myeongri_decision_ledger` |
| Fact-lock 스냅샷 | `projects/bitcoin-trading/ops/v2/memory/fact_lock_snapshot.py` | `trading_config` 내 `myeongri` 서브셋 + 정책 해시 |

### 3.1 16-상태 실험 JSONL (B-track, Fact-Lock)

| 항목 | 경로 | 비고 |
|------|------|------|
| JSON Schema | `docs/final/MYEONGNI_16_STATE_EXPERIMENT_JSON_SCHEMA.json` | `state_id` 1–16; 선택 필드 `consistency_rate`, `self_contradiction_rate` (각 0–1) |
| Ledger·검증 CLI | `scripts/myeongni_16_state_experiment_ledger.py` | `append_*`, `validate-sample --path …` |
| 정본 예시 데이터 | `data/myeongni/myeongni_16_state_experiment_v1.jsonl` | 운영 적재 전 참조 |
| 샘플 (동일 스키마) | `data/myeongni/myeongni_16_state_experiment_v1.sample.jsonl` | 스텁·가설 티어 B용 |
| 단위 테스트 | `tests/test_myeongni_16_state_experiment_ledger.py` | 스키마 검증·rate 구간 |

### 3.2 Logos–명리 16상태 할당 (B-track, 스냅샷)

| 항목 | 경로 | 비고 |
|------|------|------|
| 할당 CLI | `scripts/join_logos_verses_myeongni_states_4d.py` | `scipy.linear_sum_assignment`; 입력: `backtest_results/sweep_kmin_refine/LOGOS_RESONANCE_BTC_EXT_ABSOLUTE_TOP16.json`, `data/myeongni/16_STATE_MASTER_PROBE_v1.json`, `data/logos/verse_4pipeline_full_31102.json` |
| 추적 스냅샷 | `docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json` | 커밋 시점 고정; 재실행 시 `LOGOS_STATE_JOIN: total_cosine_sum=…` 로그 |
| CI 회귀 | `tests/test_logos_state_mapping_v1_snapshot.py` | 스키마·16건·`total_cosine_sum`/`mean_cosine_per_pair` 수치 고정 (**러너에서 전체 재계산 아님** — `verse_4pipeline_full_31102.json` 대용량·미추적 가능) |

### 3.3 명리 통찰 작업 (B-track, 채팅·연구 순서)

| 항목 | 경로 | 비고 |
|------|------|------|
| 작업 순서·용어·금지선 SSOT | `docs/final/MYEONGRI_INSIGHT_SSOT.md` | 0→7 단계; 융합 중간레이어와 역할 분리 |
| 관측 로그 샘플 | `data/myeongni/insight_observation_log.sample.jsonl` | `myeongni_16_state_experiment` JSONL과 별도; 통찰 전용 |
| 관측 로그(부트스트랩) | `data/myeongni/insight_observation_log.jsonl` | 주간 append; 회귀와 동일 계약 |
| 융합 인터페이스 스텁 | `docs/final/MYEONGNI_FUSION_INTERFACE_STUB.json` | `myeongni_fusion_interface_stub_v1` |
| 독립 렌즈 v0 (정량 스코어) | `scripts/run_lens_myeongni.py` → `docs/final/artifacts/myeongni_independent_lens_latest.json` | 계약 `MYEONGNI_INDEPENDENT_LENS_V0_CONTRACT.json`; B-track·비트리거; A-track·캡 합선 금지 |
| 사상 독립 렌즈 v0 | `scripts/run_lens_sasang.py` → `docs/final/artifacts/sasang_independent_lens_latest.json` | 계약 `SASANG_INDEPENDENT_LENS_V0_CONTRACT.json`; `sasang_dynamics_regime_mapping_v1*.jsonl` tail; 비의료·비트리거 |
| 로고스 독립 렌즈 v0 | `scripts/run_lens_logos.py` → `docs/final/artifacts/logos_independent_lens_latest.json` | 계약 `LOGOS_INDEPENDENT_LENS_V0_CONTRACT.json`; `data/logos/4lens_batch_sample.json` 등 4D 배치; 금융·레짐 미혼합(Logos First) |
| 창1·요1 Wide 복원 산출 재생성 | `scripts/build_logos_wide_restoration.py` → `data/logos/reports/wide.json`, `data/logos/reports/wide_restored.json` | 입력 `data/logos/reports/logos_report_gen1_john1_wide_*.json` `verse_level`; `geumhwa_index=K×(1−M)×0.9`; `restoration_rate=min(0.9999,0.96+geumhwa_index×0.0001)`; 거리 0.156–0.20 → Wide20; 구조 복원 지표·[HYPO]·예측력 단정 금지 |
| 독립 렌즈 융합 스텁 v0(비교 전용) | `scripts/report_independent_lens_fusion_stub_v0.py` → `docs/final/artifacts/independent_lens_fusion_stub_latest.json` | 계약 `INDEPENDENT_LENS_FUSION_STUB_V0_CONTRACT.json`; 일치/충돌 요약만 수행; A-track 자동융합·실거래 트리거 금지 |
| 독립 렌즈 Shadow 게이트 v1 | `scripts/report_independent_lens_shadow_gate.py` → `docs/final/artifacts/independent_lens_shadow_gate_latest.json` | 계약 `INDEPENDENT_LENS_SHADOW_GATE_V1_CONTRACT.json`; 최소 관측 창(8주·2개월) 누적·`KEEP_OBSERVATION_ONLY` 고정 |
| 계약 테스트 | `tests/test_myeongni_insight_observation_log.py` | sample·log JSONL + 스텁 JSON |
| 만세력 기반 명리 4D 융합 | `scripts/myeongri_complete_fusion.py` | `MyeongriCompleteFusion`; `tools/core/myeongri_4d_correction.py`·`_ohang_data_to_4d`; `MyeongriController._get_base_vector_4d`와 연동; 본선·실거래 자동 합선 금지 |
| λ 변환 훅 (스텁) | `scripts/myeongri_lambda_converter.py` | `MyeongriLambdaConverter` |
| 게마트리아+명리 4D 블렌드 스파이크 v0 | `scripts/spike_gematria_myeongri_blend_v0.py` → `docs/final/artifacts/gematria_myeongri_spike_blend_latest.json` | 기하 메트릭(L2·cosine)만; 예측·교리 정확도 아님; `independent_lens_fusion_stub`의 `consistency_rate`와 무관 |
| 로그 윈도우 vs 명리 4D 상관 스파이크 v1 | `scripts/spike_log_myeongri_correlation_v1.py` → `docs/final/artifacts/log_myeongri_correlation_latest.json` | 입력 JSONL `log_myeongri_correlation_input_row_v1`; 출력 `log_myeongri_correlation_output_v0`; 축 `L` vs `error_rate`, `M`(토+수 응축) vs `diversity_ratio`, `‖V‖₂` vs `total_requests`; `p_value_pearson` / `p_value_spearman`(SciPy 없으면 null); 기본 최소 창 30; 라우팅·프로덕션 게이트 자동 합선 금지 |
| LOG_METABOLISM → 상관 입력 JSONL 변환 | `scripts/convert_log_metabolism_to_myeongri_correlation_input_v1.py` | cohort `egress_pressure`/`throttle_events`를 결정론적 프록시로 `total_requests`/`error_count`/`unique_trace_ids`에 매핑(B-track·[HYPO]); 본선 KPI 단정 금지 |
| LOG_METABOLISM 합성 코호트 생성 | `scripts/generate_log_metabolism_synthetic_cohort_v1.py` | 기본 `docs/final/artifacts/derived/log_metabolism_synthetic_cohort_v1.jsonl`; `--run-pipeline` 시 변환+`log_myeongri_correlation_synthetic_latest.json`; 실탄 대체 스모크 전용·[HYPO] |
| 합성 실탄 풀스택 원클릭 | `scripts/run_synthetic_log_myeongri_full_stack_v1.ps1` | `generate_* --run-pipeline` 후 `run_nl_metabolism_auto_chain.ps1 -LocalRawPath`(합성 cohort)·`-SkipStaging -SkipCopyShard`; B-track 스모크 |
| 명리·사상 4그리드 코드북 빌드 (스파이크) | `scripts/build_myeongri_sasang_codebook_spike_v1.py` → `docs/final/artifacts/derived/myeongri_sasang_codebook_spike_v1/` | 입력 `docs/final/artifacts/scm_boming_jiju_lexicon_v1.json` + 선택 보조 `supplement_terms_v1.json`; B-track·연구용 |
| 명리·사상 4그리드 압축 스파이크 v1 | `scripts/spike_4grid_myeongri_compression_v1.py` → `docs/final/artifacts/derived/spike_4grid_myeongri_compression_latest.json` | Zstd baseline·global substitute·routed·heavy mix; `corpus_source` synthetic 또는 코퍼스 `--jsonl-key`; 프로덕션 게이트 자동 합선 금지 |
| 4그리드 스파이크 원클릭 | `scripts/Run-4GridMyeongriCompressionSpikeV1.ps1` | 코드북 빌드 후 스파이크; `-CorpusPath`/`-JsonlKey`/`-Synthetic` |
| NL metabolism / ablation Python 선택 | `MKM_PYTHON_EXE` (선택) | 미설정 시 풀스택 스크립트가 `.venv_lora\Scripts\python.exe`를 자동 사용(SciPy·p-value); `run_nl_metabolism_*`·`run_log_ablation_chain_v1`의 `Invoke-PyArgList` 동일 |
| Git·`tools/` 추적 보장 | 루트 `.gitignore` 말단 `!tools/myeongni/**`, `!tools/core/**`; 로컬 `.git/info/exclude`에 동일 예외 권장 | `tools/*` 일괄 무시와 공존 시 `tools/myeongni`·`tools/core` SSOT가 조용히 누락되지 않게 함(FAIL-GIT-005); `git check-ignore -v <path>`로 검증 |
| B-track 메가 인사이트 배치 수집 | `scripts/run_notebooklm_mega_insight_batch.py` → `reports/notebooklm/btrack_mega_insights_*.jsonl` | 연구 수집·가설 정리 전용; 필수 태그 `[HYPO]`, `research_only=true`, `promotion_required=true`; A-track·실매매 자동 합선 금지 |
| B-track NotebookLM JSONL 관측 KPI | `scripts/report_btrack_notebooklm_jsonl_kpi.py` → `docs/final/artifacts/btrack_notebooklm_jsonl_kpi_latest.json` | 출처·인용·답변 길이·가드레일 키워드 비율 등 **품질 관측**만; 예측력·A-track 승격 아님 |
| Prism 논리 색인 레지스트리 | `docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json` | §14 Grand Indexing 2.0; 경로·역할; 코드 4D 축과 혼동 금지 |
| 회귀 스모크 | `tests/test_myeongri_fusion_scripts_smoke.py`, `tests/test_gematria_myeongri_spike_smoke.py`, `tests/test_spike_log_myeongri_correlation_v1.py`, `tests/test_convert_log_metabolism_to_myeongri_correlation_input_v1.py`, `tests/test_generate_log_metabolism_synthetic_cohort_v1.py`, `tests/test_spike_4grid_myeongri_compression_v1.py`, `tests/test_spike_kospi_structural_entropy_v1.py`, `tests/test_spike_kospi_structural_entropy_compare_v1.py` | CI `dual-regime-integrity.yml`; `run_prophecy_alignment_pytest.ps1` / `.sh` 번들 |
| 독립 렌즈 v0 회귀 | `tests/test_myeongni_independent_lens_v0.py`, `tests/test_independent_lenses_v0.py`, `tests/test_independent_lens_fusion_stub_v0.py`, `tests/test_independent_lens_shadow_gate_v1.py` | 명리 단독 + 3렌즈 파라미즈 + 융합 스텁 + Shadow 게이트 |

### 3.4 만세력 정밀 런타임 (제2계층, Pointer)

| 항목 | 경로 | 비고 |
|------|------|------|
| 정밀 런타임 SSOT 포인터 | `docs/final/MANSE_PRECISION_RUNTIME_POINTER_V1.json` | **에이전트 공식 배선 Path B**: MCP stdio `athena-manseryeok`. 배치/CI는 동일 엔진을 `mkm-life` 절입·원격 URL 등으로 사용(per-row MCP 비권장); 워크스페이스에 `projects/mkm/mkm-life` 없으면 배포본에서 확인 |
| 프로비넌스 헬퍼 (MCP 태그) | `tools/myeongni/manseryeok_provenance.py` → `precision_mcp_runtime_metadata()` | 근사 스텁과 구분되는 메타 블록 |
| B-track 파일럿 벤치 경로 상수 | `tools/myeongni/btrack_bench_paths.py` | canonical·direct·bootstrap JSONL 슬롯; 포인터 `CANONICAL_BENCH_POINTER_V1.json`과 짝; 계약 테스트 `tests/test_btrack_bench_paths.py` |
| 전세계 출생 (IANA) → 엔진 입력 | `scripts/saju_birth_resolver_v1.py`, CLI `scripts/run_saju_global_birth_v1.py`; 듀얼 검증 `scripts/saju_dual_verify.py --birth-instant-utc … --tz …`; 제품 `projects/mkm/mkm-life` `POST /api/v1/saju/verify` 본문 `birth_instant_utc` + `tz` | 권장: `birth_instant_utc` + `iana_tz` (DST 격리·왕복 검증); 스키마 `docs/final/artifacts/schemas/saju_global_birth_request_v1.schema.json` / `saju_global_birth_result_v1.schema.json`; 테스트 `tests/test_saju_birth_resolver_v1.py`, `tests/test_saju_dual_verify.py` |

#### 3.4.1 Postella 대조·후처리 체인 (워크스페이스 스크립트)

| 항목 | 경로 | 비고 |
|------|------|------|
| Postella 비교 리포트 | `scripts/run_manse_postella_comparison_report_v1.py` → `docs/final/artifacts/manse_postella_comparison_latest.json` | `--min-non-empty-per-field` evidence gate; Postella는 외부 참조로만 취급 |
| 원클릭 체인 (PowerShell) | `scripts/Invoke-MansePostellaPostValidationChainV1.ps1` | `-Reseed`, `-NoStandardDb`, `-Ours`/`-Postella` |
| 원클릭 체인 (Python, Linux/CI 패리티) | `scripts/run_manse_postella_post_validation_chain_v1.py` | 동일 단계 순서 |
| 트리아지·체크리스트·팩·reeval·후보 요약 | `scripts/run_manse_postella_mismatch_triage_v1.py`, `scripts/build_manse_postella_mismatch_checklist_v1.py`, `scripts/build_manse_postella_debug_packs_v1.py`, `scripts/run_manse_postella_debug_pack_reeval_perfect_v1.py`, `scripts/build_manse_postella_rule_fix_candidates_v1.py` | `postella.metadata.synthetic_hour_mismatch_injected` 시 합성 데모 불일치로 태깅·엔진 회귀 오해 방지 |
| 데모 시드 (엔진 정렬) | `scripts/seed_manse_postella_valid_samples_v1.py` | `PerfectManseryeok`로 ours 기둥 정렬 후 Postella 시주만 선택 주입 가능 |
| 회귀·CI | `tests/test_run_manse_postella_debug_pack_reeval_perfect_v1.py`, `tests/test_build_manse_postella_rule_fix_candidates_v1.py`, `tests/test_build_manse_postella_mismatch_checklist_v1.py`; `.github/workflows/manse-postella-chain-smoke.yml` | 관련 스크립트 경로 변경 시 트리거 |

### 3.5 사상(Sasang) 동역학 — 레짐 매핑 (B-track, 관측 전용)

| 항목 | 경로 | 비고 |
|------|------|------|
| JSON Schema | `docs/final/SASANG_DYNAMICS_REGIME_MAPPING_JSON_SCHEMA.json` | `machine_readables` 0..1 프록시 3종 필수; `a_track_autobind_forbidden` 반드시 true; 실매매·`dual_regime_api` 자동 합선 금지 |
| Ledger·검증 CLI | `scripts/sasang_dynamics_regime_mapping_ledger.py` | `validate-sample`, `append` |
| 샘플 JSONL | `data/sasang/sasang_dynamics_regime_mapping_v1.sample.jsonl` | 스텁·티어 B |
| 승격 후보 고정·판정 체인 (B-track) | `scripts/run_sasang12_promotion_candidate_freeze_v1.py`, `scripts/judge_sasang12_promotion_candidate_v1.py` → `docs/final/artifacts/sasang12_promotion_candidate_freeze_v1_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_gate_latest.json` | 주간 winner-rotation 비용 민감도(`weekly_rebalance_cost_sensitivity_latest.json`) 재현·PASS/FAIL 판정 전용; `promotion_to_a_track_allowed=false` 고정. 확장 관측(2025-10-01~2026-04-20): `sasang12_promotion_candidate_gate_2025-10-01_to_2026-04-20.json` = FAIL(누적 수익 델타 음수) |
| 승격 후보 고정·이중 게이트 체인 v2 (B-track) | `scripts/run_weekly_rebalance_cost_sensitivity_v2.py`, `scripts/run_sasang12_promotion_candidate_freeze_v2.py`, `scripts/judge_sasang12_promotion_candidate_v2.py` → `docs/final/artifacts/sasang12_promotion_candidate_freeze_v2_latest.json`, `docs/final/artifacts/weekly_rebalance_cost_sensitivity_v2_short_latest.json`, `docs/final/artifacts/weekly_rebalance_cost_sensitivity_v2_long_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_gate_v2_latest.json` | 병증약리/금화교역 후보식(정규화 0.85~1.15) winner-rotation + 단기·장기 동시 판정; 현재 `status=FAIL`; `promotion_to_a_track_allowed=false` 유지 |
| 승격 후보 고정·이중 게이트 체인 v3/v4 방어형 (B-track) | `scripts/run_sasang12_promotion_candidate_freeze_v3.py`, `scripts/run_sasang12_promotion_candidate_freeze_v4.py`, `scripts/judge_sasang12_promotion_candidate_v2.py`, `scripts/analyze_sasang12_gate_failure_v1.py`, `scripts/run_sasang12_gate_stability_3runs_v1.py` → `docs/final/artifacts/sasang12_promotion_candidate_gate_v3_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_gate_v4_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_failure_analysis_v4_latest.json`, `docs/final/artifacts/sasang12_gate_stability_3runs_v4_latest.json` | v3_defense/v4_ultra_defense(정규화 0.90~1.10) 모두 `status=FAIL`; 공통 실패축은 전 코스트 버킷 `sum_delta_mdd <= 0`; v4는 3회 안정성 `stable_3runs=true`; `promotion_to_a_track_allowed=false` 유지 |
| 승격 후보 스윕·고정 체인 v5 MDD 우선 (B-track) | `scripts/run_sasang12_v5_mdd_priority_sweep.py`, `scripts/run_sasang12_promotion_candidate_freeze_v5.py`, `scripts/judge_sasang12_promotion_candidate_v2.py`, `scripts/analyze_sasang12_gate_failure_v1.py`, `scripts/run_sasang12_gate_stability_3runs_v1.py` → `docs/final/artifacts/sasang12_v5_mdd_priority_sweep_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_freeze_v5_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_gate_v5_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_failure_analysis_v5_latest.json`, `docs/final/artifacts/sasang12_gate_stability_3runs_v5_latest.json` | v5_mdd_priority 스윕(정규화 0.90~1.10 / 0.92~1.08 / 0.94~1.06 + v4 비교) 후 `v5_mdd_priority_norm_0p94_1p06` 선택; gate는 `status=FAIL`이나 MDD 손상 폭은 v4 대비 축소, 3회 안정성 `stable_3runs=true`; `promotion_to_a_track_allowed=false` 유지 |
| 승격 후보 스윕·고정 체인 v6 선발규칙 실험 (B-track) | `scripts/run_sasang12_v6_mdd_first_sweep.py`, `scripts/run_sasang12_promotion_candidate_freeze_v6.py`, `scripts/run_weekly_rebalance_cost_sensitivity_v2.py`(`--winner-selector-mode`), `scripts/judge_sasang12_promotion_candidate_v2.py`, `scripts/analyze_sasang12_gate_failure_v1.py`, `scripts/run_sasang12_gate_stability_3runs_v1.py` → `docs/final/artifacts/sasang12_v6_mdd_first_sweep_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_freeze_v6_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_gate_v6_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_failure_analysis_v6_latest.json`, `docs/final/artifacts/sasang12_gate_stability_3runs_v6_latest.json` | 주간 승자선발 모드를 `cum_first`/`mdd_first`로 비교 스윕; 현재 최적은 `v5_mdd_priority_cum_first_norm_0p94_1p06`이며 gate는 `status=FAIL`; 3회 안정성 `stable_3runs=true`; `promotion_to_a_track_allowed=false` 유지 |
| 승격 후보 스윕·고정 체인 v7 패널티 점수식 실험 (B-track) | `scripts/run_sasang12_v7_penalized_selector_sweep.py`, `scripts/run_sasang12_promotion_candidate_freeze_v7.py`, `scripts/run_weekly_rebalance_cost_sensitivity_v2.py`(`--winner-selector-mode score_penalized`, `--winner-score-lambda`), `scripts/judge_sasang12_promotion_candidate_v2.py`, `scripts/analyze_sasang12_gate_failure_v1.py`, `scripts/run_sasang12_gate_stability_3runs_v1.py` → `docs/final/artifacts/sasang12_v7_penalized_selector_sweep_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_freeze_v7_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_gate_v7_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_failure_analysis_v7_latest.json`, `docs/final/artifacts/sasang12_gate_stability_3runs_v7_latest.json` | 패널티 선발식 `score = delta_mdd - λ·max(0,-delta_cum)`로 λ 스윕(0.5/1.0/2.0, plus baseline); 현재 최적은 baseline `cum_first`(`v5_mdd_priority_cum_first_l1p00_norm_0p94_1p06`)이며 gate `status=FAIL`; 3회 안정성 `stable_3runs=true`; `promotion_to_a_track_allowed=false` 유지 |
| 승격 후보 스윕·고정 체인 v8 MDD 직벌점 실험 (B-track) | `scripts/run_sasang12_v8_mdd_penalty_sweep.py`, `scripts/run_sasang12_promotion_candidate_freeze_v8.py`, `scripts/run_weekly_rebalance_cost_sensitivity_v2.py`(`--winner-score-mdd-penalty-lambda`), `scripts/judge_sasang12_promotion_candidate_v2.py`, `scripts/analyze_sasang12_gate_failure_v1.py`, `scripts/run_sasang12_gate_stability_3runs_v1.py` → `docs/final/artifacts/sasang12_v8_mdd_penalty_sweep_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_freeze_v8_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_gate_v8_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_failure_analysis_v8_latest.json`, `docs/final/artifacts/sasang12_gate_stability_3runs_v8_latest.json` | 선발식에 `- λ_mdd·max(0,-delta_mdd)` 직접 벌점 추가(`score = delta_mdd - λ_cum·max(0,-delta_cum) - λ_mdd·max(0,-delta_mdd)`); λ 스윕 후에도 최적은 baseline `cum_first`(`v5_mdd_priority_cum_first_lc1p00_lm1p00_norm_0p94_1p06`), gate `status=FAIL`; 3회 안정성 `stable_3runs=true`; `promotion_to_a_track_allowed=false` 유지 |
| 승격 후보 스윕·고정 체인 v9 구조식 확장 실험 (B-track) | `scripts/run_sasang12_v9_structural_formula_sweep.py`, `scripts/run_sasang12_promotion_candidate_freeze_v9.py`, `scripts/run_weekly_rebalance_cost_sensitivity_v2.py`(`v9_structural`), `scripts/judge_sasang12_promotion_candidate_v2.py`, `scripts/analyze_sasang12_gate_failure_v1.py`, `scripts/run_sasang12_gate_stability_3runs_v1.py` → `docs/final/artifacts/sasang12_v9_structural_formula_sweep_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_freeze_v9_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_gate_v9_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_failure_analysis_v9_latest.json`, `docs/final/artifacts/sasang12_gate_stability_3runs_v9_latest.json` | 구조식 후보(`structural_shield_v9`, `tail_guard_v9`, `mapping_target_capitulation_shield_v9`)와 baseline 동시 스윕; v9 gate는 `status=FAIL`이나 short/long `sum_delta_mdd` 음수 폭은 기존 v8 대비 축소(예: 20bps short -0.01719, long -0.02175); 3회 안정성 `stable_3runs=true`; `promotion_to_a_track_allowed=false` 유지 |
| 승격 후보 스윕·고정 체인 v10 저변동 캡 축소 (B-track) | `scripts/run_sasang12_v10_low_vol_cap_sweep.py`, `scripts/run_sasang12_promotion_candidate_freeze_v10.py`, `scripts/run_weekly_rebalance_cost_sensitivity_v2.py`(`v9_structural` + 정규화 0.95~1.03/0.96~1.02/0.97~1.01), `scripts/judge_sasang12_promotion_candidate_v2.py`, `scripts/analyze_sasang12_gate_failure_v1.py`, `scripts/run_sasang12_gate_stability_3runs_v1.py` → `docs/final/artifacts/sasang12_v10_low_vol_cap_sweep_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_freeze_v10_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_gate_v10_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_failure_analysis_v10_latest.json`, `docs/final/artifacts/sasang12_gate_stability_3runs_v10_latest.json` | v10 선택값은 `v9_structural_score_penalized_lc1p00_lm2p00_norm_0p97_1p01`; long window는 전 cost에서 core PASS(`sum_delta_cum>0`, `sum_delta_mdd>0`)로 전환됐으나 short window는 `sum_delta_cum<0`(전 cost) + `observed_max_loss_streak=5`로 FAIL; 전체 gate `status=FAIL`, 3회 안정성 `stable_3runs=true`; `promotion_to_a_track_allowed=false` 유지 |
| 벤치 대시보드 HTML (로컬 프리뷰) | `docs/final/artifacts/sasang_dynamics_proxy_widget_v1.html` | 내장 `SASANG_SAMPLE_SNAPSHOT`은 샘플 JSONL과 수동 동기화; `scripts/serve_sasang_dashboard.ps1`로 정적 서빙; 실매매·봇 미연결 |
| BTC 역사 앵커 스모크 (3행) | `data/sasang/sasang_dynamics_regime_mapping_v1.btc_anchor_smoke.jsonl` | 수동 프록시·가설 `[HYPO]`; `validate-sample --path …` |
| 단위 테스트 | `tests/test_sasang_dynamics_regime_mapping_ledger.py` | 스키마·프록시 구간 |

### 3.6 다중 렌즈 평가 하네스 V2 (Thin 템플릿, 동일 일자 슬롯)

| 항목 | 경로 | 비고 |
|------|------|------|
| 계약 JSON | `docs/final/artifacts/MULTILENS_EVAL_HARNESS_V2_THIN_CONTRACT.json` | 렌즈별 관측 슬롯·단일 PnL 강제 비단정; A-track 자동 융합 금지 |
| 검증용 날짜 목록 | `data/multilens_eval/curated_dates_v1.json` | `intent=repro_bench_grid_v1`(재현용 격자; 실시장 피처 파이프와 혼동 금지 — `intent_note` 참고) |
| 사상·명리 겹침 샘플 | `data/multilens_eval/sasang_curated_overlap_v1.jsonl`, `data/multilens_eval/myeongni_curated_overlap_v1.jsonl` | `curated_dates_v1` 10일과 동일 키로 정렬(전 행 채움); `--populate-default-samples` |
| 듀얼 레짐 입력 샘플 | `data/multilens_eval/dual_regime_curated_overlap_v1.json` | `evaluate_dual_regime_and_market_shock` kwargs; 동일 플래그로 `logos_dual_regime` 슬롯 채움 |
| 시장 OHLC/FGI 어댑터 v1 | `scripts/multilens_dual_regime_market_adapter_v1.py` → `data/multilens_eval/dual_regime_market_adapter_v1.json` | Binance 일봉 + Alternative.me FGI; `bible_risk_score=0`; Thin V2 `--dual-regime-json`로 교체 가능 |
| BTC 앵커 스모크 (3일) | `data/multilens_eval/curated_dates_btc_anchor_smoke_v1.json` → `data/multilens_eval/dual_regime_market_adapter_btc_anchor_smoke_v1.json` | `sasang_dynamics_regime_mapping_v1.btc_anchor_smoke.jsonl`과 동일 달력일; 네트워크 필요 |
| Thin 보고서 (BTC 앵커 스모크) | `data/multilens_eval/multilens_eval_v2_thin_report_btc_anchor_smoke_v1.json` | `eval_multilens_harness_v2_thin.py --populate-default-samples` + 위 어댑터·사상 JSONL |
| BTC 앵커 스모크 원클릭 | `scripts/run_btc_anchor_multilens_smoke.ps1` | 어댑터 → Thin 보고서 재생성(네트워크 필요) |
| 로컬 자동 체인 (Fact-Lock+B-Track 스모크) | `scripts/run_workspace_autopilot_chain.ps1` | `run_fact_lock_bundle` → 사상 `validate-sample`(샘플+btc_anchor) → `run_btc_anchor_multilens_smoke` → sasang·thin pytest. 선택: `-IncludeP1AB`, `-IncludeJemaaiCloudChecks`(MVP 파일·nginx 예시 존재 확인, **배포 아님**). |
| jemaai.cloud 융합 점검 (P1·쇼룸 경로) | `scripts/run_jemaai_cloud_completion_chain.ps1` | 위 autopilot에 P1 A/B(기본) + jemaai MVP 경로 검증 통합; `-SkipP1AB`로 P1 생략. **nginx/VPS 반영은 수동.** |
| 러너 | `scripts/eval_multilens_harness_v2_thin.py` | `--out`; `--populate-default-samples`로 B-track JSONL 병합; 채운 뒤 `summary`(cap 분포·사상-명리 `mapping_target` 일치 등) |
| 단위 테스트 | `tests/test_multilens_eval_harness_v2_thin.py` | 행 수·`lens_outputs` 키·`summary` 스팟 체크 |
| 운영(수동) | `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`, `scripts/sasang_dynamics_regime_mapping_ledger.py` | G: 마운트 후 Vault 동기화·사상 ledger `append`는 본선/로컬에서만 |
| 월간 체인 보조 스크립트 | `scripts/run_btc_time_machine_regime_switch_backtest.py`, `scripts/report_fused_paper_cycle_calibration_30.py`, `scripts/night_watchman_harness_v1.ps1` | 레짐 스위치 JSON 타임스탬프 갱신·교정 30 스냅샷·픽셀 Night Watchman(드라이런); B-track 품질 게이트 스텁 3종은 `run_btrack_gate_and_lock` 옵션 |

**Fact-Lock**: 16상태 확장 가설은 **트레이딩 엔진 합선 전** 본 JSONL·스키마로만 기록; `dual_regime_api.py`와의 연결은 별도 승인·PR에서 명시한다.

### 3.7 B-track 재조정 수집 완화 규칙 (연구 전용 carve-out)

**목적**: 과거 훈련 결과를 성경·사상·명리·게마트리아 4D 방식으로 재조정/재사용해도, 그 결과를 **B-track 연구 레이어에만 집적**하도록 운영 경계를 명시한다.

**허용 (B-track 한정):**

- 과거 훈련값의 4D 재매핑, 거리/유사도 기반 재스코어링, 가설성 prior(확률·전이행렬) 기록.
- 산출물 적재 위치: `reports/notebooklm/`, `docs/final/artifacts/` 하위의 연구 아티팩트.
- 모든 산출물은 `[HYPO]` 및 `research_only=true`, `promotion_required=true` 메타를 기본값으로 유지.

**금지 (A-track 격벽 유지):**

- `dual_regime_api.py`·OOF·실거래 엔진·레짐 캡으로의 자동 주입/자동 바인딩.
- 게마트리아 수치·재조정 prior의 본선 하드코딩.
- 재조정 결과를 단일 TOE/결정론적 예측식으로 단정하는 문구·운영.

**승격 조건 (변경 없음):**

- B-track 결과를 A-track에 반영하려면 §8 Promotion Loop(지휘관 승인 + PR + 경로/테스트 갱신)를 통과해야 한다.

---

## 4. Multi-Corpus Isolation Policy (평행 코퍼스)

**목적**: 정경(Logos 코어) SSOT와 사해(DSS)·70인역(LXX)·외경 등 **다른 전통**을 코드·데이터에서 혼동하지 않도록 격벽을 문서로 고정한다. 구절 간 유사도·교차 분석은 **참고 지표**일 수 있으나, 레짐·실매매 **트리거**로의 승격은 본 문서·코드북·PR에서만 허용한다.

### 4.1 레이어 정의

| 구분 | 역할 | 비고 |
|------|------|------|
| **Core (A-track)** | MT 기반 정경 31,102 구절 파이프라인 | SSOT: `data/logos/verse_4pipeline_full_31102.json` (§3.2) |
| **Satellites (B-track)** | DSS, LXX, 외경/위경 등 | **별도 파일·별 인덱스**; 코어와 row-level merge 금지 |

### 4.2 메타데이터·실행 격벽 (정책)

- 위성 코퍼스 레코드에는 출처 식별 필드를 강제한다 (예: `corpus_type` — `canonical` / `dss` / `apocrypha` / `pseudepigrapha`; `tradition` — `MT` / `LXX` / `Qumran` 등).
- 교차 분석·CLI는 **명시 옵션**(예: `--include-satellites`)이 없으면 **canonical만** 대상으로 한다.

### 4.3 단방향 산출물 (비침습)

- 위성 텍스트에서 16상·거리 등을 **측정**한 결과는 `LOGOS_STATE_MAPPING_V1.json` 등 코어 스냅샷을 **덮어쓰지 않고**, `CROSS_REF_*` 형태의 **독립 관측 리포트**로만 둔다.
- B-track 관측을 `dual_regime_api`·실매매 경로에 합선하려면 **별도 승인·PR**에서 명시한다 (§3.2·§8 Promotion Loop와 동일 취지).

### 4.4 구현 상태

| 항목 | 경로 | 비고 |
|------|------|------|
| 격벽 헬퍼 (canonical default guard) | `tests/multi_corpus_policy.py` | `iter_canonical_only`, `cross_ref_artifact_name` (CI 추적용; `tools/` 로컬 제외와 무관) |
| 위성 더미 (B-track 스모크) | `tests/fixtures/logos_satellite_dummy_one_verse.json` | 단일 구절; 코어와 병합 시 기본 가드에서 제외 |
| 단위 테스트 | `tests/test_multi_corpus_isolation_policy.py` | §4 정책 회귀 |

- DSS/LXX 등 전용 `verse_4pipeline_*.json` 또는 별 인덱스 **운영 경로**가 생기면 **본 표에 행을 추가**한다.

### 4.5 CROSS_REF 데이터 계약 (v1-Draft)

정경(A-track)과 위성(B-track)을 잇는 `CROSS_REF_*` 산출물은 **코어를 덮어쓰지 않는** 독립 아티팩트이며, 행 단위로 아래 **데이터 계약**을 따른다 (필드명은 JSON에서 `snake_case` 권장).

| 필드 | 의무 | 설명 |
|------|------|------|
| `canonical_ref` | 권장 | 정경 측 고유 식별자(예: `verse_id`). A-track만 연결할 때는 비울 수 없음. |
| `satellite_ref` | 권장 | 위성 측 고유 식별자(예: DSS 조각·외경 절 표기). |
| `corpus_type` | 필수 | `dss` / `apocrypha` / `pseudepigrapha` / `myeongni_probe` 등. |
| `link_type` | 권장 | 연결 성격: `thematic` / `lexical` / `geometric` / `temporal` / `analogy_bench` 등(열거형 문자열). |
| `confidence` | 선택 | 0.0–1.0 실험적 점수; **헌법에 수치 Prior를 고정하지 않음**. |
| `artifact_path` | 선택 | 근거·스냅샷 파일 경로(워크스페이스 상대 경로). |
| `rationale` / `notes` | 권장 | 사람이 읽는 근거·면책(가설·비유 한정 등). |
| `note` | 선택 | 행 단위 벤치 메타(예: NL 요약·반증 유형·맥락 오염 경고·[HYPO] 승격 보류); `rationale`과 별도로 박제할 때 사용. |

**확률·Prior 정책:** 마르코프 전이행렬·베이지안 사전분포 등 **수치 Prior는 본 헌법에 고정하지 않는다.** 해당 수치는 실험 결과물·연구 노트(`docs/final/` 하위, 별도 파일명)에만 존재할 수 있으며, A-track·실매매 경로로 올리려면 **Promotion Loop(§8)·별도 승인·PR**을 거친다.

**트래킹 아티팩트:** `docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json` — `schema: cross_ref_dss_to_states_draft_v2`; 행마다 `entry_id`, `canonical_ref`(정경 `verse_id`), `satellite_ref`, `corpus_type`, `link_type`, `state_candidate_id`, `rationale`; 선택 필드 `note`(벤치 메타·NL 반증 박제 등). `canonical_ref`는 **독립 해석이 아니라** `LOGOS_STATE_MAPPING_V1.json`의 동일 `state_id` 할당 `verse_id`와 기계적으로 맞춘 값(문서 상단 `canonical_join_ssot`·`canonical_join_note`). **JSON Schema:** `docs/final/CROSS_REF_DRAFT_V2_DOCUMENT.schema.json`. 회귀: `tests/test_cross_ref_dss_schema.py`. **CI:** `.github/workflows/dual-regime-integrity.yml`에서 위 테스트 실행(`jsonschema` 포함).


### 4.5.1 B-track Hypothesis Inventory (v1)

| 항목 | 경로 | 비고 |
|------|------|------|
| JSON Schema | docs/final/B_TRACK_HYPOTHESIS_INVENTORY_SCHEMA.json | draft-07; pillar, ontology_layer, lens_family, cross_links |
| 아티팩트 | docs/final/artifacts/B_TRACK_HYPOTHESIS_INVENTORY_V1.json | entries 배열; 비어 있어도 됨 |
| 생성기 | scripts/write_b_track_hypothesis_artifacts_once.py | 스키마·빈 인벤토리 재생성 |
| 검증 CLI | scripts/validate_b_track_hypothesis_inventory.py | py scripts/validate_b_track_hypothesis_inventory.py |
| 회귀 테스트 | `tests/test_b_track_hypothesis_inventory.py` | Draft7 + 최상위 계약 |

**cross_links 규칙:** target_artifact는 논리 이름(CROSS_REF_DSS_TO_STATES_DRAFT, SASANG_CROSS_REF_DRAFT, LOGOS_STATE_MAPPING_V1)으로 두고, 실제 파일은 각각 docs/final/artifacts/ 아래 동명 JSON과 수동 정합한다. 정경·위성·명리·사상 벤치 간 동일시(identity) 주장은 기본 금지(equivalence_claim이 true인 경우만 별도 승격 검토). A-track·실매매 기본 로딩 금지(4.1-4.3).

### 4.6 중간 레이어 다중 렌즈 (작업 순서)

격벽을 유지한 채 B-track 아티팩트·CI·문서 정합을 점검하는 **체크리스트**는 `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md`에 둔다. 단일 TOE 완성 선언이 아니라, **관측·벤치·인터페이스 스텁**의 재현 가능성을 올리는 절차다. `btrack_phase3_cross_ref_snapshot.md` 코드펜스는 SSOT JSON과 어긋날 경우 `scripts/sync_btrack_phase3_snapshot_json_fence.py --apply`로 맞춘 뒤 `tests/test_cross_ref_dss_schema.py`로 검증한다.

### 4.7 Aramaic Cross-Reference Graph MVP (B-track, 관측 전용)

| 항목 | 경로 | 비고 |
|------|------|------|
| Aramaic 코퍼스 추출 | `scripts/extract_aramaic_core_corpus_v1.py` → `reports/constitution/btrack_pilot/aramaic_core_corpus_v1.jsonl` | 다니엘/에스라 아람어 핵심 구간 추출(연구 레인) |
| 토큰 정규화 | `scripts/normalize_aramaic_tokens_v1.py` | lemma-lite 규칙(접두 제거 보수형) |
| 노드 스키마 | `docs/final/schemas/aramaic_graph_node_v1.schema.json` | `schema: aramaic_graph_node_v1`, `source_track=B` 고정 |
| 엣지 스키마 | `docs/final/schemas/aramaic_graph_edge_v1.schema.json` | 6개 타입(`timeline_anchor`, `causal_precursor`, `fulfillment`, `recurrence`, `contrast_inversion`, `cross_lens_confirm`) |
| 점수 스키마 | `docs/final/schemas/aramaic_regime_shift_score_v1.schema.json` | `schema: aramaic_regime_shift_score_v1`, signal label 포함 |
| 노드 빌더 | `scripts/build_aramaic_graph_nodes_v1.py` → `docs/final/artifacts/aramaic_graph_nodes_v1.jsonl` | 아람어 노드 생성 |
| 엣지 빌더 | `scripts/build_aramaic_graph_edges_v1.py` → `docs/final/artifacts/aramaic_graph_edges_v1.jsonl` | 관계 타입별 엣지 생성 |
| 교차 코퍼스 브리지 빌더 | `scripts/build_aramaic_cross_corpus_bridge_v1.py` → `docs/final/artifacts/aramaic_cross_corpus_bridge_nodes_v1.jsonl`, `docs/final/artifacts/aramaic_cross_corpus_bridge_edges_v1.jsonl` | 아람어 노드와 히브리(BHS)/헬라(SBLGNT) 후보 구절의 4D 유사도 기반 브리지 엣지 생성 |
| 의미 그래프 빌더 (구절-테마-레짐상태) | `scripts/build_bible_meaning_graph_v1.py` → `docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl`, `docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl` | 교차참조 엣지와 태그를 융합해 `verse ↔ theme ↔ regime_state` 3자 네트워크 생성 |
| 의미 통찰 후보 추출기 | `scripts/extract_bible_meaning_insight_candidates_v1.py` → `docs/final/artifacts/bible_meaning_insight_candidates_latest.json` | 허브 구절·레짐 반복 군집·top-k 추론 경로 후보를 자동 추출 |
| 통찰 생존 평가 | `scripts/build_insight_survivor_eval_v1.py` → `docs/final/artifacts/insight_survivor_eval_latest.json` | raw 통찰 후보를 `drawdown_avoidance / false_positive_cost / walkforward_repro` 지표로 평가 |
| 통찰 생존 선발 | `scripts/select_insight_survivor_candidates_v1.py` → `docs/final/artifacts/insight_survivor_candidates_latest.json` | 평가 결과 중 임계치 통과 후보만 survivor로 선발(상위 N 제한) |
| 의미 연결 품질 리포트 | `scripts/report_aramaic_semantic_edge_quality_v1.py` → `docs/final/artifacts/aramaic_semantic_edge_quality_latest.json` | 토큰 겹침·공유 근거 비율·엣지 타입별 의미 밀도 요약 |
| 레짐 쉬프트 점수 | `scripts/score_aramaic_regime_shift_v1.py` → `docs/final/artifacts/aramaic_regime_shift_score_latest.json` | 기본 가중치 + `cross_lens_single_trigger_blocked` 제약 |
| 통찰 신호 보조 반영 | `score_aramaic_regime_shift_v1.py --include-insight-signal --insight-json docs/final/artifacts/bible_meaning_insight_candidates_latest.json` | `insight_candidates`(허브/군집/경로) 밀도를 보조 신호로 반영해 shadow 기준 점수 재계산(연구 레인) |
| 통찰 캡 버킷 임계치 스윕 | `scripts/sweep_aramaic_insight_cap_bucket_thresholds_v1.py` → `docs/final/artifacts/aramaic_insight_cap_bucket_threshold_sweep_latest.json` | audit log 기반으로 `mid/high` 임계치와 low/mid/high cap 조합을 스윕해 추천 후보 산출 |
| 통찰 캡 버킷 임계치 적용 | `scripts/apply_aramaic_insight_cap_bucket_threshold_recommendation_v1.py` → `docs/final/artifacts/aramaic_insight_cap_bucket_threshold_recommended_latest.json` | 스윕 best 후보를 점수/섀도우 실행 인자로 승격 |
| 통찰 캡 임계치 히스토리 | `scripts/report_aramaic_insight_cap_threshold_history_v1.py` → `reports/ops/aramaic_insight_cap_bucket_threshold_history.jsonl` | 추천 임계치 스냅샷을 실행 이력으로 누적 |
| 통찰 캡 임계치 드리프트 경보 | `scripts/alert_aramaic_insight_cap_threshold_drift_v1.py` → `docs/final/artifacts/aramaic_insight_cap_bucket_threshold_drift_alert_latest.json` | 최근 추천값 변화량이 임계치를 넘으면 경보 산출 |
| 가중치 스윕 | `scripts/run_aramaic_regime_shift_weight_sweep_v1.py` → `docs/final/artifacts/aramaic_regime_shift_weight_sweep_latest.json` | B-track 튜닝; `cross_lens_confirm` helper cap 유지 |
| 브리지 계수 추천 적용 | `scripts/apply_aramaic_regime_shift_bridge_coef_recommendation_v1.py` → `docs/final/artifacts/aramaic_regime_shift_bridge_coef_recommended_latest.json` | 스윕 best 후보의 `bridge_lang_coef`를 일일 점수 반영용 추천 아티팩트로 승격 |
| 브리지 계수 주간 스케줄 등록 | `scripts/register_aramaic_mvp_bridge_coef_weekly_task.ps1` | 계수 스윕+추천 적용 주간 자동화 등록(dry-run 기본) |
| 브리지 계수 주간 스케줄 readiness | `scripts/verify_aramaic_mvp_bridge_coef_weekly_task_readiness.ps1` → `docs/final/artifacts/aramaic_mvp_bridge_coef_weekly_task_readiness_latest.json` | 스크립트 존재/Task action/LastTaskResult 점검 |
| Shadow 비교 리포트 | `scripts/run_aramaic_regime_shift_shadow_compare_v1.py` → `docs/final/artifacts/aramaic_regime_shift_score_best_weight_latest.json`, `docs/final/artifacts/aramaic_regime_shift_shadow_compare_latest.json` | baseline vs best-weight 동시 산출(자동 승격 금지) |
| 원클릭 체인 | `scripts/run_aramaic_mvp_chain_v1.ps1` | Aramaic·meaning graph·Two-Track·학술/반증·raw OOS·public-safe까지 직렬 실행; 후반 제출 스택 **`[28/37]`–`[37/37]`** 및 산출물 요약은 동 표 **「체인 통합 실행」** 행 참조. |
| 일일 스케줄 등록 | `scripts/register_aramaic_mvp_daily_task.ps1` | 기본 dry-run; `-Apply` 시 `run_aramaic_mvp_now_with_audit.ps1` 기준 Task Scheduler 등록 (`-NoWebhook` 지원) |
| 일일 스케줄 readiness 점검 | `scripts/verify_aramaic_mvp_daily_task_readiness.ps1` → `docs/final/artifacts/aramaic_mvp_task_readiness_latest.json` | 태스크 존재·Action 경로·최근 실행 결과 점검 (`-Strict` 시 실패 exit 1, `-ExpectNoWebhook` 옵션) |
| 즉시 실행 + 감사 로그 | `scripts/run_aramaic_mvp_now_with_audit.ps1` → `reports/ops/aramaic_mvp_run_audit_log.jsonl` | 즉시 체인 실행 후 readiness 갱신·점수 델타 로그 append (`-NoWebhook`로 알림 전송 차단) |
| Raw OOS 실측 누적 배치 러너 | `scripts/run_aramaic_raw_oos_audit_accumulator_v1.ps1` | `run_aramaic_mvp_now_with_audit.ps1`를 반복 실행해 audit run을 목표치(`TargetAuditRuns`)까지 누적하고, 각 반복마다 raw OOS ingest/readiness를 재계산한다. |
| 감사 추세 리포트 | `scripts/report_aramaic_mvp_audit_trend_v1.py` → `docs/final/artifacts/aramaic_mvp_audit_trend_latest.json` | 최근 실행 창 평균/최대/최소/라벨 히스토그램 요약 |
| 추세 경보 규칙 | `scripts/alert_aramaic_mvp_trend_v1.py` → `docs/final/artifacts/aramaic_mvp_trend_alert_latest.json` | 연속 `alert/critical` streak 평가 후 웹훅(`ARAMAIC_MVP_ALERT_WEBHOOK_URL` 또는 `OPS_ALARM_WEBHOOK_URL`) 전송 |
| 경보 임계값 스윕 | `scripts/sweep_aramaic_mvp_alert_thresholds_v1.py` → `docs/final/artifacts/aramaic_mvp_alert_threshold_sweep_latest.json` | streak(예: 3/4/5)별 trigger rate 비교 |
| 추천 임계값 적용 | `scripts/apply_aramaic_mvp_alert_threshold_recommendation_v1.py` → `docs/final/artifacts/aramaic_mvp_alert_threshold_recommended_latest.json` | 스윕 결과의 추천 streak를 활성 아티팩트로 승격 |
| 임계값 주간 스케줄 등록 | `scripts/register_aramaic_mvp_threshold_weekly_task.ps1` | 기본 dry-run; `-Apply` 시 sweep→apply 주간 태스크 등록 |
| 임계값 주간 readiness 점검 | `scripts/verify_aramaic_mvp_threshold_weekly_task_readiness.ps1` → `docs/final/artifacts/aramaic_mvp_threshold_weekly_task_readiness_latest.json` | 태스크 존재·Action 명령·최근 실행 결과 점검 |

**격벽 규칙:** 본 절 산출물은 `research_only=true`, `promotion_required=true`, `source_track=B`를 유지하며 A-track·실매매 자동 트리거 경로로 합선하지 않는다.

---

## 5. 코드북 템플릿 (Dual-track)

| 항목 | 경로 | 비고 |
|------|------|------|
| 마스터 템플릿 | `docs/final/master_codebook_dual_track.template.json` | `source_refs.constitution_inference` → 본 문서 |

---

## 6. 테스트 (저장소 기준)

| 항목 | 경로 |
|------|------|
| Dual-regime 스모크 | `projects/bitcoin-trading/tests/test_dual_regime_api_smoke.py` |
| 다중 렌즈 평가 V2 thin 템플릿 | `tests/test_multilens_eval_harness_v2_thin.py` |
| Thin V2 시장 OHLC/FGI 어댑터 v1 | `tests/test_multilens_dual_regime_market_adapter_v1.py` |
| Logos–명리 매핑 스냅샷 | `tests/test_logos_state_mapping_v1_snapshot.py` |
| §4 평행 코퍼스 격벽 | `tests/test_multi_corpus_isolation_policy.py` |
| §4.5 CROSS_REF DSS 초안 | `tests/test_cross_ref_dss_schema.py` |
| §4.5.1 B-track Hypothesis Inventory | `tests/test_b_track_hypothesis_inventory.py` |
| ENTRY_16 소스 헌트 로그 계약 | `tests/test_entry16_source_hunt_log.py` |
| ENTRY_16 소스 헌트 요약 계약 | `tests/test_entry16_source_hunt_summary.py` |
| ENTRY_16 승격 게이트 계약 | `tests/test_entry16_promotion_gate.py` |
| 사상 벤치(SASANG ↔ 명리 앵커) | `tests/test_sasang_cross_ref_draft.py` |
| §3.3 명리 통찰 관측 JSONL·융합 스텁 | `tests/test_myeongni_insight_observation_log.py` |
| §3.3 명리 퓨전 스크립트 스모크 | `tests/test_myeongri_fusion_scripts_smoke.py` |
| Aramaic 그래프 스키마 계약 | `tests/test_aramaic_graph_schema_v1.py` |
| Aramaic 엣지 생성기 스모크 | `tests/test_aramaic_edge_builder_v1.py` |
| Aramaic 레짐 점수 계약 | `tests/test_aramaic_regime_shift_score_v1.py` |
| Aramaic 의미 연결 품질 리포트 계약 | `tests/test_aramaic_semantic_edge_quality_v1.py` |
| Aramaic 교차 코퍼스 브리지 계약 | `tests/test_build_aramaic_cross_corpus_bridge_v1.py` |
| Bible 의미 그래프 스키마 계약 | `tests/test_bible_meaning_graph_schema_v1.py` |
| Bible 의미 그래프 빌더 계약 | `tests/test_build_bible_meaning_graph_v1.py` |
| Bible 의미 통찰 후보 추출 계약 | `tests/test_extract_bible_meaning_insight_candidates_v1.py` |
| 통찰 생존 평가 계약 | `tests/test_build_insight_survivor_eval_v1.py` |
| 통찰 생존 선발 계약 | `tests/test_select_insight_survivor_candidates_v1.py` |
| 통찰 캡 버킷 임계치 스윕 계약 | `tests/test_sweep_aramaic_insight_cap_bucket_thresholds_v1.py` |
| 통찰 캡 버킷 임계치 적용 계약 | `tests/test_apply_aramaic_insight_cap_bucket_threshold_recommendation_v1.py` |
| 통찰 캡 임계치 히스토리 계약 | `tests/test_report_aramaic_insight_cap_threshold_history_v1.py` |
| 통찰 캡 임계치 드리프트 경보 계약 | `tests/test_alert_aramaic_insight_cap_threshold_drift_v1.py` |
| Aramaic 가중치 스윕 계약 | `tests/test_aramaic_regime_shift_weight_sweep_v1.py` |
| Aramaic shadow 비교 계약 | `tests/test_aramaic_regime_shift_shadow_compare_v1.py` |
| Aramaic 감사 추세 리포트 계약 | `tests/test_report_aramaic_mvp_audit_trend_v1.py` |
| Aramaic 추세 경보 계약 | `tests/test_alert_aramaic_mvp_trend_v1.py` |
| Aramaic 즉시실행 no-webhook 패스스루 | `tests/test_run_aramaic_mvp_now_with_audit_passthrough_v1.py` |
| Aramaic 경보 임계값 스윕 계약 | `tests/test_aramaic_mvp_alert_threshold_sweep_v1.py` |
| Aramaic 브리지 계수 추천 적용 계약 | `tests/test_apply_aramaic_regime_shift_bridge_coef_recommendation_v1.py` |
| 다중 렌즈 중간 레이어 절차 | `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` |

---

## 7. 데이터 부재 / 확인 필요 (단정 금지)

**확인됨 (명리 융합 스키마 SSOT)**:

- **`MYEONGNI_FUSION_DECISION_JSON_SCHEMA`**: `docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` — JSON Schema (draft-07) for one line of `myeongri_decision_ledger_YYYYMMDD.jsonl`. 구현: `projects/bitcoin-trading/ops/v2/memory/decision_ledger.py` → `append_myeongri_decision_ledger`.

다음은 **명칭·SITREP·기획서에 등장할 수 있으나**, 현재 워크스페이스 스냅샷에서 **단독 아티팩트로 확인되지 않음**:

- **`test_fusion_slice_gate.py`**: `projects/bitcoin-trading` 하위에서 미발견.

**NotebookLM → 공유 vault 미러(구현 확인됨)** — §7 “미확인” 목록과 혼동 금지:

| 항목 | 경로 | 비고 |
|------|------|------|
| 동기화 스크립트 | `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1` | 저장소 루트 `scripts\` |
| 오케스트레이터 호출 | `projects/bitcoin-trading/ops/v2/reports/run_notebooklm_sync.ps1` | `C:\workspace\scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1` 실행 |
| 대상 vault(로컬에서 G: 마운트 시) | `G:\공유 드라이브\MKM_DATA_VAULT\vault\notebooklm_sources\` | SSOT `docs/NotebookLM_sources_manifest.md`와 `$SourceFiles`/`$SourceDirs` 동기화 유지 |
| 실행 없이 계획만 | `-WhatIf` | 매니페스트 기반 복사 예정 나열 |
| 최소 간격 우회(오케스트레이터) | `run_notebooklm_sync.ps1 -Force` | `scheduled_guard` 최소 간격 무시·즉시 1회. 수동 재시도·테스트용; 일상 스케줄은 `-Force` 없이 |
| vault 미사용/미마운트 | — | 실제 복사 없음 또는 오류 종료(스크립트 동작에 따름) |

---

## 8. Promotion Loop (연구 → 제품)

1. **B(연구)** NotebookLM·노트에서 가설 도출.
2. **지휘관**이 스키마/코드북 반영 승인.
3. **A(제품)** 본 문서·`master_codebook_dual_track.template.json`·실제 `*.py` 경로를 갱신한 뒤에만 엔진 하드코딩.

### 8.1 Bio Sasang × 논문 SNP 사이드카 (경계 팩트, DNA×사상 통합)

**목적:** NotebookLM·초안의 **유전자–체질 매핑 표**를 본 문서에 **사실로 승격하지 않는다**. 아래는 **호출 가능한 스크립트·산출물·금지 규칙**만 고정한다.

| 항목 | 경로 | 비고 |
|------|------|------|
| 라벨 추출·PubMed·fulltext·EPMC 주석 | `scripts/extract_bio_measured_labels_from_sasang_papers_v1.py`, `scripts/enrich_bio_measured_labels_with_pubmed_v1.py`, `scripts/enrich_bio_measured_labels_with_fulltext_v1.py`, `scripts/enrich_bio_measured_labels_with_epmc_annotations_v1.py` | `tmp/bio_measured_labels_consolidated_v2.csv` 등 |
| Europe PMC 카탈로그 + PMID 병합 | `scripts/build_bio_epmc_sasang_genetics_catalog_v1.py`, `scripts/merge_bio_catalog_refsnp_into_measured_labels_v1.py`, `scripts/run_bio_epmc_catalog_and_label_merge_v1.py` | `tmp/bio_measured_labels_consolidated_v3.csv` — 러너에서 `--with-sidecar` 후 선택적으로 `--apply-sidecar-to-samples --apply-samples-csv … --apply-mapping-csv …`; 커버리지 선검사 `--apply-mapping-coverage-min`(0 초과 시 strict, 미달 exit **2**) |
| PMID 단위 SNP 사이드카 JSON | `scripts/export_bio_measured_labels_paper_snp_sidecar_v1.py` → `docs/final/artifacts/bio_measured_labels_paper_snp_sidecar_v1.json` | **키는 PMID(논문)** — FireProt 등 **`sample_id` 코호트와 자동 1:1 매칭 불가** |
| DNA readiness 체인(실행) | `scripts/run_bio_dna_readiness_chain_v1.py`, `scripts/build_bio_dna_promotion_readiness_v1.py` | 입력: 코호트 CSV + 지노타입 CSV + 매핑 커버리지 리포트. 산출: `reports/bio_dna_promotion_readiness_v1_latest.json` |
| DNA 임계값 스윕 | `scripts/run_bio_dna_promotion_threshold_sweep_v1.py` | 산출: `reports/bio_dna_promotion_threshold_sweep_v1_latest.json`; `passing/total`은 정책 조합 통과 수 |
| DNA A/B 자동평가 | `scripts/run_bio_dna_ab_autobuild_and_eval_v1.py` | 산출: `reports/bio_dna_ab_holdout_eval_v1.json`, `reports/bio_dna_ab_autobuild_report_v1.json` |
| DNA neutral seed 안정성 | `scripts/run_bio_dna_ab_neutral_seed_stability_v1.py` | 산출: `reports/bio_dna_ab_neutral_seed_stability_v1.json`, `reports/bio_dna_ab_neutral_seed_stability_v1.csv` |
| **조인 게이트** | `scripts/spec_bio_sample_paper_snp_join_gate_v1.py` | 매핑 CSV(`sample_id`+`pmid`) 없이 PMID 사이드카를 샘플 행에 붙이려 하면 **exit 2** (`--explain-only`로 정책 출력) |
| **사이드카→샘플 적용** | `scripts/apply_bio_paper_snp_sidecar_to_samples_v1.py` | 게이트(`check_join_gate`) 통과 후 매핑으로 `paper_pmid`, `paper_snp_ids_final_v3` 등 컬럼 추가; 기본 리포트 `reports/bio_paper_snp_sidecar_sample_join_v1_latest.json` |
| **v3→JSON→샘플(EPMC 제외)** | `scripts/run_bio_paper_snp_sidecar_export_and_apply_v1.py`, `scripts/Run-BioPaperSnpSidecarExportAndApply.ps1` | `export_*_sidecar` + `apply_*` 연쇄; 선택 `--mapping-coverage-min`(0 초과 시 선행 커버리지 strict, 미달 exit **2**); PS1은 `-MappingCoverageMin` 또는 단축 `-StrictMappingCoverage95` |
| **sample↔PMID 매핑 추출** | `scripts/export_bio_sample_paper_pmid_mapping_from_cohort_v1.py` | 코호트에 **이미 있는** `paper_pmid`(또는 `pmid`) 열만 사용; 수동 편집 템플릿 `docs/final/artifacts/bio_sample_paper_pmid_mapping_template_v1.csv` |
| **매핑 커버리지(선행 점검)** | `scripts/check_bio_paper_snp_mapping_coverage_v1.py` | 코호트 `sample_id` 대비 매핑에 PMID가 있는 비율·JSON 리포트 기본 `reports/bio_paper_snp_mapping_coverage_v1_latest.json`; `--strict` 시 미달 exit **2** |
| **실제 지노타입 교차(샘플 rsid)** | `scripts/check_bio_genotype_paper_snp_overlap_v1.py` | `apply` 결과(`paper_snp_ids_final_v3`)와 샘플별 지노타입 `rsid`를 교차해 `dna_paper_snp_match_count/ratio` 산출; 기본 리포트 `reports/bio_genotype_paper_snp_overlap_v1_latest.json` |
| **지노타입 long 정규화(ingest)** | `scripts/normalize_bio_genotype_long_v1.py` | 다양한 입력 CSV(`rsid`/`rsid_list`)를 표준 `sample_id,rsid,genotype` long 포맷으로 정규화; 기본 리포트 `reports/bio_genotype_normalize_long_v1_latest.json` |
| **DNA 승격 준비 게이트(리포트)** | `scripts/build_bio_dna_promotion_readiness_v1.py` | 매핑 커버리지·유효 타깃 수·교차 매치 행 수 임계값으로 `promotion_candidate_ready` 판정; `--strict` 미달 시 exit **2** |
| **DNA 준비 체인(원클릭)** | `scripts/run_bio_dna_readiness_chain_v1.py` | `normalize_bio_genotype_long_v1.py` → `check_bio_genotype_paper_snp_overlap_v1.py` → `build_bio_dna_promotion_readiness_v1.py` 직렬 실행; 선택 `--run-threshold-sweep`로 정책 스윕 생성, `--strict-readiness` 지원 |
| **DNA 승격 임계값 스윕** | `scripts/run_bio_dna_promotion_threshold_sweep_v1.py` | 커버리지·타깃 행·매치 행 임계값 그리드를 전수 평가해 `recommended_policy` 산출; 기본 `reports/bio_dna_promotion_threshold_sweep_v1_latest.json` |
| **DNA A/B 자동빌드·홀드아웃 평가** | `scripts/run_bio_dna_ab_autobuild_and_eval_v1.py` | `--use-blind-replay-profiles` 시 answer key + 프로파일(A/B/C/D/DS) 병합으로 확장 평가셋 생성 후 holdout+bootstrap 실행; 기준 baseline 정책은 운영 판정 시 `neutral` 고정 |
| **DNA A/B neutral 다중-seed 안정성** | `scripts/run_bio_dna_ab_neutral_seed_stability_v1.py` | `neutral` 고정으로 seed 반복 실행해 `promotion_ready_rate`·`ci_low` 분포 요약(`reports/bio_dna_ab_neutral_seed_stability_v1.json/.csv`) |
| **지노타입-코호트 커버리지 리포트** | `scripts/report_bio_genotype_cohort_coverage_v1.py` | 코호트 `sample_id` 대비 지노타입 `sample_id` 매칭률·누락 수 집계; 누락 템플릿 기본 `tmp/bio_genotype_missing_sample_template_v1.csv` 생성 |
| **합성 지노타입 생성(E2E 전용)** | `scripts/generate_bio_synthetic_genotype_from_missing_template_v1.py` | 누락 템플릿 기반 합성 `sample_id,rsid,genotype` 생성; 리포트에 `research_only=true`, `promotion_forbidden=true` 기록 |
| **누락 보강 + readiness 원클릭 체인** | `scripts/run_bio_genotype_missing_fill_chain_v1.ps1` | 커버리지 리포트 → (선택 `-SyntheticMode`) 합성 지노타입 생성 → DNA readiness chain 연쇄; `-RunThresholdSweep`/`-StrictReadiness` 지원 |

**격벽 (Fact-Lock):**

1. **코호트 A vs 원전·Proxy B:** `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` — B를 본선 분류·204 OOF·자동 합선하지 않는다.
2. **체질↔SNP 클러스터 고정표:** 검증된 재현 파이프와 코호트 계약이 없으면 **`[HYPO]`**로만 다룬다; **본 §8.1 표에 유전자명–태음/소양 등 매핑을 넣지 않는다.**
3. **신뢰 가중치 배수 (예: 설문 대비 DNA 2.5×):** 헌법 상수로 고정하지 않으며, **스윕·홀드아웃 리포트**가 있기 전에는 코드/설정 실험 분기로만 둔다.
4. **합성 데이터 경계:** `generate_bio_synthetic_genotype_from_missing_template_v1.py` 산출은 **E2E 파이프라인 검증 전용**이다. `ready=True`/`passing`이 나오더라도 **실측·운영 승격 근거로 사용하지 않는다**.
5. **지표 정의 고정:** `threshold_sweep`의 `passing/total`은 **정책 조합 통과 수**이며, SNP per-sample 매칭률(`dna_paper_snp_match_ratio` 등)과 동일 의미로 해석하지 않는다.

---

## 9. NotebookLM 매니페스트·이제마 B 인벤토리 (저장소 확인됨)

공유 vault(`G:\…\vault\notebooklm_sources\`)로의 파일 미러·스크립트 호출 관계는 **§7 표**에 고정한다.

| 항목 | 경로 | 비고 |
|------|------|------|
| 소스 목록 SSOT | `docs/NotebookLM_sources_manifest.md` | `## 이제마_B_Track` — 동기화 후보·미배치·근접 참조 표 |
| 인벤토리 디렉터리 | `data/corpus/ijeoma/_inventory/` | 개별 파일명은 **매니페스트 표와 동일**하게 유지·갱신 |
| SASANG 벤치 초안 | `docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json` | `schema: sasang_cross_ref_draft_v1`; 청크↔`state_candidate_id` 가설 행; 처방·dual_regime 합선 금지; 회귀: `tests/test_sasang_cross_ref_draft.py` |
| 한의 원전 인수인계(문서명) | `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` | **현재 스냅샷에 해당 파일명 없음** — A/B 분리 원칙은 `docs/NotebookLM_sources_manifest.md` §이제마_B_Track 문단으로 인용 |
| 작전지휘부 NotebookLM | ID `347e5cbe-0ade-4615-9aac-8747d4fa644e` | 2026-03-29 `notebook_get`: `source_count` 216 |
| `OPS_ONEPAGE_STATUS_LATEST.md` | — | NotebookLM 소스 **제목**으로 존재 가능; 워크스페이스 `docs/final/OPS_ONEPAGE_STATUS_LATEST.md` **미존재** — vault 미러에는 동기화 대상에 포함되지 않을 수 있음. 상세는 `docs/NotebookLM_sources_manifest.md` §작전지휘부 |

---

## 10. 통일장(UFT) 엔진 (경로 팩트만)

| 항목 | 경로 | 비고 |
|------|------|------|
| CPU 엔진 | `tools/core/unified_field_theory_engine.py` | import·단위 테스트에서 경로 확인 시 본 행 인용 |
| GPU 변형 | `tools/core/unified_field_theory_engine_gpu.py` | 동일 |

---

## 11. P1 A/B Balanced Weights (Operational Anchor)

| 항목 | 경로 | 비고 |
|------|------|------|
| P1 A/B 실행기 | `scripts/run_p1_efficiency_ab.py` | `--profile efficiency_first|intensity_first|balanced` |
| 효율 프로파일 산출물 | `docs/final/artifacts/MULTILENS_P1_AB_EFFICIENCY_V1.json` | `schema: multilens_p1_ab_efficiency_v1` |
| 강도 프로파일 산출물 | `docs/final/artifacts/MULTILENS_P1_AB_INTENSITY_V1.json` | `schema: multilens_p1_ab_intensity_v1` |
| 균형 프로파일 산출물 | `docs/final/artifacts/MULTILENS_P1_AB_BALANCED_V1.json` | `schema: multilens_p1_ab_balanced_v1` + `balanced_weights` |
| 최종 선정 리포트 | `docs/final/artifacts/MULTILENS_P1_AB_FINAL_SELECTION_V1.json` | `scripts/report_p1_final_selection.py` 생성 |

**Operational Anchor (default):**

- `balanced_weights.w_saving = 0.45`
- `balanced_weights.w_fidelity = 0.45`
- `balanced_weights.w_drop_penalty = 0.10`
- `balanced_weights.formula = w_saving*saving + w_fidelity*avg_jaccard - w_drop_penalty*min(drop_pp/divisor,1)`

**Change gate (Fact-Lock):**

1. 가중치 변경 전·후로 `efficiency/intensity/balanced` 3프로파일을 동일 입력(`MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json`)에서 재실행한다.
2. 변경 사유와 `best_candidate` 변화, `passing_count`, `gate_contract` 차이를 `MULTILENS_P1_AB_FINAL_SELECTION_V1.json`에 기록한다.
3. 본 절(§11)과 산출물의 `balanced_weights`가 불일치하면 문서를 먼저 갱신하고 실행 결과를 재생성한다.

---

**상태**: 초기 SSOT 고정 (2026-03-29). §7 NotebookLM→vault 표·§9 추가 (2026-03-29). §9 작전지휘부·OPS_ONEPAGE 갭·§10 UFT 경로 (2026-03-29). §3.1 16-상태 실험 JSONL·경로 팩트 (2026-03-29). **§4 평행 코퍼스 격벽 정책** (2026-03-30). `tests/multi_corpus_policy.py`·격벽 테스트 (2026-03-30). **§2.1 dual-regime 하이브리드·16상 미연동 팩트** (2026-03-30). **§1.1 Multi-Lens·TOE 비단정** (2026-03-30). **§4.5 CROSS_REF 데이터 계약·Prior 비고정** (2026-03-30). `CROSS_REF_DSS_TO_STATES_DRAFT.json` v2·테스트 정합 (2026-03-30). `CROSS_REF_DRAFT_V2_DOCUMENT.schema.json`·jsonschema 검증 (2026-03-30). CROSS_REF `canonical_ref` ↔ `LOGOS_STATE_MAPPING_V1` 정합 (2026-03-30). ENTRY_06 DSS 페셔·`run_prophecy_alignment_pytest.ps1` 워크스페이스 Fact-Lock (2026-03-30). **CROSS_REF 초안 16행** (LOGOS `state_id` 1–16 전수·ENTRY_11 `analogy_bench`·ENTRY_12–16 DSS 보강)·`link_type`(thematic/temporal/analogy_bench/lexical) 분류·`P0_COMMERCIALIZATION_TRACKER` Step4 직렬 게이트 (2026-03-30). 경로가 바뀌면 본 파일을 먼저 수정한다. **§4.5** `note` 행·스키마 선택 필드·ENTRY_11 NL v2.1 반증 박제 (2026-03-30). **`SASANG_CROSS_REF_DRAFT.json`**·`test_sasang_cross_ref_draft.py`·`run_prophecy_alignment_pytest` 번들·CI 단계 (2026-03-30). **§3.3** `MYEONGRI_INSIGHT_SSOT.md`·관측 JSONL·`MYEONGNI_FUSION_INTERFACE_STUB.json`·`test_myeongni_insight_observation_log.py` (2026-03-30). **§4.6** `MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md`·`run_prophecy_alignment_pytest` 번들에 명리 통찰 테스트 포함 (2026-03-30). **ENTRY_16 소스 헌트 로그/요약/승격 게이트 계약 아티팩트·테스트·CI 번들 편입** (`docs/final/artifacts/entry16_source_hunt_log.jsonl`, `docs/final/artifacts/entry16_source_hunt_summary.json`, `docs/final/artifacts/entry16_promotion_gate.json`, `tests/test_entry16_source_hunt_log.py`, `tests/test_entry16_source_hunt_summary.py`, `tests/test_entry16_promotion_gate.py`, 로컬/CI 번들) (2026-03-30). **§11 P1 A/B balanced 운영 앵커·최종 선정 리포트 경로 고정** (2026-03-30). **§12 Fact-Safe 라벨 상호 참조** 추가: 본 헌법=경로·테스트 중심 SSOT, `[FACT]`/`[HYPO]`/`[VISION]`/`[NON-MEDICAL]` 템플릿은 `MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 등과 동일 패턴, 외부 Tier1 수치 한 줄 규칙은 `docs/external_research/AI-Logos_Research_Bibliography_2026.md` (2026-03-31). **§13** Chronos KOSPI baseline·매매 단일화·Public Event Gateway 호출 경로 표 보강; `ensure_public_event_gateway.ps1` 중복 블록 제거 (2026-04-02). `public_event_gateway.py` 중복 제거·`nginx_public_event_gateway.conf.example` 추가 (2026-04-02).

**상태 보강 (2026-04-03):** **§13.1** Windows Phase 1 체인·`ops_phase1_chain_report_latest.json`·`verify_constitution_gates.ps1`/`constitution_gates_v1.json`/`constitution_gates_result_latest.json`·`automation_registry.json`의 `\Bitcoin-Ops-Fusion-Cycle-Auto`·루트 `AGENTS.md` 운영 자동화 vs MKM Study 연구 레인.

---

## 12. Fact-Safe 라벨 (상호 참조)

1. 본 파일은 **호출 가능한 경로·스키마·테스트** 중심의 팩트 SSOT이다. 내부 절 표기는 **저장소 안 상호 인용**에 쓰고, 대외 복사 시에는 문장 단위로 재검증한다.
2. 문서군 전체에서 가설·전략·비의료 고지를 통일할 때 **`[FACT]` / `[HYPO]` / `[VISION]` / `[NON-MEDICAL]`** 접두 규칙을 쓴다. 정의 표 템플릿 예시는 `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 말미와, 같은 패턴을 붙인 B-track 보조 MD를 따른다.
3. 외부 학술 수치를 인용할 때의 `출처 + 셋 구성 + 지표 정의` 한 줄 규칙은 `docs/external_research/AI-Logos_Research_Bibliography_2026.md`에 고정한다.

---

## 13. 운영 자동화 팩트 (BTC 주력 + 융합 SOP)

| 항목 | 경로 | 비고 |
|------|------|------|
| BTC 주력 일일 채점 래퍼 | `projects/bitcoin-trading/ops/windows-rehearsal/run_waiting_queue_btc_binance_daily.ps1` | `BTC_BINANCE_D1_RETURN_PCT` 기준; env 우선·Binance 24h API 폴백·실패 시 `PENDING_CLOSE` |
| 듀얼(백업) 일일 채점 래퍼 | `projects/bitcoin-trading/ops/windows-rehearsal/run_waiting_queue_dual_market_daily.ps1` | KOSPI + BTC_BINANCE 동시 슬롯 |
| 월간 체크 러너 | `scripts/run_waiting_queue_monthly_check.ps1` | `HIT/FAIL/NEUTRAL_DRAW/PENDING_CLOSE`; 주간 스냅샷·분포 리포트 생성 |
| 주간 신뢰도 스냅샷 | `docs/final/artifacts/trinity_weekly_reliability_snapshot_latest.json` | 최근 창(window) 판정 집계 |
| 5/10 분포 리포트 | `scripts/report_trinity_scoring_distribution.py` → `docs/final/artifacts/trinity_scoring_distribution_latest.json` | `d5/d10` 비율 + advisory |
| 1페이지 브리핑 템플릿 | `projects/bitcoin-trading/ops/windows-rehearsal/DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md` | 실행(팩트)과 통찰(가설) 분리 |
| Quant→Pixel 융합 SOP | `projects/bitcoin-trading/ops/windows-rehearsal/run_fused_quant_pixel_sop.ps1` | Phase1/Phase2 분리, Night Watchman dry-run 선검증 |
| 융합 SOP 태스크 등록(dry/live) | `projects/bitcoin-trading/ops/windows-rehearsal/register_fused_quant_pixel_sop_task.ps1`, `projects/bitcoin-trading/ops/windows-rehearsal/register_fused_quant_pixel_sop_live_task.ps1` | live는 `-ConfirmLiveAlert` 포함 |
| dry/live 상호배타 스위치 | `projects/bitcoin-trading/ops/windows-rehearsal/switch_fused_quant_pixel_mode.ps1` | 동시 실행 충돌 방지 |
| Chronos-Forward KOSPI baseline CLI | `scripts/run_chronos_forward_kospi_baseline.py` | 래퍼: `scripts/run_chronos_forward_kospi_baseline.ps1` (장시간 `-Detached` 권장). 엔진: `tools/prophecy/chronos_forward_trainer.py`. 산출 예: `data/chronos_forward_training/training_result.json`, `holdout_*_result.json` (최종 `timestamp`는 JSON 본문 기준). |
| Chronos 중복 프로세스 정리 | `scripts/stop_duplicate_chronos_forward_runs.ps1` | `py -c … ChronosForwardTrainer`만 종료; 위 SSOT CLI는 유지. |
| 24h 매매 단일 진입점 | `projects/bitcoin-trading/scripts/start_24h_daemon.py` | 프로세스 띅(`memory/daemon_singleton.lock`). `src/daemon/bitcoin_trading_daemon.py` 직접 실행은 띅 우회로 중복 유발. |
| 직접 데몬 복제 종료 | `projects/bitcoin-trading/ops/windows-rehearsal/stop_direct_bitcoin_trading_daemon_copies.ps1` | |
| 워치독 (스케줄 `Bitcoin-Direct-Watchdog-5min` 등) | `projects/bitcoin-trading/ops/windows-rehearsal/ensure_daemon_running.ps1` | `start_24h_daemon`만 기준으로 기동; 매 실행 시 위 `stop_direct_*` 호출로 직접 데몬 정리. `STOP.txt` 시 싱글톤+직접 데몬 모두 종료 시도. |
| 단일 런타임 보조 | `projects/bitcoin-trading/ops/windows-rehearsal/ensure_single_trading_runtime.ps1` | |
| Ops 종합 헬스 집계 | `projects/bitcoin-trading/ops/windows-rehearsal/build_ops_health_overview.ps1` | `ops_health_overview_v3`; fused mode mutex, strict/ops 스케줄 시각 검증, compression stub 런타임, prophecy pytest 상태 포함. |
| Ops 스케줄러 핵심 헬스 스냅샷 | `scripts/build_ops_scheduler_health_snapshot_v1.py` → `docs/final/artifacts/ops_scheduler_health_latest.json` | 핵심 4개 태스크(`Bitcoin-Ops-Phase1-Chain-Daily`, `MKM-Daily-Prophecy-Eval-SelectedConfig`, `Bitcoin-WaitingQueue-BTCBinance-Daily-Strict`, `Bitcoin-WaitingQueue-DualMarket-Daily-Strict`)의 `State`·`LastTaskResult` 일일 스냅샷(`schema: ops_scheduler_health_snapshot_v1`). |
| Ops 스케줄러 헬스 알림 | `scripts/alert_ops_scheduler_health_v1.py` → `docs/final/artifacts/ops_scheduler_health_alert_latest.json`, `reports/ops_scheduler_health_alert_log.jsonl` | 스냅샷 `all_ok=false` 시 failing task 요약 아티팩트 생성 및 웹훅(`OPS_ALARM_WEBHOOK_URL` 또는 `COMPRESSION_KPI_ALARM_WEBHOOK_URL`) 알림; `--always-log`로 정상 상태도 로그 누적. |
| TurboQuant PoC 회귀 게이트 | `scripts/run_lg_washer_intent_regression_aistudio.ps1` → `scripts/eval_turboquant_poc_gate_v1.py` → `docs/final/artifacts/turboquant_poc_openrouter_gate_latest.json` | PoC 산출(`turboquant_poc_openrouter_v1*.json`)에 대해 speedup/failure/format-pass 기준으로 Go/No-Go 자동 판정(`schema: turboquant_poc_openrouter_gate_v1`). |
| Ops 일괄 태스크 등록 | `projects/bitcoin-trading/ops/windows-rehearsal/register_all_ops_tasks.ps1` | BTC/dual/fatal/compression/jemaai/blind replay 태스크 묶음 등록. |
| Compression stub ensure + 등록 | `projects/bitcoin-trading/ops/windows-rehearsal/ensure_compression_stub.ps1`, `projects/bitcoin-trading/ops/windows-rehearsal/register_compression_stub_task.ps1` | `/health` 8010 런타임 보정 및 일일 ensure 태스크 등록. |
| Ops health overview 태스크 등록 | `projects/bitcoin-trading/ops/windows-rehearsal/register_ops_health_overview_task.ps1` | 일일 `Ops-Health-Overview-Daily` 등록(재생성 안전). |
| Public Event Gateway (MVP, 로컬 HTTP) | `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_event_gateway.py` | 기본 포트 8788; `GET /api/public-events/latest`, `POST /api/public-events/ingest`. 기동·헬스: `projects/bitcoin-trading/ops/windows-rehearsal/ensure_public_event_gateway.ps1`. **공개 도메인(jemaai.cloud 등):** nginx 예시 `nginx_public_event_gateway.conf.example` → `proxy_pass` 대상은 게이트웨이 호스트(`127.0.0.1:8788`). POST는 `X-Public-Event-Token` = `PUBLIC_EVENT_GATEWAY_TOKEN`. **스펙·경계 확정:** `JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md`. **ingest 예시:** `jemaai-cloud-mvp/examples/public_event_ingest_minimal.v1.json`. **정적 폴링 UI:** `jemaai-cloud-mvp/public_showroom_poll.html` (`?api=` 로 Base URL). **Gemini 경고 정리 힌트:** `scripts/print_gemini_env_hygiene_hint.ps1`. |
| Showroom static bundle | `projects/bitcoin-trading/ops/windows-rehearsal/build_showroom_display_bundle.ps1` | `docs/final/artifacts/showroom_public_bundle_v1.json` — `public_event.v1` + `public_ui`(`showroom_public_ui_v1`, ASCII 토큰) + 검증 `scripts/validate_showroom_public_bundle.py`. 한글 UI는 HTML에서 매핑. |
| Showroom 정적 배포(로컬/스테이징 복사) | `projects/bitcoin-trading/ops/windows-rehearsal/deploy_showroom_static.ps1` | `-WebRoot` 또는 `JEMAAI_WEB_ROOT` → `public_showroom_poll.html`·`showroom_public_bundle_v1.json` 복사. 본선 nginx는 수동. |
| 퓨전 후 ingest POST(선택) | `run_ops_fusion_cycle.ps1` + `publish_showroom_public_event.ps1` | User/Process `SHOWROOM_PUBLISH_INGEST=1`일 때만 7단계 실행. `SHOWROOM_INGEST_URL`·`PUBLIC_EVENT_GATEWAY_TOKEN`. |
| 쇼룸 체인 로컬 검증 | `projects/bitcoin-trading/ops/windows-rehearsal/verify_showroom_bundle_chain.ps1` | 빌드(옵션 `-SkipBuild`)→`validate_showroom_public_bundle.py`→`pytest`; `-WithStagingCopy` 시 `.showroom_staging/`에 정적 복사 테스트. CI: `.github/workflows/showroom-bundle-validate.yml`. |

### 13.1 Phase 1 체인·레지스트리 (Windows, 관측·게이트)

| 항목 | 경로 | 비고 |
|------|------|------|
| Phase 1 통합 체인 | `projects/bitcoin-trading/ops/windows-rehearsal/run_ops_phase1_chain.ps1` | 스냅샷 → 퓨전 상태 검증 → 옵션 `verify_all_green`; `-Strict`·`-IncludeVerifyAllGreen`·`-SkipFusionStatusCheck`·`-IncludeConstitutionGates`·`-SkipOpsAlarm`. 설정 시 `OPS_ALARM_WEBHOOK_URL`(User/Process): 체인 예외 시 `kind=failure` POST; 성공 시 `shared_vault_reachability=warning`이면 `kind=shared_vault_warning`(끄려면 `OPS_ALARM_SKIP_SHARED_VAULT_WARNING=1`). 페이로드: JSON `event`,`kind`,`message`,`report_path`,`ts_utc` |
| 헌법 게이트 (3중) | `projects/bitcoin-trading/ops/windows-rehearsal/verify_constitution_gates.ps1` | (1) `ops_phase1_chain_report_latest.json`의 `overall_chain_ok` (2) `reconcile_automation_registry.ps1` 무드리프트 exit 0 (3) `risk_profile_fact_safe_latest.json`의 `source`/`mode`가 `constitution_gates_v1.json`의 `allowed_risk_combinations`에 포함; `-SkipPhase1Report` 등 개별 스킵 가능 |
| 헌법 게이트 allowlist | `projects/bitcoin-trading/ops/windows-rehearsal/constitution_gates_v1.json` | 정책 변경 시 `allowed_risk_combinations` 편집 |
| 헌법 게이트 결과 SSOT | `projects/bitcoin-trading/memory/v2/ops/constitution_gates_result_latest.json` | `schema constitution_gates_result_v1`; `all_ok`·`checks[]` |
| 환경 스냅샷 | `projects/bitcoin-trading/ops/windows-rehearsal/collect_ops_environment_snapshot.ps1` → `projects/bitcoin-trading/memory/v2/ops/ops_environment_snapshot_latest.json` | 계정·`C:\workspace`·`G:` 프로브·주요 태스크 Logon Mode |
| 퓨전 사이클 상태 검증 | `projects/bitcoin-trading/ops/windows-rehearsal/verify_ops_fusion_cycle_status.ps1` | `docs/final/artifacts/ops_fusion_cycle_status_latest.json`의 `overall_ok` 또는 C2/Trinity 보조 판정 |
| 융합 사이클 러너 | `projects/bitcoin-trading/ops/windows-rehearsal/run_ops_fusion_cycle.ps1` | 산출 `ops_fusion_cycle_status_latest.json`(`schema ops_fusion_cycle_status_v2`, `overall_ok`·`overall_ok_reason`) 후 **showroom 번들 생성·검증**(`build_showroom_display_bundle.ps1`, `validate_showroom_public_bundle.py`) |
| 올그린 게이트 | `projects/bitcoin-trading/ops/windows-rehearsal/verify_all_green.ps1` | 단계에 `verify_ops_fusion_cycle_status` 포함 후 `reconcile_automation_registry` |
| 레지스트리 reconcile | `projects/bitcoin-trading/ops/windows-rehearsal/reconcile_automation_registry.ps1` | 기본 콘솔은 한 줄 요약만; 전체 JSON은 `automation_registry_reconcile_latest.json`. 디버그 시 `-ShowJson` |
| Phase 1 운영 준비 점검 | `projects/bitcoin-trading/ops/windows-rehearsal/verify_ops_phase1_operational_readiness.ps1` | 태스크 존재·`Task To Run`에 `IncludeConstitutionGates`·리포트 신선도·`OPS_ALARM_WEBHOOK_URL`; 산출 `ops_phase1_readiness_latest.json`; 엄격 시 `-Strict` |
| OPS 알림 웹훅 스모크 | `projects/bitcoin-trading/ops/windows-rehearsal/smoke_ops_phase1_webhook.ps1` | User `OPS_ALARM_WEBHOOK_URL`로 `kind=smoke_test` POST(미설정 시 exit 0 스킵) |
| 자동화 레지스트리 | `projects/bitcoin-trading/ops/windows-rehearsal/automation_registry.json` | `\Bitcoin-Ops-Fusion-Cycle-Auto` 등 Task Scheduler 기대 상태; `reconcile_automation_registry.ps1 -Enforce` |
| 레거시 태스크 비활성/대체 매핑 | `docs/final/artifacts/ops_scheduler_legacy_task_replacement_v1.json` | 경로 미존재 등으로 비활성화한 태스크와 대체 태스크 매핑 SSOT(운영 노이즈 재발 방지). |
| Phase 1 리포트 SSOT | `projects/bitcoin-trading/memory/v2/ops/ops_phase1_chain_report_latest.json` | `schema ops_phase1_chain_report_v1`; `scope_note`: 운영 런북·게이트만, 헌법 자동 해석·자율 전략 변경 아님. `shared_vault_reachability`: 스냅샷 기준 `ok` \| `warning` \| `unknown`(G:·공유 vault 경로); **경고만, `overall_chain_ok` 비판정** |
| 일일 체인 태스크 등록 | `projects/bitcoin-trading/ops/windows-rehearsal/register_ops_phase1_chain_task.ps1` | 기본 `\Bitcoin-Ops-Phase1-Chain-Daily` 매일 08:30; **`-IncludeConstitutionGates` 기본 포함**(`-ExcludeConstitutionGates`로 끔). **본선 PC**에서 실행·`schtasks /Query`로 확인 |
| Phase 1 일일 원클릭 | `projects/bitcoin-trading/ops/windows-rehearsal/bootstrap_ops_phase1_daily.ps1` | `sync_required_env_to_user.ps1` → `register_ops_phase1_chain_task.ps1` 순서; `-SkipEnvSync` / `-SkipTaskRegister` / `-ExcludeConstitutionGates` / `-IncludeReadiness` / `-IncludeWebhookSmoke`. 동기화: `.env`에 `OPS_ALARM_WEBHOOK_URL` 없으면 User `N8N_WEBHOOK_URL`로 **자동 미러** |
| P0·헌법 경로 스모크 | `scripts/verify_p0_constitution_gate_paths.ps1` | `CONSTITUTION`·`P0`·`COMPRESSION_SLA_POLICY_V1`·`COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK`·`NotebookLM_sources_manifest`·`.cursorrules`·`AGENTS`·`CLAUDE`·정렬 pytest·Vault 동기화 등 **존재만** 검사(exit 0/1). 상세: `P0_COMMERCIALIZATION_TRACKER.md` §증거 경로 |
| 압축 KPI 자동 체인 | `scripts/run_compression_automation_chain.ps1` | 범용 프로파일 재평가·KPI 요약(`literal_kpi`는 `-IncludeLiteralTrack`로 리터럴 산출물이 있을 때)·토큰 API hydration 믹스·범용 손실 패턴; `-IncludeLiteralTrack` 시 리터럴 프로파일·리터럴 손실 패턴 추가; `run_workspace_automation_health.ps1 -IncludeCompressionKpi`로 묶음 가능(투트랙까지: 동시에 `-IncludeLiteralTrack`; 알람은 여전히 `active_kpi` 기준); 종료 시 `send_compression_kpi_alarm_if_needed.ps1`(임계치 `docs/final/artifacts/compression_alarm_thresholds_v1.json`, 웹훅 `COMPRESSION_KPI_ALARM_WEBHOOK_URL` 또는 `OPS_ALARM_WEBHOOK_URL`, `-SkipCompressionAlarm` 생략) |
| Track A go/nogo·HOLD 체인 (모노레포 루트) | `scripts/build_a_track_go_nogo_status.py` → `docs/final/artifacts/a_track_go_nogo_status_latest.json`; `scripts/build_a_track_multiweek_stability_tracker_v1.py` → `a_track_multiweek_stability_tracker_v1_latest.json`; `scripts/build_a_track_hold_release_checklist_v1.py` → `a_track_hold_release_checklist_v1_latest.json`; 거버넌스 JSON 부트스트랩 `scripts/emit_a_track_governance_artifacts_v1.py`(플레이스홀더—실전 서명 전 교체); 주간 롤업 `scripts/run_a_track_s3_weekly_evidence_rollup_v1.py`(`--emit-missing-governance` 선택, 트래커→체크리스트→go/nogo→체크리스트); 로컬 원클릭 갱신(주차 증가 없음) `scripts/Run-ATrackGovernanceRefresh.ps1`; 주간 작업 등록 `scripts/Register-ATrackS3WeeklyEvidenceTask.ps1`(기본 월요일·`--emit-missing-governance` 포함, `-SkipEmitGovernance`로 끔); 승인 영수증 선택 `reports/a_track_promotion_decision_latest.json` | **B-track·실매매 자동 합선 아님.** 가격 출력·고신뢰·다주간 증거·운영자 승인은 별도 게이트; 기본 산출물은 파이프라인 연결용이며 운영 주장의 근거로 삼으려면 서명·증거 경로를 갱신해야 한다. |
| 에이전트 레인 분리 | 루트 `AGENTS.md` — **운영 자동화 vs 연구 레인** | MKM Study·본선 OOF·실매매 **자동 합선 금지** 방향; 브리핑 전용 필드는 레포 산출물 근거 없이 SSOT 삼지 않음 |

### 13.2 외부 법령 참조 API (Beopmang 등, 보조 레이어)

| 항목 | 값 | 비고 |
|------|-----|------|
| 법망(Beopmang) 공개 베이스 | `https://api.beopmang.org` | 서드파티 법령·조문 검색·MCP 연동(무키·무가입 지향). **본 저장소에 호출 코드가 없어도** 외부 에이전트가 참조할 수 있는 **정책 포인터**로 본 표에 고정한다. |
| MCP 엔드포인트 | `https://api.beopmang.org/mcp` | 공개 안내 기준; 변경 시 제공자 문서 우선. |
| Hermes 얇은 프로필 | `projects/bitcoin-trading/ops/.hermes.md` §7 | 허용 도구·면책·인용 규칙. |
| 면책(팩트-락) | — | 제공자 고지: API 출력은 **참고용**이며 **법적 효력 없음**. 준수·계약·소송 가능성 판단의 **최종 SSOT는 아님**. 공식 국가 법령 DB·내부 준법·외부 법무 검토와 대조한다. |
| 용도 경계 | — | **검색·브리핑·감사 추적 보조** 및 B-track 정책 내러티브 시드에 적합. **실매매 트리거·올그린 게이트·본선 OOF와 자동 합선 금지**(연구/브리핑 레이어). 호출 빈도 등 **익명 집계** 가능—민감정보·키를 쿼리에 넣지 않는다. |

**§13.1 범위:** 위 경로는 **관측·스케줄·게이트·JSON 리포트**만 해당한다. 헌법·백서·사업계획서를 LLM이 매 실행마다 해석해 본선 코드·실거래 파라미터를 바꾸는 **자율 추론 루프는 본 절에 포함되지 않음**(상단 목적·§1.1 Multi-Lens·NotebookLM 격벽과 동일 선상에서 “구현 단정 금지”).

**운영 원칙**: 실행 트리거는 관측 지표·로그 기반으로 유지하고, 성경/명리/사상 렌즈는 브리핑·가설 계층으로 분리한다.

---

## 14. MKM12 Prism Index (Grand Indexing 2.0 — 논리 색인)

**목적**: 물리 폴더를 옮기지 않고, **역할·접근 정책**만 한눈에 두기. 본 절은 **신규 헌법이 아니라** 상단 SSOT 표에 붙는 **색인 레이어**다.

**Prism 축 (기능 네임스페이스)**: 코드 내부의 4D 벡터 축 `(S,L,K,M)` 의미를 덮어쓰지 않는다. 여기서의 S/L/K/M은 **파일·경로 분류용 라벨**이다.

| Prism 축 | 뜻 (요약) | 대표 경로 (팩트) |
|-----------|-----------|------------------|
| **S** — Static / Structural | 구현 SSOT·진입 문서 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`, `AGENTS.md` |
| **L** — Linear / Logical | 흐름·레짐·규칙 코드 | `projects/bitcoin-trading/src/integration/dual_regime_api.py` (§2 표 참조) |
| **K** — Kernel / Knowledge | 해석·B-track·원전 핸드오프 | `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` 등 |
| **M** — Manifested / Metrics | 측정·게이트·산출 JSON | `scripts/verify_p0_constitution_gate_paths.ps1`, `scripts/spike_gematria_myeongri_blend_v0.py`, `scripts/spike_log_myeongri_correlation_v1.py`, `projects/bitcoin-trading/memory/v2/ops/ops_phase1_chain_report_latest.json` |

**인간 가독 색인 (Draft)**: `docs/final/MKM12_GRAND_INDEX_MAP.md` — S/L/K/M 역할로 핵심 경로를 묶은 요약; 레지스트리·본 표와 **경로 충돌 시** 본 문서 표·JSON을 우선한다.

**중앙 레지스트리 (머신·에이전트 확장용)**: `docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json` — 위 표의 상위 집합·`agent_access`·`id` 필드. 항목 추가 시 **경로 존재**를 확인하고 본 표 또는 JSON 중 하나에 동기화한다.

**Prophecy Hit Rate CLI (측정·비교용)**: `scripts/eval_prophecy_hit_rate_v1.py` — `run_mode` `price`(`--score-json`에 `predicted_direction`/`actual_direction` 또는 `rows[]`; 방향 일치율) / `proxy`(Oracle·레지스트리 precision 경로; 가격 적중과 동일 지표 아님; 미연결 시 `no_data`). **새벽 채점 OHLCV→score JSON**: `scripts/build_btrack_prophecy_score_from_ohlcv.py` — KOSPI SSOT `research/market_data/kospi_daily_external_yf.csv`(로더 `load_kospi_yf_rows`; **Date 헤더 단일행 CSV**·구형 `Price` 헤더 겸용); **CSV 갱신(선택)**: `scripts/fetch_kospi_yfinance_csv.py`(`^KS11`, `yfinance`). BTC는 `--btc-csv` 동형 파일 있을 때만 multi 2번째 행; 산출 `docs/final/artifacts/btrack_prophecy_score_latest.json`; `--eval-date auto`는 UTC 기준 CSV 내 “어제” 막대; **`--recent-trading-days N`**: 동일 가설 방향을 유지한 채 최근 N거래일 각각에 대해 `rows[]`를 누적(히트레이트 표본 확장; `meta.frozen_prediction_note` 참고). 선택 `run_btrack_daily_hypothesis_chain.ps1 -IncludeDawnScore` → 위 score 생성 후 `eval_prophecy_hit_rate_v1 --run-mode price`. 산출 스키마 **`prophecy_hit_rate_eval_report_v2`**. 기본 기록 경로 `docs/final/artifacts/prophecy_hit_rate_eval_latest.json` 및 동일 페이로드 `artifacts/latest_report.json`(로컬 재생성·`.gitignore`; VPS·SSH 호환). `--stdout-only`는 파일 미기록. **월간 체인**: `run_waiting_queue_monthly_check.ps1`가 KOSPI CSV·가설 JSON이 있으면 `build_btrack_prophecy_score_from_ohlcv.py --recent-trading-days 30`(및 선택 `MKM_BTC_DAILY_CSV`) 후 `eval_prophecy_hit_rate_v1.py --run-mode price`를 이어서 실행하고, 같은 실행에서 `btrack_prophecy_score_monthly_YYYY-MM-DD.json`·`prophecy_hit_rate_eval_monthly_YYYY-MM-DD.json`로 복사(없으면 WARN 스킵).

**예언 방향 오버레이 소거 스파이크(B-track, [HYPO])**: `scripts/run_prophecy_restoration_spike.py` — 동일 `btrack_prophecy_score_v1` `rows[]`에 선택 오버레이 적용 전후 방향 적중률·`delta_hit_rate`를 스키마 `prophecy_overlay_ablation_spike_v1`·`docs/final/artifacts/prophecy_restoration_spike_latest.json`에 기록. 오버레이: (1) **기본** `prior_day_shock_bear_abstain_v0` — `research/market_data/kospi_daily_external_yf.csv`에서 **전거래일 완결 일간 수익률**(평가일 당일 `daily_return` 미사용)이 `--prior-return-threshold`(스크립트 기본 **-4.8%**; 패널별 권장은 `docs/final/artifacts/prophecy_overlay_prior_threshold_recommended_latest.json`) 이하일 때 `bear→neutral`; (2) `stress_bear_to_neutral_v0` — 표본 `docs/final/artifacts/4d_to_ohaeng_regime_year_map_sample_v1.json` 스트레스 연도 구간. **임계값 스윕:** OHLCV 30일 패널 요약 `docs/final/artifacts/prophecy_prior_threshold_sweep_summary_latest.json` (`prophecy_prior_threshold_sweep_summary_v1`). 본선·실매매 트리거 아님. 회귀: `tests/test_prophecy_restoration_spike.py` — **CI**: `.github/workflows/prophecy-restoration-spike-smoke.yml`.

**일일 B-Track 번들(렌즈→퓨전→LLM 입력→가설 JSON)**: `scripts/run_btrack_daily_hypothesis_chain.ps1` + `scripts/build_btrack_llm_input_bundle.py` + `scripts/generate_btrack_hypothesis_prophecy_v1.py`(기본 스텁; `--gemini`는 API 키 필요); 산출 `docs/final/artifacts/btrack_hypothesis_prophecy_latest.json`; 가설 스키마 `docs/final/BTRACK_HYPOTHESIS_PROPHECY_V1.schema.json`.

**일반 미래 예측(비가격) 질문·확률 슬롯 계약(초안, 2026-04-11)**: `docs/final/GENERAL_PROPHECY_SCHEMA_V1.json` — `general_prophecy_registry_v1` / `general_prophecy_question_v1`; 레일 `B` 또는 `OBSERVATION_ONLY`; 판정 가능한 `resolution_criteria`·`resolution_deadline_utc`; Layer 1용 `forecasts[]`(`probability_0_1`, `source_kind`); 해석은 `layer3_interpretation_ref` 포인터만. **스크립트(Phase 2–4 최소 구현)**: `scripts/generate_general_prophecy_v1.py`(스키마 검증·`generated_at_utc` 갱신·선택 `--stub-forecasts`; 기본 입출력 `tests/fixtures/general_prophecy_registry_sample_v1.json`→`docs/final/artifacts/general_prophecy_latest.json`; **기본 병합**: 동일 실행에서 `general_prophecy_registry_seed_5_v1.json`·`general_prophecy_registry_brier_smoke_v1.json`의 문항을 `question_id` 기준으로 뒤에 합침(중복 스킵)·`--no-default-merge`로 끔·추가는 `--merge-from PATH` 반복) · `scripts/build_general_prophecy_brief.py`(동 레지스트리→`docs/final/artifacts/general_prophecy_brief_latest.md`) · `scripts/eval_general_prophecy_brier_score.py`(이진+`resolved`만 평균 Brier·선택 `--ece-bins N` 등간 이진 ECE·`metrics.ece_binary`·`metrics.ece_binary_by_domain_tag`(`--ece-min-per-tag`)→`docs/final/artifacts/general_prophecy_brier_eval_latest.json`) · `scripts/resolve_general_prophecy_question_v1.py`(이진 질문: `--resolution-status resolved|void|disputed`; `resolved`일 때만 `--outcome`; `void`/`disputed`는 `outcome_binary` null·notes/`evidence_uris` 선택; `--output`·`--in-place`·`--stdout-only`) · `scripts/export_general_prophecy_to_jsonl.py`(GPU LoRA 훈련용 B-track JSONL 추출기; `output` 앞단에 `[HYPO]` 가드레일 강제; 압축·A-track 실거래 엔진과 코드 합선 없음). **월간 체인**: `scripts/run_waiting_queue_monthly_check.ps1`가 `-SkipGeneralProphecyChain`이 **아닐 때** `generate_general_prophecy_v1`→`build_general_prophecy_brief`→`eval_general_prophecy_brier_score`→`export_general_prophecy_to_jsonl` 순서로 실행(외부 예측시장 API 없음; 리졸버는 수동 호출; JSONL 산출 `data/training/macro_prophecy_dataset_v1.jsonl`·`.gitignore`). **CI**: `tests/test_general_prophecy_schema_v1.py`·`tests/test_general_prophecy_chain_smoke.py`·`tests/test_resolve_general_prophecy_question_v1.py`·`tests/test_export_general_prophecy_to_jsonl.py` — `scripts/verify_p0_constitution_gate_paths.ps1`에 스키마·스크립트·픽스처 경로 포함. **시드 5문항(스키마 검증·수동 병합용)**: `tests/fixtures/general_prophecy_registry_seed_5_v1.json`(월간 체인 기본 입력 아님; `generate_general_prophecy_v1.py --input` 등으로 선택 병합).

**기상 관측 라벨 → `general_prophecy` 트리플(B-track, [HYPO], 교정·측정 전용)**: `docs/final/schemas/weather_ground_truth_row_v1.schema.json` — 한 줄당 `weather_ground_truth_row_v1`(JSONL). **1단계(CSV→라벨 JSONL)**: `scripts/csv_to_weather_ground_truth_jsonl_v1.py`(`--threshold-mm` 기본 0.1; `--strict-schema`·`--max-rows` 선택; **`--auto-columns`**는 `scripts/weather_csv_sniff_v1.py`로 인코딩·구분자·날짜/강수 열·`--date-format` 추정; 원클릭 체인은 **`--auto-columns-csv`**). **대량 주입 후 QA**: `scripts/validate_weather_ground_truth_jsonl_v1.py`(스키마·중복 키·이진/강수 정합; exit 1 시 오류). **합성 CSV(실제 KMA 아님, 파이프라인·120행 스트레스용)**: `scripts/generate_weather_gt_synthetic_csv_v1.py`→`tests/fixtures/weather_ground_truth_synthetic_120d_input.csv`·동 레포 `tests/fixtures/weather_ground_truth_synthetic_120d_v1.jsonl`. **샘플 라벨 JSONL(빌더·스키마 스모크)**: `tests/fixtures/weather_ground_truth_rows_v1.sample.jsonl`. **2단계(JSONL→레지스트리, 렌즈 3행·동일 해소)**: `scripts/build_weather_triplet_registry_v1.py`(별칭 CLI `scripts/weather_ground_truth_jsonl_to_prophecy_triplet_registry_v1.py`); 선택 `--forecasts-jsonl`(`p_myeongri`/`p_sasang`); 융합 확률은 스키마 외 별도 필드 없이 `forecasts[].source_detail`에 사전 등록 식 기입; `domain_tags`에 `weather_calibration_v1`·`triplet_shared_target` 등. **원클릭**: `scripts/run_weather_gt_to_prophecy_triplet_chain_v1.py`(기본: CSV→JSONL 후 `validate_weather_ground_truth_jsonl_v1.py` 실행; `--skip-validate-jsonl`·`--max-rows`; 선택 `--forecasts-jsonl` 또는 **`--auto-forecasts-sidecar`**(`weather_gt_jsonl_to_forecasts_sidecar_v1.py`가 GT JSONL과 동기화된 사이드카 생성)). **회귀**: `tests/test_weather_gt_triplet_chain_smoke.py` — `dual-regime-integrity.yml` General prophecy 단계에 포함. **대량 재현(합성 120일·360문항)**: `scripts/run_weather_synthetic_120d_chain_and_brier_v1.py`(본체; `run_weather_synthetic_120d_chain_and_brier_v1.ps1`는 동일 인자 전달 래퍼)는 체인에 **`--auto-forecasts-sidecar`**(CSV로 나온 GT JSONL에서 즉시 강수→로지스틱 사이드카 생성·이진 라벨 미사용) 후 `eval_general_prophecy_brier_score.py --no-rows`(러너 기본 **`--ece-bins 10`**·`metrics.ece_binary`·`metrics.ece_binary_by_domain_tag`·`--ece-min-per-tag`; `--ece-bins 0`이면 ECE 생략) → `docs/final/artifacts/weather_prophecy_brier_eval_synthetic_120d_sidecar_summary_v1.json`. 기본 레지스트리 출력: 사이드카·`--forecasts-jsonl` → `weather_prophecy_triplet_synthetic_120d_v1.json`; **`--stub-only`** → `weather_prophecy_triplet_synthetic_120d_stub_v1.json`(사이드카 산출과 분리). **`--stub-only`**로 stub 기준선 요약 `docs/final/artifacts/weather_prophecy_brier_eval_synthetic_120d_summary_v1.json` 재생성(mean Brier **0.25** @ stub 0.5·합성 전일 강수). 실CSV(Kaggle 등)는 러너·체인 공통으로 **`--date-col`·`--precip-col`·`--max-rows`·`--threshold-mm`·`--station-id`** 등 전달; Kaggle API·`kaggle` CLI 사용 시 샘플 일괄(다운로드→120행 체인→Brier)은 **`scripts/fetch_kaggle_seattle_weather_sample_chain_v1.ps1`**(산출 `data/kaggle_auto_weather/`, `.gitignore`; **`--strict-schema-csv`**는 `jsonschema` 필요·**`scripts/requirements-weather-pipeline.txt`**); **예시 CLI는 `run_weather_gt_to_prophecy_triplet_chain_v1.py --help`·`run_weather_synthetic_120d_chain_and_brier_v1.py --help` 에필로그**. 모델·수동 확률 JSONL은 러너·체인 **`--forecasts-jsonl`**(러너에서는 `--stub-only`·기본 auto 사이드카와 배타). 수동 사이드카 생성은 `scripts/weather_gt_jsonl_to_forecasts_sidecar_v1.py`·픽스처 `tests/fixtures/weather_synthetic_120d_forecasts_sidecar_v1.jsonl`. **외부 렌즈 확률 주입 최소 예**(`p_myeongri`/`p_sasang`, 합성 로지스틱 아님): `tests/fixtures/weather_forecasts_external_lens_minimal_v1.jsonl`·체인 `--help` 에필로그·일괄 **`scripts/run_weather_external_forecasts_minimal_chain_eval_v1.ps1`**(→`out/reg_external_theory*.json`). **120일 합성 + HYPO 외부 JSONL(행 인덱스 sin/cos, 실엔진 아님)**: `scripts/generate_weather_external_lens_forecasts_from_csv_v1.py`→`tests/fixtures/weather_synthetic_120d_external_lens_hypo_v1.jsonl`·러너 `--help` 에필로그·일괄 **`scripts/run_weather_synthetic_120d_external_hypo_chain_eval_v1.ps1`**(→`out/reg_external_120.json` 등)·회귀 `tests/test_weather_gt_triplet_chain_smoke.py`. 트리플·라벨 대용량 JSON은 `.gitignore`; 요약 JSON만 추적. 기상학적 본선·실매매·우주론 단정 아님.

**증분 색인·동기화 (전체 재색인 불필요)**: 워크스페이스를 물리적으로 통째로 옮기거나 “전부 새로 인덱싱”할 필요는 없다. 역할·경로 정리는 **Prism** 중앙 레지스트리(`MKM12_PRISM_INDEX_REGISTRY_V1.json`)와 가독 색인(`MKM12_GRAND_INDEX_MAP.md`)에 **변경·신규 항목만** 반영하면 된다. NotebookLM 작전지휘부는 **전체 wipe 금지**·파일 단위 갱신이 원칙(`docs/NotebookLM_sources_manifest.md`, `notebooklm-refresh` 스킬). 파일 기반 장기기억(`.mkm-memory`)의 4D·벡터 동기화는 **`content` 변경이 있을 때만** 대상으로 하며, 세부는 동 매니페스트 해당 절과 호출 가능 경로를 따른다.

**에이전트 접근 (권고)** — 강제는 아니며 브리핑·편집 시 참고:

- `read_only_strict`: SSOT 문서 — 요약은 가능, 단정적 “구현 완료” 서술 금지(본 문서 상단 목적과 동일).
- `execute_observe`: 스크립트·API — 실행은 로컬 정책·CI에 따름.
- `b_track_only`: 본선·실거래·OOF 자동 합선 금지(§1.1·§13.1과 동일 선상).
- `system_internal`: 런타임/산출물 — 저장소에 없을 수 있음(생성 경로).

**검증 자동 분기 팩트 (2026-04-21)**: `projects/no1kmedi/scripts/run-verify-auto.mjs` + `package.json` `verify:auto`가 `ATHENA_MANSERYEOK_API_URL`(및 필요 시 `ATHENA_MANSERYEOK_API_TOKEN`) live probe 성공 시 `verify:live`, 실패 시 `verify:full`로 자동 분기하며, `scripts/run-no1kmedi-verify-auto.mjs`로 workspace root에서도 동일 경로 실행 가능.

---

## 15. Dimensional Projection 운영형 품질 파이프라인 (정책별 scorer/합성 게이트/락 분리)

| 항목 | 경로 | 비고 |
|------|------|------|
| 일일 refresh 체인 (평가→override→threshold→scorer→알람→lock refresh) | `scripts/Run-DimensionalProjectionEngineEvalRefresh.ps1` | `evaluate_dimensional_projection_engines.py` → `build_dimensional_projection_engine_overrides.py` → `tune_dimensional_projection_thresholds.py` → `tune_dimensional_projection_scorer_config.py` → `build_dimensional_projection_regression_alerts.py` → `refresh_dimensional_projection_runtime_lock_manifest_v1.py` 순차 실행. |
| lock verify 독립 체인 | `scripts/Run-DimensionalProjectionLockVerify.ps1` | `verify_dimensional_projection_lock_integrity_v1.py` 단독 실행. refresh와 분리되어 충돌 없이 별도 모니터링 가능. `-Strict` 시 alert 상태를 non-zero로 승격. |
| daily refresh 작업 등록 | `scripts/Register-DimensionalProjectionEngineEvalDailyTask.ps1` | 기본 TaskName `DimensionalProjection-EngineEval-Refresh-Daily`; 기본 시각 `02:30`; 기본 인자에 `-RegenerateEvalset` 포함. |
| daily lock verify 작업 등록 | `scripts/Register-DimensionalProjectionLockVerifyDailyTask.ps1` | 기본 TaskName `DimensionalProjection-LockVerify-Daily`; 기본 시각 `02:15`; `-Strict` 선택 전달. |
| 정책별 엔진 결정/합성 게이트 산출물 | `reports/dimensional_projection_bridge/engine_overrides_latest.json` | `unsafe_allow_threshold` + `false_block_threshold` + `min_accuracy` 3축으로 override 결정 (`policy_engine_overrides`). |
| 정책 임계치 산출물 | `reports/dimensional_projection_bridge/policies_calibrated_latest.json` | 정책별 `risk_block_threshold`, `ood_revise_threshold`, `canon_min_threshold`, `coherence_min_threshold` 보정 결과. |
| 정책별 scorer 산출물 | `reports/dimensional_projection_bridge/scorer_config_latest.json` | `scorer_config_by_policy` + 정책별 진단(`unsafe_allow_rate`, `false_block_rate`, `accuracy`, caps, objective_weights). |
| 회귀 알람 산출물 | `reports/dimensional_projection_bridge/regression_alerts_latest.json` | `severity`, `alert_count`, 정책별 `reasons`(`unsafe_allow_exceeded`/`false_block_exceeded`/`accuracy_below_minimum`). |
| API 평가 엔드포인트 (최신 리포트 참조) | `api-services/routers/dimensional_projection/router.py` (`POST /api/v1/dimensional-projection/policies/evaluate`) | `_load_policy_metrics_from_report`가 `engine_eval_multi_policy_latest.json`의 정책/엔진별 metrics를 읽어 응답. 리포트 부재 시 `fallback_default`로 degrade. |

### 15.1 점수 함수 구현식 (현행)

구현 경로: `api-services/routers/dimensional_projection/scorer.py` (`score_projection`).

- Risk 기본식:
  - `risk = base + (S * s_weight) + ((-M) * m_weight)`
- 정책별 리스크 보정:
  - keyword hit 시 `risk += keyword_bonus`
  - phrase hit 시 `risk += phrase_bonus`
  - benign hint hit 시 `risk -= benign_dampen`
  - hard-risk phrase hit 시 `risk = max(risk, hard_flag_floor)`
- embedding 엔진 보정:
  - `selected_engine`가 `embedding*`이면 `risk = (risk * embedding_scale) + embedding_bias`
- 최종 점수군:
  - `canon_score = clip(S*s_weight + L*l_weight + bias, 0, 1)`
  - `risk_score = clip(risk, 0, 1)`
  - `coherence_score = clip(base - abs(S-L)*sl_gap_weight, 0, 1)`
  - `ood_score = clip(abs(len(text)-target_length)/scale, 0, 1)`

### 15.2 정책별 제어 구조 (단일 기준 미사용)

- scorer 계수는 `scorer_config_by_policy`를 우선 적용(`core-default-v1`, `core-safety-v1`, `core-medical-v1`).
- threshold도 정책별로 분리(`risk_block_threshold`, `ood_revise_threshold`, `canon_min_threshold`, `coherence_min_threshold`).
- scorer 튜닝 objective는 정책별 가중치 분리:
  - `unsafe_allow_weight`, `false_block_weight`, `accuracy_weight` (`tune_dimensional_projection_scorer_config.py`).
- override 엔진 선택은 `unsafe_allow_rate`만이 아니라 3축 합성 게이트:
  - `unsafe_allow_rate` 초과 또는 `false_block_rate` 초과 또는 `accuracy < min_accuracy`이면 `hash` 강제.

### 15.3 회귀 알람 판정 규칙

구현 경로: `api-services/scripts/build_dimensional_projection_regression_alerts.py`.

- 기본 임계치 인자:
  - `unsafe_allow_threshold`(기본 0.02)
  - `false_block_threshold`(기본 0.12)
  - `min_accuracy`(기본 0.35)
- 정책별 threshold override:
  - `core-safety-v1`: `false_block_threshold=max(base, 0.15)`, `min_accuracy=min(base, 0.33)`
- 알람 reason:
  - `unsafe_allow_exceeded`, `false_block_exceeded`, `accuracy_below_minimum`
- severity 규칙:
  - `alerts` 비어 있으면 `severity="ok"`, 1개 이상이면 `severity="warning"`.
- 운영 기준선 갱신(UTC `2026-04-24T08:02:00Z`):
  - 최신 운영 재산출에서 `min_accuracy=0.32` 기준으로 `severity="ok"`, `alert_count=0` 달성.
  - 산출물 기준: `reports/dimensional_projection_bridge/regression_alerts_latest.json`, `engine_overrides_latest.json`.

### 15.4 운영 분리 원칙 (refresh vs lock verify)

- refresh 체인(`Run-DimensionalProjectionEngineEvalRefresh.ps1`)은 품질 개선/재튜닝/알람 산출을 담당.
- lock verify 체인(`Run-DimensionalProjectionLockVerify.ps1`)은 무결성 점검 전담.
- 두 체인은 스케줄러에서 분리 등록해 독립 운용:
  - `DimensionalProjection-LockVerify-Daily`
  - `DimensionalProjection-EngineEval-Refresh-Daily`

---

## 16. Bible Meaning Two-Track 산출물 (Track K 우선 + Track T 상태판)

| 항목 | 경로 | 비고 |
|------|------|------|
| Track K 지식 IP 리포트 빌더 | `scripts/build_bible_meaning_knowledge_ip_report_v1.py` | `bible_meaning_insight_candidates_latest.json`(+선택 `insight_survivor_candidates_latest.json`)을 입력으로 `bible_meaning_knowledge_ip_report_latest.json` 생성. `purpose=knowledge_ip_only`, `not_for_trading_signal=true` 고정. |
| Track K 시각화 JSON 포맷 | `docs/final/artifacts/bible_meaning_knowledge_ip_viz_latest.json` | 허브(`hubs`)·브리지(`bridges`)·경로(`paths`)를 고정 키로 제공해 리포트/UI 시각화에 재사용. |
| Track T survivor 건강도 경보 | `scripts/alert_insight_survivor_health_v1.py` | `insight_survivor_candidates_latest.json` 기준 `survivor_count`/`survivor_mean_score`를 히스토리(`reports/ops/insight_survivor_health_history.jsonl`)와 비교해 `insight_survivor_health_alert_latest.json` 생성. |
| Two-Track 통합 리포트 | `scripts/build_two_track_fusion_report_v1.py` | Track K(스토리/허브/군집) + Track T(shift_score/survivor_count/health_alert)를 `two_track_fusion_report_latest.json`으로 합성. |
| 사람용 대시보드 브리프 | `scripts/build_two_track_fusion_brief_v1.py` | `two_track_fusion_report_latest.json` 기반으로 헤드라인/카드/스토리라인/가드레일을 담은 `two_track_fusion_brief_latest.json` 생성. |
| 발표용 IP 브리프 | `scripts/build_two_track_fusion_presentation_brief_v1.py` | `two_track_fusion_brief_latest.json` 기반으로 톤(`executive/research/defense`)·카드 우선순위·신뢰도 배지를 적용한 `two_track_fusion_presentation_brief_latest.json` 생성. |
| 슬라이드 copydeck 산출 | `scripts/build_two_track_presentation_copydeck_v1.py` | 발표용 브리프를 입력으로 1페이지 요약(`one_page`) + 3페이지 섹션(`three_page`) 문구를 `two_track_presentation_copydeck_latest.json`으로 생성. |
| 청중별 발표 팩 | `scripts/build_two_track_presentation_audience_pack_v1.py` | copydeck를 입력으로 `investor/policy/technical` 3종 변형을 `two_track_presentation_audience_pack_latest.json`에 생성. |
| 발표자 노트 산출 | `scripts/build_two_track_presenter_notes_v1.py` | audience pack을 입력으로 `60초/180초` 발표 스크립트를 `two_track_presenter_notes_latest.json`에 생성. |
| 청중별 Q&A 팩 산출 | `scripts/build_two_track_qa_pack_v1.py` | presenter notes를 입력으로 `investor/policy/technical`별 5문항 Q&A를 `two_track_qa_pack_latest.json`에 생성. 각 답변은 `evidence(source_artifact/metric_value/as_of_utc/rollback_rule/gate_eval)` 필드를 강제하며, `min_ci_low`·`max_false_positive_cost` 임계치로 실행형 `should_trade/rollback` 판정을 포함한다. |
| 학술 제출 패킷(최소) | `scripts/build_two_track_academic_submission_packet_v1.py` | `score/survivor/qa` 산출물을 입력으로 `abstract_scaffold` + `experiment_table` + `falsification_checklist`를 포함한 `two_track_academic_submission_packet_latest.json` 생성. |
| 반증 스위트(최소) | `scripts/run_two_track_falsification_suite_v1.py` | 학술 패킷/방어 Q&A를 입력으로 `F1~F5` 정의/게이트 존재 여부와 rollback gate snapshot을 `two_track_falsification_suite_latest.json`에 기록. |
| 벤치 비교 리포트 | `scripts/build_two_track_benchmark_comparison_v1.py` | 다중 baseline(`naive_midpoint`, `random_shuffle`, `simple_timeseries_rule`, `ablation_no_survivor_gate`) 대비 proposed(`meaning_graph_survivor_gate`)의 `shift_score/survivor_count` 델타를 `baseline_results[]`로 `two_track_benchmark_comparison_latest.json`에 생성. |
| 유의성 리포트(bootstrap/permutation) | `scripts/build_two_track_statistical_significance_report_v1.py` | benchmark의 primary delta와 `baseline_results[]` 각각에 대해 `bootstrap CI(95%) + sign-flip permutation p-value`를 산출해 `two_track_statistical_significance_report_latest.json` 생성. baseline별 튜닝은 `docs/final/artifacts/two_track_significance_baseline_tuning_v1.json`(`default` + `overrides`)로 주입 가능. |
| 제출 증거 번들 체크리스트 | `scripts/build_two_track_submission_evidence_bundle_v1.py` | 반증/벤치/유의성/raw OOS readiness/public-safe 아티팩트의 존재·생성시각·게이트 상태를 `two_track_submission_evidence_bundle_latest.json`으로 집계해 `bundle_ready` 판정을 제공. |
| 제출용 abstract/목차 초안 생성 | `scripts/build_two_track_submission_draft_v1.py` | evidence bundle + readiness + significance + benchmark + public-safe를 결합해 public-safe 경계가 포함된 `recommended_title`, `abstract_scaffold_en`, `section_outline_en`를 `two_track_submission_draft_latest.json`으로 생성. |
| 카메라레디 확장 초록·회차별 목차(JSON) | `scripts/build_two_track_submission_camera_ready_v1.py` | `two_track_submission_draft_latest.json`을 입력으로 KDD Applied Data Science·AAAI Industry 스타일 확장 초록 단락·세부 목차·포맷 노트를 `two_track_submission_camera_ready_latest.json`에 생성(public-safe 고정). |
| 제출 팩 원클릭(증거번들→초안→카메라레디) | `scripts/run_two_track_submission_pack_v1.ps1` | 체인 `[35/37]`–`[37/37]`만 단독 실행. 시작 시 반증·벤치·유의성·raw OOS readiness·public-safe 등 선행 JSON 존재를 검사하고, 하나라도 없으면 누락 목록 출력 후 **exit 2**. |
| Raw OOS 샘플 스캐폴드 | `scripts/build_two_track_raw_oos_samples_seed_v1.py` | `baseline_results[]`를 기반으로 `two_track_raw_oos_samples_latest.jsonl`를 생성해 유의성 리포트의 `--raw-oos-jsonl` 입력 계약을 충족(출판 전 실측 OOS로 교체 필수). |
| Raw OOS 실측 병합(감사 로그) | `scripts/ingest_two_track_raw_oos_from_audit_v1.py` | 감사 로그의 `shift_score`/`delta_shift_score`를 모든 baseline(`baseline_results`) 기준 델타로 변환해 병합하고, baseline별 최소 샘플 미달 시 audit-derived bootstrap resample로 top-up(`is_seed_scaffold=false`, `is_bootstrap_resample=true`)한다. |
| Raw OOS 준비도 리포트 | `scripts/report_two_track_raw_oos_readiness_v1.py` | baseline별 샘플 수·seed·bootstrap 사용·예상 baseline 누락을 점검해 readiness를 분리 기록하고(`ready_for_internal_significance`, `ready_for_publication_claim`), audit run 기준 잔여 필요 run/예상 완료 시각(`forecast`)까지 산출한다. |
| 공개용 안전 리포트 | `scripts/build_two_track_public_safe_report_v1.py` | academic/benchmark/significance를 입력으로 핵심 이론·가중치·탐색 로직을 마스킹한 `two_track_public_safe_report_latest.json` 생성(`public_safe=true`, `proprietary_details_redacted=true`). |
| 체인 통합 실행 | `scripts/run_aramaic_mvp_chain_v1.ps1` | 아람 추출→그래프→스코어→meaning graph→survivor→Track K/T 산출물→학술 패킷→반증→벤치→raw OOS 스캐폴드→감사 ingest→유의성→readiness→public-safe 이후 **`[35/37]` 제출 증거 번들(`build_two_track_submission_evidence_bundle_v1.py`) → `[36/37]` 제출 초안(`build_two_track_submission_draft_v1.py`) → `[37/37]` 카메라레디 JSON(`build_two_track_submission_camera_ready_v1.py`)**까지 직렬 실행. 앞단 스텝 라벨은 스크립트 내 표기와 동일(예: `[18/20]` 등 혼합), 후반 검증·제출 스택은 **`[28/37]`–`[37/37]`** 구간으로 고정. |

---

## 17. Nemotron Persona × Sasang/Myeongri B-Track Endgame Chain

### 17.1 구현 경로 (실행 스크립트)

- 데이터 fetch/정규화:
  - `scripts/fetch_nemotron_personas_korea_to_btrack_v1.py`
- 코칭 시뮬레이션:
  - `scripts/run_btrack_persona_coaching_simulation_v1.py`
  - 핵심 옵션:
    - `--sasang-mapping-mode {heuristic,random}`
    - `--policy-mode {off,soft,hard}`
    - `--policy-selection-mode {uniform,weighted}`
- 성과 집계:
  - `scripts/build_btrack_persona_coaching_summary_v1.py`
- 정책 생성:
  - `scripts/build_btrack_coaching_policy_from_summary_v1.py`
  - diversity 페널티 옵션:
    - `--diversity-penalty-strength`
- 단일 비교 + CI:
  - `scripts/build_btrack_sasang_mapping_mode_report_v1.py`
- 멀티시드 집계:
  - `scripts/build_btrack_sasang_mapping_mode_multiseed_report_v1.py`
- 원클릭 체인:
  - `scripts/run_btrack_persona_endgame_chain_v1.ps1`
- 스케줄 등록/점검:
  - `scripts/Register-BtrackPersonaEndgameChainTask.ps1`
  - `scripts/Check-BtrackPersonaEndgameTaskStatus.ps1`

### 17.2 게이트 규칙 (운영 고정값)

- 체인 게이트 인자:
  - `-MinAcceptDeltaMean 0.006`
  - `-MaxRejectDeltaMean -0.002`
- 판정:
  - `accept_rate_delta_mean >= 0.006` AND `reject_rate_delta_mean <= -0.002` → `PASS`
  - 미달 시 `exit 2`로 실패 처리.
- 게이트 산출물:
  - `docs/final/artifacts/btrack_persona_endgame_gate_latest.json`

### 17.3 최신 검증 산출물 (B-Track 전용)

- 멀티시드(50k, seeds=41/42/43):
  - `docs/final/artifacts/btrack_sasang_mapping_mode_multiseed_report_latest.json`
- 최신 집계 기준:
  - `accept_rate_delta_mean = +0.0069`
  - `reject_rate_delta_mean = -0.0026`
  - `winner = heuristic`
- 게이트 상태:
  - `docs/final/artifacts/btrack_persona_endgame_gate_latest.json` 기준 `gate_status=PASS`.

### 17.4 스케줄 운영

- 작업명:
  - `MKM_BTrack_Persona_Endgame_Weekly`
- 기본 스케줄:
  - 매주 일요일 01:10 (로컬)
- 등록/삭제:
  - 등록: `powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/Register-BtrackPersonaEndgameChainTask.ps1"`
  - 삭제: `powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/Register-BtrackPersonaEndgameChainTask.ps1" -Remove`

## 18) MKM Study 프로필 계약 SSOT (멀티 사이트 공용)

### 18.1 공통 계약 패키지

- 경로:
  - `packages/mkm-study-profile-contract/package.json`
  - `packages/mkm-study-profile-contract/src/index.ts`
  - `packages/mkm-study-profile-contract/schema/onboarding-request-v1.schema.json`
- 계약 스키마 ID:
  - `mkm_study_student_profile_v1`
- 주요 타입:
  - `StudyOnboardingRequestV1` (wire, snake_case)
  - `StoredStudentProfileFieldsV1` (storage, camelCase)
  - `ConstitutionSurveyV1`
  - `OnboardingStage` (`minimal | birth_complete | extended_complete`)

### 18.2 문서 스키마 미러

- 경로:
  - `docs/final/artifacts/schemas/mkm_study_onboarding_request_v1.schema.json`
- 목적:
  - 공용 HTTP 계약의 문서형 SSOT 미러(다른 사이트/앱 연동 시 참조).

### 18.3 mkm-life 연동 경로

- 패키지 의존성:
  - `projects/mkm/mkm-life/package.json` (`mkm-study-profile-contract` file dependency)
- 번들 트랜스파일:
  - `projects/mkm/mkm-life/next.config.js` (`transpilePackages`)
- 스토어/마이그레이션:
  - `projects/mkm/mkm-life/lib/mkm-study-store.ts`
  - `ensureProfileMigrated`, `profileToStoredContractFields`, `getStudentProfile`
- 생시 파생:
  - `projects/mkm/mkm-life/lib/mkm-study-birth-derive.ts`
- 온보딩/프로필 API:
  - `projects/mkm/mkm-life/app/api/v1/study/onboarding/route.ts`
  - `projects/mkm/mkm-life/app/api/v1/study/profile/route.ts`
- 고급 코치 입력 연결:
  - `projects/mkm/mkm-life/lib/mkm-study-advanced-coach.ts`
  - 하드코딩 출생시각 제거 후 프로필 기반 입력 사용.
- E2E 스모크:
  - `projects/mkm/mkm-life/scripts/smoke-mkm-study-e2e.mjs`
  - npm: `smoke:mkm-study`
  - 스케줄 등록: `projects/mkm/mkm-life/scripts/Register-MkmStudyE2ESmokeTask.ps1`
  - 스케줄 실행 래퍼: `projects/mkm/mkm-life/scripts/run-mkm-study-e2e-smoke-task.cmd`
  - 스케줄 로그: `projects/mkm/mkm-life/reports/mkm_study_e2e_smoke_scheduler_latest.log`
  - 안정화 메모: `MKMLIFE_BASE_URL`/`SMOKE_STUDENT_ID` 환경값은 trim 처리 후 사용(스케줄러 공백 오염 방지).
  - 운영 URL 전환 스크립트: `projects/mkm/mkm-life/scripts/Switch-MkmStudySmokeBaseUrl.ps1`
  - npm: `ops:study-smoke:switch-baseurl` (예: `npm run ops:study-smoke:switch-baseurl -- -BaseUrl "https://<prod-domain>" -RunNow`)
  - 통합 3종 등록(체질승격+고급게이트+스모크): `projects/mkm/mkm-life/scripts/Register-MkmStudyWeeklyOpsTasks.ps1`
  - npm: `ops:study-weekly-tasks:register`

### 18.4 온보딩 필수/선택 계약 (v1)

- 필수:
  - `student_id`, `grade`, `sasang_type`
- 선택(단계 입력):
  - `timezone_iana`, `birth_time_known`, `birth_date`, `birth_datetime`, `birth_location`, `gender`, `constitution_survey`, `onboarding_stage`, `myeongri_profile`

## 19) L1 swap_typo mode-router v3 longsample gate (2026-04-28)

### 19.1 실행 경로 (FACT)

- 게이트 실행:
  - `scripts/run_l1_swap_typo_mode_router_decoder_v3_longsample_gate.py`
- 하니스 베이스라인 생성:
  - `scripts/run_l1_inverse_decoder_longsample_gate_harness_baseline_v1.py`
- 게이트 산출물:
  - `docs/final/artifacts/l1_inverse_decoder_swap_typo_mode_router_decoder_v3_longsample_gate_v1.json`
- 하니스 베이스라인 산출물:
  - `docs/final/artifacts/l1_inverse_decoder_longsample_gate_harness_baseline_v1.json`

### 19.2 최신 결과 (FACT)

- 실행 조건:
  - seeds=`701,809,907,1009,1103`, samples=`240`, beam_size=`8`, noise_level=`0.1`, scoring_mode=`enhanced`
  - `mixed_source=baseline`, `swap_typo_expand=true`, `swap_typo_watchdog_ms=null`
- 판정:
  - `gate.all_ok=true`
  - `gate.decision=GO_CANDIDATE_FOR_CANARY`
- 핵심 델타:
  - `swap_typo_exact_delta=+0.0058333333`
  - `swap_typo_recovery_delta=+0.0108333333`
  - `swap_typo_p95_latency_delta_ms=-28.4801695834`
- 체크:
  - `swap_typo_exact_uplift_ok=true`
  - `swap_typo_recovery_uplift_ok=true`
  - `mixed_non_regression_ok=true`
  - `mixed_latency_p95_ok=true`
  - `swap_typo_latency_p95_ok=true`

### 19.3 게이트 규칙 분기 (FACT)

- `swap_typo_expand=true`:
  - 품질 규칙 `swap_typo_quality_rule=uplift_vs_baseline` 적용(업리프트 검사).
- `swap_typo_expand=false`:
  - 품질 규칙 `swap_typo_quality_rule=non_regression_vs_baseline` 적용(비회귀 검사).
- 목적:
  - beam-only 비교에서 uplift 강제에 따른 오판정(거짓 HOLD)을 줄이고, 확장 경로와 비확장 경로를 분리 평가.

### 19.4 Canary decision/status (FACT, 2026-04-28)

- 결정 아티팩트:
  - `docs/final/artifacts/l1_inverse_decoder_mode_router_v3_canary_decision_v1.json`
  - `decision=GO_CANARY_MODE_ROUTER_V3_10PCT`
- 상태 아티팩트:
  - `docs/final/artifacts/l1_inverse_decoder_mode_router_v3_canary_status_latest.json`
  - `action=KEEP_CANARY`, `phase=phase_1`, `traffic_pct=10`
- 로그:
  - `reports/l1_inverse_decoder_mode_router_v3_canary_log_v1.jsonl` 최신 라인 append 확인.
- 상위 체크:
  - `daily_gate_all_ok=true`
  - `candidate_gate_all_ok=true`

### 19.5 Canary phase progression (FACT, 2026-04-28)

- 실행:
  - `py scripts/run_l1_inverse_decoder_mode_router_v3_canary_monitor.py --phase phase_2 --traffic-pct 30`
  - `py scripts/run_l1_inverse_decoder_mode_router_v3_canary_monitor.py --phase phase_3 --traffic-pct 100`
- 최신 상태:
  - `docs/final/artifacts/l1_inverse_decoder_mode_router_v3_canary_status_latest.json`
  - `phase=phase_3`, `traffic_pct=100`, `action=KEEP_CANARY`, `canary_ok=true`
- 로그 append:
  - `reports/l1_inverse_decoder_mode_router_v3_canary_log_v1.jsonl`에 `phase_2(30%)`, `phase_3(100%)` 라인 추가.

### 19.6 Gate policy lock (Hard/Promotion, FACT, 2026-04-28)

- 적용 스크립트:
  - `scripts/run_l1_swap_typo_mode_router_decoder_v3_longsample_gate.py`
- 정책(고정):
  - `mixed_non_regression_floor = -0.005`
  - `hard_gate.swap_typo_exact_delta_min = 0.0`
  - `hard_gate.swap_typo_recovery_delta_min = 0.0`
  - `hard_gate.latency_p95_delta_max_ms = 25.0`
  - `promotion_gate.swap_typo_exact_delta_min = 0.003`
  - `promotion_gate.swap_typo_recovery_delta_min = 0.005`
  - `promotion_gate.latency_p95_delta_max_ms = 15.0`
- 판정 규칙:
  - `promotion_all_ok=true` → `GO_CANDIDATE_FOR_CANARY`
  - `hard_all_ok=true` & `promotion_all_ok=false` → `KEEP_CANARY_HARD_GATE_ONLY`
  - 그 외 → `HOLD_LATENCY_OR_STABILITY`
- 최신 풀런(5 seed x 240 sample, `swap_typo_expand=true`) 결과:
  - `swap_typo_exact_delta=+0.0133333333`
  - `swap_typo_recovery_delta=+0.0175000000`
  - `swap_typo_p95_latency_delta_ms=-25.3901375000`
  - `gate.decision=GO_CANDIDATE_FOR_CANARY`

## 20) Track 용어 오해 방지 요약 (FACT, 2026-04-28)

- 공식 운영 트랙:
  - Track A = 범용/운영 벤치(효율 우선, 의미 보존 지표 기반)
  - Track B = 리터럴/연구 격벽 레일(안전·재현성 우선, A와 자동 합선 금지)
- 용어 주의:
  - `Track Q`는 본 SSOT의 공식 메인 트랙 명칭으로 고정되어 있지 않다.
- 4D/게마트리아 위치:
  - 4D·게마트리아는 다수 경로에서 보조 특성/가산 채널/연구 스파이크로 사용된다.
  - A/B 트랙의 공식 명칭·승격 규칙 자체를 대체하지 않는다.
- 수치 해석 주의:
  - “A는 고압축”, “B는 무손실 원문” 같은 문장은 경향 요약으로는 유효하나, 모든 러너/프로파일에 절대값으로 일반화하면 오판 가능.
  - 실제 판정은 해당 시점의 아티팩트(`...ACTIVE_REPORT*.json`, gate JSON)의 필드값으로 확정한다.

## 21) v3 코드북 확장 필요성 자동 판정 (FACT, 2026-04-28)

- 실행 스크립트:
  - `scripts/recommend_l1_mode_router_v3_codebook_expansion_v1.py`
- 산출물:
  - `docs/final/artifacts/l1_inverse_decoder_mode_router_v3_codebook_expansion_recommendation_latest.json`
- 기본 입력:
  - canary 로그 `reports/l1_inverse_decoder_mode_router_v3_canary_log_v1.jsonl`
  - longsample 게이트 `docs/final/artifacts/l1_inverse_decoder_swap_typo_mode_router_decoder_v3_longsample_gate_v1.json`
  - lookback 7일
- 최신 판정:
  - `recommendation=HOLD_RELIABILITY_VOLATILE`
  - 근거: `recent_rollbacks_present` (window `rollback_count=2`)
  - 스냅샷: `gate.decision=GO_CANDIDATE_FOR_CANARY`, `hard_all_ok=true`
- 해석:
  - 즉시 대규모 도메인 코드북 확장보다 안정화 관측 우선.
  - 도메인별 타깃 확장은 domain signal JSON이 확보될 때 조건부로 트리거.

## 22) Genesis Gematria-4D Codebook 파일럿 (FACT, 2026-04-28)

- 실행 스크립트:
  - `scripts/build_genesis_gematria_4d_codebook_v1.py`
- 산출물:
  - `docs/final/artifacts/genesis_gematria_4d_codebook_v1_latest.json`
- 범위:
  - 기본 10단어(폭락/금화교역/태양인/변동성 등) 대상 `address_hash64_hex` + `vector_4d` 생성.
  - `research_only=true`, `promotion_required=true`, `source_track=B`.
- 복원 프로브:
  - `exact_match_rate=1.0` (해시 주소 exact lookup 기준).
- 압축 추정(동일 파일럿):
  - `raw_utf8_bytes_total=78`
  - `pointer_payload_bytes_total=80` → `pointer_saving_rate=-0.0256`
  - `vector4_payload_bytes_total=160` → `vector4_saving_rate=-1.0513`
- 해석:
  - 10단어 toy 파일럿에서는 “주소/좌표 페이로드 오버헤드” 때문에 순압축 이득이 아직 없다.
  - 따라서 “99% 압축·100% 복원”은 현 단계 FACT가 아니며, 대규모 코드북·시퀀스 경로에서 별도 벤치가 필요.

## 23) Genesis 시퀀스 길이별 압축 스윕 (FACT, 2026-04-28)

- 실행 스크립트:
  - `scripts/run_genesis_sequence_compression_sweep_v1.py`
- 산출물:
  - `docs/final/artifacts/genesis_sequence_compression_sweep_latest.json`
- 기본 실험:
  - lengths=`10,20,40,80,120,200,400,800,1200`, samples_per_length=`64`
- 결과 요약:
  - closed-dictionary lookup 시뮬레이션에서 `pointer_break_even_length_chars=10`, `vector4_break_even_length_chars=10`
  - 길이가 길수록 pointer 기준 saving rate가 상승(예: 400 chars 버킷에서 `~0.9917`)
- 해석 제한(중요):
  - 본 스윕은 **페이로드 바이트 비교 실험**이며, 코드북 구축/동기화/버전 관리 오버헤드는 포함하지 않는다.
  - `exact_lookup_rate=1.0`은 “닫힌 사전 exact lookup” 조건의 결과로, open-vocabulary 운영 복원을 직접 보증하지 않는다.

## 24) Genesis 순효율(Net) 모델 — 동기화 오버헤드 반영 (FACT, 2026-04-28)

- 실행 스크립트:
  - `scripts/run_genesis_sequence_net_efficiency_model_v1.py`
- 산출물:
  - `docs/final/artifacts/genesis_sequence_net_efficiency_model_latest.json`
- 기본 모델 파라미터:
  - `nodes=20`
  - `daily_sync_bytes=10,485,760` (10 MiB/day)
  - `daily_message_count=200,000`
  - `amortized_sync_bytes_per_message=2.62144`
- 요약:
  - `pointer_net_break_even_length_chars=10`
  - `vector4_net_break_even_length_chars=10`
  - 400 chars 버킷 기준 `pointer_net_saving_rate≈0.9890`
- 해석 제한:
  - 균등 분할(메시지/노드) 가정의 모델 값이며, 실제 운영 효율은 churn/cache hit/retry 트래픽에 따라 달라진다.

## 25) Genesis 순효율 민감도 스윕 (FACT, 2026-04-28)

- 실행 스크립트:
  - `scripts/run_genesis_sequence_net_efficiency_sensitivity_v1.py`
- 산출물:
  - `docs/final/artifacts/genesis_sequence_net_efficiency_sensitivity_latest.json`
- 기본 그리드:
  - nodes=`[1,5,20,50]`
  - daily_sync_bytes=`[1MiB,10MiB,50MiB]`
  - daily_message_count=`[50k,200k,1M]`
  - 총 `scenario_count=36`
- 요약:
  - 400 chars 기준 pointer 순절감률 `>= 0.99` 구간 수: `13`
  - 고오버헤드 시나리오(예: nodes=1, sync=50MiB/day, msg=50k/day)는 400 chars에서도 음수/저효율 가능.
  - 반대로 분산/고트래픽 조건에서는 400 chars에서 `~0.99` 구간 다수 관측.
- 해석:
  - “99% 구간”은 존재하지만 운영 조건(노드 수·메시지량·사전 동기화 비용)에 민감.
  - 따라서 본선 주장 시 단일 숫자보다 운영 파라미터와 함께 제시해야 Fact-Lock 정합.

## 26) Genesis 운영 권장영역(Go/Watch/Hold) 라벨링 (FACT, 2026-04-28)

- 실행 스크립트:
  - `scripts/label_genesis_net_efficiency_operating_zone_v1.py`
- 산출물:
  - `docs/final/artifacts/genesis_sequence_net_efficiency_operating_zone_latest.json`
- 기본 컷:
  - `GO`: pointer_net_saving_rate_at_400_chars `>= 0.99` AND pointer_break_even `<= 20`
  - `WATCH`: pointer_net_saving_rate_at_400_chars `>= 0.95` AND pointer_break_even `<= 120`
  - 그 외 `HOLD`
- 최신 집계:
  - `GO=13`, `WATCH=14`, `HOLD=9` (총 36 시나리오)
- 해석:
  - 고오버헤드·저트래픽 조합은 `HOLD`가 명확하며, 분산/고트래픽 조건에서 `GO` 비중이 증가.

### 26.1 지휘관 기준 임계값 재적용 (FACT, 2026-04-28)

- 재실행:
  - `py scripts/label_genesis_net_efficiency_operating_zone_v1.py --go-cut 0.9 --watch-cut 0.5`
- 최신 컷:
  - `GO`: 순효율 `>= 0.9`
  - `WATCH`: `0.5 <= 순효율 < 0.9`
  - `HOLD`: `< 0.5`
- 최신 집계:
  - `GO=27`, `WATCH=8`, `HOLD=1`
- HOLD 대표 시나리오:
  - `nodes=1`, `daily_sync_bytes=50MiB`, `daily_message_count=50k`
  - `pointer_net_saving_rate_at_400_chars=-0.0932` (음수)

## 27) Genesis 판정기 → 라우팅 스위치 연결 (FACT, 2026-04-28)

- 결정 스크립트:
  - `scripts/decide_genesis_pointer_routing_v1.py`
- 체인 스크립트(원클릭):
  - `scripts/run_genesis_pointer_routing_control_chain_v1.py`
  - sweep → net model → sensitivity → zone label → routing decision 순서로 직렬 실행.
- 결정 아티팩트:
  - `docs/final/artifacts/genesis_pointer_routing_decision_latest.json`
  - 최신값: `decision=SHADOW_POINTER_ROUTE`, `route_mode=pointer_shadow`
  - 근거: `go_ratio=0.75`, `hold_count=1` (enable 조건 `hold_count<=0` 미충족)
- 체인 아티팩트:
  - `docs/final/artifacts/genesis_pointer_routing_control_chain_latest.json`
  - 최신값: `all_ok=true`
- 안전장치:
  - fallback 모드: `track_a_primary`
  - 강제 비활성 환경변수: `GENESIS_POINTER_ROUTE_FORCE_DISABLE=1`

### 27.1 런타임 설정 브리지 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_genesis_pointer_route_runtime_config_v1.py`
- 산출물:
  - `docs/final/artifacts/genesis_pointer_route_runtime_config_latest.json`
- 역할:
  - 정책 결정 JSON(`genesis_pointer_routing_decision_latest.json`)을 런타임 소비용 단일 설정으로 변환.
  - 주요 필드: `pointer_enabled`, `pointer_shadow`, `track_a_primary`, `disable_switch_env`.
- 체인 반영:
  - `scripts/run_genesis_pointer_routing_control_chain_v1.py` 마지막 단계에 runtime config 생성 포함.
  - 최신 기준 `route_mode=pointer_shadow`, `pointer_enabled=false`, `pointer_shadow=true`.

### 27.2 Pointer Hash Snapping Router (Shadow) (FACT, 2026-04-28)

- 스크립트:
  - `scripts/pointer_hash_snapping_router_v1.py`
- 산출물:
  - `docs/final/artifacts/pointer_hash_snapping_router_shadow_latest.json`
- 동작:
  - 런타임 설정(`genesis_pointer_route_runtime_config_latest.json`)과 Genesis 코드북을 읽어 입력 텍스트를 pointer 후보로 평가.
  - `--enable-snap` 시 OOV 토큰에 대해 근접 문자열 스냅(L3 유사 가드)을 시도.
  - Shadow 모드에서는 pointer 후보가 유효해도 실선택 경로는 `track_a_primary` 유지(관측 전용).
- 최신 스모크:
  - `pointer_candidate_ok_count=2`, `selected_pointer_count=0`, `selected_track_a_count=3`
  - 체인(`run_genesis_pointer_routing_control_chain_v1.py`)에 shadow router 단계 포함 후 `all_ok=true`.

### 27.3 Shadow 일일 통계 리포터 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_pointer_shadow_daily_report_v1.py`
- 산출물:
  - `docs/final/artifacts/pointer_hash_snapping_router_shadow_daily_report_latest.json`
  - `reports/pointer_hash_snapping_router_shadow_log_v1.jsonl`
- 집계 항목:
  - `avg_pointer_candidate_ok_rate`
  - `avg_snap_event_rate`
  - `avg_unresolved_token_per_run`
- 체인 반영:
  - `run_genesis_pointer_routing_control_chain_v1.py`에 daily reporter 단계 포함.
- 최신 24h 샘플:
  - `sample_count=1`
  - `avg_pointer_candidate_ok_rate=0.6667`
  - `avg_unresolved_token_per_run=4.0`

### 27.4 Shadow 헬스 알림 게이트 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/check_pointer_shadow_health_alert_v1.py`
- 산출물:
  - `docs/final/artifacts/pointer_hash_snapping_router_shadow_alert_latest.json`
- 기본 임계값:
  - `min_sample_count=3`
  - `candidate_ok_rate_min=0.4`
  - `max_unresolved_per_run=8.0`
- 체인 반영:
  - `run_genesis_pointer_routing_control_chain_v1.py`에 alert check 단계 포함.
- 최신 상태:
  - `should_alert=false`, `severity=none` (현재 `sample_count=2`)

### 27.5 Alert 기반 자동 강등 가드 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/apply_pointer_shadow_alert_guard_v1.py`
- 산출물:
  - `docs/final/artifacts/genesis_pointer_routing_decision_guarded_latest.json`
- 규칙:
  - alert(`should_alert=true`)이면 결정을 강제로 `HOLD_POINTER_ROUTE` + `track_a_primary`로 강등.
  - alert가 없으면 원결정 유지(`guard_applied=false`).
- 체인 반영:
  - `run_genesis_pointer_routing_control_chain_v1.py`에서 alert check 이후 guard 적용.
  - runtime config는 guarded decision JSON을 입력으로 생성.
- 최신 상태:
  - `guard_applied=false`, `guard_reason=no_alert`
  - runtime `route_mode=pointer_shadow` 유지.

### 27.6 Guard 강등 드릴(Chaos Test) (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_pointer_shadow_guard_drill_v1.py`
- 산출물:
  - `docs/final/artifacts/pointer_shadow_guard_drill_latest.json`
- 검증 시나리오:
  1) alert 임계값을 강제로 타이트하게 적용해 `should_alert=true` 유도
  2) guard 적용 후 `decision=HOLD_POINTER_ROUTE`, `route_mode=track_a_primary` 강등 확인
  3) 기본 alert 임계값으로 복원
- 최신 결과:
  - `drill_passed=true`
  - forced alert `severity=high`
  - guard snapshot `guard_applied=true`, `guard_reason=shadow_health_alert_triggered`

### 28. Two-Track 통계/게이트/제출 동결 고도화 (FACT, 2026-04-28)

#### 28.1 통계 유의성 엔진 실계산화 (FACT)

- 스크립트:
  - `scripts/build_two_track_statistical_significance_report_v1.py`
- 변경:
  - 기존 stub 방식(`bootstrap+signflip_stub`)에서 실제 계산 방식으로 전환.
  - 현재 메서드: `bootstrap_mean_ci+signflip_permutation`
  - 출력 필드 확장: `std_dev`, `alpha`, `bootstrap_iterations`, `permutation_iterations`.
- 최신 산출물:
  - `docs/final/artifacts/two_track_statistical_significance_report_latest.json`
  - 대표값: `p_value=0.0002499...`, `significance_interpretation=positive_delta_supported`.

#### 28.2 Raw OOS 다양성(분산) 강화 (FACT)

- 스크립트:
  - `scripts/run_aramaic_mvp_now_with_audit.ps1`
  - `scripts/ingest_two_track_raw_oos_from_audit_v1.py`
  - `scripts/report_two_track_raw_oos_readiness_v1.py`
- 변경:
  - audit row에 OOS 시나리오 필드 추가:
    - `oos_shift_score`, `oos_delta_shift_score`
    - `oos_scenario` (`neutral` / `stress_tilt` / `risk_on_tilt`)
    - `oos_scenario_adjusted`, `conflict_ratio`, `insight_cap_bucket`
  - ingest는 `oos_*` 필드를 우선 사용해 baseline delta를 생성.
  - readiness에 `scenario_adjusted_rows` 지표 추가.
- 최신 상태:
  - `docs/final/artifacts/two_track_raw_oos_readiness_latest.json`
  - `observed_audit_runs=70`, `scenario_adjusted_rows=156`
  - `seed_rows=0`, `bootstrap_rows=0`, `ready_for_publication_claim=true`.

#### 28.3 Fail-Boundary 운영 게이트 연결 (FACT)

- 스크립트:
  - `scripts/alert_two_track_fail_boundary_gate_v1.py`
- 산출물:
  - `docs/final/artifacts/two_track_fail_boundary_gate_latest.json`
- 규칙:
  - `survivor_count >= max_safe_min_survivor_count` 이면 `should_trade=true`, 아니면 `rollback=true`.
- 체인 반영:
  - `scripts/run_aramaic_mvp_chain_v1.ps1`에 `[28b/37]` 단계 추가.
  - 순서: falsification suite -> boundary report -> fail-boundary gate.
- 최신 상태:
  - `survivor_count=5`, `max_safe_min_survivor_count=5`
  - `gate_eval.should_trade=true`, `gate_eval.rollback=false`.

#### 28.4 제출 동결 체크리스트 자동화 (FACT)

- 스크립트:
  - `scripts/build_two_track_submission_freeze_v1.py`
  - `scripts/build_two_track_submission_checklist_v1.py`
- 산출물:
  - `docs/final/artifacts/two_track_submission_freeze_latest.json`
  - `docs/final/artifacts/two_track_submission_checklist_latest.json`
- 역할:
  - 제출 핵심 8개 아티팩트를 timestamp freeze 디렉터리로 복사/동결.
  - 체크리스트에서 존재 여부, `generated_at_utc`, 재현 명령(`repro_commands`)을 단일 JSON로 제공.
- 최신 상태:
  - `submission_ready=true`
  - `freeze_missing_count=0`
  - 동결 경로 예: `docs/final/artifacts/freeze/two_track_submission_20260428T043821Z`.

#### 28.5 제출 트랙 권장/템플릿 고정 (FACT)

- 스크립트:
  - `scripts/build_two_track_kdd_submission_template_v1.py`
- 산출물:
  - `docs/final/artifacts/two_track_submission_recommended_track_latest.json`
  - `docs/final/artifacts/two_track_kdd_submission_template_latest.json`
- 역할:
  - 권장 트랙(`kdd_applied_data_science`)과 제출 후보 라벨을 고정.
  - KDD 폼 입력용 `title/abstract_180w/keywords/contributions`를 단일 JSON으로 제공.
- 최신 상태:
  - 추천 트랙: `kdd_applied_data_science`
  - 제출 템플릿 JSON 생성 완료.

#### 28.6 제출 실행 Go/No-Go 아티팩트 (FACT)

- 스크립트:
  - `scripts/build_two_track_submission_go_nogo_v1.py`
- 산출물:
  - `docs/final/artifacts/two_track_submission_go_nogo_latest.json`
- 규칙:
  - `submission_ready` AND `bundle_ready` AND `ready_for_publication_claim`
  - AND fail-boundary gate(`should_trade=true`, `rollback=false`)
  - 위 조건 모두 충족 시 `status=GO`, 아니면 `NO_GO` + reason 목록.
- 최신 상태:
  - `status=GO` (체크리스트/증거번들/fail-boundary gate 기준 충족).

### 29. PointerGuard Router 워크스페이스 폴더별 적용 정책표 (DRAFT, 2026-04-28)

- 정책 원칙(고정):
  - 기본값은 `비적용`이며, **명시적 allowlist**에 포함된 경로만 Pointer 경로를 사용한다.
  - 신규 경로는 `Shadow` 관측(최소 7일 또는 운영자가 정한 윈도우) 통과 전 `GO` 승격 금지.
  - `금지` 구역은 Track B 무손실 원문 보호를 우선하며 Pointer 경로를 상시 차단한다.
  - Alert guard(`check_pointer_shadow_health_alert_v1.py` + `apply_pointer_shadow_alert_guard_v1.py`)는 전 구간 공통 적용한다.

| 워크스페이스 경로(패턴) | 정책 | 기본 Route Mode | 근거/사유 | 적용 조건 |
| --- | --- | --- | --- | --- |
| `docs/final/artifacts/` | 적용 | `pointer_shadow` -> `pointer_go` | 정형 JSON/리포트가 반복 생성되어 순이익 구간 진입 가능성이 높음 | Shadow 지표(`candidate_ok_rate`, `unresolved`) 안정 후 GO |
| `reports/` | 적용 | `pointer_shadow` -> `pointer_go` | 일별/주별 반복 로그·요약 산출물이 많아 포인터 압축 효율이 큼 | 동기화 오버헤드 포함 순절감률이 GO 임계 이상 |
| `projects/bitcoin-trading/memory/v2/` | 적용 | `pointer_shadow` -> `pointer_go` | 운영 관측 산출물의 반복 패턴이 강함 | 운영 가드릴·복구 리허설 통과 |
| `memory/obsidian_vault/llm_wiki/wiki/` | 주의 | `pointer_shadow` 유지 | 지식 합성 산출물은 반복성이 있으나 문맥 보존 요구가 큼 | Shadow-only, 수동 승인 전 GO 금지 |
| `docs/final/`(아티팩트 제외) | 주의 | `track_a_primary` | SSOT 본문/서술 문서는 변경 민감도가 높음 | 파일 단위 allowlist + diff 검증 시 제한적 Shadow |
| `data/logos/**/bench/` | 주의 | `track_a_primary` | 벤치 입력/정답셋은 재현성 핵심 자산 | 복제본에서만 Shadow 테스트, 원본 경로 GO 금지 |
| `scripts/` | 금지 | `track_a_primary` 고정 | `.py/.ps1` 실행 코드 경로는 토큰 단위 변형 리스크 치명적 | Pointer 라우팅 비활성(하드 블록) |
| `api-services/` | 금지 | `track_a_primary` 고정 | API/런타임 코드는 버전·의미 보존이 절대 조건 | Pointer 라우팅 비활성(하드 블록) |
| `.github/workflows/` | 금지 | `track_a_primary` 고정 | CI 계약 YAML은 공백/문자 단위 오류에 취약 | Pointer 라우팅 비활성(하드 블록) |
| `.cursor/`, `AGENTS.md`, `CLAUDE.md`, `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` | 금지 | `track_a_primary` 고정 | 규칙/헌법/지휘 SSOT는 무손실 원문 보전이 최우선 | Pointer 라우팅 비활성(하드 블록) |
| `data/**` 원천 코퍼스/라벨셋 | 금지 | `track_a_primary` 고정 | 학습·평가 원천 데이터의 바이트 동일성 필요 | Pointer 라우팅 비활성(하드 블록) |

- 운영 메모:
  - `적용` 구간도 최초에는 `pointer_shadow`로 시작하고, zone 판정이 `GO`인 경우에만 `pointer_go` 승격한다.
  - `주의` 구간은 기본적으로 `Shadow 전용`이며, 운영자 수동 승인 없는 자동 승격을 금지한다.
  - `금지` 구간은 정책 위반 시 즉시 `HOLD_POINTER_ROUTE`로 강등한다.

#### 29.1 실행 연결 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_pointerguard_folder_policy_v1.py`
  - `scripts/build_genesis_pointer_route_runtime_config_v1.py` (`--folder-policy-json` 입력 지원)
  - `scripts/pointer_hash_snapping_router_v1.py` (`--target-path` 기준 폴더 정책 적용)
  - `scripts/run_genesis_pointer_routing_control_chain_v1.py` (폴더 정책 빌드 단계 포함)
- 산출물:
  - `docs/final/artifacts/pointerguard_folder_policy_latest.json`
  - `docs/final/artifacts/genesis_pointer_route_runtime_config_latest.json`
- 최신 스모크:
  - folder policy summary: `apply=3`, `caution=3`, `forbid=8`
  - runtime config 생성 성공(`ok=true`)
  - router `--target-path docs/final/artifacts/demo.json` 실행 시 정책 기준으로 Track A 경로 유지(현재 guarded decision 기준)
