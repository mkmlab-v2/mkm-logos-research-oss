<#
.SYNOPSIS
  로컬 Fact-Lock 번들 — GitHub Actions `dual-regime-integrity.yml`과 **동일 pytest·스크립트 집합**을 Windows에서 회귀한다.

.DESCRIPTION
  CI `dual-regime-integrity.yml` 단일 잡에는 토큰 API·렌즈 뮤직·Athena §28 블록 등 **긴 전제 단계**가 끼어 로컬 번들의 **상대 순서**(예: meta 봉투 vs `test_athena_checkpoint` vs Logos)와 1:1로 같지 않을 수 있다. **동일 회귀 케이스 커버**가 목적이며, 라인 단위 동시 실행 순서 동치는 보장하지 않는다.
  1. `py scripts/integrity_guard.py` (CI 첫 단계)
  1b. `py scripts/check_cursor_rules_context_diet_v1.py --strict` (core 8 · slim AGENTS; `-SkipCursorRulesContextDiet`)
  2. `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1`
     — dual-regime 스모크 + multilens marginal(V1) 후 워크스페이스 루트 Fact-Lock(Thin V2·시장 어댑터·일반예언·**B-track 세션 패널→조인→상관 4 pytest** 등 명시 목록)
  3. `py -m pytest tests/test_sasang_interpretive_insight_bundle_v1.py` — 사상 통찰 참조 번들 v1.1 스키마·`synthesis_v1`(dual-regime 동일 단계)
  3b. `py -m pytest tests/test_bio_sasang_nstates_strict_comparison_rehydrate_v1.py` — Bio n-state strict JSON 재수화 계약(CONSTITUTION §3.5)
  3c. `py -m pytest tests/test_mkm_trinity_index_v1.py` — MKM Trinity 인덱스 JSON·스키마 계약(CONSTITUTION §1 렌즈 인덱스 bullet)
  3d. `py -m pytest tests/test_mkm_meta_layer_envelope_v1.py` — 메타 인지 봉투 v1·킬 스위치 정규화·`AthenaValidator`(CONSTITUTION §1.3.1 보강 2026-05-05)
  3d2. `py -m pytest tests/test_athena_checkpoint.py` — CENTRAL `athena_checkpoint.py` prepend·`--max-checkpoints`(CI `Athena execution governance` 스텝에 포함된 동일 테스트)
  3d2e. `py -m pytest tests/test_record_coding_intent_link_v1.py` — Coding intent 3-point link PoC(git↔checkpoint↔gate·diff schema; `research_only`; CI `dual-regime-integrity` Athena §28 블록과 동일). `-SkipCodingIntentLinkSmoke` 로 생략.
  3d2f. `py -m pytest tests/test_build_coding_intent_pr_manifest_v1.py` — PR manifest PoC(base..HEAD ↔ checkpoints ↔ link log; `research_only`). `-SkipCodingIntentPrManifestSmoke` 로 생략.
  3d2g. `py -m pytest tests/test_build_coding_intent_gitea_merge_precheck_v1.py` — Gitea/internal merge precheck summary(`internal_first`; GitHub PR 비의존). `-SkipCodingIntentGiteaMergePrecheckSmoke` 로 생략.
  3d2c. `py -m pytest tests/test_run_vertex_gemini_agent_search_context_v1.py` — Vertex Agent Search → 명시적 RAG 컨텍스트 헬퍼(오프라인; GCP 미호출). `-SkipVertexAgentSearchContextUnit` 로 생략.
  3d2d. `py -m pytest tests/test_athena_daily_thread_log_sync_v1.py` — 다중 채팅 일기 MD 병합(오프라인). `-SkipDailyThreadWorkLogUnit` 로 생략.
  3d2a. `py -m pytest …` — CI `dual-regime-integrity.yml`에서 Aramaic 직전의 **Two-track submission pack**(pytest **3**) + **Multi-symbol gates and counterfactual QA**(pytest **3**)를 **동일 순서**로 한 번에 실행(총 **6**개 파일). `-SkipTwoTrackSubmissionAndMultiSymbolSmoke` 로 생략.
  3d2b. `py -m pytest …` — Aramaic B-track graph pipeline smoke **27**개 파일(CI `dual-regime-integrity.yml` `Aramaic B-track graph pipeline smoke` 단계와 동일 목록: 코퍼스·audit trend·alert·threshold sweep/apply·MVP audit PS1 passthrough·그래프·점수·시맨틱·bridge·Bible meaning graph·insight survivor·cap bucket·drift alert schema·insight/cap CLI 연쇄 jsonschema·Track T survivor health·survivor health alert schema·weight/shadow·bridge coef). `-SkipAramaicBtrackGraphPipelineSmoke` 로 생략.
  3d3. `py -m pytest tests/test_logos_insight_bundle_schema_v1.py tests/test_build_logos_insight_bundle_v1.py tests/test_build_logos_macro_horizon_2030_scenario_v1.py` — Logos insight bundle v1 + macro horizon 2030(CI `Logos insight bundle + macro horizon 2030` 스텝과 동일)
  3d3b. `py -m pytest tests/test_btrack_science_core_v1.py tests/test_run_prophecy_lens_combo_science_core_v1.py tests/test_build_science_core_instrument_matrix_v1.py tests/test_run_science_core_conditional_attach_research_v1.py tests/test_run_science_core_prophecy_combo_sensitivity_v1.py` — Science Core B-track lane v1 + prophecy combo science arms + instrument matrix + conditional attach + fee sensitivity(CI `Science Core B-track lane v1` 스텝과 동일). `-SkipScienceCoreLaneSmoke` 로 생략.
  3d3a. `py -m pytest tests/test_stt_routing_audit_log_schema_v1.py tests/test_append_stt_routing_audit_log_v1.py tests/test_build_showroom_trust_visualization_slice_v1.py` — STT audit jsonschema + append·summarize + 쇼룸 Trust Visualization thin slice(CI `STT routing audit log v1 + showroom trust viz thin slice` 단계와 동일; CI YAML에서는 `Lens music prompt PoC M26-M30` 직후, 본 번들에서는 Logos insight 직후). `-SkipSttRoutingAuditShowroomTrustSlice` 로 생략.
  3d3b-hub. `py scripts/check_mkm_universe_hub_shell_v2.py` + universe hub UX pytest 6종(CI `Universe Hub v2 UX gate` 단계; `4c` domain design offline pytest에 포함). `-SkipMkmDomainDesignOfflineSmoke` 로 생략.
  3e. `py -m pytest …` — 한의 의사 CDS 봉투 v1 스키마·빌더·JSONL 배치 + 환자 통합 번들(`patient_care_bundle_v1`) 스키마·assemble·CDS 체인·슬롯 템플릿/정책/MD 렌더(`test_patient_care_bundle_templates_policy_render_v1`)·원클릭 `Invoke-PatientCareBundleAssemblePatientFacing_v1.ps1` + `tests/test_automation_registry_json_v1.py`(자동화 레지스트리 MKM 태스크명; dual-regime 동일 단계). `-SkipKmPhysicianCdsEnvelope` 로 생략.
  4. `py -m pytest tests/test_build_daily_execution_insight_brief_v1.py` — 일일 실행 인사이트 브리프 머티리얼라이저(CONSTITUTION §3.3)
  4b. `py -m pytest tests/test_premium_btrack_multilens_report_schema_v1.py tests/test_build_premium_btrack_multilens_report_v1.py tests/test_premium_multilens_job_queue_stub_v1.py tests/test_build_premium_multilens_queue_promotion_gate_v1.py` — Premium B-track multi-lens report v1(스키마·동기 빌더 subprocess·파일 큐 스텁·S1 승격 게이트 회귀); 직후 **`py scripts/premium_multilens_job_queue_stub_v1.py drain --allow-missing-queue`**(큐 없으면 SKIP·exit 0)·**`py scripts/build_premium_multilens_queue_promotion_gate_v1.py --skip-pytest`**(S1_SHADOW 승격 게이트 산출); 일상 원클릭은 **`scripts/Invoke-PremiumMultilensQueueRoutine_v1.ps1`**; `dual-regime-integrity.yml` 동일 pytest+drain+gate 단계
  4c. `py scripts/check_mkm_domain_design_tokens_v1.py` + domain design offline pytest 8종(tokens·personadiary·mkmlife facade). `-SkipMkmDomainDesignOfflineSmoke` 로 생략. 라이브 결선은 **`Invoke-MkmDomainDesignClosureBundle_v1.ps1`**.
  5. `py -m pytest tests/test_emit_myeongni_thin_bridge_line_v1.py` — 명리 독립 렌즈 → Thin JSONL 브리지(§3.6)
  5b. `py -m pytest tests/test_validate_mkm_personal_briefing_guardrails_v1.py` — 개인 인사이트 브리핑 Fact-Lock 휴리스틱(운영 단계 라벨·시장↔부채 합선)
  5c. `py -m pytest tests/test_run_graphrag_pilot_router_v1.py` — GraphRAG 파일럿 라우터(Track B/K 관측 전용, GO 게이트·한글 별칭·brief fallback) 회귀.
  5c4. `py -m pytest` COMP-ATOM-05 graph wire selective bridge — `test_mkm_graph_wire_bridge_influence_v1.py`·`test_comp_atom05_graph_wire_bridge_smoke_v1.py`·`test_v2_graph_wire_selective_bridge_v1.py`·OpenAPI contract·semantic_pointer smoke(`dual-regime` path filter와 동일 5종). `-SkipCompAtom05WireSmoke` 로 생략.
  5c2. `py -m pytest tests/test_philosophy_lane_rag_pilot_v1.py` — 철학·상담 레인 RAG 파일럿(금지어 JSON·ANN-lite 스킵 계약).
  5c2c. `py -m pytest tests/test_build_compression_deep_pack_tri_vertical_signoff_checklist_v1.py tests/test_build_compression_deep_pack_tri_vertical_post_signoff_checklist_v1.py` — tri-vertical ZF/BIZ/CS deep pack rollup + post-commander-signoff status(B-track; SEND HOLD). `-SkipCompressionDeepPackTriVerticalSmoke` 로 생략.
  5c2b. `py -m pytest tests/test_generate_linkedin_b2b_copy_v1.py tests/test_check_linkedin_b2b_draft_copy_v1.py` — LinkedIn B2B draft queue v1(로컬 JSON·assemble/Gemini·카피 가드; 자동 발행 없음). `-SkipLinkedInB2bDraftSmoke` 로 생략.
  5c3. `py -m pytest tests/test_semantic_rag_bridge_insight_bundle_schema_v1.py tests/test_build_semantic_rag_bridge_insight_bundle_v1.py` — 내부 시맨틱+RAG 번역 브리지 번들 v1(스키마·Premium/철학 병합 CLI; `dual-regime-integrity.yml` 동일 단계).
  5d. `py -m pytest tests/test_mkm_control_integrity_pipeline_smoke_v1.py` — Control-Integrity Golden/LoRA 파이프라인 스모크(aggregate·프로모션 게이트·오라클 추론 타이밍; GPU 불필요). `-SkipMkmControlIntegritySmoke` 로 생략.
  5d2. `py -m pytest tests/test_va_fusion_control_integrity_chain_v1.py tests/test_va_fusion_policy_golden_v1.py` — VA→fusion→감사 체인 + `va_tag_boost_v1` 정책 골든(CONSTITUTION §3.8.4). `-SkipVaFusionControlIntegritySmoke` 로 생략.
  5e. 사상–사주 조인트 문헌·큐레이트 회귀 **9**개 파일(Europe PMC 픽스처·오프라인 **7** + 인제스트 **1** + staleness **1**; CONSTITUTION §3.3 표「사상체질↔문헌↔사주 조인트」). `-SkipSasangSajuJointLiteraturePipeline` 로 생략.
  6. (기본) 명리·멀티렌즈 **권장 스택** — CI `multilens-independent-lens-smoke`와 동일 **15**개 pytest 파일(선행: 일일 브리프 1 + Thin 브리지 1; 이어 배치 13에 Yang 2015 B-track 스키마·벤치 포함). `-SkipMyeongniLensRecommendedStack` 로 생략.

  테스트 파일 목록 이중 관리를 피하기 위해 2단계는 기존 PS1에 위임합니다. 3·3b·3c·3d·3d2·3d2c·3d2d·3d2a·3d2b·3d3·3e·4·4b·5·5b·5c·5d·5e·6단계는 본 스크립트에서 직접 실행합니다.

.PARAMETER SkipIntegrityGuard
  `integrity_guard.py` 생략(빠른 확인용). CI와 완전 동치가 아님.

.PARAMETER SkipCursorRulesContextDiet
  `check_cursor_rules_context_diet_v1.py --strict` 생략(규칙·AGENTS 주입층 미변경 시).

.PARAMETER IncludeP1AB
  Fact-Lock 핵심 검증 후 `scripts/run_p1_ab_bundle.ps1`를 추가 실행한다.

.PARAMETER IncludeCodebookFactSafe
  압축 복원 브리지 이후 `scripts/run_codebook_factsafe_bundle.ps1 -IncludeRecoveredReadiness`를 실행한다(코드북·복구 레일 스모크).

.PARAMETER Include4dOhaengRegimeSnapshotGate
  B-track 스파이크: `scripts/run_4d_to_ohaeng_regime_snapshot_gate_chain_spike.ps1` 실행(스냅샷 갱신 + 게이트). 기본 번들과 격리; 아티팩트 없으면 실패한다.

.PARAMETER IncludeBtrackBalancedRegimeEval
  B-track 균형 레짐 평가 체인(`scripts/run_btrack_balanced_regime_eval_chain_v1.ps1`)을 후단에서 실행한다.

.PARAMETER IncludeTruthfulQaBenchmarkGate
  TruthfulQA A/B 벤치 산출물 존재 여부를 점검한다(빠른 파일 게이트).

.PARAMETER StrictTruthfulQaBenchmarkGate
  TruthfulQA A/B 벤치 산출물 미존재 시 경고 대신 실패(exit 1)로 처리한다.

.PARAMETER IncludeTruthfulQaBenchmarkEvalGate
  TruthfulQA MC/Generation 벤치 결과를 GO/NO_GO로 판정하는 게이트 스크립트를 실행한다.

.PARAMETER StrictTruthfulQaBenchmarkEvalGate
  TruthfulQA 판정 결과가 NO_GO면 실패(exit 1)로 처리한다.

.PARAMETER TruthfulQaEvalMcOnly
  Eval 게이트에 `--mc-only`를 넘겨 MC 비교만으로 판정한다(promotion-friendly). generation 산출물이 없어도 실행 가능.

.PARAMETER TruthfulQaBenchmarkGateMcOnly
  `-IncludeTruthfulQaBenchmarkGate` 사용 시 generation JSON 없어도 경고/실패 대상에서 제외(MC 파일만 필수).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1

.EXAMPLE
  원클릭 Ops(본 번들 + 예언 클로저 + VPS 쇼룸 + pytest·Pack0-B·체크포인트): `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\Run-MkmOpsFullPush_v1.ps1` (빠른 스모크: `-SkipFactLock`)

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipIntegrityGuard

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipIntegrityGuard -IncludeP1AB

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -IncludeCodebookFactSafe

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -Include4dOhaengRegimeSnapshotGate

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -IncludeBtrackBalancedRegimeEval

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -IncludeTruthfulQaBenchmarkGate

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -IncludeTruthfulQaBenchmarkEvalGate -StrictTruthfulQaBenchmarkEvalGate

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -IncludeTruthfulQaBenchmarkGate -TruthfulQaBenchmarkGateMcOnly -IncludeTruthfulQaBenchmarkEvalGate -TruthfulQaEvalMcOnly -StrictTruthfulQaBenchmarkEvalGate

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipNewsObservationContractSmoke

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -IncludeBTrackDomainFeedbackSmoke

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipMyeongniLensRecommendedStack

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipSasangSajuJointLiteraturePipeline

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipKmPhysicianCdsEnvelope

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipVertexAgentSearchContextUnit

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipDailyThreadWorkLogUnit

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipAramaicBtrackGraphPipelineSmoke

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipSttRoutingAuditShowroomTrustSlice

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipTwoTrackSubmissionAndMultiSymbolSmoke

.PARAMETER SkipVertexAgentSearchContextUnit
  `tests/test_run_vertex_gemini_agent_search_context_v1.py`(Agent Search 명시적 RAG 헬퍼; 오프라인)를 생략한다.

.PARAMETER SkipDailyThreadWorkLogUnit
  `tests/test_athena_daily_thread_log_sync_v1.py`(다중 채팅 일기 MD 병합; 오프라인)를 생략한다.

.PARAMETER SkipTwoTrackSubmissionAndMultiSymbolSmoke
  CI `dual-regime-integrity.yml`의 **Two-track submission pack**(pytest 3) + **Multi-symbol gates**(pytest 3) — 총 **6**개 파일을 생략한다(Aramaic 3d2b 직전 단계).

.PARAMETER SkipAramaicBtrackGraphPipelineSmoke
  Aramaic B-track graph pipeline smoke pytest **27**개(CI `dual-regime-integrity.yml` Aramaic 단계와 동일 목록)를 생략한다.

.PARAMETER SkipScienceCoreLaneSmoke
  Science Core B-track lane pytest(`tests/test_btrack_science_core_v1.py`·`tests/test_run_prophecy_lens_combo_science_core_v1.py`; CI `Science Core B-track lane v1` 단계)를 생략한다.

.PARAMETER SkipSttRoutingAuditShowroomTrustSlice
  STT audit jsonschema + append·summarize 및 쇼룸 Trust Visualization thin slice pytest 3개(CI `STT routing audit log v1 + showroom trust viz thin slice` 단계)를 생략한다.

.PARAMETER SkipMyeongniLensRecommendedStack
  명리 독립 렌즈 v0/v1·융합 브리지·봇 체인·융합 스텁 등 9종 멀티렌즈 pytest(권장 CI 패리티)를 생략한다.

.PARAMETER SkipSasangSajuJointLiteraturePipeline
  사상–사주 조인트 문헌·큐레이트·staleness 회귀 9개 pytest(`dual-regime-integrity` 의 Sasang 단계와 동일 목록)를 생략한다.

.PARAMETER SkipCuratedJointStalenessCheck
  끝단: `data/myeongni/curated_saju_joint_v1.jsonl` 시각 신호 vs `myeongni_celebrity_hit_rate_v1` 산출 시각의 staleness 점검(`check_curated_saju_joint_staleness_v1.py`)을 생략한다.

.PARAMETER SkipCompAtom05WireSmoke
  COMP-ATOM-05 graph wire selective bridge pytest 5종(influence·smoke·v2 API·OpenAPI contract·semantic_pointer)을 생략한다.

.PARAMETER SkipMkmControlIntegritySmoke
  `tests/test_mkm_control_integrity_pipeline_smoke_v1.py`(Golden Set·홀드아웃 집계·게이트 CLI 회귀)를 생략한다.

.PARAMETER SkipVaFusionControlIntegritySmoke
  VA→fusion→감사 체인 pytest(`test_va_fusion_control_integrity_chain_v1`) 및 정책 골든(`test_va_fusion_policy_golden_v1`)을 생략한다.

.PARAMETER SkipKmPhysicianCdsEnvelope
  한의 의사 CDS assist envelope v1 회귀 3종 pytest + `tests/test_automation_registry_json_v1.py`(MKM 주간 태스크 SSOT; `dual-regime` 의「Myeongri AI interpretation + KM physician CDS」단계와 동일 목록)를 생략한다.

.PARAMETER SkipSchedulerSoloCoreStackSmoke
  MKM solo scheduler SSOT band gate pytest 3종(`tests/test_mkm_scheduler_solo_core_stack_audit_v1.py`; 오프라인+EnforceSoloBand 스모크) 생략.

.PARAMETER SkipSafeOpsSurfaceCheck
  말미 권장 단계 `Invoke-SafeOpsSurfaceCheck.ps1`(운영 표면·신선도·Verify-Trading) 생략.

.PARAMETER SafeOpsIgnoreLiveSync
  말미 SafeOps 호출에 `-IgnoreLiveSync`를 넘긴다(VPS live_sync 미러 없는 로컬에서 stale 경고만 억제; 예언 클로저 `-SkipLiveSyncPull`과 동일 선상).

.PARAMETER SafeOpsStrictTradingGoNoGo
  말미 SafeOps 호출에 `-StrictTradingGoNoGo`를 넘긴다(기본은 Trinity LOCKED `NO_GO`를 헬스 실패로 취급하지 않음; 감사용으로만 사용).

.PARAMETER SkipIntegratedGovernanceBuild
  `Invoke-BuildIntegratedGovernanceIfDepsPresent_v1.ps1` 생략(기본: KOSPI 게이트·config가 모두 있으면 `--validate-digest-schema`로 갱신).

.NOTES
  SSOT 순서: `.github/workflows/dual-regime-integrity.yml`
  말미 권장: KOSPI 게이트·config가 모두 있으면 `Invoke-BuildIntegratedGovernanceIfDepsPresent_v1.ps1`로 통합 거버넌스 갱신(`--validate-digest-schema`). `-SkipIntegratedGovernanceBuild` 로 생략.
  pytest·`py` 규칙: `docs/final/P0_COMMERCIALIZATION_TRACKER.md`
#>
param(
    [switch]$SkipIntegrityGuard,
    [switch]$IncludeP1AB,
    [switch]$SkipCompressionRestoreBridge,
    [switch]$IncludeCodebookFactSafe,
    [switch]$Include4dOhaengRegimeSnapshotGate,
    [switch]$IncludeBtrackBalancedRegimeEval,
    [switch]$IncludeTruthfulQaBenchmarkGate,
    [switch]$StrictTruthfulQaBenchmarkGate,
    [switch]$IncludeTruthfulQaBenchmarkEvalGate,
    [switch]$StrictTruthfulQaBenchmarkEvalGate,
    [switch]$TruthfulQaEvalMcOnly,
    [switch]$TruthfulQaBenchmarkGateMcOnly,

    # B-track news_observation JSONL contract smoke runs by default after prophecy alignment; use -Skip to omit.
    [switch]$SkipNewsObservationContractSmoke,

    # Optional: general_prophecy registry/export pytest + weather triplet smoke (see scripts\Run-BTrackDomainFeedbackSmoke.ps1).
    # When default news smoke ran above, invokes -SkipNews on that wrapper to avoid duplicate news steps.
    [switch]$IncludeBTrackDomainFeedbackSmoke,

    # Myeongni / multilens recommended CI parity (9 pytests, excluding daily brief + thin bridge already run above)
    [switch]$SkipMyeongniLensRecommendedStack,

    # Sasang–saju joint literature harvest/enrich/resolve/export/dummy benchmark pytest bundle (offline)
    [switch]$SkipSasangSajuJointLiteraturePipeline,

    # Curated joint staleness (curated JSONL signal vs celebrity hit-rate artifact; writes reports/*.json; non-failing by default)
    [switch]$SkipCuratedJointStalenessCheck,

    # Control-Integrity LoRA / Golden pipeline CLI smoke (dual-regime parity step)
    [switch]$SkipMkmControlIntegritySmoke,

    # VA trajectory -> fusion stub -> integrity audit chain + policy golden (B-track §3.8.4)
    [switch]$SkipVaFusionControlIntegritySmoke,

    # KM physician CDS envelope v1 schema + builder pytest (dual-regime parity)
    [switch]$SkipKmPhysicianCdsEnvelope,

    # Vertex Agent Search explicit-RAG context helpers (offline pytest; not in dual-regime CI)
    [switch]$SkipVertexAgentSearchContextUnit,

    # Daily multi-chat work log merge helpers (offline pytest)
    [switch]$SkipDailyThreadWorkLogUnit,

    # Two-track submission + multi-symbol gates (6 pytests; dual-regime steps immediately before Aramaic)
    [switch]$SkipTwoTrackSubmissionAndMultiSymbolSmoke,

    # Aramaic B-track graph pipeline smoke (27 pytests; dual-regime `Aramaic B-track graph pipeline smoke` step)
    [switch]$SkipAramaicBtrackGraphPipelineSmoke,

    # Science Core B-track lane v1 (offline pytest; dual-regime step after Logos insight bundle)
    [switch]$SkipScienceCoreLaneSmoke,

    # STT audit + showroom trust viz thin slice (2 pytests; dual-regime STT + thin slice step)
    [switch]$SkipSttRoutingAuditShowroomTrustSlice,

    # COMP-ATOM-05 graph wire selective bridge (5 pytest; B-track)
    [switch]$SkipCompAtom05WireSmoke,

    # Tri-vertical deep pack signoff rollup + post-signoff checklist (B-track; research envelope only)
    [switch]$SkipCompressionDeepPackTriVerticalSmoke,

    # MKM solo scheduler SSOT band gate (3 pytest; offline + EnforceSoloBand subprocess)
    [switch]$SkipSchedulerSoloCoreStackSmoke,

    # LinkedIn B2B draft queue v1 (2 pytest; no API publish)
    [switch]$SkipLinkedInB2bDraftSmoke,

    # Coding intent 3-point link PoC (1 pytest; research_only)
    [switch]$SkipCodingIntentLinkSmoke,

    # Coding intent PR manifest PoC (1 pytest; research_only)
    [switch]$SkipCodingIntentPrManifestSmoke,

    # Gitea/internal merge precheck summary (1 pytest; research_only)
    [switch]$SkipCodingIntentGiteaMergePrecheckSmoke,

    # Recommended tail: Invoke-SafeOpsSurfaceCheck.ps1 after pytest bundle (exit 2 fails; exit 1 warns only).
    [switch]$SkipSafeOpsSurfaceCheck,

    # Pass -IgnoreLiveSync to SafeOps tail (pairs with prophecy closure -SkipLiveSyncPull; avoids local stale live_sync/daemon WARN).
    [switch]$SafeOpsIgnoreLiveSync,

    # Pass -StrictTradingGoNoGo to SafeOps tail (audit: policy LOCKED NO_GO fails verify).
    [switch]$SafeOpsStrictTradingGoNoGo,

    # Integrated governance rebuild when deps exist (see Invoke-BuildIntegratedGovernanceIfDepsPresent_v1.ps1).
    [switch]$SkipIntegratedGovernanceBuild,

    # MKM multi-domain design tokens + personadiary/mkmlife offline pytest (no live HTTP)
    [switch]$SkipMkmDomainDesignOfflineSmoke,

    # Cursor rules context diet + slim AGENTS.md line budget (default on)
    [switch]$SkipCursorRulesContextDiet
)

$ErrorActionPreference = 'Stop'

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$prophecyBundle = Join-Path $workspaceRoot 'projects\bitcoin-trading\ops\v2\tasks\run_prophecy_alignment_pytest.ps1'
$p1AbBundle = Join-Path $workspaceRoot 'scripts\run_p1_ab_bundle.ps1'
$insightScoreboardScript = Join-Path $workspaceRoot 'scripts\build_insight_effectiveness_scoreboard.py'
$trackbQuaternionGateScript = Join-Path $workspaceRoot 'scripts\report_trackb_quaternion_two_stage_gate.py'
$compressionRestoreBridgeScript = Join-Path $workspaceRoot 'scripts\run_agent_compression_restore_bridge.ps1'
$codebookFactSafeBundleScript = Join-Path $workspaceRoot 'scripts\run_codebook_factsafe_bundle.ps1'
$ohaengRegimeSnapshotGateChain = Join-Path $workspaceRoot 'scripts\run_4d_to_ohaeng_regime_snapshot_gate_chain_spike.ps1'
$btrackBalancedRegimeEvalChain = Join-Path $workspaceRoot 'scripts\run_btrack_balanced_regime_eval_chain_v1.ps1'
$trackCEvidenceScript = Join-Path $workspaceRoot 'scripts\build_track_c_evidence_pack_v1.py'
$trackCCopyGuardScript = Join-Path $workspaceRoot 'scripts\check_track_c_copy_guard_v1.py'
$trackCClaimValidatorScript = Join-Path $workspaceRoot 'scripts\validate_track_c_landing_claims_v1.py'
$sajuGoldenReplayScript = Join-Path $workspaceRoot 'scripts\run_saju_golden_replay.py'
$sasangInterpretiveBundleTest = Join-Path $workspaceRoot 'tests\test_sasang_interpretive_insight_bundle_v1.py'
$bioSasangNstatesRehydrateTest = Join-Path $workspaceRoot 'tests\test_bio_sasang_nstates_strict_comparison_rehydrate_v1.py'
$mkmTrinityIndexTest = Join-Path $workspaceRoot 'tests\test_mkm_trinity_index_v1.py'
$mkmMetaLayerEnvelopeTest = Join-Path $workspaceRoot 'tests\test_mkm_meta_layer_envelope_v1.py'
$athenaCheckpointTest = Join-Path $workspaceRoot 'tests\test_athena_checkpoint.py'
$codingIntentLinkSmokeTest = Join-Path $workspaceRoot 'tests\test_record_coding_intent_link_v1.py'
$codingIntentPrManifestSmokeTest = Join-Path $workspaceRoot 'tests\test_build_coding_intent_pr_manifest_v1.py'
$codingIntentGiteaMergePrecheckSmokeTest = Join-Path $workspaceRoot 'tests\test_build_coding_intent_gitea_merge_precheck_v1.py'
$vertexAgentSearchContextUnitTest = Join-Path $workspaceRoot 'tests\test_run_vertex_gemini_agent_search_context_v1.py'
$dailyThreadWorkLogUnitTest = Join-Path $workspaceRoot 'tests\test_athena_daily_thread_log_sync_v1.py'
# CI `dual-regime-integrity.yml` — Two-track submission pack + Multi-symbol gates (steps before Aramaic; keep in sync)
$twoTrackSubmissionPackPytests = @(
    (Join-Path $workspaceRoot 'tests\test_build_two_track_submission_evidence_bundle_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_two_track_submission_draft_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_two_track_submission_camera_ready_v1.py')
)
$multiSymbolGatesPytests = @(
    (Join-Path $workspaceRoot 'tests\test_multi_symbol_contract_gates_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_multi_symbol_counterfactual_comparison_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_two_track_qa_overlay_counterfactual_v1.py')
)
# CI `dual-regime-integrity.yml` — name: Aramaic B-track graph pipeline smoke (single-line pytest list; keep in sync)
$aramaicBtrackGraphPipelineSmokePytests = @(
    (Join-Path $workspaceRoot 'tests\test_extract_aramaic_core_corpus_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_report_aramaic_mvp_audit_trend_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_alert_aramaic_mvp_trend_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_sweep_aramaic_mvp_alert_thresholds_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_apply_aramaic_mvp_alert_threshold_recommendation_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_run_aramaic_mvp_now_with_audit_passthrough_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_aramaic_graph_schema_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_aramaic_edge_builder_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_aramaic_regime_shift_score_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_aramaic_semantic_edge_quality_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_aramaic_cross_corpus_bridge_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_bible_meaning_graph_schema_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_bible_meaning_graph_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_extract_bible_meaning_insight_candidates_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_insight_survivor_eval_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_select_insight_survivor_candidates_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_sweep_aramaic_insight_cap_bucket_thresholds_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_apply_aramaic_insight_cap_bucket_threshold_recommendation_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_report_aramaic_insight_cap_threshold_history_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_alert_aramaic_insight_cap_threshold_drift_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_aramaic_insight_cap_threshold_drift_alert_schema_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_bible_meaning_insight_survivor_and_cap_bucket_schemas_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_insight_survivor_health_alert_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_insight_survivor_health_alert_schema_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_showroom_topology_radar_snapshot_schema_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_showroom_topology_radar_snapshot_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_aramaic_regime_shift_weight_sweep_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_aramaic_regime_shift_shadow_compare_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_apply_aramaic_regime_shift_bridge_coef_recommendation_v1.py')
)
$logosInsightBundlePytests = @(
    (Join-Path $workspaceRoot 'tests\test_logos_insight_bundle_schema_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_logos_insight_bundle_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_logos_macro_horizon_2030_scenario_v1.py')
)
$scienceCoreLaneSmokeTest = Join-Path $workspaceRoot 'tests\test_btrack_science_core_v1.py'
$scienceCoreComboSmokeTest = Join-Path $workspaceRoot 'tests\test_run_prophecy_lens_combo_science_core_v1.py'
$scienceCoreInstrumentMatrixTest = Join-Path $workspaceRoot 'tests\test_build_science_core_instrument_matrix_v1.py'
$scienceCoreConditionalAttachTest = Join-Path $workspaceRoot 'tests\test_run_science_core_conditional_attach_research_v1.py'
$scienceCoreProphecySensitivityTest = Join-Path $workspaceRoot 'tests\test_run_science_core_prophecy_combo_sensitivity_v1.py'
$sttRoutingAuditShowroomTrustSlicePytests = @(
    (Join-Path $workspaceRoot 'tests\test_stt_routing_audit_log_schema_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_append_stt_routing_audit_log_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_showroom_trust_visualization_slice_v1.py')
)
$dailyExecutionInsightBriefTest = Join-Path $workspaceRoot 'tests\test_build_daily_execution_insight_brief_v1.py'
$premiumBtrackMultilensReportPytests = @(
    (Join-Path $workspaceRoot 'tests\test_premium_btrack_multilens_report_schema_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_premium_btrack_multilens_report_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_premium_multilens_job_queue_stub_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_premium_multilens_queue_promotion_gate_v1.py')
)
$mkmDomainDesignOfflinePytests = @(
    (Join-Path $workspaceRoot 'tests\test_check_mkm_domain_design_tokens_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_check_mkm_ui_shell_contract_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_check_mkm_universe_hub_shell_v2.py'),
    (Join-Path $workspaceRoot 'tests\test_universe_hub_intent_router_v2.py'),
    (Join-Path $workspaceRoot 'tests\test_universe_hub_path_active_plugin_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_universe_hub_rq025_oracle_card_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_universe_hub_report_ledger_stub_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_universe_hub_mkmlife_embed_v2.py'),
    (Join-Path $workspaceRoot 'tests\test_personadiary_ritual_draw_lut_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_personadiary_lattice_convergence_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_personadiary_live_ops_smoke_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_check_mkmlife_portal_commercialization_gate_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_check_mkmlife_pixel_sprite_urls_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_mkmlife_news_observation_deck_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_mkmlife_skim_read_preference_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_mkm_consumer_facade_v1.py')
)
$mkmDomainDesignTokensScript = Join-Path $workspaceRoot 'scripts\check_mkm_domain_design_tokens_v1.py'
$myeongniThinBridgeTest = Join-Path $workspaceRoot 'tests\test_emit_myeongni_thin_bridge_line_v1.py'
$mkmBriefingGuardrailsTest = Join-Path $workspaceRoot 'tests\test_validate_mkm_personal_briefing_guardrails_v1.py'
$graphragPilotRouterTest = Join-Path $workspaceRoot 'tests\test_run_graphrag_pilot_router_v1.py'
$compAtom05WirePytests = @(
    (Join-Path $workspaceRoot 'tests\test_mkm_graph_wire_bridge_influence_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_comp_atom05_graph_wire_bridge_smoke_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_v2_graph_wire_selective_bridge_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_compression_token_api_v2_stub.py::test_openapi_v2_contract_has_graph_wire_selective_bridge'),
    (Join-Path $workspaceRoot 'tests\test_multilens_performance_eval_report.py::test_evaluate_report_emit_semantic_pointer_smoke')
)
$compressionDeepPackTriVerticalSmokePytests = @(
    (Join-Path $workspaceRoot 'tests\test_build_compression_deep_pack_tri_vertical_signoff_checklist_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_compression_deep_pack_tri_vertical_post_signoff_checklist_v1.py')
)
$philosophyLaneRagPilotTest = Join-Path $workspaceRoot 'tests\test_philosophy_lane_rag_pilot_v1.py'
$linkedinB2bDraftPytests = @(
    (Join-Path $workspaceRoot 'tests\test_generate_linkedin_b2b_copy_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_check_linkedin_b2b_draft_copy_v1.py')
)
$linkedinQueueExample = Join-Path $workspaceRoot 'data\marketing\linkedin_queue_v1.example.json'
$linkedinGenerateScript = Join-Path $workspaceRoot 'scripts\generate_linkedin_b2b_copy_v1.py'
$semanticRagBridgeBundlePytests = @(
    (Join-Path $workspaceRoot 'tests\test_semantic_rag_bridge_insight_bundle_schema_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_semantic_rag_bridge_insight_bundle_v1.py')
)
$mkmControlIntegrityPipelineSmokeTest = Join-Path $workspaceRoot 'tests\test_mkm_control_integrity_pipeline_smoke_v1.py'
$vaFusionControlIntegritySmokeTests = @(
    (Join-Path $workspaceRoot 'tests\test_va_fusion_control_integrity_chain_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_va_fusion_policy_golden_v1.py')
)
$kmPhysicianCdsEnvelopeTests = @(
    (Join-Path $workspaceRoot 'tests\test_km_physician_cds_assist_envelope_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_km_physician_cds_assist_envelope_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_run_km_physician_cds_assist_envelope_batch_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_patient_care_bundle_v1_schema.py'),
    (Join-Path $workspaceRoot 'tests\test_assemble_patient_care_bundle_with_myeongni_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_patient_care_bundle_from_km_cds_chain_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_patient_care_bundle_templates_policy_render_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_automation_registry_json_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_resolve_km_classics_citations_hypo_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_km_classics_index_hypo_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_km_classics_citation_cds_smoke_v1.py')
)
$myeongniLensRecommendedPytests = @(
    (Join-Path $workspaceRoot 'tests\test_independent_lenses_v0.py'),
    (Join-Path $workspaceRoot 'tests\test_myeongni_independent_lens_v0.py'),
    (Join-Path $workspaceRoot 'tests\test_myeongni_lens_v1_contract.py'),
    (Join-Path $workspaceRoot 'tests\test_myeongni_fusion_bridge_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_myeongni_lens_chain_from_bot_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_independent_lens_shadow_gate_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_independent_lens_fusion_stub_v0.py'),
    (Join-Path $workspaceRoot 'tests\test_scm_boming_jiju_lexicon_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_sasang_boming_jiju_clinical_lens_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_patient_intake_constitution_fixtures_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_showroom_patient_intake_slice_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_validate_showroom_trust_slice_local_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_eval_btrack_insight_sidecar_lens_hit_agreement_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_btrack_yang_2015_style_metrics_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_myeongni_paper_contract_map_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_run_myeongni_celebrity_benchmark_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_yang_2015_btrack_json_schema_v1.py')
)
$sasangSajuJointLiteraturePytests = @(
    (Join-Path $workspaceRoot 'tests\test_fetch_europepmc_sasang_saju_literature_catalog_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_filter_sasang_saju_literature_catalog_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_build_sasang_saju_joint_review_queue_from_catalog_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_auto_enrich_sasang_from_literature_stub_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_resolve_literature_sasang_majority_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_export_sasang_literature_supervised_jsonl_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_validate_sasang_saju_joint_benchmark_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_ingest_curated_saju_joint_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_check_curated_saju_joint_staleness_v1.py')
)
$curatedJointStalenessScript = Join-Path $workspaceRoot 'scripts\check_curated_saju_joint_staleness_v1.py'
$truthfulQaBenchmarkScript = Join-Path $workspaceRoot 'scripts\run_truthfulqa_ab_benchmark_v1.py'
$truthfulQaBenchmarkEvalGateScript = Join-Path $workspaceRoot 'scripts\check_truthfulqa_ab_gate_v1.py'
$truthfulQaMcBenchmarkArtifact = Join-Path $workspaceRoot 'docs\final\artifacts\truthfulqa_ab_benchmark_latest.json'
$truthfulQaGenerationBenchmarkArtifact = Join-Path $workspaceRoot 'docs\final\artifacts\truthfulqa_generation_ab_benchmark_latest.json'
$truthfulQaGateArtifact = Join-Path $workspaceRoot 'docs\final\artifacts\truthfulqa_ab_gate_latest.json'
$igGovernanceInvoker = Join-Path $workspaceRoot 'scripts\invoke_build_integrated_governance_if_deps_present_v1.py'

if (-not (Test-Path -LiteralPath $prophecyBundle)) {
    throw "Bundle script not found: $prophecyBundle"
}

Set-Location -LiteralPath $workspaceRoot

if (-not $SkipIntegrityGuard) {
    Write-Host '== Fact-Lock: integrity_guard.py ==' -ForegroundColor Cyan
    & py (Join-Path $workspaceRoot 'scripts\integrity_guard.py')
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipCursorRulesContextDiet) {
    Write-Host '== Fact-Lock: check_cursor_rules_context_diet_v1.py --strict ==' -ForegroundColor Cyan
    & py (Join-Path $workspaceRoot 'scripts\check_cursor_rules_context_diet_v1.py') --strict
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Host '== Fact-Lock: run_prophecy_alignment_pytest.ps1 ==' -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File $prophecyBundle
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipNewsObservationContractSmoke) {
    $newsSmoke = Join-Path $workspaceRoot 'scripts\Run-NewsObservationContractSmoke.ps1'
    if (-not (Test-Path -LiteralPath $newsSmoke)) {
        throw "News observation contract smoke script not found: $newsSmoke"
    }
    Write-Host '== Fact-Lock: Run-NewsObservationContractSmoke.ps1 (default) ==' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $newsSmoke
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($IncludeBTrackDomainFeedbackSmoke) {
    $btrackSmoke = Join-Path $workspaceRoot 'scripts\Run-BTrackDomainFeedbackSmoke.ps1'
    if (-not (Test-Path -LiteralPath $btrackSmoke)) {
        throw "B-track domain feedback smoke script not found: $btrackSmoke"
    }
    if ($SkipNewsObservationContractSmoke) {
        Write-Host '== Fact-Lock: Run-BTrackDomainFeedbackSmoke.ps1 (full; news smoke skipped above) ==' -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File $btrackSmoke
    }
    else {
        Write-Host '== Fact-Lock: Run-BTrackDomainFeedbackSmoke.ps1 (-SkipNews; news already ran) ==' -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File $btrackSmoke -SkipNews
    }
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($IncludeP1AB) {
    if (-not (Test-Path -LiteralPath $p1AbBundle)) {
        throw "P1 A/B bundle script not found: $p1AbBundle"
    }
    Write-Host '== Fact-Lock: run_p1_ab_bundle.ps1 ==' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $p1AbBundle
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path -LiteralPath $insightScoreboardScript)) {
    throw "Insight scoreboard script not found: $insightScoreboardScript"
}
Write-Host '== Fact-Lock: build_insight_effectiveness_scoreboard.py ==' -ForegroundColor Cyan
& py $insightScoreboardScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $trackbQuaternionGateScript)) {
    throw "Track B quaternion two-stage gate script not found: $trackbQuaternionGateScript"
}
Write-Host '== Fact-Lock: report_trackb_quaternion_two_stage_gate.py ==' -ForegroundColor Cyan
& py $trackbQuaternionGateScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipCompressionRestoreBridge) {
    if (-not (Test-Path -LiteralPath $compressionRestoreBridgeScript)) {
        throw "Compression/restore bridge script not found: $compressionRestoreBridgeScript"
    }
    Write-Host '== Fact-Lock: run_agent_compression_restore_bridge.ps1 ==' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $compressionRestoreBridgeScript
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipCompressionDeepPackTriVerticalSmoke) {
    foreach ($t in $compressionDeepPackTriVerticalSmokePytests) {
        if (-not (Test-Path -LiteralPath $t)) {
            throw "Compression deep pack tri-vertical pytest not found: $t"
        }
    }
    Write-Host '== Fact-Lock: compression deep pack tri-vertical signoff smoke (pytest) ==' -ForegroundColor Cyan
    & py -m pytest @compressionDeepPackTriVerticalSmokePytests -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path -LiteralPath $trackCEvidenceScript)) {
    throw "Track C evidence script not found: $trackCEvidenceScript"
}
Write-Host '== Fact-Lock: build_track_c_evidence_pack_v1.py ==' -ForegroundColor Cyan
& py $trackCEvidenceScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $trackCCopyGuardScript)) {
    throw "Track C copy guard script not found: $trackCCopyGuardScript"
}
Write-Host '== Fact-Lock: check_track_c_copy_guard_v1.py ==' -ForegroundColor Cyan
& py $trackCCopyGuardScript (Join-Path $workspaceRoot 'docs\final\TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md')
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $trackCClaimValidatorScript)) {
    throw "Track C landing validator script not found: $trackCClaimValidatorScript"
}
Write-Host '== Fact-Lock: validate_track_c_landing_claims_v1.py ==' -ForegroundColor Cyan
& py $trackCClaimValidatorScript --evidence-pack (Join-Path $workspaceRoot 'docs\final\artifacts\track_c_evidence_pack_latest.json')
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $sajuGoldenReplayScript)) {
    throw "Saju golden replay script not found: $sajuGoldenReplayScript"
}
Write-Host '== Fact-Lock: run_saju_golden_replay.py ==' -ForegroundColor Cyan
& py $sajuGoldenReplayScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $sasangInterpretiveBundleTest)) {
    throw "Sasang interpretive bundle pytest not found: $sasangInterpretiveBundleTest"
}
Write-Host '== Fact-Lock: test_sasang_interpretive_insight_bundle_v1.py ==' -ForegroundColor Cyan
& py -m pytest $sasangInterpretiveBundleTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $bioSasangNstatesRehydrateTest)) {
    throw "Bio Sasang n-states rehydrate pytest not found: $bioSasangNstatesRehydrateTest"
}
Write-Host '== Fact-Lock: test_bio_sasang_nstates_strict_comparison_rehydrate_v1.py ==' -ForegroundColor Cyan
& py -m pytest $bioSasangNstatesRehydrateTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $mkmTrinityIndexTest)) {
    throw "MKM Trinity index pytest not found: $mkmTrinityIndexTest"
}
Write-Host '== Fact-Lock: test_mkm_trinity_index_v1.py ==' -ForegroundColor Cyan
& py -m pytest $mkmTrinityIndexTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $mkmMetaLayerEnvelopeTest)) {
    throw "MKM meta-layer envelope pytest not found: $mkmMetaLayerEnvelopeTest"
}
Write-Host '== Fact-Lock: test_mkm_meta_layer_envelope_v1.py ==' -ForegroundColor Cyan
& py -m pytest $mkmMetaLayerEnvelopeTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $athenaCheckpointTest)) {
    throw "Athena checkpoint pytest not found: $athenaCheckpointTest"
}
Write-Host '== Fact-Lock: test_athena_checkpoint.py (CENTRAL checkpoint prepend) ==' -ForegroundColor Cyan
& py -m pytest $athenaCheckpointTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipCodingIntentLinkSmoke) {
    if (-not (Test-Path -LiteralPath $codingIntentLinkSmokeTest)) {
        throw "Coding intent link pytest not found: $codingIntentLinkSmokeTest"
    }
    Write-Host '== Fact-Lock: test_record_coding_intent_link_v1.py (coding intent 3-point link PoC) ==' -ForegroundColor Cyan
    & py -m pytest $codingIntentLinkSmokeTest -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipCodingIntentPrManifestSmoke) {
    if (-not (Test-Path -LiteralPath $codingIntentPrManifestSmokeTest)) {
        throw "Coding intent PR manifest pytest not found: $codingIntentPrManifestSmokeTest"
    }
    Write-Host '== Fact-Lock: test_build_coding_intent_pr_manifest_v1.py (PR manifest PoC) ==' -ForegroundColor Cyan
    & py -m pytest $codingIntentPrManifestSmokeTest -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipCodingIntentGiteaMergePrecheckSmoke) {
    if (-not (Test-Path -LiteralPath $codingIntentGiteaMergePrecheckSmokeTest)) {
        throw "Coding intent gitea merge precheck pytest not found: $codingIntentGiteaMergePrecheckSmokeTest"
    }
    Write-Host '== Fact-Lock: test_build_coding_intent_gitea_merge_precheck_v1.py (gitea merge precheck) ==' -ForegroundColor Cyan
    & py -m pytest $codingIntentGiteaMergePrecheckSmokeTest -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipVertexAgentSearchContextUnit) {
    if (-not (Test-Path -LiteralPath $vertexAgentSearchContextUnitTest)) {
        throw "Vertex Agent Search context unit pytest not found: $vertexAgentSearchContextUnitTest"
    }
    Write-Host '== Fact-Lock: test_run_vertex_gemini_agent_search_context_v1.py (Agent Search RAG helpers; offline) ==' -ForegroundColor Cyan
    & py -m pytest $vertexAgentSearchContextUnitTest -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipDailyThreadWorkLogUnit) {
    if (-not (Test-Path -LiteralPath $dailyThreadWorkLogUnitTest)) {
        throw "Daily thread work log unit pytest not found: $dailyThreadWorkLogUnitTest"
    }
    Write-Host '== Fact-Lock: test_athena_daily_thread_log_sync_v1.py (multi-chat diary merge; offline) ==' -ForegroundColor Cyan
    & py -m pytest $dailyThreadWorkLogUnitTest -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipTwoTrackSubmissionAndMultiSymbolSmoke) {
    foreach ($t in $twoTrackSubmissionPackPytests) {
        if (-not (Test-Path -LiteralPath $t)) {
            throw "Two-track submission pack pytest not found: $t"
        }
    }
    foreach ($t in $multiSymbolGatesPytests) {
        if (-not (Test-Path -LiteralPath $t)) {
            throw "Multi-symbol gates pytest not found: $t"
        }
    }
    Write-Host '== Fact-Lock: Two-track submission pack (dual-regime parity; 3 pytest files) ==' -ForegroundColor Cyan
    & py -m pytest @twoTrackSubmissionPackPytests -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    Write-Host '== Fact-Lock: Multi-symbol gates and counterfactual QA (dual-regime parity; 3 pytest files) ==' -ForegroundColor Cyan
    & py -m pytest @multiSymbolGatesPytests -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipAramaicBtrackGraphPipelineSmoke) {
    foreach ($t in $aramaicBtrackGraphPipelineSmokePytests) {
        if (-not (Test-Path -LiteralPath $t)) {
            throw "Aramaic B-track graph pipeline pytest not found: $t"
        }
    }
    Write-Host '== Fact-Lock: Aramaic B-track graph pipeline smoke (dual-regime parity; 27 pytest files) ==' -ForegroundColor Cyan
    & py -m pytest @aramaicBtrackGraphPipelineSmokePytests -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

foreach ($t in $logosInsightBundlePytests) {
    if (-not (Test-Path -LiteralPath $t)) {
        throw "Logos insight bundle pytest not found: $t"
    }
}
Write-Host '== Fact-Lock: Logos insight bundle v1 (schema + builder; dual-regime parity) ==' -ForegroundColor Cyan
& py -m pytest @logosInsightBundlePytests -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipScienceCoreLaneSmoke) {
    foreach ($t in @($scienceCoreLaneSmokeTest, $scienceCoreComboSmokeTest, $scienceCoreInstrumentMatrixTest, $scienceCoreConditionalAttachTest, $scienceCoreProphecySensitivityTest)) {
        if (-not (Test-Path -LiteralPath $t)) {
            throw "Science Core lane pytest not found: $t"
        }
    }
    Write-Host '== Fact-Lock: Science Core B-track lane v1 + prophecy combo science arms (dual-regime parity) ==' -ForegroundColor Cyan
    & py -m pytest $scienceCoreLaneSmokeTest $scienceCoreComboSmokeTest $scienceCoreInstrumentMatrixTest $scienceCoreConditionalAttachTest $scienceCoreProphecySensitivityTest -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipSttRoutingAuditShowroomTrustSlice) {
    foreach ($t in $sttRoutingAuditShowroomTrustSlicePytests) {
        if (-not (Test-Path -LiteralPath $t)) {
            throw "STT routing audit / showroom trust slice pytest not found: $t"
        }
    }
    Write-Host '== Fact-Lock: STT routing audit log v1 + showroom trust viz thin slice (dual-regime parity; 3 pytest files) ==' -ForegroundColor Cyan
    & py -m pytest @sttRoutingAuditShowroomTrustSlicePytests -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipKmPhysicianCdsEnvelope) {
    foreach ($t in $kmPhysicianCdsEnvelopeTests) {
        if (-not (Test-Path -LiteralPath $t)) {
            throw "KM physician CDS envelope pytest not found: $t"
        }
    }
    Write-Host '== Fact-Lock: KM physician CDS assist envelope v1 (schema + builder pytest; dual-regime parity) ==' -ForegroundColor Cyan
    & py -m pytest @kmPhysicianCdsEnvelopeTests -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path -LiteralPath $dailyExecutionInsightBriefTest)) {
    throw "Daily execution insight brief pytest not found: $dailyExecutionInsightBriefTest"
}
Write-Host '== Fact-Lock: test_build_daily_execution_insight_brief_v1.py ==' -ForegroundColor Cyan
& py -m pytest $dailyExecutionInsightBriefTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

foreach ($t in $premiumBtrackMultilensReportPytests) {
    if (-not (Test-Path -LiteralPath $t)) {
        throw "Premium B-track multilens report pytest not found: $t"
    }
}
Write-Host '== Fact-Lock: premium_btrack_multilens_report_v1 (schema + builder; dual-regime parity) ==' -ForegroundColor Cyan
& py -m pytest @premiumBtrackMultilensReportPytests -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$premiumQueueStub = Join-Path $workspaceRoot 'scripts\premium_multilens_job_queue_stub_v1.py'
$premiumQueuePromotionGate = Join-Path $workspaceRoot 'scripts\build_premium_multilens_queue_promotion_gate_v1.py'
if (Test-Path -LiteralPath $premiumQueueStub) {
    Write-Host '== Fact-Lock: premium_multilens queue drain v0 (dry-run; allow-missing-queue) ==' -ForegroundColor Cyan
    & py $premiumQueueStub drain --root $workspaceRoot --allow-missing-queue --max-jobs 25
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
if (Test-Path -LiteralPath $premiumQueuePromotionGate) {
    Write-Host '== Fact-Lock: premium_multilens queue promotion gate v1 (S1 shadow; --skip-pytest) ==' -ForegroundColor Cyan
    & py $premiumQueuePromotionGate --skip-pytest --root $workspaceRoot
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipMkmDomainDesignOfflineSmoke) {
    if (-not (Test-Path -LiteralPath $mkmDomainDesignTokensScript)) {
        throw "MKM domain design tokens script not found: $mkmDomainDesignTokensScript"
    }
    foreach ($t in $mkmDomainDesignOfflinePytests) {
        if (-not (Test-Path -LiteralPath $t)) {
            throw "MKM domain design offline pytest not found: $t"
        }
    }
    Write-Host '== Fact-Lock: mkm_domain_design_tokens_v1 + universe hub UX gate + personadiary/mkmlife offline pytest ==' -ForegroundColor Cyan
    & py $mkmDomainDesignTokensScript
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    & py scripts/check_mkm_universe_hub_shell_v2.py
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    & py -m pytest @mkmDomainDesignOfflinePytests -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path -LiteralPath $myeongniThinBridgeTest)) {
    throw "Myeongni thin bridge pytest not found: $myeongniThinBridgeTest"
}
Write-Host '== Fact-Lock: test_emit_myeongni_thin_bridge_line_v1.py ==' -ForegroundColor Cyan
& py -m pytest $myeongniThinBridgeTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $mkmBriefingGuardrailsTest)) {
    throw "MKM personal briefing guardrails pytest not found: $mkmBriefingGuardrailsTest"
}
Write-Host '== Fact-Lock: test_validate_mkm_personal_briefing_guardrails_v1.py ==' -ForegroundColor Cyan
& py -m pytest $mkmBriefingGuardrailsTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $graphragPilotRouterTest)) {
    throw "GraphRAG pilot router pytest not found: $graphragPilotRouterTest"
}
Write-Host '== Fact-Lock: test_run_graphrag_pilot_router_v1.py ==' -ForegroundColor Cyan
& py -m pytest $graphragPilotRouterTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipCompAtom05WireSmoke) {
    foreach ($t in $compAtom05WirePytests) {
        if ($t -match '::') {
            continue
        }
        if (-not (Test-Path -LiteralPath $t)) {
            throw "COMP-ATOM-05 wire pytest not found: $t"
        }
    }
    Write-Host '== Fact-Lock: COMP-ATOM-05 graph wire selective bridge (pytest) ==' -ForegroundColor Cyan
    & py -m pytest @compAtom05WirePytests -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path -LiteralPath $philosophyLaneRagPilotTest)) {
    throw "Philosophy lane RAG pilot pytest not found: $philosophyLaneRagPilotTest"
}
Write-Host '== Fact-Lock: test_philosophy_lane_rag_pilot_v1.py ==' -ForegroundColor Cyan
& py -m pytest $philosophyLaneRagPilotTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipLinkedInB2bDraftSmoke) {
    foreach ($t in $linkedinB2bDraftPytests) {
        if (-not (Test-Path -LiteralPath $t)) {
            throw "LinkedIn B2B draft pytest not found: $t"
        }
    }
    Write-Host '== Fact-Lock: LinkedIn B2B draft queue v1 (pytest) ==' -ForegroundColor Cyan
    & py -m pytest @linkedinB2bDraftPytests -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    if ((Test-Path -LiteralPath $linkedinGenerateScript) -and (Test-Path -LiteralPath $linkedinQueueExample)) {
        Write-Host '== Fact-Lock: linkedin_queue_v1.example.json dry-run ==' -ForegroundColor Cyan
        & py $linkedinGenerateScript --queue $linkedinQueueExample --dry-run
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}

foreach ($t in $semanticRagBridgeBundlePytests) {
    if (-not (Test-Path -LiteralPath $t)) {
        throw "Semantic RAG bridge bundle pytest not found: $t"
    }
}
Write-Host '== Fact-Lock: semantic_rag_bridge_insight_bundle_v1 (schema + builder; dual-regime parity) ==' -ForegroundColor Cyan
& py -m pytest @semanticRagBridgeBundlePytests -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipMkmControlIntegritySmoke) {
    if (-not (Test-Path -LiteralPath $mkmControlIntegrityPipelineSmokeTest)) {
        throw "Control-Integrity pipeline smoke pytest not found: $mkmControlIntegrityPipelineSmokeTest"
    }
    Write-Host '== Fact-Lock: test_mkm_control_integrity_pipeline_smoke_v1.py ==' -ForegroundColor Cyan
    & py -m pytest $mkmControlIntegrityPipelineSmokeTest -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipVaFusionControlIntegritySmoke) {
    foreach ($t in $vaFusionControlIntegritySmokeTests) {
        if (-not (Test-Path -LiteralPath $t)) {
            throw "VA fusion control-integrity smoke pytest not found: $t"
        }
    }
    Write-Host '== Fact-Lock: VA fusion control-integrity chain + policy golden (CONSTITUTION 3.8.4) ==' -ForegroundColor Cyan
    & py -m pytest @vaFusionControlIntegritySmokeTests -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipSasangSajuJointLiteraturePipeline) {
    # 5c 조인트 7 pytest — Europe PMC·문헌 체인 회귀(CONSTITUTION §3.3 · dual-regime `Sasang–saju joint literature pipeline`)
    #    + 인제스트·staleness(test_ingest_* , test_check_* ) → 배열 총 9 파일
    foreach ($t in $sasangSajuJointLiteraturePytests) {
        if (-not (Test-Path -LiteralPath $t)) {
            throw "Sasang-saju joint literature pytest not found: $t"
        }
    }
    Write-Host '== Fact-Lock: Sasang-saju joint pipeline (dual-regime parity: 7 literature + 1 ingest + 1 staleness pytest files) ==' -ForegroundColor Cyan
    & py -m pytest @sasangSajuJointLiteraturePytests -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipMyeongniLensRecommendedStack) {
    foreach ($t in $myeongniLensRecommendedPytests) {
        if (-not (Test-Path -LiteralPath $t)) {
            throw "Myeongni lens recommended pytest not found: $t"
        }
    }
    Write-Host '== Fact-Lock: Myeongni lens recommended stack (multilens CI parity, 15 pytest files: brief+thin then batch 13) ==' -ForegroundColor Cyan
    & py -m pytest @myeongniLensRecommendedPytests -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($IncludeCodebookFactSafe) {
    if (-not (Test-Path -LiteralPath $codebookFactSafeBundleScript)) {
        throw "Codebook Fact-Safe bundle script not found: $codebookFactSafeBundleScript"
    }
    Write-Host '== Fact-Lock: run_codebook_factsafe_bundle.ps1 ==' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $codebookFactSafeBundleScript -IncludeRecoveredReadiness
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($Include4dOhaengRegimeSnapshotGate) {
    if (-not (Test-Path -LiteralPath $ohaengRegimeSnapshotGateChain)) {
        Write-Host "WARN: 4D->Ohaeng chain script not in repo; skip (not a gate failure): $ohaengRegimeSnapshotGateChain" -ForegroundColor Yellow
    } else {
        Write-Host '== Fact-Lock (optional): 4D->Ohaeng regime snapshot + gate ==' -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File $ohaengRegimeSnapshotGateChain
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}

if ($IncludeBtrackBalancedRegimeEval) {
    if (-not (Test-Path -LiteralPath $btrackBalancedRegimeEvalChain)) {
        Write-Host "WARN: B-track balanced regime eval script not in repo; skip (not a gate failure): $btrackBalancedRegimeEvalChain" -ForegroundColor Yellow
    } else {
        Write-Host '== Fact-Lock (optional): B-track balanced regime eval chain ==' -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File $btrackBalancedRegimeEvalChain
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}

if ($IncludeTruthfulQaBenchmarkGate) {
    if (-not (Test-Path -LiteralPath $truthfulQaBenchmarkScript)) {
        throw "TruthfulQA benchmark script not found: $truthfulQaBenchmarkScript"
    }

    Write-Host '== Fact-Lock (optional): TruthfulQA A/B benchmark artifact gate ==' -ForegroundColor Cyan
    $missingTruthfulQaArtifacts = @()
    if (-not (Test-Path -LiteralPath $truthfulQaMcBenchmarkArtifact)) {
        $missingTruthfulQaArtifacts += $truthfulQaMcBenchmarkArtifact
    }
    if (-not $TruthfulQaBenchmarkGateMcOnly) {
        if (-not (Test-Path -LiteralPath $truthfulQaGenerationBenchmarkArtifact)) {
            $missingTruthfulQaArtifacts += $truthfulQaGenerationBenchmarkArtifact
        }
    }

    if ($missingTruthfulQaArtifacts.Count -gt 0) {
        if ($StrictTruthfulQaBenchmarkGate) {
            Write-Host 'FAIL: TruthfulQA benchmark artifacts missing:' -ForegroundColor Red
            $missingTruthfulQaArtifacts | ForEach-Object { Write-Host "  $_" }
            exit 1
        }
        Write-Host 'WARN: TruthfulQA benchmark artifacts missing (run A/B benchmark script to generate):' -ForegroundColor Yellow
        $missingTruthfulQaArtifacts | ForEach-Object { Write-Host "  $_" }
    } else {
        if ($TruthfulQaBenchmarkGateMcOnly) {
            Write-Host 'OK: TruthfulQA MC benchmark artifact present (generation not required).' -ForegroundColor Green
        } else {
            Write-Host 'OK: TruthfulQA benchmark artifacts present (mc + generation).' -ForegroundColor Green
        }
    }
}

if ($IncludeTruthfulQaBenchmarkEvalGate) {
    if (-not (Test-Path -LiteralPath $truthfulQaBenchmarkEvalGateScript)) {
        throw "TruthfulQA eval gate script not found: $truthfulQaBenchmarkEvalGateScript"
    }
    Write-Host '== Fact-Lock (optional): TruthfulQA A/B eval gate ==' -ForegroundColor Cyan
    $truthfulQaEvalArgs = @(
        $truthfulQaBenchmarkEvalGateScript,
        '--mc-json', $truthfulQaMcBenchmarkArtifact,
        '--generation-json', $truthfulQaGenerationBenchmarkArtifact,
        '--out-json', $truthfulQaGateArtifact
    )
    if ($StrictTruthfulQaBenchmarkEvalGate) {
        $truthfulQaEvalArgs += '--strict'
    }
    if ($TruthfulQaEvalMcOnly) {
        $truthfulQaEvalArgs += '--mc-only'
    }
    & py @truthfulQaEvalArgs
    if ($LASTEXITCODE -ne 0) {
        if ($StrictTruthfulQaBenchmarkEvalGate) {
            exit $LASTEXITCODE
        }
        Write-Host "WARN: TruthfulQA eval gate returned NO_GO (strict disabled)." -ForegroundColor Yellow
    }
}

if (-not $SkipCuratedJointStalenessCheck) {
    if (-not (Test-Path -LiteralPath $curatedJointStalenessScript)) {
        Write-Host "WARN: curated joint staleness script missing; skip: $curatedJointStalenessScript" -ForegroundColor Yellow
    } else {
        Write-Host '== Fact-Lock: curated saju joint staleness (curated signal vs hit-rate artifact) ==' -ForegroundColor Cyan
        & py $curatedJointStalenessScript
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'WARN: staleness check returned non-zero (use --strict on script only if you want CI fail).' -ForegroundColor Yellow
        }
    }
}

if (-not $SkipSchedulerSoloCoreStackSmoke) {
    $schedulerPytest = Join-Path $workspaceRoot 'tests\test_mkm_scheduler_solo_core_stack_audit_v1.py'
    if (-not (Test-Path -LiteralPath $schedulerPytest)) {
        Write-Host "WARN: scheduler solo stack pytest missing; skip: $schedulerPytest" -ForegroundColor Yellow
    }
    else {
        Write-Host '== Fact-Lock: MKM scheduler solo core stack band gate (pytest) ==' -ForegroundColor Cyan
        & py -m pytest $schedulerPytest -q
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}

if (-not $SkipIntegratedGovernanceBuild) {
    if (-not (Test-Path -LiteralPath $igGovernanceInvoker)) {
        Write-Host "WARN: integrated governance invoker missing; skip: $igGovernanceInvoker" -ForegroundColor Yellow
    }
    else {
        Write-Host '== Fact-Lock (recommended): integrated governance v1 (deps-gated + digest schema) ==' -ForegroundColor Cyan
        & py $igGovernanceInvoker --workspace-root $workspaceRoot
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}

if (-not $SkipSafeOpsSurfaceCheck) {
    $safeOpsTail = Join-Path $workspaceRoot 'scripts\Invoke-SafeOpsSurfaceCheck.ps1'
    if (Test-Path -LiteralPath $safeOpsTail) {
        if (-not $SafeOpsIgnoreLiveSync) {
            $livePull = Join-Path $workspaceRoot 'scripts\Invoke-LiveSyncHeartbeatPull.ps1'
            if (Test-Path -LiteralPath $livePull) {
                Write-Host '== Fact-Lock (pre-safe-ops): LiveSync heartbeat pull (soft) ==' -ForegroundColor DarkCyan
                & powershell -NoProfile -ExecutionPolicy Bypass -File $livePull -WorkspaceRoot $workspaceRoot -SoftFail | Out-Null
            }
        }
        Write-Host '== Fact-Lock (recommended tail): Safe ops surface check ==' -ForegroundColor Cyan
        $safeOpsCli = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $safeOpsTail, '-WorkspaceRoot', $workspaceRoot)
        if ($SafeOpsIgnoreLiveSync) { $safeOpsCli += '-IgnoreLiveSync' }
        if ($SafeOpsStrictTradingGoNoGo) { $safeOpsCli += '-StrictTradingGoNoGo' }
        & powershell @safeOpsCli
        $safeTailExit = $LASTEXITCODE
        if ($safeTailExit -eq 2) {
            Write-Host 'FAIL: Safe ops surface CRITICAL (exit 2). See reports/safe_ops_surface_check_latest.json' -ForegroundColor Red
            exit 2
        }
        if ($safeTailExit -eq 1) {
            Write-Host 'WARN: Safe ops surface degraded (exit 1); pytest Fact-Lock bundle succeeded.' -ForegroundColor Yellow
        }
    } else {
        Write-Host "WARN: Invoke-SafeOpsSurfaceCheck.ps1 missing; skip tail: $safeOpsTail" -ForegroundColor Yellow
    }
}

exit 0
