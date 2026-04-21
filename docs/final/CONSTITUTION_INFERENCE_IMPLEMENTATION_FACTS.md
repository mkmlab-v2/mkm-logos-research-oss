# Constitution / Inference — 구현 팩트 (SSOT)

**작성일**: 2026-03-29  
**최종 갱신**: 2026-04-19 — 기상 관측 라벨→`general_prophecy` 트리플(B-track 교정 측정용): 스키마 `docs/final/schemas/weather_ground_truth_row_v1.schema.json`·`scripts/csv_to_weather_ground_truth_jsonl_v1.py`·`scripts/weather_csv_sniff_v1.py`·`scripts/validate_weather_ground_truth_jsonl_v1.py`·`scripts/validate_weather_forecasts_jsonl_against_gt_v1.py`·`scripts/emit_weather_forecasts_jsonl_template_from_gt_v1.py`·`scripts/optimize_weather_lens_fusion_weights_v1.py`(융합 가중 그리드)·`scripts/build_weather_btrack_summary_comparison_v1.py`(요약 비교)·`scripts/build_weather_btrack_reliability_check_v1.py`(delta gate)·`scripts/append_weather_reliability_audit_to_go_nogo_v1.py`(`a_track_go_nogo_status_latest.json` 감사 로그 append)·`build_weather_triplet_registry_v1.py`(`--fusion-weight-myeongri`)·`scripts/run_weather_gt_to_prophecy_triplet_chain_v1.py`(`--fusion-search-json`)·`scripts/run_weather_synthetic_120d_chain_and_brier_v1.py`·`scripts/run_weather_synthetic_120d_optimize_fusion_then_chain_v1.ps1`·`scripts/run_weather_btrack_hypo_fusionopt_to_artifacts_v1.py`·`scripts/run_weather_btrack_external_forecasts_to_artifacts_v1.py`·`scripts/run_weather_btrack_external_real_week_chain_v1.ps1`·`scripts/run_weather_btrack_external_real_week_full_gate_v1.ps1`·산출 `docs/final/artifacts/weather_btrack_pipeline_hypo_fusionopt_summary_v1.json`(HYPO 고정)·`docs/final/artifacts/weather_btrack_pipeline_external_hypo_120d_v1_summary.json`(외부 입력 체인 스모크)·`docs/final/artifacts/weather_btrack_summary_comparison_hypo_vs_external_hypo_120d_v1.json`(비교)·`eval_general_prophecy_brier_score.py`(`--no-print-output-path`·`ece_binary`·`ece_binary_by_domain_tag`)·회귀 `tests/test_weather_gt_triplet_chain_smoke.py`·선택 스모크 `scripts/run_workspace_automation_health.ps1`(`-IncludeWeatherPipelineSmoke`)·P0 `verify_p0_constitution_gate_paths.ps1`·CI `dual-regime-integrity.yml` (본문 단락 동일). **이전 갱신**: 2026-04-18 — §1.1.1 `[VISION]` 예언 성능 우선·국방 서사 `research_only` 격리; OHLCV 30일 패널 **재빌드 후 스윕 재실행**(best_delta 동일 **-4.8%**·수정 최소 타이브레이크); `prophecy_overlay_prior_threshold_recommended_latest.json`·`prophecy_prior_threshold_sweep_summary_latest.json`; `eval_prophecy_hit_rate_v1.py --run-mode price`; 스파이크 기본 `-0.048`; CI `prophecy-restoration-spike-smoke.yml`; 이전 갱신: Prism §14 Prophecy 오버레이 단락·스키마 `prophecy_overlay_ablation_spike_v1`; 그 이전: 2026-04-14 — `google.genai` `HttpOptions.timeout` ms 정합(`gemini_multimodal_batch`·`staging_shard_inference_run`·`generate_btrack_hypothesis_prophecy_v1`); `fill_human_regime_audit_llm_spike` 루트 `.env` 로드; dual-regime-integrity에 `zstandard` 의존성 및 branch-optional 스파이크 pytest 파일 존재 가드(미추적 시 skip, 추적 시 엄격 실행).  
**이전 갱신**: 2026-04-14 §2 B-track `4d_to_ohaeng`·human regime audit 스파이크 행; §3.4.1 Postella; 2026-04-13 §1.2 AE-2 KOSPI.  
**목적**: “기획·NotebookLM·헌법 문서만 보고 구현됨”이라고 단정하지 않도록, **호출 가능한 경로**와 **검증 상태**를 한곳에 고정한다.

**갱신 (2026-04-21):** §8.1 Bio Sasang×논문 SNP **경계 팩트** 및 조인 게이트 `scripts/spec_bio_sample_paper_snp_join_gate_v1.py` 추가. 유전자명–체질 고정 매핑 표는 **본 문서 FACT 본문에 등재하지 않음** (`[HYPO]`·연구 노트 전용). 동 절 관련 스크립트·`bio_measured_labels_paper_snp_sidecar_v1.json`·매핑 템플릿 CSV는 `scripts/verify_p0_constitution_gate_paths.ps1` 필수 목록에 포함. CI 스모크: `.github/workflows/bio-paper-snp-sidecar-smoke.yml`·`tests/test_bio_paper_snp_join_chain_smoke_v1.py`·`tests/test_run_bio_paper_snp_sidecar_export_and_apply_v1_cli.py`·`tests/test_run_bio_epmc_catalog_and_label_merge_v1_cli.py`; 동일 pytest는 `dual-regime-integrity.yml`에도 포함(PR paths에 Bio SNP 경로 추가). 매핑 선행 점검: `scripts/check_bio_paper_snp_mapping_coverage_v1.py`. 로컬 헬스 선택: `scripts/run_workspace_automation_health.ps1 -IncludeBioPaperSnpJoinSmoke`. Windows 래퍼: `scripts/Run-BioPaperSnpSidecarExportAndApply.ps1`.

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
| HTTP v2 Trust Packet (OpenAPI + stub) | `docs/final/openapi_token_compression_v2_draft.yaml` | FastAPI: `scripts/compression_token_api_v2_stub.py` — `POST /v2/compress`, `POST /v2/expand`; 압축 경로는 `evaluate_report` + 도메인 라우터(초안 명칭 `GlobalPivotCompressionPipeline` 대체). 상용 SLA 아님. §11 |
| Master codebook lexicon V1 export | `scripts/export_master_codebook_v1.py` | 아톰+Strong+MorphHB 시드 조인 산출; 루브릭은 동 COMPRESSION 문서 §9 |
| Master codebook lexicon V1 → multilens route join (bridge) | `scripts/core/master_codebook_lexicon_v1_bridge.py` | `evaluate_report(..., use_master_codebook_lexicon_v1=True)` 시 원문 토큰과 `normalized_form` 교집합으로 must_keep 보강; 4D·샤드 정책 대체 아님. 호출부: `report_multilens_performance_eval.py`, ultra/P1 러너·벤치·압축 스텁 |
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
| 토큰 압축 API (스텁 v1) | `scripts/compression_token_api_stub.py` | FastAPI: `POST /v1/compress`, `POST /v1/expand`, `GET /health`. **연구 레인(additive):** `POST /v1/research/l1_side_channel/wire` — L1 사이드 채널 최소 페이로드를 `scripts/l1_side_channel_wire_codec.py`(`encode_adaptive_msgpack` 등)로 적응형 와이어 인코딩·base64 반환; **HTTP 503**: (1) 런타임에 msgpack 미설치, (2) 내부 `msgpack_payload_bytes`가 `None`(pack 불가). 응답에 `api_contract_version`; `eval_context.hydrate_metrics` 없으면 `compression_metrics` null(라우터만). **enterprise 티어**에서 `hydrate_live_eval` 시 `evaluate_report` 시도·실패 시 `integrity_flags.hydration_live_eval_failed` 가능. **public 티어(Track B·literal KPI 추정)**는 동일 요청 시 `hydrate_live_eval_suppressed`로 라이브 경로 차단. **expand는 원문 에코**. 회귀: `tests/test_compression_token_api_stub.py`(OpenAPI 경로 포함·와이어 라운드트립·`test_public_tier_bulkhead_never_calls_live_eval_even_when_requested`). 대외 설명 SSOT: `COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` §10 + `openapi_token_compression_stub_v1.yaml` description. |
| 토큰 압축 스텁 부하 벤치 (§9.2 draft SLA) | `scripts/bench_l1_api_load.py` → `docs/final/artifacts/bench_l1_api_load_latest.json` | stdlib `urllib` 스레드 풀; **클라이언트 RTT** p50/p95/p99. 서버 RSS는 동일 호스트 `--server-pid`+`psutil` 선택. `research_only`/`draft_benchmark`; FACT 승격은 플레이북 9.2 절차. dry-run 회귀: `tests/test_bench_l1_api_load.py`. |
| OpenAPI (압축 스텁) | `docs/final/openapi_token_compression_stub_v1.yaml` | HTTP 계약(SSOT); `info.version` **1.1.1+** (예시 문서만 PATCH). `mode_live` 요청 예시 텍스트는 기본 `COMPRESSION_API_LIVE_EVAL_MIN_TOKENS`(12, 스텁 `TOKEN_RE` 토큰 수) 이상. EvalContext·HydrationHints·CompressionMetrics 스키마 포함. **v1.1.0** 에 `POST /v1/research/l1_side_channel/wire` 추가; 스키마 `L1SideChannelWireRequest` / `L1SideChannelWireResponse`, 응답 `schema_version` 예시 `l1_side_channel_wire_stub_v1`. 상용 SLA·인증은 범위 외. |
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
| 우선순위 체인·강건성 | `scripts/run_bio_sasang_priority_chain_v1.py`, `scripts/run_bio_sasang_external_robustness_v1.py`, `scripts/run_bio_sasang_multimodal_robustness_v1.py` | 입력은 **단백질 서열·DDG·멀티모달 JSON**; **원시 DNA 염기서열·지노타입·타깃 SNP 지정**은 내장되어 있지 않음 |
| 실행 상태 합성 | `scripts/build_bio_sasang_priority_execution_status_from_reports_v1.py` | `reports/bio_sasang_priority_execution_status_v4.json` |
| 프로모션 판정 | `scripts/build_bio_sasang_promotion_decision_v1.py` | 임계값은 CLI 정책 입력; **유전자 표 삽입 없음** |
| 완화 GO 번들 | `scripts/run_bio_sasang_promotion_relaxed_go_bundle_v1.py` | strict 스냅샷 + relaxed `promotion_decision_v1_latest` |
| **조인 게이트** | `scripts/spec_bio_sample_paper_snp_join_gate_v1.py` | 매핑 CSV(`sample_id`+`pmid`) 없이 PMID 사이드카를 샘플 행에 붙이려 하면 **exit 2** (`--explain-only`로 정책 출력) |
| **사이드카→샘플 적용** | `scripts/apply_bio_paper_snp_sidecar_to_samples_v1.py` | 게이트(`check_join_gate`) 통과 후 매핑으로 `paper_pmid`, `paper_snp_ids_final_v3` 등 컬럼 추가; 기본 리포트 `reports/bio_paper_snp_sidecar_sample_join_v1_latest.json` |
| **v3→JSON→샘플(EPMC 제외)** | `scripts/run_bio_paper_snp_sidecar_export_and_apply_v1.py`, `scripts/Run-BioPaperSnpSidecarExportAndApply.ps1` | `export_*_sidecar` + `apply_*` 연쇄; 선택 `--mapping-coverage-min`(0 초과 시 선행 커버리지 strict, 미달 exit **2**); PS1은 `-MappingCoverageMin` 또는 단축 `-StrictMappingCoverage95` |
| **sample↔PMID 매핑 추출** | `scripts/export_bio_sample_paper_pmid_mapping_from_cohort_v1.py` | 코호트에 **이미 있는** `paper_pmid`(또는 `pmid`) 열만 사용; 수동 편집 템플릿 `docs/final/artifacts/bio_sample_paper_pmid_mapping_template_v1.csv` |
| **매핑 커버리지(선행 점검)** | `scripts/check_bio_paper_snp_mapping_coverage_v1.py` | 코호트 `sample_id` 대비 매핑에 PMID가 있는 비율·JSON 리포트 기본 `reports/bio_paper_snp_mapping_coverage_v1_latest.json`; `--strict` 시 미달 exit **2** |

**격벽 (Fact-Lock):**

1. **코호트 A vs 원전·Proxy B:** `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` — B를 본선 분류·204 OOF·자동 합선하지 않는다.
2. **체질↔SNP 클러스터 고정표:** 검증된 재현 파이프와 코호트 계약이 없으면 **`[HYPO]`**로만 다룬다; **본 §8.1 표에 유전자명–태음/소양 등 매핑을 넣지 않는다.**
3. **신뢰 가중치 배수 (예: 설문 대비 DNA 2.5×):** 헌법 상수로 고정하지 않으며, **스윕·홀드아웃 리포트**가 있기 전에는 코드/설정 실험 분기로만 둔다.

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
