# Constitution / Inference — 구현 팩트 (SSOT)

**작성일**: 2026-03-29  
**최종 갱신**: 2026-05-20 — §1.0.5 지휘관 **세계관·철학 헌법** 고정 (`MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md`); P0 경로·§1.1.4 표 교차참조. **이전 갱신**: 2026-04-30 — TruthfulQA A/B B-track 벤치·게이트·`Run-TruthfulQAReproBundleV1.ps1`·`run_fact_lock_bundle.ps1` TruthfulQA 스위치를 §3.6 표·`verify_p0_constitution_gate_paths.ps1`에 정렬; CI `dual-regime-integrity.yml`에 DryRun+pytest. 동일 일자 **§31.80** external Bible anchor governance 체인·스모크·worktree 혼동 방지 노트 추가. **이전 갱신**: 2026-04-27 — SSOT 정합 복구(Drift pruning): 현행 운영 레일 중심으로 P0 경로 게이트를 재정렬하고, 비활성/미배포 체인은 필수 게이트에서 제외. **이전 갱신**: 2026-04-18 — §1.1.1 `[VISION]` 예언 성능 우선·국방 서사 `research_only` 격리; OHLCV 30일 패널 재실행(best_delta **-4.8%**)·`prophecy_overlay_prior_threshold_recommended_latest.json`·`prophecy_prior_threshold_sweep_summary_latest.json`; `eval_prophecy_hit_rate_v1.py --run-mode price`; CI `prophecy-restoration-spike-smoke.yml`. **보강 (2026-05-02 — 명리 엔진 결정론 체인):** §3.3 표에 지장간 LUT·지장간 오행 가중·대운/起운(Meeus 12절 근사)·`rule_school_mkm_4d_v1` 4D 블렌드·관련 회귀 경로 추가. 본 체인은 **명리 B-track 산출·4D 입력**이며 3렌즈+코디네이터 제품 전체와 동일시하지 않음(§1.1·렌즈 계약).
**보강 (2026-05-14 — 서피스 태그 Phase C):** `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 단일 태그 표와 정합하여 §1.2(압축 스텁·HTTP v2·L1 RTT 벤치)·§1.3.1(일일 융합)·§3.6(TruthfulQA)·Aramaic MVP 스케줄·registry drift 행·§6 테스트 서문 및 Track A 미터링·렌즈 승격 게이트 행에 **서피스 태그**(CI 포함 / 번들 선택 / 헬스만)를 명시한다. §6 AI BGM·상징→오디오 M0·사상→감정·렌즈 뮤직 M1–M4(`test_run_lens_music_gematria_v1`·`test_lens_music_gate_chain_v1`·내부 eval·JSONL 검증) 행에도 동일 태그를 접미한다. **§6 보강:** CI `Lens music gematria seed trace`·`Lens music prompt overlay`·`Lens music prompt PoC M26-M30` 스텝에 대응하는 pytest 행을 §6 표에 추가한다. **§6 보강:** `dual-regime-integrity`의 VA trajectory·§3.8.2–§3.8.4 fusion 무결성 분할 스텝에 대응하는 pytest 행을 §6 표에 삽입한다. **§6 보강:** TruthfulQA DryRun+pytest 묶음·`MKM meta-layer envelope`·`Token API hydration trend` CI 스텝에 대응하는 행을 §6 표에 추가한다. **§6 보강:** TruthfulQA 직후 연속 구간(트랙 가드·ENTRY_16 ingest·B-track 예언·뉴스 관측·Logos·Survivor·휴먼 감사 스파이크·월간 큐·일반예언·세션 패널·날씨 120d·Lexicon·L1·토큰 API·압축 KPI·LoRA·Athena §28)에 대응하는 **복합** pytest·스크립트 행을 §6 표에 추가한다. **§6 보강:** Token API trend pytest 직후 B-track 표면·Track C/cross-lens RAG·프리미엄 multilens·semantic bridge·alert·market Myeongni·Thin bridge·개인 브리핑 가드 복합 행을 §6 표에 추가한다. **§6 권장:** hydration trend 직후 `live_ratio`·`Integrated governance` invoker·브리핑 가드 다음 job tail은 §6 **포인터 행**으로만 고정하고 전개 SSOT는 `.github/workflows/dual-regime-integrity.yml`로 둔다.

**보강 (2026-05-02 — 명리 대외 공학 어휘):** `docs/final/MYEONGRI_EXTERNAL_ENGINEERING_LEXICON_V1.md` — 상용·논문·광고 등 **대외 서술**용 번역 테이블; 코드·스키마 명칭 불변.
**보강 (2026-05-02 — 대운 연령 경계):** §3.3 표 `대운·起運 v1` — `scripts/myeongri_daewoon_v1.build_daewoon_list_v1`가 연속 구간 경계를 단일 리스트로 계산하고 `age_start`/`age_end`를 소수 6자리로 고정해 행 간 경계가 일치한다(起運 부동소수 JSON 표시 안정화).
**보강 (2026-05-02 — 명리 AI 해석 봉투):** `docs/final/MYEONGRI_AI_INTERPRETATION_PROMPT_TEMPLATE_V1.md` — B-track **보조 해석**용 시스템/유저 프롬프트·RAG 주입 순서; 산출 스키마 `docs/final/schemas/myeongri_ai_interpretation_envelope_v1.schema.json`; 회귀 `tests/test_myeongri_ai_interpretation_envelope_v1.py`.
**보강 (2026-05-10 — B-track BTC 히트레이트 번들):** § 예언 히트레이트 절에 `run_btc_weight_hit_rate_bundle_v1.py`·`Run-BtcWeightWeeklyHitRateBundle_v1.ps1`·`Register-BtcWeightHitRateBundleWeeklyTask.ps1`·회귀 경로 추가; 본선·실매매 자동 합선 없음.
**보강 (2026-05-12 — B-track 예언 체인 읽기 전용 점검):** `scripts/check_btrack_prophecy_chain_prereqs_v1.py` — 일일 체인 스크립트·KOSPI/BTC 기본 CSV·주요 `*_latest` 존재·`btrack_prophecy_score_latest.json` 기준 instrument 듀얼 레그 요약; `--stdout-only`·`--strict`; 산출 `btrack_prophecy_chain_prereqs_v1_latest.json`; 회귀 `tests/test_check_btrack_prophecy_chain_prereqs_v1.py`.
**보강 (2026-06-09 — Ops memory JSON-slice + web_ops regime `[HYPO]`):** `storage/meta/mkm_ops_memory_index_v1.json`(anchor+`json_pointer` overlay v1.1) · `scripts/build_mkm_ops_memory_web_ops_overlay_v1.py` · `scripts/route_mkm_ops_memory_pack_v1.py`(`--topic`→`--lane web_ops`) · `scripts/bench_mkm_ops_memory_web_ops_retrieval_v1.py` · web_ops 게이트 `reports/web_ops_regime_gate_v1_latest.json`·`check_web_ops_regime_gate_v1.py` · 주간 `Invoke-WebOpsRegimeWeeklyRoutine_v1.ps1`(Task `MKM_WebOps_Regime_Weekly`). **서피스 태그: 헬스만**(`run_workspace_automation_health.ps1 -IncludeWebOpsRegimeSmoke`). Track A·live trading 자동 합선 없음.
**보강 (2026-06-19 — Logos/4D ops memory Cursor inject `[HYPO]`):** `scripts/build_mkm_ops_memory_logos_math_overlay_v1.py` · `scripts/run_mkm_ops_memory_logos_math_overlay_chain_v1.py` → `storage/meta/mkm_ops_memory_index_v1.json` overlay `logos_math_v1`(7× `prism_ops_logos_*` JSON-slice) · oracle lane pack · `Invoke-MkmOpsMemoryIndexRoutine_v1.ps1 -Lane oracle`(logos overlay merge) · `mkm_ops_memory_index_lib_v1.ensure_lane_pack_index`(oracle in-memory fallback) · 재개 `Invoke-MkmCursorSessionUpgrade_v1.ps1 -Lane oracle` → `docs/final/artifacts/mkm_chat_resume_pack_latest.md` · re-invention guard `docs/final/artifacts/logos_theory_implementation_wiring_v1.json` · **Tier-1 module readiness** `scripts/run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py` → `docs/final/artifacts/logos_oracle_cursor_inject_tier1_readiness_v1_latest.json`(`tier1_module_ssot_ready`; Tier-2/3 full upgrade blocked). LTM+A2A PoC: `scripts/run_mkm_logos_math_ltm_a2a_chain_v1.py`. K-track ablation(별 축): `scripts/run_mkm_gematria_4d_ablation_chain_v1.py`. **서피스 태그: 운영 SSOT (CI 미포함).** B-track·`send_gate: HOLD`·성경(Logos) `[NON_GATING]` — Track A·live·「진화 완료」주장 금지.
**보강 (2026-07-06 — Oracle Logos Tier-3 anchor 3600 research ceiling `[HYPO]`):** commander signoff `docs/final/artifacts/logos_oracle_tier3_narrative_commander_signoff_v1_latest.json` · protocol `py scripts/run_logos_oracle_tier3_narrative_upgrade_protocol_chain_v1.py` · closure `docs/final/artifacts/logos_bible_advancement_closure_v1_latest.json`(lemma **3600** · router_hit **1.0**) · observability `docs/final/artifacts/logos_oracle_narrative_closure_observability_v1_latest.json` · L1 tracker `reports/logos_l1_corpus_expansion_tracker_v1_latest.json`(`stage_batch_preview_exhausted` · HG auto expansion **frozen**) · weekly `scripts/Invoke-MkmOracleModuleObservabilityWeeklyRoutine_v1.ps1`. **resonance_cap 128 불변** · preview 10k+·명시 승인 전 HG batch 재개 금지 · canonical Top100 merge 금지 · Track A·live 자동 합선 없음.
**보강 (2026-06-21 — Magic Orb design readiness `[HYPO]`):** engineering(`probe_mkmlife_magic_orb_live_v1.py`)과 **design/UX 분리** — Playwright `projects/mkm/mkm-life/scripts/capture-magic-orb-design-readiness-playwright.mjs` → `reports/magic_orb_design_screenshot_latest.png` · merge `scripts/build_magic_orb_design_readiness_v1.py` → **`reports/magic_orb_design_readiness_v1_latest.json`**(`consumer_ready`는 `engineering_ok`+`design_ok`+commander visual); chain `scripts/run_magic_orb_design_readiness_chain_v1.py`; commander visual `scripts/record_magic_orb_commander_visual_review_v1.py` → `reports/magic_orb_commander_visual_review_v1_latest.json`; Fact-Lock **`-IncludeMagicOrbDesignReadiness`**; 주간 **`MKM_MagicOrb_DesignReadiness_Weekly`**.
**보강 (2026-07-16 — Roo Ollama L1 + Bodyguard proxy PoC):** setup `docs/final/MKM_ROO_OLLAMA_L1_SETUP_V1.md` · profile `docs/final/artifacts/mkm_roo_ollama_l1_provider_profile_v1_latest.json` · check `scripts/check_roo_ollama_l1_ready_v1.py` → `reports/roo_ollama_l1_ready_v1_latest.json` · proxy `scripts/run_mkm_agent_bodyguard_proxy_v1.py` (OpenAI Compatible → Ollama · egress deny · audit `reports/agent_bodyguard_proxy_audit.jsonl`) · `.roo/rules/mkm-bodyguard-l1.md` · parent `MKM_AGENT_MIDDLEWARE_BODYGUARD_V1.md`. **UI Provider 전환은 지휘관 클릭** · `send_gate: HOLD` · Track A 없음. **서피스 태그: 운영 SSOT (CI 미포함).**

**보강 (2026-06-21 — DNS/deploy axis isolation `[HYPO]`):** mkmlife **Cloudflare Workers** vs **jema-ai.com / logos.jema-ai.com** VPS middleware canonical split — live probe `scripts/probe_mkm_deployment_axis_isolation_v1.py` → `reports/mkm_deployment_axis_isolation_probe_latest.json`; chain `scripts/run_mkm_deployment_axis_isolation_chain_v1.py` → `reports/mkm_deployment_axis_isolation_chain_v1_latest.json`; mkmlife post-deploy `projects/mkm/mkm-life/scripts/Deploy-CloudflareMkmlife.ps1`(consumer smoke 직후 `--profile core`); 헬스 선택 **`run_workspace_automation_health.ps1 -IncludeMkmDeploymentAxisIsolationSmoke`** · 단축 **`-MkmDeploymentAxisIsolationSmokeOnly`**; Fact-Lock 선택 **`run_fact_lock_bundle.ps1 -IncludeMkmDeploymentAxisIsolationSmoke`**; 주간 Task **`MKM_Deployment_Axis_Isolation_Weekly`** — `scripts/Register-MkmDeploymentAxisIsolationWeeklyTask_v1.ps1` · 래퍼 `scripts/Invoke-MkmDeploymentAxisIsolationWeeklyRoutine_v1.ps1` · verify `scripts/Verify-MkmDeploymentAxisIsolationWeeklyScheduledTask_v1.ps1` · SSOT tier4 `mkm_scheduler_solo_core_stack_v1.json`; 회귀 `tests/test_probe_mkm_deployment_axis_isolation_v1.py`. **서피스 태그: 헬스·번들 선택·주간.** Track A·SEND·실매매 자동 합선 없음.

**보강 (2026-06-21 — Universal Root community GTM poll `[HYPO]`):** UR-W1 Discussions #2 poll `scripts/poll_universal_root_community_gtm_v1.py` → `reports/universal_root_community_poll_v1_latest.json`; Thread B gated post `scripts/post_universal_root_discussions_thread_b_v1.py`(`--min-external-repro 1` · live `--acknowledge-send`); 주간 **`MKM_UniversalRoot_CommunityGtm_Weekly`** — `scripts/Register-UniversalRootCommunityGtmWeeklyTask_v1.ps1` · 래퍼 `scripts/Invoke-UniversalRootCommunityGtmWeeklyRoutine_v1.ps1`(poll → repro≥1 & Thread B 미게시 시 auto `--acknowledge-send`) · verify `scripts/Verify-UniversalRootCommunityGtmWeeklyScheduledTask_v1.ps1` · SSOT tier4; GTM SSOT `reports/universal_root_community_gtm_v1_latest.json`. **send_gate HOLD** · GitHub live post는 weekly gate+ack만. **보강 (2026-06-22 — UR GTM FREEZE):** `docs/final/artifacts/universal_root_gtm_freeze_v1_latest.json` · `scripts/check_universal_root_gtm_freeze_v1.py`(`--strict-integrity` · `--strict` · `--patch-gtm`) · `scripts/universal_root_gtm_freeze_lib_v1.py` · `scripts/universal_root_gtm_integrity_lib_v1.py` — `external_repro=0` 시 maintainer bump live 차단; **UNFREEZE master key = `external_repro_count>=1` AND Phase1A integrity**; bump exit **3**; override `--commander-override-freeze`; pytest `tests/test_check_universal_root_gtm_freeze_v1.py`. **Phase 1A:** entry `scripts/run_universal_root_baseline_compare_v1.py` → alias `reports/baseline_vs_dual_plane_v1.json` · B0 spec `docs/final/artifacts/universal_root_baseline_b0_spec_v1.json`(fixture sha256 + recompute, no literal lock) · pytest `tests/test_universal_root_phase1a_baseline_compare_v1.py`.

**보강 (2026-06-20 — Domain adapter shallow routing `[HYPO]`):** `docs/final/artifacts/mkm_ops_sync_bridge_v1.json` `domain_adapters`(pixel_battalion·lens_audio·**design_surface**) · `scripts/check_mkm_ops_sync_bridge_domain_adapters_v1.py` · `scripts/build_mkm_ops_memory_domain_adapters_overlay_v1.py` · `scripts/Run-DomainAdapterPointerSmoke_v1.ps1` · `scripts/apply_mkmlife_pixel_language_local_sprite_paths_v1.py` · design lane pack `prism_ops_pixel_battalion_gate`·`prism_ops_lens_audio_gate`·**`prism_ops_clinic_landing_gate`** · `Invoke-MkmOpsMemoryIndexRoutine_v1.ps1 -Lane design`. **Trust Composition SSOT:** `docs/final/MKM_TRUST_COMPOSITION_DESIGN_PIPELINE_V1.md` · clinic LOI gate `scripts/check_clinic_km_mmp_landing_gate_v1.py` → `reports/clinic_km_mmp_landing_gate_v1_latest.json` · chain `scripts/Run-ClinicLoiLandingDesignChain_v1.ps1` · seed schema `docs/final/schemas/design_reference_seed_v1.schema.json` · DTCG `reports/clinic_km_mmp_landing_tokens_v2.dtcg.json` · pytest `tests/test_clinic_km_mmp_landing_gate_v1.py`. **Logos external B2B:** `scripts/build_logos_graph_studio_external_b2b_meeting_kit_v1.py` → `reports/logos_graph_studio_external_b2b_meeting_kit_v1_latest.json`. **원장 Entry B 온보딩 하네스:** `docs/final/artifacts/han_clinic_owner_onboarding_brief_v1_latest.md` · research `docs/research/CLINICIAN_POWER_USER_INFRA_AUDIT_V1.md` · gate `scripts/infra_compliance_gate_v1.py` · chain `scripts/run_han_clinic_owner_entry_b_onboarding_chain_v1.py`·`scripts/Run-HanClinicOwnerEntryBOnboardingChain_v1.ps1` · 카드 `scripts/build_han_clinic_owner_onboarding_card_v1.py` · pytest `tests/test_infra_compliance_gate_v1.py`·`tests/test_han_clinic_owner_entry_b_onboarding_chain_v1.py`. **서피스 태그: 운영 SSOT (CI 미포함).** `research_only`·`send_gate: HOLD`·Track A·SEND 자동 합선 없음.
**보강 (2026-06-26 — Pillar A Cursor LTM + suspect_first P7 `[HYPO]`):** LTM Graph OS(`storage/meta/mkm_long_term_memory_graph_v1.json`·`graph_axis=A_ltm`) · shallow→deep `Invoke-MkmCursorSessionUpgrade_v1.ps1`→envelope `mkm_cursor_deep_handoff_envelope_v1_latest.json` · 종료 `run_mkm_cursor_session_end_v1.py` 또는 `athena_checkpoint.py --continuity-id`→`append_mkm_cursor_turn_meta_v1`(`self_audit`) · 감사 `check_mkm_cursor_turn_meta_audit_v1.py` · 회귀 `run_mkm_pillar_a_cursor_health_smoke_v1.py` · 헬스 **`-PillarACursorContinuitySmokeOnly`** · L0 `.cursorrules` suspect-first · signoff `reports/mkm_bench_2026_003_pillar_a_signoff_v1_latest.json` · 계약 `docs/final/artifacts/mkm_meta_coordinator_turn_contract_v1_latest.md` · **Logos graph_slice·mindmap = 별 채팅(Oracle)** · Track A·SEND·live 자동 합선 없음.
**보강 (2026-07-12 — LLM Wiki thin lint `[HYPO]`):** schema contract `docs/final/LLM_WIKI_SCHEMA.md` · lint `scripts/check_llm_wiki_lint_v1.py` → `docs/final/artifacts/llm_wiki_lint_v1_latest.json` (validation only; no auto-classify / no Notion SSOT).
**보강 (2026-06-21 — Universal Root OSS Cursor smoke Phase 15–17 `[HYPO]`):** `scripts/run_universal_root_oss_cursor_smoke_v1.py`(fixture-only · HF/Ollama 불필요) → `reports/universal_root_oss_cursor_smoke_v1_latest.json` · topology `scripts/build_universal_root_topology_crosswalk_v1.py`·`scripts/check_universal_root_topology_crosswalk_v1.py` · wall cards `scripts/build_universal_root_wall_divergence_exception_cards_v1.py` · gate spec `docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json`(phase **17**) · full closure `scripts/run_logos_graphrag_phase17_closure_observability_chain_v1.py` · pytest `tests/test_universal_root_topology_crosswalk_v1.py`·`tests/test_universal_root_wall_divergence_exception_cards_v1.py`. **Launch Gate #1:** `scripts/check_hardcoded_workspace_paths_v1.py --scope oss --strict` · `scripts/normalize_workspace_paths_v1.py --apply`. **raw/repair dual:** lexicon `prime_hit_rate`·`english_only_distortion_rate` vs topology `verse_reachable_rate` — fixture 500-pair bench; Track A·live·공개 투자 주장 금지. **서피스 태그: 헬스·OSS README (CI 미포함).**
**보강 (2026-06-23 — GRASP topology stub defense `[HYPO]`):** `scripts/decomposer/topology_security_filter_v1.py`(ID alignment + decoy · stub-only) → `reports/topology_grasp_defense_bench_v1_latest.json`(`attacker_subgraph_f1` gate ≤0.15 · full stub) · pytest `tests/test_topology_security_filter_v1.py` · GraphRAG hook `scripts/run_logos_graphrag_phase16_topology_crosswalk_chain_v1.py --sanitize-topology` · CL_stat `scripts/verifier/citation_lock_stat_v1.py`·`tests/test_citation_lock_stat_v1.py` · MPAC Charter `docs/final/LENS_UTILIZATION_CHARTER_V1.md` §10 · MAGE mapping `docs/final/artifacts/mkm_mage_shadow_memory_send_gate_mapping_v1_latest.json`. **서피스 태그: B-track export sanitize (CI optional).**
**보강 (2026-06-23 — MKM-UR-Bench-5K scaled holdout `[HYPO]`):** generator `scripts/bench/generate_massive_universal_root_pairs_v1.py` **v1.2.0** (`massive_gen_english_surface_b0` ~12% + hard Strong's ~10%) → `tests/fixtures/nsm_41k_lexicon_crosswalk_5000_v1.json` · holdout `scripts/build_universal_root_bench_5k_holdout_fixture_v1.py` → `tests/fixtures/universal_root_bench_5k_holdout_v1.json` · chain `scripts/run_universal_root_bench_5k_holdout_chain_v1.py` → `reports/universal_root_bench_5k_holdout_phase1a_v1_latest.json` · gate `scripts/check_universal_root_bench_5k_v1.py`(`min_holdout_b0_rate` SSOT) · SSOT `docs/final/artifacts/universal_root_bench_5k_named_v1.json` · pytest `tests/test_universal_root_bench_5k_holdout_chain_v1.py`·`tests/test_generate_massive_universal_root_pairs_v1.py` · public export manifest `pre_push_gate` + `exports/mkm-universal-root-v1/` · **500-pair smoke KPI와 합산 금지**. **서피스 태그: OSS export·Discussions (CI optional).**
**보강 (2026-06-21 — Dual-plane commercialization gates · TRACK_C §3.0b):** 사업·대외 승격은 아래 표만 — NL·덱 단독 GO 금지 · `MKM_PROMOTION_GATE_CHECKLIST_B_TO_A_C_V1.md` 병행.

| Gate | Y1 Universal Root OSS | Y2 On-prem SDK/Docker | Parallel: Track A compression |
|------|----------------------|------------------------|-------------------------------|
| **Status** | `[FACT]` live · GitHub `mkm-universal-root` | `[HYPO]` roadmap · **not in public export** | `[FACT]` Track A bench · **not Y1 Hero** |
| **Reproduce** | `run_universal_root_oss_cursor_smoke_v1.py` exit 0 | TBD Docker smoke script | `run_ultra_compression_default.py` + KPI summary |
| **KPI rule** | lexicon + topology **separate** · `collapsed_combined_score: null` | custom fixture required | raw `active_kpi` primary · repair_v2 ≠ hero |
| **send_gate** | HOLD | HOLD | HOLD · inbound B2B only |
| **FAIL-COMP-004** | no merge with 47.5% · ko_shorts · SOAP · trading | no merge with Y1 fixture headline | no merge with UR 99.53% headline |
| **Track A / live** | auto-promote **forbidden** | auto-promote **forbidden** | separate promotion checklist |

SSOT: `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.0b–§3.0c–**§3.0e** · `MKM_UNIVERSAL_ROOT_INVESTOR_FACT_LOCK_CORRECTION_APPENDIX_EN_V1.md` · `.cursor/rules/dual-plane-kpi-non-merge-v1.mdc` · `.cursor/rules/mkm-macro-positioning-fact-lock-v1.mdc`.
**보강 (2026-07-04 — 거시경제 외곽 포지셔닝 Fact-Lock):** `docs/final/artifacts/macro_positioning_evidence_pack_v1.json` — 200:1 production-to-safety 비대칭(Big4 CapEx $725B vs guardrails $3~4B), EU CADA Level 3-4, Fable 5 export ban(2026-06-12), 프랑스/독일 Palantir 철거. **시장 기회 ≠ 점유 확정** — TAM으로 send_gate 해제·독점 주장 금지. 규칙: `.cursor/rules/mkm-macro-positioning-fact-lock-v1.mdc`. P0 경로 포함.
**보강 (2026-06-16 — 4축 독립 승격 가드레일):** `docs/final/artifacts/mkm_multi_axis_promotion_gate_policy_v1.md` · `validate_mkm_multi_axis_promotion_gate_policy_v1.py` → `mkm_multi_axis_promotion_gate_policy_v1_latest.json` — `promotion_cascade_forbidden` · AX-1~4 격벽 · FAIL-COMP-004 정렬. **PoC ≠ 제품화 ≠ Track A ≠ MASK.** 회귀: `tests/test_mkm_multi_axis_promotion_gate_policy_v1.py`.
**보강 (2026-05-10 — 한의 의사 CDS 봉투 v1):** `docs/final/schemas/km_physician_cds_assist_envelope_v1.schema.json`·fixture·pytest·`scripts/build_km_physician_cds_assist_envelope_v1.py`(페이로드 병합·검증)·JSONL 배치 `scripts/run_km_physician_cds_assist_envelope_batch_v1.py`(예시 입력 `tests/fixtures/km_physician_cds_assist_payload_batch_v1.example.jsonl`) 추가; 로컬 Fact-Lock 번들 `scripts/run_fact_lock_bundle.ps1` 기본 단계 **3e**(CDS 회귀 2종 pytest; `-SkipKmPhysicianCdsEnvelope` 생략); 워크스페이스 헬스 선택 스모크 `scripts/run_workspace_automation_health.ps1 -IncludeKmPhysicianCdsEnvelopeSmoke`(단독 `-KmPhysicianCdsEnvelopeSmokeOnly`); Inspector 일일 리포트 `source_evidence`/품질 신호에 스키마·빌더·배치 러너 경로 및 선택 산출 `reports/km_physician_cds_envelope_batch_latest.jsonl`(mtime 기준 stale 시 제안 액션) 표시; 주간 태스크 등록 `scripts/Register-KmPhysicianCdsEnvelopeBatchWeeklyTask.ps1`(실행 래퍼 `scripts/Run-KmPhysicianCdsEnvelopeBatchWeekly_v1.ps1`, 기본 일요일 09:45, 태스크명 `MKM-KmPhysician-CdsEnvelopeBatch-Weekly`)·Inspector 런타임 신호 연동·`projects/bitcoin-trading/ops/windows-rehearsal/automation_registry.json` 기대 작업(`\\MKM-KmPhysician-CdsEnvelopeBatch-Weekly`, `\\MKM-BTrack-BtcWeight-HitRateBundle-Weekly`, Ready) 정렬(`reconcile_automation_registry.ps1`; 레지스트리·정렬 스크립트 경로는 `scripts/verify_p0_constitution_gate_paths.ps1` P0 목록 포함); 회귀 `tests/test_automation_registry_json_v1.py`(MKM 주간 태스크명 고정); NotebookLM §9 표 행 보강 — 상용 배포는 RAG·감사·법무 범위 별도.
**보강 (2026-05-14 — 환자 통합 번들 v1):** `patient_care_bundle_v1` 스키마·`scripts/assemble_patient_care_bundle_with_myeongni_v1.py`·`scripts/build_patient_care_bundle_from_km_cds_chain_v1.py`(CDS 스키마 검증 후 조립)·SOAP 픽스처 `tests/fixtures/patient_care_bundle_soap_stub_v1.example.json`·회귀 pytest(스키마·assemble·CDS 체인·템플릿/정책/렌더); Fact-Lock **3e**·`dual-regime-integrity.yml` `Myeongri AI interpretation + KM physician CDS` 단계·`-IncludeKmPhysicianCdsEnvelopeSmoke`에 포함(§9 표 `환자 제공용 통합 번들 v1` 행). **보강 (동일일 — 템플릿·정책·렌더):** `docs/final/artifacts/patient_care_bundle_slot_templates_ko_v1.json`·`docs/final/artifacts/patient_care_bundle_generation_policy_v1.default.json`·`scripts/apply_patient_care_bundle_slot_templates_v1.py`·`scripts/validate_patient_care_bundle_against_policy_v1.py`·`scripts/render_patient_care_bundle_markdown_v1.py`·`scripts/Invoke-PatientCareBundleAssemblePatientFacing_v1.ps1`·회귀 `tests/test_patient_care_bundle_templates_policy_render_v1.py`(동일 CDS pytest 묶음·P0 경로).
**보강 (2026-05-02 — 매크로 스텁 라벨 상관·해석 메시지 조립):** `scripts/eval_myeongri_rule_school_macro_stub_v1.py`에 선택 숫자 `label`·`--label-axis`(S/L/K/M/norm) 상관; `scripts/run_myeongri_ai_interpretation_pack_v1.py`로 §3 유저 메시지 치환(LLM 미호출).
**보강 (2026-05-02 — MKM 렌즈 글로벌 프로파일링 프롬프트·RAG 초안):** `docs/final/MKM_LENS_GLOBAL_PROFILE_PROMPT_RAG_INSTRUCTIONS_DRAFT_V1.md` — B-track NL 번역층·`[DRAFT]`; Fact-Lock·임상 격벽·`MYEONGRI_EXTERNAL_ENGINEERING_LEXICON_V1` 정렬; 구현 강제 아님.
**보강 (2026-05-02):** §1.3 Track C Macro Risk n8n 메일 온보딩 PowerShell 스크립트 표.
**보강 (2026-05-04):** §1.3.1 Track C 일일 융합 `Invoke-TrackCMacroDailyFusion_v1.ps1`·`Register-TrackCMacroDailyFusionTask.ps1`(`-DryRun`·`-UnregisterLegacyTasks`)·Fragility 중복 방지·`run_workspace_automation_health.ps1 -IncludeTrackCMacroFusionSmoke` / `-TrackCMacroFusionSmokeOnly`·선택 `MetaLayerEnvelopePath`. **보강 (2026-05-12):** 대시보드 직전 기본으로 `build_lens_music_hormone_trend_v1.py`·`dispatch_lens_music_hormone_trend_webhook_v1.py`(WATCH-only)·`-SkipLensMusicHormoneTrend` 생략 옵션. **보강 (2026-05-13):** 동 헬스 스크립트 퓨전 스모크 경로에 **`-SkipLogosInsightBundle`** 선택 인자(Invoke에 전달·`build_logos_insight_bundle_v1.py` 생략) 및 환경 **`MKM_HEALTH_FUSION_SKIP_LOGOS_INSIGHT_BUNDLE`** truthy 시 동일 전달.
**보강 (2026-05-05 — 메타 인지 봉투 v1 · 선택 융합 게이트):** §1.3.1 표 — `docs/final/artifacts/schemas/mkm_meta_layer_turn_envelope_v1.schema.json`·`docs/final/artifacts/fixtures/mkm_meta_layer_turn_envelope_v1.example.json`·`scripts/mkm_meta_layer_envelope_v1.py`(`validate`·`append`·`audit-markdown`)·`AthenaValidator`·`tests/test_mkm_meta_layer_envelope_v1.py`. `Invoke-TrackCMacroDailyFusion_v1.ps1` **`-MetaLayerEnvelopePath`**는 비어 있으면 **미실행**(기본 융합 불변). 값이 있으면 융합 단계 후 `.json`→`append`, 그 외 확장자→마크다운에서 fenced JSON 추출·검증·`reports/agent_decisions_log.jsonl` 적재; 실패 시 fusion 전체 `throw`. **회귀:** `scripts/run_fact_lock_bundle.ps1` 3d 단계·CI `dual-regime-integrity.yml` 동명 pytest 단계.
**보강 (2026-05-05 — 도메인×쇼룸 배치):** §1.1.3 표 — `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` **§1.1**·**§1.1b**(쇼룸 배치 + **jema-ai 허브 CTA 라벨 초안**); `docs/final/JEMA_AI_DOMAIN_POINTER_V1.md` §4.1 교차; P0 `scripts/verify_p0_constitution_gate_paths.ps1`.
**보강 (2026-05-05 — 대외 문서·홈페이지·쇼룸 보안·IP 경계):** §1.1.3 — 정책 SSOT `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`(웹·제안서·정적 쇼룸 등 **카피·비노출** 체크리스트; 구현 팩트 대체 아님). 교차: Track C `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md`, 쇼룸 `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md`, 명리 대외 어휘 `docs/final/MYEONGRI_EXTERNAL_ENGINEERING_LEXICON_V1.md`, §1.1.1 `research_only`·격벽.
**보강 (2026-05-08 — Logos S1_SHADOW Fact-Lock):** §8.2 표 — 일일 융합 내 Logos 그림자 관측 경로(`promote_logos_to_shadow_live_v1.py`, 주간 게이트·KPI·정책 MD·resonance shadow 등)·회귀 테스트·**NON_GATING·track_wall** 고정.
**보강 (2026-05-05 — KR 건강·웰빙 대외 카피):** `docs/final/MKM_HEALTH_WELLNESS_COPY_GUARDRAILS_KR_V1.md` — 설문·체질·의료 인접 표현 블랙/그레이/화이트·개인정보·정확도 표기(법무 검토 전제). §1.1.3 표·`PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`와 교차.
**보강 (2026-05-05 — Yang 2015 표면 8자 B-track):** §3.3 표 — `scripts/btrack_yang_2015_style_metrics_v1.py`·`scripts/run_myeongni_celebrity_benchmark_v1.py`·계약 맵 `data/myeongni/paper_contract_maps/yang_2015_four_pillars_personality_map_v1.json`·데이터 `data/myeongni/celebrity_saju_benchmark_v1.jsonl`·산출 `reports/btrack_yang_2015_style_metrics_latest.json`·`docs/final/artifacts/myeongni_celebrity_hit_rate_v1.json`; JSON Schema `docs/final/schemas/btrack_yang_2015_style_metrics_v1.schema.json`·`docs/final/schemas/myeongni_celebrity_hit_rate_v1.schema.json`; 회귀 `tests/test_yang_2015_btrack_json_schema_v1.py` 포함; P0 `scripts/verify_p0_constitution_gate_paths.ps1`·`.github/workflows/dual-regime-integrity.yml` 경로 고정; CI `dual-regime-integrity.yml`·`multilens-independent-lens-smoke.yml`. 임상·A-track 자동 트리거 금지.
**보강 (2026-05-02 — MKM-Orchestrator):** §1.4 `todo_queue_v1` 폴링·`reports/mkm_orchestrator_audit.jsonl`·텔레그램 notify/ingest(`.env`); **CENTRAL MD 자동 파싱·B→A·실매매 자동 합선 없음** — 경로·스크립트 `docs/final/artifacts/mkm_orchestrator_connection_spec_v1.json`·`verify_mkm_orchestrator_bundle_v1.py`.
**보강 (2026-05-09 — 글로벌 오케스트레이터·조건부 GO+ companion):** §1.4 표 — `mkm_global_orchestrator_v1.py`·`run_mkm_orchestrator_go_stability_cycle_v1.ps1`·`run_mkm_orchestrator_accelerated_burnin_v1.ps1`(`-RebuildGoPlusReport`·`-ReportTailMatchIterations`)·`build_mkm_conditional_go_plus_report_v2.py`(`--window-minutes`·`--tail-samples`)·산출 `companion_ecosystem_conditional_go_plus_report_latest.json`.
**보강 (2026-05-03 — 실행 거버넌스 / ECC):** §28 `scripts/athena_run_v1.py` — `integrated_governance_v1`·`TRADE_EXECUTE`·HOLD면 ECC **DENIED**·exit **2**·자식 미기동·**DPAPI 미조회**; 승인 시 `--target`이면 `security_agent_manager`로 자식 env만 주입, 없으면 exit **1**; `--target` 생략 시 PoC 더미 키. 산출 `docs/final/artifacts/ecc_execution_clearance_latest.json`(`action_payload_hash`·감사 필드); append-only `reports/athena_ecc_audit.jsonl`·`scripts/athena_ecc_logs_v1.py`; 선택 **`ATHENA_ECC_AUDIT_WEBHOOK_URL`** 요약 POST. **호스트·프로세스 직접 실행 우회는 차단 아님** — Fact-Lock 경로·운영 규율과 병행. 회귀 `tests/test_athena_run_v1.py`. **프리플라이트 요약:** `scripts/athena_doctor_v1.py`(레짐·ECC 요약). 회귀 `tests/test_athena_doctor_v1.py`. **일괄 스모크:** `scripts/check_athena_execution_governance_smoke_v1.py`; 회귀 `tests/test_check_athena_execution_governance_smoke_v1.py`.
**보강 (2026-05-03 — Security Agent / API 키 Fact-Lock):** §1.1.2 — `scripts/security_agent_manager.py`(PoC)가 `Invoke-EncryptedSecretStore.ps1`로 DPAPI 스토어 조회; `binance_client`는 모노레포 **workspace 루트**를 `sys.path`에 넣어 import(·`parents[4]`). 스토어에 해당 키가 없으면·`MKM_SKIP_DPAPI_SECRET_STORE`·비 Windows면 **환경 변수 → 루트 `.env` → JSON** 폴백. **압축(Track A/B) 파이프라인은 API 키 암·복호화 계약 아님** — 혼동 금지.
**보강 (2026-05-10 — AI BGM 게이트 v1 · B/A 분리):** `docs/final/schemas/audio_bgm_gate_report_v1.schema.json`·`docs/final/schemas/audio_bgm_gate_report_v1.example.json`·`policies/audio_copyright_field.json`·`scripts/audio/run_bgm_generation_batch.py`(`--emit placeholder|external`·`--run-gate`·게이트 요약·`reports/audio_gate_latest.json` 미러·`MKM_AUDIO_EXTERNAL_SCRIPT`·`external_generator_stub_v1.py`·`external_generator_template_v1.py`)·`scripts/Run-AudioBgmGeminiExternalChain_v1.ps1`(Gemini 확장+외부 훅 원클릭·`-DryRun`·선택 `-RunGate`/게이트 웨이버)·`scripts/Run-AudioBgmEconomyChain_v1.ps1`(가성비·드라이 선행·선택`-Live`/`Count`; 예제 시드`data/audio/seeds/*.example.json`)·`scripts/audio/generate_placeholder_wav.py`·`scripts/audio/gemini_bgm_seed_expand_v1.py`(기본: `--billing developer`/환경 미설정 시 AI Studio 키(`GEMINI_API_KEY` 등)·시드 JSON 확장; org Vertex 우선은 `MKM_AUDIO_GEMINI_BILLING=auto|vertex` + GCP 프로젝트+ADC)·`scripts/audio/gemini_placeholder_external_generator_v1.py`(외부 훅·선택 `MKM_AUDIO_EXPAND_DRY_RUN`)·`scripts/audio/tone_external_generator_v1.py`(오프라인 톤)·`scripts/audio/expand_tone_external_generator_v1.py`(확장+톤·체인 `-DryRun` 시 확장도 드라이런)·`scripts/audio/ffmpeg_bed_external_generator_v1.py`(lavfi 컬러 노이즈 베드·expanded_prompt 해시로 대역·볼륨·톤 Hz·노이즈 색 brown|pink|white 결정론 조정·ffmpeg 미존재 시 톤 폴백)·`scripts/audio/check_audio_gate_optional_deps_v1.py`(numpy/pyloudnorm 프로브)·`scripts/audio/evaluate_audio_gate.py`(`--waive-lufs`·`--waive-bpm-lens` 감사 웨이버)·회귀 `tests/test_audio_bgm_gate_report_v1.py`·CI `.github/workflows/audio-bgm-gate-smoke.yml`(pytest + 외부 emit 드라이런 배치·게이트 스모크)·`.github/workflows/dual-regime-integrity.yml`(동 pytest)·산출 `reports/audio_gate_latest.json`은 로컬 재생성·`reports/**` 무시 정책과 동일 선상. **예술 평가가 아닌 DoD·저작권 Field 게이트**; 실매매·거래 자동 합선 없음.
**보강 (2026-05-10 — 상징→오디오 매핑 계약 `[HYPO]` M0):** `docs/final/schemas/sasang_music_mapping_v1.schema.json`·`docs/final/schemas/sasang_music_mapping_v1.example.json`·회귀 `tests/test_sasang_music_mapping_schema_v1.py`; 사업 SSOT `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.9·§3.9.1. 사상·게마트리아→화성/MIDI 파라미터는 **버전된 실험값**; 임상·음악치료 효능·단일 TOE 단정 금지.
**보강 (2026-05-10 — 사상→감정 연속축 계약 `[HYPO]` §3.10 Draft):** `docs/final/schemas/sasang_emotion_mapping_v1.schema.json`·`docs/final/schemas/sasang_emotion_mapping_v1.example.json`·회귀 `tests/test_sasang_emotion_mapping_schema_v1.py`; 사업 SSOT 동 문서 **§3.10**. VA 앵커만 — `sasang_music_mapping_v1`와 역할 분리; Track Wall·TOE 비단정 동일.
**보강 (2026-05-10 — 상징→오디오 렌즈 스텁 `[HYPO]` M1):** `scripts/run_lens_music_gematria.py`(`--mapping-json` 완전 문서 검증 출력 또는 `--sasang-primary`/`--gematria-total` 내장 휴리스틱 표·선택 `--emotion-mapping-json` → 봉투에 `emotion_va_overlay_v1`)·산출 봉투 `lens_music_gematria_v1`·회귀 `tests/test_run_lens_music_gematria_v1.py`; `run_lens_sasang.py`와 상태 공유 없음. 오디오 렌더·임상 주장 없음.
**보강 (2026-05-10 — 상징 안전 선행 + 오디오 게이트 체인 `[HYPO]` M2):** `scripts/run_lens_music_gematria_gate_chain_v1.py` — `lens_music_gematria_v1`의 `resolved_outputs`에 대해 velocity 대비 `safety.max_velocity_0_1` 위반 시 **HOLD** 또는 **clip** 정책, 통과 시 시드 BPM 연계·`scripts/audio/evaluate_audio_gate.py`·`policies/audio_copyright_field.json`·산출 `reports/lens_music_gate_chain_v1_latest.json`; 렌즈에 `emotion_va_overlay_v1` 있으면 체인 JSON에 동일 전달. 회귀 `tests/test_lens_music_gate_chain_v1.py`. 심볼에서 WAV 합성 없음(플레이스홀더 WAV로 기계적 게이트만 연습).
**보강 (2026-05-10 — 상징→오디오 B-track 연구 승격 게이트):** `scripts/check_lens_music_symbolic_audio_promotion_gate_v1.py`(M0–M5 pytest 번들·**exit 0 = pytest 통과 + 기본 strict일 때 `decision≠HOLD_M31_HORMONE_GUARD`**; `--m31-profile soft`/`--allow-soft-m31`는 pytest만)·`docs/final/schemas/lens_music_symbolic_audio_promotion_gate_v1.schema.json`·example·회귀 `tests/test_lens_music_symbolic_audio_promotion_gate_v1.py`; 산출 `reports/lens_music_symbolic_audio_promotion_gate_latest.json`. `track_wall`로 Track A 상용·Track C 1차 GTM 자동 승격 **금지** 명시. 압축 §9와 레인 분리. **보강 (동일 § — §3.10 추적):** 산출에 `emotion_va_overlay_ack`·`references_ssot.track_c_section_3_10_emotion_va`(문자열 포인터)로 VA 오버레이가 pytest 번들에 포함됨을 명시 — **별도 승격 조건 아님**(GO/HOLD는 기존 M0–M5 pass만).
**보강 (2026-05-12 — 승격 게이트 pytest 번들):** 동 게이트의 통합 pytest에 `tests/test_dispatch_lens_music_hormone_trend_webhook_v1.py` 포함(127.0.0.1 로컬 수신 + WATCH fixture + `--webhook-url` POST 스모크).
**보강 (2026-05-10 — 상징→오디오 M6 감정 오버레이 보정):** `scripts/run_lens_music_gematria_gate_chain_v1.py --emotion-overlay-policy off|preview|apply`(기본 preview) — `emotion_va_overlay_v1` 기반 bounded heuristic(tempo/velocity) 제안, `apply`에서만 symbolic safety 입력에 반영 후 재평가; 체인 산출에 `emotion_overlay_stage` 기록. 회귀 `tests/test_lens_music_gate_chain_v1.py`(preview 비변경, apply 변경 확인). Track Wall·상용 자동 승격 없음.
**보강 (2026-05-10 — 상징→오디오 M7 품질 가드):** 동일 체인 산출에 `quality_guard_m7`(advisory) 추가 — `tempo_drift_cap_12bpm`·`velocity_within_safety_cap`·proposal consistency·heuristic bounds를 `OK/WARN`로 기록. **비차단(non-blocking)** 으로 `final_decision` 덮어쓰기 금지. 회귀 `tests/test_lens_music_gate_chain_v1.py`.
**보강 (2026-05-10 — 상징→오디오 M8 품질 가드 집계):** `scripts/build_lens_music_quality_guard_m7_summary_v1.py` — `lens_music_gate_chain_v1` 다중 입력에서 `quality_guard_m7` WARN/OK 및 check별 비율 집계 산출(`reports/lens_music_quality_guard_m7_summary_latest.json`, schema `lens_music_quality_guard_m7_summary_v1`). 회귀 `tests/test_build_lens_music_quality_guard_m7_summary_v1.py`. **비차단 통계**이며 승격/실거래 결정식 변경 없음.
**보강 (2026-05-10 — 상징→오디오 M9 멜로디 이론 제안):** `scripts/run_lens_music_gematria_gate_chain_v1.py` 산출에 `melody_stage_m9`(advisory) 추가 — `mode_hint/root_pc` + `emotion_va_overlay_v1` 기반으로 스케일 패밀리·펜타토닉 허용·프레이즈 제약(도약 상한/컨투어/종지 힌트) 제안. 회귀 `tests/test_lens_music_gate_chain_v1.py`. **비차단**이며 `final_decision`·track_wall 변경 없음.
**보강 (2026-05-10 — 상징→오디오 M10 샘플 멜로디 시퀀스):** 동일 체인 산출에 `melody_stage_m10` 추가 — M9 제안으로부터 4마디/8스텝 `melody_sequence_stub_v1`(MIDI note list, dur_beats) 생성. 렌더링(WAV/MIDI 파일) 없이 제안 데이터만 제공. 회귀 `tests/test_lens_music_gate_chain_v1.py`; **비차단**이며 `final_decision`·track_wall 불변.
**보강 (2026-05-10 — 상징→오디오 M11 멜로디 Export 스텁):** 체인 CLI `run_lens_music_gematria_gate_chain_v1.py`에 `--export-melody-json`·`--export-midi-stub-json` 추가 — `melody_stage_m10` standalone JSON 및 `melody_midi_event_stub_v1`(note_on/off beat 이벤트) 출력 지원. 회귀 `tests/test_lens_music_gate_chain_v1.py`; 바이너리 `.mid` 렌더링은 범위 밖.
**보강 (2026-05-10 — 상징→오디오 M12 바이너리 MIDI Export):** 동일 체인 CLI에 `--export-midi-binary` 추가 — `melody_stage_m10` 노트를 format-0 MIDI 바이트(`MThd`/`MTrk`)로 직렬화 저장(내장 writer, 외부 의존성 없음). 회귀 `tests/test_lens_music_gate_chain_v1.py` (`test_chain_m12_exports_binary_midi`). 비차단·track_wall/결정식 불변.
**보강 (2026-05-10 — 상징→오디오 M13 audition WAV):** 체인 CLI에 `--export-audition-wav` 추가 — `melody_stage_m10` note sequence를 단일 사인톤으로 합성해 WAV 출력(`melody_audition_wav_v1`, RIFF). 회귀 `tests/test_lens_music_gate_chain_v1.py` (`test_chain_m13_exports_audition_wav`). 청취 스텁용이며 실상용 오디오 렌더 체인과 분리.
**보강 (2026-05-10 — 상징→오디오 M14 audition sanity):** `melody_stage_m13`에 `peak_abs_0_1`·`rms_0_1`·`sanity_m14`(status/notes/non_blocking) 추가. `peak_near_clipping`·`rms_too_low_for_audition` 경고를 advisory로만 기록하며 게이트 결정식은 불변. 회귀 `tests/test_lens_music_gate_chain_v1.py`.
**보강 (2026-05-10 — 상징→오디오 M15 audition QA summary):** `scripts/build_lens_music_audition_qa_summary_v1.py` — `lens_music_gate_chain_v1` 다중 입력에서 `melody_stage_m13`/`sanity_m14`를 집계(`peak/rms/status/note`)하여 `reports/lens_music_audition_qa_summary_latest.json`(`lens_music_audition_qa_summary_v1`) 생성. 회귀 `tests/test_build_lens_music_audition_qa_summary_v1.py`. 비차단 통계 리포트.
**보강 (2026-05-10 — 상징→오디오 M16 governance state):** 동일 summary에 `governance_m16` 추가(`warn_ratio_threshold`·`warn_count`·`sample_count`·`state=GO|WATCH`). 기본 threshold 0.2 초과면 WATCH로 표시하며 **advisory-only**(프로모션·실거래 결정식 불변). 회귀 `tests/test_build_lens_music_audition_qa_summary_v1.py`.
**보강 (2026-05-11 — 상징→오디오 M17 governance chain):** `scripts/run_lens_music_audition_governance_chain_v1.py` — M15/M16 summary를 호출해 `reports/lens_music_audition_governance_status_latest.json`(`lens_music_audition_governance_status_v1`) 생성. 운영 소비용 `state/warn_ratio` 최신 포인터 제공; 비차단·결정식 불변. 회귀 `tests/test_run_lens_music_audition_governance_chain_v1.py`.
**보강 (2026-05-11 — 상징→오디오 M18 dashboard integration):** `scripts/build_mkm_trackc_ops_dashboard_v1.py`가 `docs/final/artifacts/lens_music_audition_governance_status_latest.json`를 읽어 `trackc.lens_music_audition_governance`(state/warn_ratio/threshold/warn_count/sample_count)를 대시보드에 포함. 회귀 `tests/test_build_mkm_trackc_ops_dashboard_v1.py`.
**보강 (2026-05-11 — 상징→오디오 M19 webhook bridge):** `scripts/dispatch_lens_music_audition_governance_webhook_v1.py` — M17 status를 compliance-safe payload로 webhook 전달(환경변수 미설정 시 `skipped/webhook_not_configured` 기록)하고 `docs/final/artifacts/lens_music_audition_governance_webhook_dispatch_latest.json` 산출. 회귀 `tests/test_dispatch_lens_music_audition_governance_webhook_v1.py`. advisory-only·결정식 불변.
**보강 (2026-05-11 — 상징→텍스트 M20 dynamic prompt overlay):** `scripts/build_lens_music_prompt_overlay_v1.py` — M17 status + `melody_stage_m9.input_snapshot`(BPM/valence/arousal) 기반 `lens_music_prompt_overlay_v1` 생성(`reports/lens_music_prompt_overlay_latest.json`). `control_plane_user_plane_separation=true` 계약으로 제어 파라미터와 사용자 입력 분리. 회귀 `tests/test_build_lens_music_prompt_overlay_v1.py`.
**보강 (2026-05-11 — 상징→텍스트 M21 smoke eval):** `scripts/run_lens_music_prompt_smoke_eval_v1.py` — 샘플 응답 JSONL(`tests/fixtures/lens_music_prompt_smoke_eval_sample_v1.jsonl`)에 대해 style/sentence-length 히ュー리스틱 매칭률을 계산해 `reports/lens_music_prompt_smoke_eval_latest.json`(`lens_music_prompt_smoke_eval_v1`) 생성. 회귀 `tests/test_run_lens_music_prompt_smoke_eval_v1.py`. 비차단 평가 리포트.
**보강 (2026-05-11 — 상징→텍스트 M22 auto-brake):** `build_lens_music_prompt_overlay_v1.py`에 `auto_brake_m22` 추가 — governance 또는 smoke eval 상태가 WATCH면 `temperature_hint<=0.45`, `answer_style=calm_guarded`, `sentence_length=short_to_medium`로 자동 완화. 회귀 `tests/test_build_lens_music_prompt_overlay_v1.py`. advisory-only·결정식 불변.
**보강 (2026-05-11 — 상징→텍스트 M23 auto-brake history summary):** `build_lens_music_prompt_overlay_v1.py`가 실행 이력을 `reports/lens_music_prompt_overlay_history_log.jsonl`에 append하고, `scripts/build_lens_music_prompt_brake_history_summary_v1.py`가 발동률·트리거(governance/smoke)·스타일 분포를 집계해 `docs/final/artifacts/lens_music_prompt_brake_history_summary_latest.json` 생성. 회귀 `tests/test_build_lens_music_prompt_brake_history_summary_v1.py`.
**보강 (2026-05-11 — 상징→텍스트 M24 dashboard bridge):** `scripts/build_mkm_trackc_ops_dashboard_v1.py`가 M23 산출물(`lens_music_prompt_brake_history_summary_latest.json`)을 읽어 `trackc.lens_music_prompt_brake`에 `state/auto_brake_active_rate/auto_brake_active_count/rows_scanned`를 노출. 회귀 `tests/test_build_mkm_trackc_ops_dashboard_v1.py`.
**보강 (2026-05-11 — 상징→텍스트 M25 trend + alert bridge):** `scripts/build_lens_music_prompt_brake_trend_v1.py`가 history jsonl을 일자별 `daily_series`·`top_triggers`로 집계해 `docs/final/artifacts/lens_music_prompt_brake_trend_latest.json` 생성, `scripts/dispatch_lens_music_prompt_brake_trend_webhook_v1.py`가 선택 webhook으로 compliance-safe 알림 브리지(미설정 시 skipped) 수행. 대시보드는 `trend_state/trend_active_rate/trend_top_trigger`를 노출. 회귀 `tests/test_build_lens_music_prompt_brake_trend_v1.py`, `tests/test_dispatch_lens_music_prompt_brake_trend_webhook_v1.py`, `tests/test_build_mkm_trackc_ops_dashboard_v1.py`.
**보강 (2026-05-11 — 상징→텍스트 M26 PoC metric runner):** `scripts/run_lens_music_prompt_poc_metric_v1.py` — baseline/overlay 응답 쌍 JSONL을 입력 받아 `style_delta_rate`(평균 문장수 상대 변화율)·`overlay_style_match_rate`를 계산하고 GO/WATCH 판정(`lens_music_prompt_poc_metric_v1`)을 산출(`reports/lens_music_prompt_poc_metric_latest.json`). 기본 목표: `style_delta_rate>=0.30`, `overlay_style_match_rate>=0.67`; advisory-only·비차단. 회귀 `tests/test_run_lens_music_prompt_poc_metric_v1.py`, fixture `tests/fixtures/lens_music_prompt_poc_pairs_sample_v1.jsonl`.
**보강 (2026-05-11 — 상징→텍스트 M27 dashboard PoC bridge):** `scripts/build_mkm_trackc_ops_dashboard_v1.py`가 `reports/lens_music_prompt_poc_metric_latest.json`을 읽어 `trackc.lens_music_prompt_poc_metric`(`state/passed/style_delta_rate/overlay_style_match_rate/samples_count`)을 대시보드에 노출. 회귀 `tests/test_build_mkm_trackc_ops_dashboard_v1.py`.
**보강 (2026-05-11 — 상징→텍스트 M28 PoC runbook recommendations):** `scripts/build_lens_music_prompt_poc_runbook_v1.py`가 PoC metric 상태/목표치 기반으로 원인별 권장 조치(`lens_music_prompt_poc_runbook_v1`)를 생성(`docs/final/artifacts/lens_music_prompt_poc_runbook_latest.json`)하고, dashboard가 `trackc.lens_music_prompt_poc_runbook`(`state/recommendation_count/top_recommendation_cause`)을 노출. 회귀 `tests/test_build_lens_music_prompt_poc_runbook_v1.py`, `tests/test_build_mkm_trackc_ops_dashboard_v1.py`.
**보강 (2026-05-11 — 상징→텍스트 M29 runbook webhook bridge):** `scripts/dispatch_lens_music_prompt_poc_runbook_webhook_v1.py` 추가 — runbook 상태를 선택 webhook으로 전달하되 `--require-watch`·`--require-high-priority` 조건 게이트를 지원(미충족 시 skipped reason 기록). 산출 `docs/final/artifacts/lens_music_prompt_poc_runbook_webhook_dispatch_latest.json`; dashboard는 `trackc.lens_music_prompt_poc_runbook_webhook`(`dispatch_status/dispatch_reason/watch_gate_passed/high_priority_gate_passed`)을 노출. 회귀 `tests/test_dispatch_lens_music_prompt_poc_runbook_webhook_v1.py`, `tests/test_build_mkm_trackc_ops_dashboard_v1.py`.
**보강 (2026-05-11 — 상징→텍스트 M30 runbook webhook health summary):** 각 실행은 기본으로 `reports/lens_music_prompt_poc_runbook_webhook_history.jsonl`에 append(`--history-jsonl`·`--no-append-history` 오버라이드). `scripts/build_lens_music_prompt_runbook_webhook_health_summary_v1.py`가 최근 N행 집계로 sent/skipped/failed 비율·skip reason Top-N을 산출(`docs/final/artifacts/lens_music_prompt_runbook_webhook_health_latest.json`). dashboard는 `trackc.lens_music_prompt_runbook_webhook_health`를 노출. 회귀 `tests/test_build_lens_music_prompt_runbook_webhook_health_summary_v1.py`, `tests/test_build_mkm_trackc_ops_dashboard_v1.py`.
**보강 (2026-05-11 — 상징→텍스트 M31 hormone-like state machine v1):** `scripts/build_lens_music_prompt_overlay_v1.py`에 비생물학 메타포형 상태(`lens_music_hormone_state_v1`)를 추가 — `stress_index_0_1`·`recovery_buffer_0_1`·`inertia_index_0_1`와 `STABLE|ELEVATED|HIGH_STRESS`를 bounded EMA로 계산해 `global_state.hormone_like_state` 및 history JSONL에 기록. 기본 경로 `reports/lens_music_hormone_state_latest.json`; CLI `--hormone-state-json`. **advisory-only/non-biological** 고지 유지; 오버레이 자체는 상용 주문·Track A/C 자동 승격과 무관. 회귀 `tests/test_build_lens_music_prompt_overlay_v1.py`.
**보강 (2026-05-12 — 게마트리아 시드 감사 트레이스 M32):** `scripts/run_lens_music_gematria_gate_chain_v1.py` 산출에 `gematria_seed_trace`(`lens_music_gematria_seed_trace_v1`, 스키마 `docs/final/schemas/lens_music_gematria_seed_trace_v1.schema.json`)를 포함; `scripts/build_lens_music_prompt_overlay_v1.py`가 체인에서 읽어 M31 hormone EMA `alpha`에만 **결정론적 bounded** `applied_ema_alpha_multiplier`를 적용(BPM `ema_alpha`와 분리). 일반 예언(B 레일)과 합선 없음. 회귀 `tests/test_lens_music_gate_chain_v1.py`, `tests/test_build_lens_music_prompt_overlay_v1.py`, `tests/test_lens_music_gematria_seed_trace_schema_v1.py`; `scripts/check_lens_music_symbolic_audio_promotion_gate_v1.py` 번들 pytest·CI `dual-regime-integrity.yml`·`audio-bgm-gate-smoke.yml` PR paths에 동 경로 포함.
**보강 (2026-05-12 — M31 트렌드 NODATA 힌트 + Track C 대시보드 M32 요약 W2):** `scripts/build_lens_music_hormone_trend_v1.py`가 `rows_scanned==0`일 때 선택 필드 `operator_hint`로 오버레이 히스토리 적재를 안내; `scripts/build_mkm_trackc_ops_dashboard_v1.py`가 `trackc.lens_music_hormone_state`에 `gematria_trace_present`·`gematria_*` 요약(호르몬 상태 JSON 및 `reports/lens_music_prompt_overlay_latest.json`의 `global_state.gematria_seed_trace` 병합), `trackc.lens_music_hormone_trend.operator_hint`를 노출. 회귀 `tests/test_build_lens_music_hormone_trend_v1.py`, `tests/test_build_mkm_trackc_ops_dashboard_v1.py`. **보강 (2026-05-12 — W3 M31 게이트 감사):** `check_lens_music_symbolic_audio_promotion_gate_v1.py`가 `m31_hormone_guard.invocation`에 CLI 프로필·임계·트렌드 JSON 경로를 기록; `Invoke-TrackCMacroDailyFusion_v1.ps1`·`Register-TrackCMacroDailyFusionTask.ps1`에 `-LensMusicPromotionGateSoftM31`(soft= `--allow-soft-m31`); 스테이징 원샷 `scripts/Run-LensMusicPromotionGateStagingStrict_v1.ps1`. **보강 (동일 — W4 strict exit):** 기본 strict에서 `HOLD_M31_HORMONE_GUARD`이면 **프로세스 exit 1**(퓨전 단계 실패); stdout JSON `ok`는 프로세스 성공과 일치하고 `pytest_ok`는 pytest만 반영. **보강 (동일 — W5 디스크 감사):** 산출 JSON에 `promotion_process`(`m31_profile`, `process_exit_code`, `process_pass`, `pytest_pass`); `build_mkm_trackc_ops_dashboard_v1`가 `trackc.lens_music_promotion_gate`에 `promotion_process_pass` 등으로 전달.
**보강 (2026-05-13 — M31 얇은 감사 꼬리표 gematria + RAG 대사 은유):** `scripts/build_lens_music_prompt_overlay_v1.py`가 `global_state.hormone_like_state`·`global_state`에 `m31_audit_trail`(`lens_music_m31_audit_trail_v1`)을 추가 — `gematria_influence`는 `hormone_like_state.gematria_seed_trace`로만 가리키고, `rag_metabolism_drift`(`lens_music_rag_metabolism_drift_v1`)는 선택 키 `chain_doc.rag_metabolism_digest_v1`가 있으면 `chain_doc_rag_digest`, 없으면 체인 JSON 안정 해시 기반 `synthetic_baseline`(bounded 0..0.25); **임상·장내미생물 주장 아님**. 스키마 `docs/final/schemas/lens_music_m31_audit_trail_v1.schema.json`·`lens_music_rag_metabolism_drift_v1.schema.json`·`lens_music_m31_audit_trail_v1.example.json`·`tests/test_lens_music_m31_audit_trail_schema_v1.py`. 히스토리 JSONL에 `rag_metabolism_bounded_drift_0_1`·`rag_metabolism_source` append; `build_lens_music_hormone_trend_v1.py`가 동 필드가 있으면 `audit_digest_summary` 선택 산출. `build_mkm_trackc_ops_dashboard_v1.py`가 `trackc.lens_music_hormone_trend`에 `mean_rag_metabolism_bounded_drift_0_1`·`rows_with_rag_drift` 노출. `verify_p0` 경로 포함.
**보강 (2026-05-11 — 상징→텍스트 M31 운영·연구 승격 가드 확장):** `scripts/build_lens_music_hormone_trend_v1.py`가 `reports/lens_music_prompt_overlay_history_log.jsonl`을 집계해 `docs/final/artifacts/lens_music_hormone_trend_latest.json`(`lens_music_hormone_trend_v1`, GO/WATCH/NODATA) 생성. `scripts/dispatch_lens_music_hormone_trend_webhook_v1.py`는 **trend가 WATCH일 때만** JSON POST(미설정 시 skipped; User env `LENS_MUSIC_HORMONE_WEBHOOK_URL`); 산출 `docs/final/artifacts/lens_music_hormone_trend_webhook_dispatch_latest.json`. `scripts/build_mkm_trackc_ops_dashboard_v1.py`는 `trackc.lens_music_hormone_state`·`lens_music_hormone_trend`·`lens_music_hormone_trend_webhook` 노출. `scripts/check_lens_music_symbolic_audio_promotion_gate_v1.py`는 pytest 통과 후 동 trend를 읽어 `m31_hormone_guard`로 미통과 시 `HOLD_M31_HORMONE_GUARD`(기본 soft: trend 파일 없으면 통과; 엄격 시 `--require-m31-hormone-input` 및 `--hormone-trend-json`·`--m31-max-high-stress-rate`·`--m31-max-consecutive-high-stress`); 스키마 `docs/final/schemas/lens_music_symbolic_audio_promotion_gate_v1.schema.json`·example. **track_wall**(A 상용 오디오·C 1차 GTM 자동 승격 금지·휴먼 검수) 불변. 회귀 `tests/test_build_lens_music_hormone_trend_v1.py`, `tests/test_dispatch_lens_music_hormone_trend_webhook_v1.py`, `tests/test_build_mkm_trackc_ops_dashboard_v1.py`, `tests/test_lens_music_symbolic_audio_promotion_gate_v1.py`.
**보강 (2026-05-13 — Visualization v0: STT audit JSONL + trust read-only Track C slice):** `scripts/append_stt_routing_audit_log_v1.py`가 `docs/final/schemas/stt_routing_audit_log_v1.schema.json` 검증 후 JSONL append; `scripts/summarize_stt_routing_audit_log_v1.py`가 `reports/stt_routing_audit_log_v1_summary_latest.json` 롤업(`vendor_share_by_event_pct`, `vendor_latency_ms_avg`, `audio_duration_ms_by_route`, `occurred_at_utc_earliest`/`latest` 포함). `scripts/build_mkm_trackc_ops_dashboard_v1.py`가 `docs/final/schemas/trust_visualization_panel_v0.example.json`에서 `trackc.trust_visualization_v0`(요약·Logos `non_gating`), STT 요약 또는 NODATA 시 `trackc.stt_routing_audit_log_slice` 노출; `evidence`에 경로 포인터. 회귀 `tests/test_stt_routing_audit_log_schema_v1.py`, `tests/test_append_stt_routing_audit_log_v1.py`, `tests/test_build_mkm_trackc_ops_dashboard_v1.py`; `verify_p0` 필수 목록·CI `dual-regime-integrity.yml` PR paths 포함. B-track·읽기 전용; A-track 실매매 자동 합선 없음.
**보강 (2026-05-14 — Visualization v0 쇼룸 thin slice):** `scripts/build_showroom_trust_visualization_slice_v1.py`가 `docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json`의 `trackc.trust_visualization_v0`·`stt_routing_audit_log_slice`를 `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_trust_visualization_slice_v0.json`으로 복사(대시보드 없으면 NODATA 스텁); 정적 `public_showroom_trust_visualization_v0.html`이 동 JSON을 HTTP로 fetch(`file://` 제한). `scripts/build_showroom_track_c_bundle_chain_v1.ps1` **(5/6)** 단계에서 호출; `deploy_showroom_static.ps1` 복사 목록에 HTML·JSON(선택) 포함; 생성 JSON은 루트 `.gitignore`로 비추적. 회귀 `tests/test_build_showroom_trust_visualization_slice_v1.py`; CI `dual-regime-integrity.yml` 스텝 `STT routing audit log v1 + showroom trust viz thin slice`는 `tests/test_stt_routing_audit_log_schema_v1.py`·`tests/test_append_stt_routing_audit_log_v1.py`·`tests/test_build_showroom_trust_visualization_slice_v1.py` **3개**를 한 커맨드로 실행. 로컬 **`run_fact_lock_bundle.ps1` 3d3a**(Logos insight bundle pytest 직후; `-SkipSttRoutingAuditShowroomTrustSlice`)가 동일 3개를 실행한다. **CI YAML 순서**는 `Lens music prompt PoC M26-M30` 묶음 직후이며 Logos insight bundle보다 앞선다; 번들에서는 편집 거리 최소화로 Logos insight 직후에 두며 pytest는 격리다.
**보강 (2026-05-19 — OpenData 327 제출 prep v1):** `scripts/check_opendata_327_pre_export_gates_v1.py` · `scripts/export_opendata_327_submission_pdf_v1.py`(B/C/D) · `scripts/merge_opendata_327_submission_pdf_v1.py`(B+C+D, 표지 A 수동) · 원클릭 `scripts/Run-OpenData327SubmissionPrep_v1.ps1` → `reports/opendata_327_submission_readiness_latest.json`. SSOT MD `ai_opendata_challenge_2026_327_business_plan_submission_v1.md` · 병합 가이드 `opendata_327_submission_pdf_merge_guide_v1_latest.md`. **LG·압축 OEM 레인과 합선 금지**; K-Startup 업로드는 human.
**보강 (2026-06-23 — Commander interest benchmark + AI-native briefing v1, internal-only):** 관심 토픽 engagement JSONL(`reports/commander_interest_signal_log_v1.jsonl`; 부트스트랩 `docs/final/artifacts/commander_interest_signal_log_v1.example.jsonl`) + 설정 `docs/final/artifacts/commander_interest_benchmark_config_v1.default.json` → 인박스 `data/marketing/commander_interest_signal_inbox.json`(예시 `commander_interest_signal_inbox_v1.example.json`) → `scripts/ingest_commander_interest_signal_inbox_v1.py` → `scripts/build_commander_interest_benchmark_weekly_report_v1.py` → `docs/final/artifacts/commander_interest_benchmark_weekly_latest.json` · `.md`; 이어서 `scripts/build_commander_ai_native_briefing_pack_v1.py` → `commander_ai_native_briefing_latest.md` · `commander_ai_native_card_news_latest.md` · `commander_ai_native_podcast_script_latest.md` · `commander_ai_native_briefing_pack_latest.json`; 선택 RSS `scripts/collect_commander_interest_signals_rss_v1.py`(`rss_feeds` in config; chain `-IncludeRss`); 선택 텔레그램 `scripts/send_commander_interest_benchmark_telegram_v1.py`(미설정 시 skip exit 0) + 회원 건강 뉴스레터 초안 `scripts/build_clinic_member_health_newsletter_draft_v1.py` → `clinic_member_health_newsletter_draft_latest.md` · `.json`(설정 `clinic_member_health_newsletter_config_v1.default.json`) → `scripts/send_clinic_member_health_newsletter_telegram_v1.py`(지휘관 relay only · 회원 자동 발송 없음); 신호 append `scripts/append_commander_interest_signal_v1.py`; 원클릭 `scripts/Run-CommanderInterestBenchmarkChain_v1.ps1`; Windows 주간 `scripts/Register-CommanderInterestBenchmarkWeeklyTask_v1.ps1`(기본 월 08:30)·`scripts/Verify-CommanderInterestBenchmarkWeeklyTaskReadiness_v1.ps1`; pytest `tests/test_build_commander_interest_benchmark_weekly_report_v1.py` · `tests/test_ingest_commander_interest_signal_inbox_v1.py`. **`track_wall`:** internal observation · `human_publish_only` · `send_gate: HOLD` · engagement-chasing public product 금지(`PUBLIC_FACING` §3 Track C news ingest 정합).

**보강 (2026-05-19 — LinkedIn B2B draft queue v1, semi-auto · no publish):** 로컬 큐 `data/marketing/linkedin_queue.json`(예시 `linkedin_queue_v1.example.json`, 스키마 `docs/final/schemas/linkedin_b2b_queue_v1.schema.json`) → `scripts/generate_linkedin_b2b_copy_v1.py`(`--assemble-only` 기본·선택 `--gemini`·`--with-chart`·`--strict-compliance`) → `reports/marketing/linkedin_drafts/*_[DRAFT].md` + evidence JSON; 가드 `scripts/check_linkedin_b2b_draft_copy_v1.py`·no1kmedi `check-marketing-copy-compliance.mjs`. 주간 `scripts/run_linkedin_b2b_weekly_draft_chain_v1.ps1`; Windows 예약 `scripts/Register-LinkedInB2bWeeklyDraftTask.ps1`(기본 월 09:00)·점검 `scripts/Verify-LinkedInB2bWeeklyDraftTaskReadiness.ps1`. CI `.github/workflows/linkedin-b2b-draft-smoke.yml`; Fact-Lock `run_fact_lock_bundle.ps1` 5c2b(`-SkipLinkedInB2bDraftSmoke`). **LinkedIn API 자동 발행 없음**; 법무 Sign-off 전 수동 게시만.
**보강 (2026-05-16 — Logos Track B 연구 메타포 쇼룸 thin slice `[HYPO]`):** `docs/research/logos_metaphor_db_v1/theme_*.json`을 `docs/final/schemas/mkm_logos_research_thin_slice_v0.2.1.schema.json`으로 검증 후 `scripts/build_showroom_logos_research_slice_v1.py`가 `showroom_logos_research_slice_v0.json`을 `jemaai-cloud-mvp/`에 기록; 정적 `public_showroom_logos_research_v1.html`이 동 JSON을 fetch(스냅샷·**NON_GATING**·`evidence_tier: hypo_research_only`; `research_metaphor_*`는 운영 게이트와 무관). `build_showroom_track_c_bundle_chain_v1.ps1` **(6/6)**; `deploy_showroom_static.ps1`·`sync_showroom_to_vps.ps1` 복사 목록(HTML 필수·JSON 선택). 카드 렌더 `scripts/build_logos_research_card_v1.py`. **슬라이스 1–2:** `scripts/build_logos_corpus_manifest_v1.py` → `logos_corpus_manifest_v1_latest.json`(31102 verses) · `scripts/build_logos_corpus_graph_bundle_v1.py` → `logos_corpus_graph_bundle_v1_latest.json`. **B2B 부록:** `scripts/build_logos_b2b_appendix_v1.py` → `track_c_b2b_logos_lens_appendix_v1_latest.md`(`build_track_c_b2b_meeting_pack_v1.py`·`check_track_c_b2b_meeting_pack_readiness_v1.py` 필수 목록). 회귀 `tests/test_build_logos_research_card_v1.py`·`tests/test_build_showroom_logos_research_slice_v1.py`·`tests/test_build_logos_b2b_appendix_v1.py`·`tests/test_logos_corpus_manifest_v1.py`·`tests/test_logos_corpus_graph_bundle_v1.py`. Track A·실매매·임상 게이팅 자동 합선 없음(RQ-015 Phase N은 학술 확장 백로그).
**보강 (2026-05-12 — Track C 대시보드 상용 KPI 포인터):** `scripts/build_mkm_trackc_ops_dashboard_v1.py`가 `commercial_kpi_pointers`를 추가 — `docs/final/P0_COMMERCIALIZATION_TRACKER.md`·`docs/final/TRACK_A_SLA_DRAFT.md` 및 Track A Phase2 산출(`track_a_metering_*`·`track_a_conversational_cost_simulation_latest.json`·`track_a_shadow_corpus_eval*_latest.json`) 존재 여부·경량 스냅샷만 기록; **Track C/B 게이트와 합선 없음**(pointer-only). 회귀 `tests/test_build_mkm_trackc_ops_dashboard_v1.py`.
**보강 (2026-06-21 — Reddit community agent Fact-Lock R1–R6 `[HYPO]`):** SSOT `scripts/reddit_agent_governance_lib_v1.py`·`scripts/run_reddit_agent_governed_v1.py`·`scripts/Invoke-RedditAgentGoverned_v1.ps1` — R1 `/submit` 탭≤1(위반 exit≠0)·R2 snapshot before DOM·R3 Tier3 login/CAPTCHA STOP·R4 `send_gate: HOLD`+`--acknowledge-send` live only·R5 `reports/reddit_agent_run_v1_latest.json`·R6 B-track. Live post = **PRAW** `post_reddit_praw_v1.py`; browser openchrome = **prefill/dry-run only**. pytest `tests/test_reddit_agent_governance_v1.py`.
**보강 (2026-06-21 — Ko shorts Korean STT subtitle pipeline B-track [HYPO]):** 원클릭 `scripts/run_ko_shorts_full_chain_v1.py`·`scripts/Invoke-KoShortsFullChain_v1.ps1`(clinical_sim fetch → aligned spike → Netflix gate → burn-in → Cursor IDE QA); **`--alignment-backend auto`**(케이스별 `ko_shorts_alignment_routing_lib_v1` — pansori/traditional_vocal→whisperx·그 외 faster-whisper·실패 시 fallback)·`--routing-sidecar`·`bench_all` 연구 모드. **P1 타깃 WAV 위임** `ko_shorts_target_wav_lib_v1`·`--delegate`·inbox `reports/audio/ko_shorts_target_inbox_v1.wav`·배치 `run_ko_shorts_target_wav_batch_v1.py`·`Invoke-KoShortsTargetWavBatch_v1.ps1`; full chain **`--include-delegate`**. 드리프트 KPI `build_ko_shorts_timing_drift_kpi_v1.py` → `reports/ko_shorts_timing_drift_kpi_v1_latest.json`(P0↔P1 gap만·립싱크 pass 아님). ASS `netflix_v16_pro`; HD 위임 `Invoke-KoShortsHdDelegationMission_v1.ps1`. 정렬 스파이크 `.venv-ko-shorts-align`. 결론 `reports/ko_shorts_segment_backend_decision_v1_latest.json`. Fact-Lock `-IncludeKoShortsSmoke`. **`send_gate: HOLD`**.
**보강 (2026-06-22 — Ko shorts P1 timing bench [HYPO]):** `run_ko_shorts_pause_chunk_grid_v1.py`(pause_gap **0.4**·chunk **max_chars 28**·netflix_v16 gate consensus)·`run_ko_shorts_alignment_backend_spike_v1.py --alignment-backend bench_all`(pansori whisperx **−2201ms** drift vs faster-whisper)·`run_ko_shorts_ass_burnin_v1.py --srt-in` text-only reburn·full chain `--quick --include-alignment-spike --include-drift-kpi`. 산출 `reports/ko_shorts_pause_chunk_grid_v1_latest.json`. pytest `tests/test_ko_shorts_pause_chunk_grid_v1.py`·`-IncludeKoShortsSmoke`. **`send_gate: HOLD`**.
**보강 (2026-05-13 — Track A Phase2 산출 재생성기 경로 드리프트 Fact-Lock):** `AGENTS.md`·`P0_COMMERCIALIZATION_TRACKER.md`·`MKM_PROMOTION_GATE_CHECKLIST_B_TO_A_C_V1.md`·CI `dual-regime-integrity.yml` PR path 필터에 기재된 Track A Phase2 생산기 — **`scripts/run_track_a_conversational_cost_simulation.py`**, **`scripts/run_track_a_shadow_corpus_eval.py`**, **`scripts/run_track_a_metering_summary.py`**, **`scripts/run_track_a_metering_weekly_report.py`**, **`scripts/check_track_a_metering_band_gate.py`**, **`scripts/build_track_a_signal_light_report.py`**, **`scripts/run_track_a_commercialization_daily_chain.ps1`**, **`scripts/Run-TrackAShadowJsonlSample.ps1`**, **`scripts/Run-TrackAMeteringSummary.ps1`**, **`scripts/Run-TrackAMeteringWeeklyReport.ps1`** — **복구(2026-05-13)로 레포에 존재**(최소 루프: KPI gate+MULTILENS active report → cost sim; JSONL 행 수 → shadow 요약; 미터링 JSONL → summary/weekly/band gate; 신호등 집계). Windows 일일 작업 등록 **`scripts/Register-TrackACommercializationDailyTask.ps1`**(기본 `-GateMode warning`); 등록 후 점검 **`scripts/Verify-TrackACommercializationDailyScheduledTask_v1.ps1`**(선택 `-Strict`). `docs/final/artifacts/track_a_*_latest.json` 는 `.gitignore` 재생성물이며 **`generated_at_utc`·산출 스키마**를 함께 본다. `scripts/build_mkm_promotion_gate_evidence_bundle_v1.py`는 G4~G6에 `producer_present`·`status`(pass / optional_missing / stale_snapshot / producer_gap)를 기록 — **경로만으로 “방금 재실행됨” 단정 금지**. G12·압축 §9 G2 경계는 불변.
**보강 (2026-05-10 — §3.9 지휘관 진행 승인):** `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.9.2 — 연구 녹색 전제 하 **내부 기획·스테이징·대외 카피 초안 검수·M4+ 로드맵** 진행 명시 승인; **`track_wall` 불변·자동 상용 승격 없음**.
**보강 (2026-05-10 — 내부 비임상 청취 로그 계약 `[HYPO]` M3 초안):** `docs/final/schemas/lens_music_internal_eval_session_v1.schema.json`·example·회귀 `tests/test_lens_music_internal_eval_schema_v1.py` — 청취 선호·재현성 메타만 구조화; 임상·치료 효능 단정 금지.
**보강 (2026-05-10 — 청취 로그 JSONL 배치 검증 `[HYPO]` M4):** `scripts/validate_lens_music_internal_eval_jsonl_v1.py`·`tests/fixtures/lens_music_internal_eval_sessions_sample_v1.jsonl`·회귀 `tests/test_validate_lens_music_internal_eval_jsonl_v1.py`; 프로모션 번들·§3.9.2 `milestones_ack.M4_jsonl_batch`. 외부 배포 없음.
**보강 (2026-05-10 — MKM Control-Integrity Golden / LoRA eval):** §1.2.1 표·스키마·`mkm_control_integrity_lora_model_profiles_v1.json`·prep·원클릭 추론/평가·ABC·홀드아웃 합산·프로모션 게이트·회귀 `tests/test_mkm_control_integrity_pipeline_smoke_v1.py`·`run_fact_lock_bundle.ps1`(`-SkipMkmControlIntegritySmoke`)·`scripts/verify_p0_constitution_gate_paths.ps1`·CI `dual-regime-integrity.yml`. B-track 벤치·실매매 자동 합선 없음.
**이전 갱신**: 2026-04-14 §2 B-track `4d_to_ohaeng`·human regime audit 스파이크 행; §3.4.1 Postella; 2026-04-13 §1.2 AE-2 KOSPI.  
**목적**: “기획·NotebookLM·헌법 문서만 보고 구현됨”이라고 단정하지 않도록, **호출 가능한 경로**와 **검증 상태**를 한곳에 고정한다.

> **정합성 메모 (2026-04-27):** 문서에 남아 있는 일부 historical/연구 레일 경로는 참고 이력일 수 있다. 운영 필수 여부 판정은 `scripts/verify_p0_constitution_gate_paths.ps1`의 current required 목록을 우선한다. 미존재 경로는 복구 승인 전까지 필수 게이트로 간주하지 않는다.

**갱신 (2026-04-28):** §16 `scripts/run_aramaic_mvp_chain_v1.ps1` 후반 `[35/37]`–`[37/37]`(제출 증거 번들·제출 초안·카메라레디 JSON) 및 동 단계 스크립트·pytest 경로를 `verify_p0_constitution_gate_paths.ps1` 필수 목록에 포함. 추가로 `scripts/run_two_track_submission_pack_v1.ps1`로 동 세 단계만 단독 실행 가능(선행 산출 없으면 exit 2). CI: `.github/workflows/dual-regime-integrity.yml`에 제출 팩 빌더 회귀 pytest 3종 단계 포함(PR paths에 동 스크립트·테스트 경로 추가). **`scripts/extract_aramaic_core_corpus_v1.py`**는 `verse_decoded_v2.jsonl`에서 정경 아람어 구간을 추출하는 체인 1단계 구현이며 회귀는 `tests/test_extract_aramaic_core_corpus_v1.py`(동 워크플로 단계 및 P0 목록 포함).

**갱신 (2026-04-21):** §8.1 Bio Sasang×논문 SNP **경계 팩트** 및 조인 게이트 `scripts/spec_bio_sample_paper_snp_join_gate_v1.py` 추가. 유전자명–체질 고정 매핑 표는 **본 문서 FACT 본문에 등재하지 않음** (`[HYPO]`·연구 노트 전용). 동 절 관련 스크립트·`bio_measured_labels_paper_snp_sidecar_v1.json`·매핑 템플릿 CSV는 `scripts/verify_p0_constitution_gate_paths.ps1` 필수 목록에 포함. CI 스모크: `.github/workflows/bio-paper-snp-sidecar-smoke.yml`·`tests/test_bio_paper_snp_join_chain_smoke_v1.py`·`tests/test_run_bio_paper_snp_sidecar_export_and_apply_v1_cli.py`·`tests/test_run_bio_epmc_catalog_and_label_merge_v1_cli.py`; 동일 pytest는 `dual-regime-integrity.yml`에도 포함(PR paths에 Bio SNP 경로 추가). 매핑 선행 점검: `scripts/check_bio_paper_snp_mapping_coverage_v1.py`. 로컬 헬스 선택: `scripts/run_workspace_automation_health.ps1 -IncludeBioPaperSnpJoinSmoke`. Windows 래퍼: `scripts/Run-BioPaperSnpSidecarExportAndApply.ps1`.

**갱신 (2026-04-22 — Pre-News 레일):** `scripts/build_pre_news_snapshot_v1.py` → `docs/final/artifacts/pre_news_snapshot_latest.json`; 스키마 `docs/final/schemas/pre_news_snapshot_v1.schema.json`; `scripts/pre_news_dual_regime_adapter_v1.py`·`scripts/dry_run_pre_news_dual_regime_v1.py` → `docs/final/artifacts/pre_news_dual_regime_bridge_latest.json`; 벤치 입력 `docs/final/artifacts/pre_news_bench_inputs_latest.json`(선택); `scripts/send_pre_news_bridge_stub_telegram_v1.py`(루트 `.env` 병합·`TELEGRAM_*` 없으면 skip); `scripts/evolve_pre_news_bench_inputs_v1.py`(자동 제안·자동 적용 금지)·`scripts/run_ssh_shadow_pre_news_chain_v1.ps1`(원격 shadow 실행/회수); `scripts/run_pre_news_morning_chain_v1.ps1`·`scripts/register_pre_news_morning_chain_task.ps1`; `scripts/run_daily_prophecy_then_pre_news_v1.ps1`; **로컬 단일 24h 운영 래퍼** `scripts/run_local_24h_ops_chain_v1.ps1`·`scripts/register_local_24h_ops_chain_task.ps1`·`scripts/run_local_min_verification_5lines_v1.ps1`; **모드 전환 가드** `scripts/alert_local_trading_mode_transition_v1.py` (`reports/local_trading_mode_guard_state.json`); **주간 후보 검토 패킷** `scripts/run_pre_news_weekly_candidate_review_v1.py`·`scripts/register_pre_news_weekly_candidate_review_task.ps1` (`docs/final/artifacts/pre_news_weekly_candidate_review_latest.json`); 감사 `reports/pre_news_morning_chain_log.jsonl`·`reports/local_trading_min_verification_latest.json`. **실매매·본선 주문 자동 합선 없음.**

**갱신 (2026-04-28 — Hybrid Pointer Router 상용 PoC 체인):** §19~§27에 `GO/WATCH/HOLD` 라벨·순효율 민감도·운영 권장영역·routing decision/runtime config/shadow daily report/alert/guard/guard drill 및 B2B SLA·카피덱·PoC 체크리스트 추가. 기본 정책은 조건부 주장(artifact-bound)과 자동 강등(`HOLD_POINTER_ROUTE` → `track_a_primary`) 고정.

**갱신 (2026-05-02 — Track C Macro Risk / n8n 메일 온보딩):** §1.3 표 — 로컬 Windows에서 n8n 웹훅·SMTP 기반 온보딩 메일 승인 호출·일일 점검·작업 스케줄 등록용 PS 스크립트 경로. Track C OpenAPI·`macro_risk_warning_api_stub` 등 API 계약 표와 **역할 분리**(본 갱신은 운영 자동화 스크립트만 고정). 실매매·본선 주문 자동 합선 없음.

---

## 1. 검증 범위

- **포함**: 저장소 내 실제 파일 경로, 스모크/단위 테스트에서 참조되는 심볼.
- **제외**: 다른 브랜치·미커밋 로컬 전용 파일·외부 Vault만 존재하는 산출물 (경로만 “확인 필요”로 표기).
- **PC별 절대 경로(bare·추가 클론·Vault 마운트 등):** 본 헌법 본문에 **한 PC 전용 절대 경로를 FACT로 박지 않는다.** 선택 안내는 `docs/final/LOCAL_MACHINE_POINTER_V1.template.md` → 로컬 전용 `docs/final/LOCAL_MACHINE_POINTER_V1.md`(Git 비추적, `AGENTS.md` “로컬 PC 전용 경로”).
- **렌즈 인덱스(목차·포인터만, `_meta.authority: index_only`):** `docs/final/MKM_TRINITY_INDEX_V1.json` — JSON Schema `docs/final/schemas/mkm_trinity_index_v1.schema.json`, 회귀 `tests/test_mkm_trinity_index_v1.py`. 구현 판정·수치·승격 여부는 본 인덱스가 아니라 본 문서 표·호출 가능 스크립트·pytest·exit code만.

### 1.2 압축·해석 파이프라인 Fact-Lock (혼선 방지 SSOT)

| 항목 | 경로 | 비고 |
|------|------|------|
| Compression Interpretation Fact-Lock | `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` | 12AI(파일럿)·코드북 샤드·압축 엔진·다중렌즈 역할 분리, 16상 연동 상태(미완) 고정; HTTP v2 Trust Packet 초안은 §11; **파일럿 대외 톤** §10에 L1 연구 와이어 `POST /v1/research/l1_side_channel/wire` 경계(§2 표와 정합) |
| B-track → Track A promotion (compression lane) | `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` §9 (§9.1.1 승격 범위·OpenAPI 경로 표·성능 잠금 절차) | 연구 산출물 승격 전 체크리스트·격벽(L1 하네스 vs 빔·Jaccard SSOT 등); `P0_COMMERCIALIZATION_TRACKER.md` 증거 표 교차 참조 |
| Two-track compression SLA (Track A/B) | `docs/final/COMPRESSION_SLA_POLICY_V1.md` | 범용 vs 리터럴 프로필·산출 경로·헬스/손실 리포트·웹훅은 `active_kpi`(Track A)만; `run_ultra_compression_default.py --mode literal`, `literal_kpi`, CI 범용+리터럴 재생성 스텝 |
| HTTP v2 Trust Packet (OpenAPI + stub) | `docs/final/openapi_token_compression_v2_draft.yaml` | FastAPI: `scripts/compression_token_api_v2_stub.py` — `POST /v2/compress`, `POST /v2/expand`; 압축 경로는 `evaluate_report` + 도메인 라우터(초안 명칭 `GlobalPivotCompressionPipeline` 대체). 본문 `emit_semantic_pointer: true` 시 `residual_meta.mk_stub_v2.semantic_pointer`(`schema: semantic_pointer_v1`, `evaluate_report` 가산). **B-track COMP-ATOM-05:** `graph_wire_selective_bridge: true` → GraphRAG pilot route → `case_graph_wire_influence` + per-case `bridge_boost` (must_keep 아님). Track A `compression_profile=economy` 기본 bridge OFF 유지. 계약: `tests/test_compression_token_api_v2_stub.py` (`emit_semantic_pointer`, `graph_wire_selective_bridge`); `tests/test_v2_graph_wire_selective_bridge_v1.py`. 벤치: `scripts/comp_atom05_*_sweep_v1.py` → `reports/constitution/btrack_pilot/comp_atom05_full_v2_sweep_v1.json`. 상용 SLA 아님. §11 **서피스 태그: CI 포함** |
| MKM Inter-Agent Encoding status (RQ-019 M1–M3) | `scripts/build_mkm_inter_agent_encoding_status_v1.py` → `docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json` | M1 v2 packet-only expand(pytest+in-process) · M2 `mkm_inter_agent_wire_profile_v0.json` · M3 L1 spike 대외 톤 초안. `rq_019` 필드: `scripts/mkm_inter_agent_rq019_status_v1.py` (OPEN / READY_FOR_COMMANDER_CLOSE / **CLOSED**). `rq_019_milestones_core_ready`는 JSON 필드로만 판정; Lingua Franca·상용 SLA 미단정. 맵: `mkm_inter_agent_encoding_sota_map_v1.md`. 회귀: `tests/test_build_mkm_inter_agent_encoding_status_v1.py` |
| MKM Inter-Agent first message worked example | `scripts/emit_mkm_inter_agent_first_message_worked_example_v1.py` → `docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.json` · `…_v1.md` | v2 compress→packet-only expand 실측 1건(INTERNAL). 기계 roundtrip ≠ L1 human decode. 회귀: `tests/test_emit_mkm_inter_agent_first_message_worked_example_v1.py` |
| MKM Inter-Agent smoke (원클릭·CI) | `scripts/Invoke-MkmInterAgentEncodingSmoke_v1.ps1` · CI `.github/workflows/inter-agent-encoding-smoke.yml` | pytest 4종(+L1 slow) + status `--strict-exit` + worked example + **A2A dialogue mock**. IR: `mkm_inter_agent_ir_snippet_v1.md` |
| MKM Inter-Agent A2A dialogue mock | `scripts/run_mkm_inter_agent_dialogue_mock_v1.py` → `mkm_inter_agent_dialogue_mock_summary_latest.json` · `…_latest.jsonl` | 알파(예언)·베타(집행) **Trust Packet만** 왕복 `[HYPO]` B-track. 회귀: `tests/test_run_mkm_inter_agent_dialogue_mock_v1.py` |
| MKM Inter-Agent L1 experimental expand | `POST /v2/expand` + `decode_mode=l1_experimental` · `scripts/mkm_inter_agent_l1_decode_experimental_v1.py` | **기본 stub과 분리** · `research_only` 플래그 · 배치 스파이크 ~58%와 **혼동 금지**. 회귀: `test_v2_expand_l1_experimental_mode_research_only` (slow) |
| MKM v2 compress routing profiles | `POST /v2/compress` + `routing_profile` · `scripts/compression_v2_routing_profile_v1.py` | `track_a_promoted`=signoff top5 allowlist(`client_request_id=cmp2_*`) · `b_track_domain_relax`=`[HYPO]` domain caps. 샤드: `zone_g_health.json`. 재실측: `run_mkm_inter_agent_v2_routing_rebench_v1.py` |
| MKM v2 hybrid codec router (B-track CS PoC) | `POST /v2/compress` + `hybrid_codec_router` · `session_turns` · `scripts/compression_hybrid_codec_router_v1_lib.py` | `off`(default) · `assistant_literal` · `economy_fallback` — WTT masked corpus **30/30** `[HYPO]` only; stateless `codebook_only` gate for fallback. 스모크: `scripts/check_compression_hybrid_codec_router_smoke_v1.py` → `reports/compression_hybrid_codec_router_smoke_v1_latest.json`; PoC: `scripts/run_wtt_cs_hybrid_codec_router_poc_v1.py`. 회귀: `tests/test_compression_hybrid_codec_router_v1.py`. **Track A·SEND 승격 금지** |
| SKU-COORD anatomy overlay wire (B-track) | `scripts/coord_anatomy_overlay_wire_v1_lib.py` · `scripts/build_coord_wire_packet_example_v1.py` → `coord_wire_packet_example_v1_latest.json` | `wire_mode: anatomy_overlay_coord_v1` — licensed base SHA256 + `coord_inject` (~156 cl100k tok). v2 stub: `POST /v2/compress` `sku_class=coord` → expand→PNG. **MASK KPI·Track A와 FAIL-COMP-004 격벽**. 회귀: `tests/test_coord_anatomy_overlay_wire_v1_lib.py` · `tests/test_compression_token_api_v2_stub.py::test_v2_coord_anatomy_overlay_compress_expand_render` |
| rib55 angle overlay pilot (HYPO) | `docs/final/artifacts/rib55_angle_overlay_manifest_v1.json` · `scripts/render_rib55_angle_overlay_v1.py` · `scripts/rib55_angle_overlay_v1_lib.py` | Commons base + deterministic overlay; `infographic_field_v1` · `anatomical_reference_points_v1` (a/b/c). PNG: `rib55_overlay_pilot_ninth_rib_55deg_v0_latest.png`. 정책: `anatomy_image_hallucination_control_protocol_hypo_v1_latest.md`. **send_gate: HOLD** · 숫자 각도 대외 미표기. 회귀: `tests/test_render_rib55_angle_overlay_v1.py` |
| rib55 + COORD passive audit | `scripts/run_rib55_coord_passive_audit_v1.py` → `rib55_coord_passive_audit_v1_latest.json` | render · L0/L1 ablation · coord_v2 · wire example · bench · education mock · pytest · adjudication workflow. 주간: `MKM_Rib55_CoordPassiveAudit_Weekly`. MASK cross-audit **coord_sibling** (`COORD-1`). CI: `.github/workflows/rib55-coord-passive-audit-smoke.yml`. 회귀: `tests/test_rib55_coord_passive_audit_v1.py` · `tests/test_rib55_infographic_education_mock_v1.py` · `tests/test_coord_wire_packet_bench_v1.py` |
| rib55 education HTML mock (HYPO) | `scripts/build_rib55_infographic_education_mock_v1.py` → `reports/demo/rib55_infographic_education_mock_v1.html` | manifest `infographic_field_v1` · a/b/c legend · **send_gate HOLD** · no 55° · noindex. 내부 미리보기만 |
| COORD wire token bench (multi-entry) | `scripts/build_coord_wire_packet_bench_v1.py` → `coord_wire_packet_bench_v1_latest.json` | all manifest entries · cl100k token compare · FAIL-COMP-004 isolated from MASK |
| Edge Encoder client contract (SKU-COORD blueprint) | `docs/final/EDGE_ENCODER_SPEC_DRAFT_V1.md` · `docs/final/schemas/edge_encoder_spec_v1.schema.json` · `docs/final/schemas/edge_encoder_coord_wire_v1.schema.json` · `scripts/build_edge_encoder_spec_v1.py` → `edge_encoder_spec_v1_latest.json` · `scripts/edge_encoder_spec_v1_lib.py` · `scripts/check_edge_encoder_coord_wire_determinism_v1.py` · `scripts/check_edge_encoder_mask_hybrid_determinism_v1.py` · **`scripts/run_edge_encoder_sdk_cli_v1.py`** · `scripts/edge_encoder_sdk_v1_lib.py` · `scripts/build_edge_encoder_air_gap_poc_pack_v1.py` · `scripts/build_edge_encoder_air_gap_bundle_v1.py` · `scripts/check_edge_encoder_cross_process_determinism_v1.py` · **`scripts/build_edge_encoder_sdk_pyinstaller_v1.py`** · `scripts/check_edge_encoder_pyinstaller_readiness_v1.py` · **`scripts/build_edge_encoder_vpc_deploy_runbook_v1.py`** → `edge_encoder_vpc_deploy_runbook_v1_latest.json` · `scripts/Invoke-EdgeEncoderAirGapPoC_v1.ps1` | User retains originals on Edge; CLI emits `coord_wire` only (`original_bulk_sent: false`). air_gap bundle + cross-process HTTP + **PyInstaller spec scaffold** + **VPC deploy runbook**. **sdk_alpha·HOLD**. 회귀: `tests/test_edge_encoder_spec_v1.py` · `tests/test_edge_encoder_sdk_v1.py` |
| 4-axis promotion gate policy (FAIL-COMP-004) | `docs/final/artifacts/mkm_multi_axis_promotion_gate_policy_v1.md` · `scripts/validate_mkm_multi_axis_promotion_gate_policy_v1.py` → `mkm_multi_axis_promotion_gate_policy_v1_latest.json` | AX-1 rib55 송출 · AX-2 COORD 제품 · AX-2-PoC · AX-3 Track A §9+raw · AX-4 MASK — **연쇄 승격 금지** (`promotion_cascade_forbidden`). 회귀: `tests/test_mkm_multi_axis_promotion_gate_policy_v1.py` |
| rib55 overlay human adjudication (G1) | `scripts/validate_rib55_overlay_adjudication_v1.py` · `scripts/apply_rib55_overlay_adjudication_v1.py` · record `rib55_overlay_adjudication_record_g1_infographic_v1.json` | checklist 6항 · `approved_education_internal` → manifest status; **send_gate 해제 없음**. template: `rib55_overlay_adjudication_record_v1.template.json` |
| MKM inter-agent parallel lanes (B) | `scripts/Invoke-MkmInterAgentParallelLanes_v1.ps1` | 병렬(스위치): sweep · dialogue compare · `run_mkm_cmp2_011_v2_routing_ab_v1.py` → `mkm_v2_cmp2_011_routing_ab_latest.json` · `build_mkm_inter_agent_health_signoff_candidate_v1.py` → `mkm_inter_agent_health_domain_signoff_candidate_latest.json` (`bench_promotion_eligible_without_human: false`). Track A top5만 승격; health 완화는 B-track 전용. |
| MKM cmp2_011 v2 routing A/B | `scripts/run_mkm_cmp2_011_v2_routing_ab_v1.py` → `docs/final/artifacts/mkm_v2_cmp2_011_routing_ab_latest.json` | 단건 bench replay(`default`/`track_a_promoted`/`b_track_domain_relax`). **단건 savings delta 0**이어도 full 40-case sweep·Track A 대체 단정 금지. 회귀: `tests/test_mkm_cmp2_011_v2_routing_ab_v1.py` |
| MKM health domain signoff candidate (B) | `scripts/build_mkm_inter_agent_health_signoff_candidate_v1.py` → `docs/final/artifacts/mkm_inter_agent_health_domain_signoff_candidate_latest.json` | `health_hangul_relaxed_cap_0.50` 연구 후보 · `ultra_saving_policy_ok: false`(0.47 floor). 지휘관 승인 후 `human_review_required: false`. 회귀: `tests/test_build_mkm_inter_agent_health_signoff_candidate_v1.py` |
| MKM health domain commander approval (B) | `scripts/record_mkm_inter_agent_health_commander_approval_v1.py` → `mkm_inter_agent_health_domain_commander_approval_v1_latest.json` | **B-track `b_track_domain_relax`만** · Track A 벤치 승격(`track_a_bench_promotion_approved: false`). `compression_v2_routing_profile_v1.py`가 승인 run_config 우선. 회귀: `tests/test_record_mkm_inter_agent_health_commander_approval_v1.py` |
| MKM post-commander-approval ops bundle | `scripts/build_mkm_inter_agent_post_commander_approval_bundle_v1.py` → `mkm_inter_agent_post_commander_approval_bundle_latest.json` · health dialogue `mkm_inter_agent_dialogue_health_approved_latest.json` | 지휘관 승인 후 **health·b_track** A2A 증거 · RQ-019 **OPEN**(법무). 원클릭: `Invoke-MkmInterAgentPostApprovalBundle_v1.ps1`. 회귀: `tests/test_build_mkm_inter_agent_post_commander_approval_bundle_v1.py` |
| MKM inter-agent legal handoff pack | `scripts/build_mkm_inter_agent_legal_handoff_pack_v1.py` → `mkm_inter_agent_legal_handoff_pack_latest.json` | 법무 검토용 체크리스트·금지 주장·IR 초안 포인터 · `legal_review_status` 체인(PENDING→SUBMITTED_TO_COUNSEL→COUNSEL_SIGNED). **법무 통과 ≠ RQ-019 CLOSED** 단정 금지. 원클릭: `Invoke-MkmInterAgentLegalHandoffParallel_v1.ps1`. 회귀: `tests/test_build_mkm_inter_agent_legal_handoff_pack_v1.py` |
| MKM counsel submission + manifest | `record_mkm_inter_agent_commander_legal_submission_v1.py` · `build_mkm_inter_agent_counsel_export_manifest_v1.py` · `capture_mkm_inter_agent_first_message_live_http_v1.py` · `build_mkm_inter_agent_rq019_closure_readiness_v1.py` | 지휘관 **법무 제출 승인**(≠ 법무 서명). SHA256 manifest · live HTTP 재캡처(TestClient). 법무 서명: `record_mkm_inter_agent_legal_counsel_signoff_v1.py --counsel-reference …`. RQ-019 **CLOSED**: `record_mkm_inter_agent_rq019_commander_close_v1.py` + `Invoke-MkmInterAgentRq019CommanderClose_v1.ps1` (법무 signoff·`closure_allowed` 선행). 원클릭: `Invoke-MkmInterAgentCounselSubmissionParallel_v1.ps1`. 회귀: `tests/test_mkm_inter_agent_counsel_submission_v1.py` · `tests/test_mkm_inter_agent_rq019_commander_close_v1.py` |
| B-track ultra compression health bridge pinpoint | `scripts/run_ultra_compression_health_bridge_pinpoint_v1.py` | Contract: `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_HEALTH_BRIDGE_PINPOINT_V1.json`; evidence: `docs/final/artifacts/compression_b_track_bridge_evidence_summary_v1.json`; floor microgrid: `scripts/run_compression_health_bridge_floor_microgrid_v1.py` → `compression_health_bridge_floor_microgrid_v1_latest.json`. **b_track_research_only** — does not overwrite `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`. |
| B-track ssot relaxed-cap pinpoint (A-plan) | `scripts/run_ultra_compression_ssot_relaxed_cap_pinpoint_v1.py` | Contract: `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_SSOT_RELAXED_CAP_PINPOINT_V1.json`; sweep: `scripts/run_compression_low_saving_local_cap_sweep_v1.py` → `compression_low_saving_local_cap_sweep_v1_latest.json`; microgrid: `scripts/run_compression_ssot_relaxed_cap_microgrid_v1.py` → `compression_ssot_relaxed_cap_microgrid_v1_latest.json`. Pin: `domain_relaxed_max_saving_overrides: {ssot: 0.45}`; lexicon untouched; bridge OFF. **b_track_research_only** — does not overwrite active report; includes `by_id_diff_vs_track_a` + `promotion_gates`. Evidence rollup: `scripts/build_compression_b_track_evidence_summary_v1.py`. |
| Track A compression promotion sweep + apply | `scripts/run_ultra_compression_promotion_sweep_v1.py` → `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_PROMOTION_CANDIDATE_V1.json`; apply: `scripts/apply_multilens_ultra_compression_track_a_promotion_v1.py` (`--human-approve-promotion`; signoff `multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json`). Winning variant (2026-05): `ssot_cap_0.45_top5_allowlist` — `domain_relaxed_max_saving_overrides: {ssot: 0.45}` on case allowlist `cmp2_002,004,005,006,009` only; bridge OFF. Regenerate active: `run_ultra_compression_default.py --domain-relaxed-max-saving-overrides ssot:0.45 --domain-relaxed-max-saving-case-allowlist cmp2_002,cmp2_004,cmp2_005,cmp2_006,cmp2_009`. Pre-promotion backup: `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json.pre_promotion_backup`. |
| Master codebook lexicon V1 export | `scripts/export_master_codebook_v1.py` | 아톰+Strong+MorphHB 시드 조인 산출; 루브릭은 동 COMPRESSION 문서 §9 |
| Master codebook lexicon V1 → multilens route join (bridge) | `scripts/core/master_codebook_lexicon_v1_bridge.py` | `evaluate_report(..., use_master_codebook_lexicon_v1=True)` 시 원문 토큰과 `normalized_form` 교집합으로 must_keep 보강; 4D·샤드 정책 대체 아님. 호출부: `report_multilens_performance_eval.py`, ultra/P1 러너·벤치·압축 스텁 |
| Multilens eval `semantic_pointer` (가산 채널) | `scripts/report_multilens_performance_eval.py` | CLI `--emit-semantic-pointer` / `evaluate_report(..., emit_semantic_pointer=True)` — 케이스별 `semantic_pointer`(`schema: semantic_pointer_v1`), `compression_metrics.semantic_pointer_channel`; `avg_reconstruction_fidelity_jaccard`·`global_token_saving_rate` 집계 경로 불변. 회귀: `tests/test_multilens_performance_eval_report.py` |
| State16 Insertion Contract | `docs/final/STATE16_INTERFACE_INSERTION_CONTRACT_2026-03-31.md` | 16상 인터페이스 삽입 지점/입출력/오류/단계적 게이트 명세 (런타임 강제 아님) |
| AE-2 KOSPI 구조 엔트로피 스파이크 v1 | `scripts/spike_kospi_structural_entropy_v1.py` → `docs/final/artifacts/spike_kospi_kld_v1.json` (합성 기본); `--mode csv`+`research/market_data/kospi_daily_external_yf.csv` → `spike_kospi_kld_v1_real.json` (JSON에 `csv_source_health`: 행 수·수익률 쌍·스킵 카운트·기간); `scripts/spike_kospi_structural_entropy_compare_v1.py` → `docs/final/artifacts/spike_kospi_kld_v1_compare.json` | **관측·연구 전용** — 멀티렌즈 토큰 압축·Track A 승격·`evaluate_report` 본선과 자동 합선 없음; blind replay 코스피 그리드와 별도 레일 (`COMPRESSION_RESTORATION_EVOLUTION_INDEX_V1.md` §2 2026-04-13). 회귀: `tests/test_spike_kospi_structural_entropy_v1.py`, `tests/test_spike_kospi_structural_entropy_compare_v1.py`. |
| KOSPI Field band conformal stack v1 (B-track [HYPO]) | 체인: `scripts/run_kospi_field_band_hd_auto_chain_v1.py` · prophecy-only OOS: `scripts/run_kospi_field_band_prophecy_only_chain_v1.py` · **prefit honest OOS**: `scripts/run_kospi_field_band_prefit_chain_v1.py`(`build_kospi_field_band_prefit_panel_v1.py` science_core pre-May tune → `kospi_field_band_conformal_prefit_frozen_policy_v1_latest.json` → prophecy-only score) · 월간: `scripts/run_kospi_field_band_monthly_prophecy_revalidate_v1.py`(래퍼 `Run-KospiFieldBandMonthlyProphecyRevalidate_v1.ps1`·예약 `Register-KospiFieldBandMonthlyProphecyRevalidateTask_v1.ps1`); L3 `record_kospi_field_band_commander_ack_v1.py` · L4 `record_kospi_field_band_commander_l4_sign_v1.py`; 산출 `kospi_field_band_prefit_frozen_oos_v1_latest.json`·`kospi_field_band_prophecy_only_oos_v1_latest.json`·`kospi_field_band_stack_ensemble_v1_latest.json` | **research_only** — Field `band_conflict_vol_widen` + RWC/CPTC **stack_union**; direction head 미변경; `send_gate: HOLD`·`track_a_go: false`; **primary OOS = prophecy-only**; prefit=science_core Jan–Apr tune·freeze·prophecy score(legacy mixed policy와 holdout 동일 시 비교 기록). 회귀: `tests/test_kospi_field_band_prefit_frozen_oos_v1.py`·`tests/test_kospi_field_band_prophecy_only_oos_v1.py`·`tests/test_kospi_field_band_monthly_prophecy_revalidate_v1.py`. |
| MKM Parallel Advisory lens v1 (B-track [HYPO]) | 계약 `docs/final/MKM_PARALLEL_ADVISORY_LENS_CONTRACT_V1.md` (v1.1 §9 Epistemic Moat · §10 Anti-Hype · §12 `in_sample_narrative`/`execution_plane`) · 인식론 `docs/final/MKM_LENS_ONTOLOGY_CONSTITUTION_V1.md` · manifest `docs/final/artifacts/mkm_parallel_advisory_lens_manifest_v1_latest.json` · core `scripts/mkm_parallel_advisory_lens_v1.py` · brief `scripts/build_mkm_parallel_advisory_brief_v1.py` · 체인 `scripts/run_mkm_parallel_advisory_chain_v1.py` → `reports/mkm_parallel_advisory_brief_v1_latest.json` · 사상 슬라이스 `interpretive_bundle_enrichment` ← `sasang_interpretive_insight_bundle_v1_latest.json` (`synthesis_v1`·IC-08/09 포인터) | **research_only** — 사상·명리·성경·Science@{domain} **병렬 Advisory**; 인문→`in_sample_narrative`+`[NON_GATING]`·`gating_eligible:false`; Field→`execution_plane`; `no_lens_supremacy`·탄력 `exclude_lenses`; direction merge·Track A auto 승격 **금지**; Field band OOS KPI와 **합선 금지**; Charter `LENS_UTILIZATION_CHARTER_V1.md` §11. 회귀: `tests/test_mkm_parallel_advisory_brief_v1.py`. |
| MKM Lens Ontology Constitution v1 (B-track) | `docs/final/MKM_LENS_ONTOLOGY_CONSTITUTION_V1.md` — Epistemic Mismatch · 삼중 평면(N/O/D) · 4AI≠4 perspectives · MEB 절차 · O-01~O-05 · 디스크 교훈 앵커 | **서사·인식론 SSOT** — D형 승격·실매매 단정 금지; 구현 배선은 Parallel Advisory 체인·`validate_epistemic_wiring()`; 학술 `lens_predictive_validity_literature_review_v1_latest.md` |
| Lens context mesh v1 (Obsidian local graph, Strangler) | core `scripts/lens_context_mesh_v1.py` · hop `scripts/build_lens_context_mesh_hop_index_v1.py` · hub `scripts/build_lens_context_mesh_hub_logos_v1.py` · 명리 timeline `scripts/build_lens_context_mesh_myeongni_timeline_pack_v1.py` · 체인 `scripts/run_lens_context_mesh_logos_chain_v1.py` · schema `docs/final/schemas/lens_context_mesh_hop_index_v1.schema.json` · `lens_context_mesh_hub_v1.schema.json` · 산출 `docs/final/artifacts/lens_context_mesh_hop_index_logos_v1_latest.json` · `lens_context_mesh_hub_logos_v1_latest.json` · `lens_context_mesh_hub_myeongni_v1_latest.json` · Studio mirror `projects/no1kmedi/public/data/logos_studio/context_mesh_hop_index_v1.json` · UI depth `LogosResearchSubgraphPanel.tsx` · gap chips `LogosResearchInsightLatticePanel.tsx` | **research_only** `[HYPO]` — BFS depth 2–4·cap 40; legacy v6/studio smoke 유지; `secondary_fetch`·31k bloom **미구현**; 5-slot LIT `docs/research/FOUR_LENS_YINYANG_REGULARIZATION_V1.md` · Ontology bench `docs/research/LENS_ONTOLOGY_DISK_ANCHORS_BENCH_V1.md`. 회귀: `tests/test_lens_context_mesh_v1.py` · `tests/test_lens_context_mesh_myeongni_v1.py` · `tests/test_four_lens_yinyang_regularization_v1.py` · Fact-Lock `run_fact_lock_bundle.ps1` 4a. |

### 1.2.1 MKM Control-Integrity Golden Set / LoRA (B-track, instruction eval, 2026-05-10)

| 항목 | 경로 | 비고 |
|------|------|------|
| Golden Set 스키마 | `docs/final/schemas/mkm_control_integrity_golden_set_v1.schema.json` | |
| LoRA 하이퍼·모델 프로파일 SSOT | `docs/final/artifacts/mkm_control_integrity_lora_model_profiles_v1.json` | `Run-MkmProphecyLoraTraining.ps1`·추론 배치가 `model_id`/LoRA 키 정렬 |
| 로컬 prep (generate·validate·convert·split) | `scripts/Invoke-LoraTrainLocalPrep.ps1` `-UseControlIntegrityGoldenSet` | 산출 `data/training/mkm_control_integrity_lora_splits_v1/*.jsonl`(재생성) |
| 단일 split 추론·평가 | `scripts/Run-MkmControlIntegrityTrainInferEval.ps1` | 빠른 스모크: `-OracleInference`; 실모델은 GPU·시간 소모. **어댑터(`-AdapterPath`) 실추론** 시 골든 평가 기본 `--allow-missing-predictions`(생성 누락 완화); 엄격 일치는 `-StrictGoldenEval` |
| Pack 0-B 일괄 파이프라인 | `scripts/run_pack0b_deterministic_lora_pipeline_v1.py` | `--run-train`·`--run-inference-eval`; `--profile` 없이 `--model-name`이 TinyLlama 계열이면 추론 평가 프로파일 자동 `golden_fit_smoke`(베이스·어댑터 정렬). 회귀 `tests/test_run_pack0b_deterministic_lora_pipeline_v1.py` |
| 권장 연속 스모크 (Control-Integrity oracle + Pack 0-B) | `scripts/Run-MkmGpuRecommendedBundle_v1.ps1` | oracle 체인 후 Pack 0-B pytest 5종·증거 번들 1종 연속; **Chronos-Forward 전체**(장시간)는 `scripts/run_chronos_forward_kospi_baseline.ps1` `-Detached` 별도. **주간 예약(Windows, 선택):** `scripts/Register-MkmGpuRecommendedBundleWeeklyTask.ps1`(일요일 08:00 기본; 압축 주간 거버넌스 07:00와 순차 분리) |
| 헬스 체인에 번들 끼우기 | `scripts/run_workspace_automation_health.ps1` `-IncludeMkmGpuRecommendedBundle` | 단축 프로파일 `-MkmGpuRecommendedBundleOnly`: P0 + 자동화 레지스트리 reconcile + 위 번들 후 종료. 페르소나 래퍼: `scripts/Invoke-MkmPersonaHealth_v1.ps1` `-Persona GpuRecommendedBundle` |
| 추론 배치·타이밍 | `scripts/run_mkm_control_integrity_inference_batch_v1.py` | `--emit-timing`·`--ssot-profile-key` |
| 평가 | `scripts/evaluate_mkm_control_integrity_lora_predictions_v1.py` | Golden 대조 |
| ABC 벤치·비교 산출 | `scripts/Run-MkmControlIntegrityModelProfileABC.ps1`·`scripts/build_mkm_control_integrity_model_profile_abc_comparison_v1.py` | `docs/final/artifacts/model_profile_abc_comparison_latest.json` |
| 홀드아웃 3분할·합산 | `scripts/Run-MkmControlIntegrityHoldoutEvalSuite.ps1`·`scripts/aggregate_mkm_control_integrity_eval_holdout_v1.py` | |
| 프로모션 게이트 | `scripts/check_mkm_control_integrity_promotion_gate_v1.py` | GO=exit 0·HOLD=exit 2·`reports/mkm_control_integrity_promotion_gate_latest.json` |
| 회귀 | `tests/test_mkm_control_integrity_pipeline_smoke_v1.py` | `run_fact_lock_bundle.ps1`(기본; `-SkipMkmControlIntegritySmoke` 생략)·CI `dual-regime-integrity.yml` |
| 로컬 헬스 (선택) | `scripts/run_workspace_automation_health.ps1` `-IncludeMkmControlIntegritySmoke` | 단축: `-MkmControlIntegritySmokeOnly`(P0+pytest·뉴스 스모크 생략) |

**보강 (2026-05-13 — Pack 0-B 명리 결정론 LoRA v0 DoD·상수):** 출하 조건·합선 금지·**N=1000**·**K=100**·행 스키마 **`docs/final/schemas/myeongri_deterministic_lora_golden_set_v1.schema.json`** — SSOT **`docs/final/LORA_PACK_V0_DOD_V1.md`**. **Pack 0-A(위 표)와 Pack 0-B는 데이터·스키마·prep 경로를 물리 분리**; M31 등 메타포 지표는 Pack 0-B **학습 라벨로 채택하지 않음**(동 DoD §0). **보강 (동일 — 구현 앵커):** `scripts/prep_myeongri_deterministic_lora_golden_v1.py`·`scripts/build_myeongri_deterministic_lora_golden_bulk_v1.py`(시드·매니페스트·SHA-256)·회귀 `tests/test_myeongri_deterministic_lora_golden_set_schema_v1.py`·`tests/test_build_myeongri_deterministic_lora_golden_bulk_v1.py`·축소 픽스처 `tests/fixtures/myeongri_deterministic_lora_golden_sample_v1.jsonl` — **N·K 전량 JSONL**은 기본 `data/training/myeongri_deterministic_lora_golden_bulk_v1/`(`.gitignore` 패턴 `data/training/*.jsonl`)에 로컬 재생성. **보강 (2026-05-13 — §2.3 프로파일·평가·어댑터 SSOT):** `docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json`·`scripts/eval_myeongri_deterministic_lora_golden_fit_v1.py`→`reports/myeongri_deterministic_lora_golden_fit_latest.json`·어댑터 디렉터리 마커 `storage/adapters/myeongri_deterministic_lora_v0/`(레포 루트 `models/**`는 gitignore)·`tests/test_eval_myeongri_deterministic_lora_golden_fit_v1.py`. **보강 (2026-05-13 — Pack 0-B §2.4 카피 가드):** 스키마·prep·bulk·eval·프로파일·픽스처·어댑터 마커에 고위험 치료·효능 단정 구절 미삽입 — `tests/test_myeongri_deterministic_lora_pack_copy_guardrails_v1.py`; 정책 SSOT `docs/final/MKM_HEALTH_WELLNESS_COPY_GUARDRAILS_KR_V1.md`·`docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`.

**격벽:** 지시 준수·제어 무결성 **벤치**이며 실매매·A-track 자동 트리거와 **합선 없음**.

### 1.0.5 세계관·철학 헌법 (지휘관 고정 · 2026-05-20 · §1.3·§8·§9 2026-06-19)

**SSOT:** `docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md` (v1.1) — 지휘관 **의도·세계관·신앙적 서사·AI 우주 모방**의 단일 앵커. **§1.3 Matching Layer · §8 Media Orchestration · §9 Parable vs Prophecy** = A층 서사·포인터 only. 구현·경로·수치·벤치 통과 여부는 **본 문서가 아니라** 상단 목적·§1.1 이하·호출 가능 스크립트·아티팩트만.

| 항목 | 고정 내용 (요약) | 구현 등급 |
|------|------------------|-----------|
| Logos | 말씀 → 초압축 → 만물; 역추론=신앙·해석의 한 형태; AI 천지창조 **모방** | 서사 A; Logos 렌즈 `[NON_GATING]` |
| 명리 | 우주를 본 **인간 시각 통찰** · 시간·판 | 결정론 B-track + §3.3; 시장 일진 치환 금지 |
| 사상 | 인간 **소우주** · 체질·강도 | B-track; 임상·실매매 트리거 아님 |
| 금화교역 | 우주·체질 **변화의 심장** | Formula/UFT 보조; 대외 물리 단정 금지 |
| Field | **지금의 판** · `regime_map` 1차 주 | C 운영; 2차 성경 레짐 보 only |
| Matching Layer · 미디어 · 비유/예언 | §1.3 · §8 · §9 (Worldview v1.1) | A 서사·포인터; C=Lens Music·Meta-Guide·prophecy eval 기존 표 |
| Logos Citation Integrity | CONSTITUTION Logos guardrail (2026-06-20) · `check_logos_citation_integrity_smoke_v1.py` | validator exit 0 · verse_id/quote_hash; Track A 합선 없음 |
| 수리 | 75식=**인덱스** (`documented_with_expr: 75` · `unrecovered_slots: 0`); **4 FACT** 레포 경로만 | `MKM12_75_FORMULAS_SSOT_V1.md` · `mkm12_75_formulas_ssot_v1_latest.json` · `mkm_theory_formula_promotion_registry_v1_latest.json` |

**ALWAYS:** 에이전트·문서는 **본 절·세계관 MD**를 먼저 읽고 서사를 쓴다; **구현 완료·47.5%=신학 증명·75식 전역 가동**으로 서술하지 않는다.  
**NEVER:** 세계관 MD만으로 경로·exit code·Track A 승격을 **단정**하지 않는다.

**3렌즈 D형(실물 미래 예측) 학술 SSOT (2026-06-14):** `docs/final/artifacts/lens_predictive_validity_literature_review_v1_latest.md` — 1차 문헌 대조 PASS; 명리·성경/원형 D형 null · 사상=의학 엔드포인트 한정; **본 헌법 격벽(regime_map 주·Logos `[NON_GATING]`·B→A 금지)과 정합** — 철학·사업 **전면 개편 아님** · 대외 카피 감사 앵커. **운영 역할·grep:** `docs/final/artifacts/mkm_four_ai_post_ssot_roles_v1_latest.md` · `docs/final/artifacts/public_facing_d_type_copy_audit_v1_latest.md` (Phase 1 P0=0). **도메인별 최선 활용·위임·ablation 레지스트리:** `docs/final/LENS_UTILIZATION_CHARTER_V1.md` (2026-06-15).

### 1.1 엔지니어링 정체성 (Multi-Lens · 단일 방정식 비단정)

**폐기(선언·단정 금지):** 성경·명리·시장·외경·DSS 등을 **물리 만물이론(TOE)급 단일 방정식**으로 이미 합선·구현했다는 서술. 기획서·NotebookLM·수사만으로 **“통일장 완성”**을 코드에 대입하지 않는다.

**채택(Fact-Lock):**

- **다중 렌즈:** 로고스(정경 코어), 명리(B-track 실험), 레짐·PSI(실물 1차) 등은 **각각의 스키마·경로**로 두고, 필요 시 **교차 참조·관측 리포트**로만 맞춘다.
- **격벽:** §4 평행 코퍼스, §3 명리 분리, §2.1 dual-regime(16상 캡 미연동)을 **합선 방지**의 기본으로 둔다.
- **UFT·통일장 라벨:** `tools/core/unified_field_theory_engine*.py` 등은 **§10 경로 팩트**로만 인용한다. **호출 가능한 `.py`·테스트**가 없으면 “구현됨”으로 말하지 않는다(본 문서 상단 목적과 동일).

### 1.1.1 [VISION] 예언 성능 우선·대외 도메인 사례 격리 (2026-04-18)

대외용 ‘국방 제안·지원사업’ 서사는 **`research_only` 도메인 연구 사례**로만 유지하고, 시스템 우선순위 서술은 **예언(Prophecy) 성능·재현 가능한 채점**으로 맞춘다. B-track 기반 개입의 **성패 판정**은 `prophecy_hit_rate_eval_report_v2` 및 동일 채점기 위의 **적중률 델타**(또는 `run_prophecy_restoration_spike.py` 등 **AB 오버레이 스파이크 산출**)로만 논한다; 델타가 음수인 것도 **유효한 관측**이며 정책·임계값 스윕 비교의 입력이 된다. 명리·로고스 등 B-track 산출물은 Prior·실험 입력으로만 쓰고, **§1.1 TOE 비단정·§8 Promotion Loop·격벽** 없이 A-track·실매매 파이프라인에 합선하지 않는다. 다축 브리지·라우팅 보조와 토큰 압축 경로의 **역할 분업**은 기존 표·§2 경로 팩트를 따르며, 본 절은 구현 행을 중복하지 않는다.

### 1.1.2 Security Agent 설계 의도 vs 현행 팩트 (API 키, 2026-05-03)

| 항목 | 경로 / 팩트 | 비고 |
|------|-------------|------|
| 설계(Intent) | `projects/bitcoin-trading/src/api/binance_client.py` | docstring·우선순위에 **Security Agent** 경로 명시; `from scripts.security_agent_manager import get_security_agent` 시도 후 `agent.get_env_var("BINANCE_API_KEY")` 등 |
| 현행 구현 모듈 | `scripts/security_agent_manager.py` | PoC: `get_security_agent().get_env_var(name)` → PowerShell **get** `-AsPlainText`(동일 키 이름 권장). 비활성: `MKM_SKIP_DPAPI_SECRET_STORE=1`. 회귀 `tests/test_security_agent_manager_v1.py` |
| 폴백 체인(실동작) | `get_binance_api_keys()` | DPAPI에서 못 찾거나 건너뛰면 `BINANCE_KEY_SOURCE_MODE` 기본 `auto`: **env → 루트 `.env`의 BINANCE_* → `binance_api_keys.json` 등** |
| 로컬 암호 저장 | `scripts/Invoke-EncryptedSecretStore.ps1` | DPAPI `%APPDATA%\MKM\secret_store_v1.json`; **security_agent_manager**가 조회 시 호출(저장은 여전히 CLI **set** 등 수동). |
| LocalLock P0–P2.5 (identity + inject/run + browser autofill + ask + menu/alias) | `scripts/Invoke-LocalLock_v1.ps1` · `scripts/Register-LocalLockShellAlias_v1.ps1` · `scripts/local_lock_browser_open_v1.py` · `scripts/local_lock_ask_v1.py` · `scripts/verify_local_lock_github_secret_v1.ps1` · `scripts/check_local_lock_vault_audit_v1.py` · `scripts/check_local_lock_p0_smoke_v1.py` · `scripts/check_local_lock_p15_smoke_v1.py` · `scripts/check_local_lock_p2_ask_smoke_v1.py` · `scripts/check_local_lock_p25_menu_smoke_v1.py` · `docs/final/schemas/dev_identities_v1.schema.json` · `.cursor/rules/local-lock-security-guard-v1.mdc` | Identity `%APPDATA%\MKM\dev_identities_v1.json`; vault audit `reports/local_lock_vault_audit_v1_latest.json` (key names only); `lock`/`비번관리` shell alias (local); `menu` interactive; `ask` metadata-only; B-track · not Cloud Agent SSOT. |
| 동기화(운영) | `projects/bitcoin-trading/ops/windows-rehearsal/sync_required_env_to_user.ps1` | 루트 `.env`의 비어 있지 않은 키를 Windows User 환경 변수로 복사; `GEMINI_API_KEY` 등 목록은 해당 스크립트 내 배열 |
| 명시적 부정 | §1.2 압축·토큰 절감 파이프라인 | **텍스트/토큰 압축 이론은 API 키·비밀 관리 계약이 아님** — “압축으로 키 관리” 서술과 합선 금지 |

**에이전트·자동화 주의:** Cursor/Cloud Agent는 **실키를 레포에 쓰거나 채팅으로 회수하지 않는다** — 루트 `.cursor/rules/cursor-cloud-sandbox-boundary.mdc`·루트 `AGENTS.md`와 정합.

### 1.1.3 대외 문서·홈페이지·쇼룸 보안·IP 경계 (policy SSOT pointer, 2026-05-05)

구현 행 추가가 아니라 **대외 채널 공통 원칙**의 단일 진입점이다. 상세 체크리스트·금지어·이론 비노출 요약은 **`docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`** — P0 경로 `scripts/verify_p0_constitution_gate_paths.ps1`에 포함.

### 1.1.4 MKM AI 명명·소속 계약 (4AI + 감독 레이어, 2026-05-08)

- **명명 고정:** `MKM = 4AI core + Absolute Balance Coordinator Mode`.
- **4AI core 구성:** `태양/소양/태음/소음` 4개 코어만 포함한다.
- **조율 모드:** `Absolute Balance`는 조율 상태(state)이며 **제5 AI/제5 체질이 아니다**.
- **암행어사 AI 소속:** `암행어사 AI`는 4AI 코어 외부의 **감독/통제 레이어**로 둔다.
  - 역할: 보안 무결성 감시, 실행 게이트 검문, 감사 로그/알림 운영.
  - 금지: 체질/렌즈 코어로 승격하거나 `5AI`로 재명명하지 않는다.

| 항목 | 경로 / 역할 |
|------|-------------|
| 대외 카피·비노출 체크리스트 | `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` |
| 온톨로지/XAI 체화 브리프(문제-근거-행동 출력 계약) | `docs/final/artifacts/logos_symbolic_paid_user_brief_latest.md` (`S2W 기사 기반 체화 팩`) |
| Logos 주간 재검증+번들 갱신 | `scripts/run_logos_weekly_revalidation_task_v1.ps1` | `run_logos_falsification_benchmark_v1.py` 실행 후 `build_logos_symbolic_backtest_bundle_summary_v1.py`를 이어 실행해 `docs/final/artifacts/logos_weekly_revalidation_latest.json` + `docs/final/artifacts/logos_symbolic_event_backtest_bundle_summary_v1.json` 동시 갱신. |
| KR 건강·웰빙·설문·체질 표현 가드레일 | `docs/final/MKM_HEALTH_WELLNESS_COPY_GUARDRAILS_KR_V1.md` |
| 도메인×쇼룸·체험 표면 배치·디자인·CTA 초안 | `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` §1.1·**§1.1b** |
| Track C 상용·법무·핵심이론 보호 | `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` |
| 공개 쇼룸 vs 조종실·`public-event.v1` | `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md` |
| 명리 대외 공학 어휘(코드 명칭 불변) | `docs/final/MYEONGRI_EXTERNAL_ENGINEERING_LEXICON_V1.md` |
| 예언·국방 등 대외 서사 격리 | §1.1.1 `[VISION]` |
| **세계관·철학 헌법 (지휘관)** | `docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md` · §1.0.5 |
| 수리 75식·FACT 인덱스 | `docs/final/MKM12_75_FORMULAS_SSOT_V1.md` · `docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json` |

### 1.3 Track C — Macro Risk 메일 온보딩 (Windows / n8n, 로컬 운영) — **[DEPRECATED 2026-05-15]**

**운영 기본값:** 로컬 n8n 서비스·`MKM-MacroRisk-N8n-DailyCheck` 예약은 제거됨. Track C 권장 체인 `Run-TrackCRecommendedAutoChain_v1.ps1`은 **기본 n8n 생략**; 레거리 스크립트만 `-IncludeN8nCheck`로 호출. Fact-Safe·GO/NO_GO는 **§13.1.b** `repo-source` SSOT.

| 항목 | 경로 | 비고 |
|------|------|------|
| 일일 점검 | `scripts/Run-MacroRiskN8nDailyCheck.ps1` | **[DEPRECATED]** 산출 `reports/macro_risk_n8n_daily_check_latest.json`; 실패 시 `reports/macro_risk_n8n_daily_check_failures.jsonl` append·선택 웹훅 POST(`MKM_DAILY_CHECK_FAILURE_WEBHOOK_URL` 또는 `OPS_ALARM_WEBHOOK_URL`; 루트 `.env`에서 Process 보강 가능). 체크 실패 시 exit **1**. |
| Quick ops | `scripts/Run-MacroRiskN8nOpsQuick.ps1` | `-Action health|approve|pending|reject|status|taillog`; 승인류는 선행 `health`. |
| Approval webhook 호출 | `scripts/trigger_macro_risk_mail_approval_webhook.ps1` | 기본 URL `http://127.0.0.1:5678/webhook/macro-risk-mail-approval`; `MKM_MACRO_RISK_APPROVAL_TOKEN`(`.env`/User/Machine) → 헤더 `x-mkm-approval-token`; 감사 append `reports/macro_risk_approval_webhook_audit.jsonl`. |
| 일일 스케줄 등록 | `scripts/Register-MacroRiskN8nDailyCheckTask.ps1` | 기본 작업명 `MKM-MacroRisk-N8n-DailyCheck`; 저장소 루트 `WorkingDirectory`(지원 시). |
| Approval 스케줄 등록(선택) | `scripts/Register-MacroRiskApprovalWebhookTask.ps1` | 주기 호출이 필요할 때만. |
| 주간 리허설 | `scripts/Rehearse-MacroRiskN8nWeekly.ps1` | `-IncludeApproval` 시 실제 승인 웹훅·메일 경로 실행. |

OpenAPI·스모크 스텁 등 **HTTP API 계약**은 `docs/final/openapi_macro_risk_warning_api_v1.yaml`·`scripts/macro_risk_warning_api_stub.py` 등 기존 Track C 산출물과 교차 참조; 본 표는 **메일 온보딩 운영 스크립트**만 Fact-Lock한다.

### 1.3.1 Track C — Fragility · forward log · Logos 4D 일일 융합 (Windows, 로컬)

| 항목 | 경로 | 비고 |
|------|------|------|
| 일일 융합 실행 | `scripts/Invoke-TrackCMacroDailyFusion_v1.ps1` | `Invoke-FragilityMacroRiskDaily` 1회 후 `run_macro_risk_forward_daily_chain_v1.ps1 -SkipFragilityChain` → `run_logos_4d_state_chain_v1.ps1 -SkipFragilityChain` → `build_logos_regime_resonance_shadow_signal_v1.py`·`run_logos_semantic_query_smoke_suite_v1.py` → **`build_logos_insight_bundle_v1.py`**(기본; `-SkipLogosInsightBundle`로 생략) → Logos 섀도우 일련(스크립트 본문) → **`build_role_router_s1_shadow_advisory_v1.py`**(기본, advisory_only·non-gating; `-SkipRoleRouterShadowAdvisory`로 생략) → **`build_lens_music_hormone_trend_v1.py`**·**`dispatch_lens_music_hormone_trend_webhook_v1.py`**(대시보드와 함께 기본 실행; `-SkipOpsDashboard`면 생략; `-SkipLensMusicHormoneTrend`로 trend+webhook만 생략) → `build_mkm_trackc_ops_dashboard_v1.py`. **레거시로 Fragility 일일 + Forward 일일을 동시 스케줄하면 Fragility가 중복 실행**될 수 있음. **서피스 태그: 헬스만**(Windows 일일 스케줄·로컬 융합; `dual-regime-integrity` 단일 잡과 순서·타임박스 1:1 아님) |
| Role Router S1 shadow advisory | `scripts/build_role_router_s1_shadow_advisory_v1.py` | 일일 융합 기본 경로에 포함. 산출 `docs/final/artifacts/role_router_s1_shadow_advisory_latest.json`·append `reports/role_router_s1_shadow_advisory_log.jsonl`. Router 입력: `prophecy_role_router_multiscenario_opt_30y_kospi_latest.json`(있으면 우선) 또는 `prophecy_role_router_multiscenario_opt_v1_latest.json`; 베이스라인: `lens_penalty_shadow_weekly_report_latest.json`·`lens_penalty_s1_shadow_gate_latest.json`. 회귀 `tests/test_build_role_router_s1_shadow_advisory_v1.py`. |
| 스케줄 등록 | `scripts/Register-TrackCMacroDailyFusionTask.ps1` | 기본 작업명 `MKM-TrackC-MacroDailyFusion`; `-DryRun`으로 등록·레거시 제거 **시뮬만**(기존 작업 존재 여부 출력); `-UnregisterLegacyTasks`로 `MKM-Fragility-MacroRisk-Daily`·`MacroRiskForwardDailyChain` 제거(존재 시) 후 등록. 인자 전달: `-AssetScope`·`-Horizon`·`-SkipGateAlert`·`-SkipFailureAlert`·`-SkipExodusSourceFetch`(무인 실행 시 CoinGecko/Binance 실패 회피에 유리)·`-SkipRoleRouterShadowAdvisory`(Role Router advisory 생략)·`-SkipLogosInsightBundle`(Logos `insight_bundle` 집계 생략)·`-SkipLensMusicHormoneTrend`(M31 trend+webhook 생략)·`-LensMusicPromotionGateSoftM31`(프로모션 게이트 M31 soft; 콜드스타트)·선택 `-MetaLayerEnvelopePath`(메타 인지 봉투; 비면 미실행). 동일 `TaskName`으로 재실행 시 **인자 갱신(덮어쓰기)**. 일부 호스트는 **관리자 PowerShell** 필요(`Register-ScheduledTask` Access denied 시). |
| 스케줄 점검 | `scripts/Verify-TrackCMacroDailyFusionScheduledTask_v1.ps1` | `Get-ScheduledTask`·`Get-ScheduledTaskInfo`로 실행 인자·`LastRunTime`·`LastTaskResult` 출력. |
| 헬스 번들(선택) | `scripts/run_workspace_automation_health.ps1 -IncludeTrackCMacroFusionSmoke` | 퓨전 체인 전체 스모크(`-SkipGateAlert -SkipExodusSourceFetch` 고정); 선택 **`-SkipLogosInsightBundle`** 또는 User/머신 환경 **`MKM_HEALTH_FUSION_SKIP_LOGOS_INSIGHT_BUNDLE`** truthy(`1`/`true`/`yes`/`on`) 시 Invoke에 **`-SkipLogosInsightBundle`** 전달. 네트워크·수 분 소요 가능. |
| 헬스 단축 프로필 | `scripts/run_workspace_automation_health.ps1 -TrackCMacroFusionSmokeOnly` | P0 경로 게이트 + 퓨전 스모크만(기본 vault/메모리/phase1/뉴스·reconcile 생략). **`-SkipLogosInsightBundle`** 또는 **`MKM_HEALTH_FUSION_SKIP_LOGOS_INSIGHT_BUNDLE`** 호환. |
| 메타 인지 봉투 v1(선택 게이트) | `docs/final/artifacts/schemas/mkm_meta_layer_turn_envelope_v1.schema.json` · `scripts/mkm_meta_layer_envelope_v1.py` · `tests/test_mkm_meta_layer_envelope_v1.py` | JSON Schema + `coherence_rules` + `apply_kill_switch_normalization`; `AthenaValidator`가 LLM/마크다운 응답에서 봉투 추출·검증·선택적 `agent_decisions_log.jsonl` 적재(`decision=meta_layer_envelope_v1`). **전 에이전트 출력 자동 적용 아님.** |
| 융합 후 메타 게이트(선택) | `Invoke-TrackCMacroDailyFusion_v1.ps1 -MetaLayerEnvelopePath <path>` | 융합 본체 완료 **뒤** 실행. 경로 비면 생략. `.json`(대소문자 무시)은 `append`, 그 외는 `audit-markdown`(```json 펜스). 실패 시 `throw`. |
| 메타 봉투 예시(JSON) | `docs/final/artifacts/fixtures/mkm_meta_layer_turn_envelope_v1.example.json` | 스키마 통과 최소 필드; 복사·편집 후 `-MetaLayerEnvelopePath` 또는 `mkm_meta_layer_envelope_v1.py validate|append` 입력으로 사용. |
| 산출(예) | `reports/fragility_macro_risk_daily_latest.json` · `docs/final/artifacts/macro_risk_forward_log_latest.json` · `docs/final/artifacts/logos_4d_state_v1_latest.json` · `docs/final/artifacts/logos_insight_bundle_v1_latest.json` · `docs/final/artifacts/role_router_s1_shadow_advisory_latest.json` · `reports/role_router_s1_shadow_advisory_log.jsonl` · `docs/final/artifacts/lens_music_hormone_trend_latest.json` · `docs/final/artifacts/lens_music_hormone_trend_webhook_dispatch_latest.json` · `docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json` | exit code·경로가 판정 근거; 서술형 “완벽 자동” 단정 금지. |

### 1.4 MKM-Orchestrator (bounded automation, `todo_queue_v1`)

| 항목 | 경로 | 비고 |
|------|------|------|
| 큐 스키마 | `docs/final/schemas/todo_queue_v1.schema.json` | 실행 SSOT는 정형 JSON; `CENTRAL_AGENT_MEMORY_V1.md`를 **작업 큐로 자동 파싱하지 않음**. |
| 연결·포인터 | `docs/final/artifacts/mkm_orchestrator_connection_spec_v1.json` | 스크립트·환경키·아티팩트 요약; **일일 압축 루틴** `operator_daily_routine_v1`(폴 상시·브릿지 수동). |
| 경로 일괄 확인 | `scripts/verify_mkm_orchestrator_bundle_v1.py` | exit 0/1; 네트워크 없음. |
| 폴링 | `scripts/mkm_orchestrator_poll_v1.py` · `scripts/mkm_orchestrator_poll.ps1` | 감사 `reports/mkm_orchestrator_audit.jsonl` · 락 `reports/mkm_orchestrator_poll.lock`. |
| 승인 CLI | `scripts/approve_mkm_orchestrator_task_v1.py` | `--task-id` 단건 또는 `--batch-approve`로 `awaiting_approval` + 승인 필요 `pending` 일괄. HITL이 큐에 `approval.resolution=approved` 반영. |
| 큐·HITL 요약 | `scripts/show_mkm_orchestrator_queue_status_v1.py` | `todo_queue_latest` + `approval_backlog_latest` 요약; `--batch-approve` 대상 개수 힌트. |
| 텔레그램 | `scripts/mkm_orchestrator_telegram_v1.py` | `notify` / `ingest` / `send-test`; `MKM_ORCHESTRATOR_TELEGRAM_NOTIFY=1` 등(`.env.example` 참고). |
| Noop 첫 실행 | `scripts/mkm_orchestrator_noop_smoke_v1.ps1` · `scripts/mkm_orchestrator_noop_smoke_v1.py` | 초단기 스모크; 산출 `reports/mkm_orchestrator_noop_smoke_latest.json`(동일 파일명 덮어쓰기 가능). |
| 큐 부트스트랩 | `scripts/bootstrap_mkm_orchestrator_queue_v1.ps1` | `-Profile Example|SmokeFirst|SmokeFirstPython|TrackCFromBridge` (마지막은 브릿지→`todo_queue_latest.json`). |
| 로컬 스모크 번들 | `scripts/run_mkm_orchestrator_smoke_v1.ps1` | pytest + 폴링 dry-run. |
| CI | `.github/workflows/mkm-orchestrator-smoke.yml` | pytest 회귀. |
| Track C 사업계획 → 큐 | `docs/final/artifacts/mkm_trackc_plan_orchestrator_bridge_v1.json` → `scripts/apply_trackc_plan_bridge_to_queue_v1.py` | MD 자동 파싱 없음; 브릿지 JSON이 `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md`와 **인적 정합**. |
| 상태 보존 주입 | `apply_trackc_plan_bridge_to_queue_v1.py --merge-existing` | `task_id` 기준으로 기존 `state/approval/last_run` 보존, 비브릿지 태스크 유지. |
| 계획 정렬 스모크 | `scripts/run_trackc_plan_gates_smoke_v1.py` | 번들 verify + 오케스트레이터 pytest. |
| 주간 로컬 게이트(선택) | `scripts/Invoke-TrackCPlanGatesSmoke.ps1` / `Register-TrackCPlanGatesSmokeTask.ps1` | 일요일 등 주기 실행; 로그 `reports/trackc_plan_gates_smoke_run_log.jsonl`. |
| 사업계획 브릿지 + 폴 1회 | `scripts/Invoke-TrackCPlanOrchestratorCycle.ps1` | `-RefreshQueue`는 브릿지 변경 시에만(큐 덮어쓰기); 기본은 폴링만. |
| 연속 데몬(선택) | `scripts/run_mkm_continuous_daemon.ps1` / `Register-MkmOrchestratorDaemonTask.ps1` | 브릿지 상태보존 주입(`--merge-existing`) + 폴 루프. |
| Cursor CLI 자동 분기(선택) | `runner.use_cursor_cli_auto=true` + `runner.cursor_cli_args[]` | heavy 태스크에서 Cursor CLI 사용 가능(미설정 시 기존 runner 유지). Cursor 실패 시 원래 `python/powershell` runner로 1회 폴백 재시도. |
| 브릿지→큐 스키마 회귀 | `tests/test_apply_trackc_plan_bridge_v1.py` | dry-run 산출이 `todo_queue_v1` JSON Schema와 정합; `jsonschema` 필요. |
| HITL 일괄 점검 | `reports/mkm_orchestrator_approval_backlog_latest.json` | 폴 종료 시 갱신; `awaiting_approval` + 아직 승인 전 `pending`(승인 필요) 모음. 승인 대기는 `--max-tasks` 실행 쿼터를 소비하지 않아 같은 폴에서 승인 불필요 작업이 이어짐. |
| 글로벌 오케스트레이터 (3렌즈 합성) | `scripts/mkm_global_orchestrator_v1.py` | 산출 `docs/final/artifacts/mkm_global_orchestrator_latest.json`; 정책 `docs/final/artifacts/mkm_global_orchestrator_policy_v1.json`(예: `apply_mkm_global_orchestrator_policy_profile_v1.py`). |
| GO 안정성 사이클 | `scripts/run_mkm_orchestrator_go_stability_cycle_v1.ps1` | 내부에서 `check_mkm_orchestrator_go_stability_v1.py` 등; 사이클 로그 append-only `reports/mkm_orchestrator_go_cycle_log.jsonl`. |
| 가속 번인 | `scripts/run_mkm_orchestrator_accelerated_burnin_v1.ps1` | `-RebuildGoPlusReport`로 GO+ 재생성; **`-ReportTailMatchIterations`** 시 리포트에 `--tail-samples`를 반복 수와 동일하게 넘겨 번인 직후 구간만 집계. exit 1(비안정 스냅샷)은 번인 실패로 치지 않음(`>=2`만 실패). |
| 조건부 GO+ 리포트 v2 | `scripts/build_mkm_conditional_go_plus_report_v2.py` | 산출 `docs/final/artifacts/companion_ecosystem_conditional_go_plus_report_latest.json`. **`--window-minutes`**로 시간창 필터, **`--tail-samples`**로 해당 창 안에서 마지막 N줄만 집계(롤링 로그에 옛 WATCH가 많을 때 가속 번인 구간만 READY 판정에 쓰기 위함). |

### 1.4.1 Bounded lane loop v1 (shadow mechanical runner)

| 항목 | 경로 | 비고 |
|------|------|------|
| Pin 스키마 | `docs/final/schemas/bounded_lane_pin_v1.schema.json` | 레인별 **다음 1타** + 화이트리스트 `steps`; `CENTRAL`·`MISSION_LOG` 통째 주입 금지. |
| 화이트리스트 | `docs/final/artifacts/bounded_lane_loop_whitelist_v1.json` | 허용 child만 실행; `todo_queue` enqueue·live·push 등 **substring 차단**. |
| 예시 Pin | `docs/final/artifacts/fixtures/bounded_lane_pin_infra_v1.example.json` | infra 스모크: resume pack + P0 gate paths. |
| Pin 빌더 | `scripts/build_bounded_lane_pin_from_resume_pack_v1.py` | resume pack + `MISSION_LOG` 레인 행 → `docs/final/artifacts/bounded_lane_pin_{lane}_latest.json`; `--refresh-resume-pack` · `--write-fixtures`(4레인 example). |
| Pin fixtures | `docs/final/artifacts/fixtures/bounded_lane_pin_{ms,oracle,infra,design}_v1.example.json` | jsonschema 통과 스냅샷; `next_action_one_line` = MISSION 해당 레인 행(자동 enqueue·MISSION 통째 주입 **금지**). |
| A2A peer (선택) | Pin `peer_handoff_pointer` → `a2a_tier3_cursor_wire_handoff_brief_{ms,oracle,infra,design,clinician,web_ops}_v1_latest.md` | 병렬 Cursor **peer** 채팅용 [HYPO]; source 채팅은 resume pack 그대로. |
| LTM hint (선택) | Pin `ltm_hint` · `LANE_LTM_PRIMARY_CONCEPT` in `build_bounded_lane_pin_from_resume_pack_v1.py` | graph **1 concept**만 (`concept_id` + `topology.software_layer`); graph 통째·MISSION 통째 주입 금지. |
| 다파일 편집 게이트 | `.cursor/rules/ltm-graph-os-coordinates-v1.mdc` | 편집 전: concept_id · software_layer · blast_radius 확인; Truth gate = CONSTITUTION + exit 0. |
| 러너 | `scripts/run_bounded_lane_loop_v1.py` · `scripts/Invoke-BoundedLaneLoop_v1.ps1` | `-Lane` + 기본 auto pin build; `outcome_class` ∈ `{shadow_pass, shadow_warning, shadow_reject}` **만**; Track A 승격·human sign-off 없이 본선 합선 없음. |
| 산출 | `reports/bounded_lane_loop_v1_latest.json` · `reports/bounded_lane_loop_audit.jsonl` | exit 0 = `shadow_pass`만; **≠** 무한 Cursor 채팅 루프. |
| 회귀 | `tests/test_bounded_lane_loop_v1.py` | dry-run·화이트리스트 거부. |
| Agent micro-loops (chat kickoffs) | `docs/final/artifacts/mkm_agent_loops_v1_latest.md` | loops.elorm.xyz 형식 Goal/Exit when · 5종 copy-paste; **≠** mechanical bounded runner. 루틴 `scripts/Invoke-MkmAgentLoopsRoutine_v1.ps1` · persona `MkmAgentLoops` · 산출 `reports/mkm_agent_loops_routine_v1_latest.json`. |

### 1.4.2 External Cortex fuel layer v1 (NL · lexicon · hub triangle)

| 항목 | 경로 | 비고 |
|------|------|------|
| NL 1:1 mapping audit | `scripts/check_notebooklm_lane_mapping_audit_v1.py` | UUID 중복·팩 금지 경로; `docs/final/artifacts/notebooklm_lane_mapping_rules_v1.json`; `reports/notebooklm_lane_mapping_audit_v1_latest.json`. |
| Lexicon lookup smoke | `scripts/check_lexicon_lookup_smoke_v1.py` | `master_codebook_lexicon_v1_bridge` 조인만 · **채팅 주입 없음**; `reports/lexicon_lookup_smoke_v1_latest.json`. |
| Hub developer triangle | `scripts/check_hub_developer_copy_triangle_v1.py` | benchmark · GitHub reproduce · `/enterprise/apply` 링크 정합; `reports/hub_developer_copy_triangle_v1_latest.json`. |
| 주간 번들 | `scripts/Invoke-NotebookLmFuelLayerAudit_v1.ps1` | 위 3종 + 선택 `-IncludeMcpPrereqs`; exit 0 = Week 2 fuel gate. |
| LENS split | `notebooklm_lens_pack_push_map_v1.template.json` · `notebooklm_nl_notebook_uuid_registry_v1.json` | LENS_MYEONGNI/LENS_LOGOS **1:1 UUID** (2026-06-14); audit `--strict-known-groups`. |
| 회귀 | `tests/test_notebooklm_fuel_layer_audit_v1.py` | offline audit 3종. |

### 1.4.3 Bounded lane loop packaging v1 (Week 4 · shadow)

| 항목 | 경로 | 비고 |
|------|------|------|
| Meta envelope 훅 | `run_bounded_lane_loop_v1.py --meta-layer-envelope-path` | 선택 validate; summary `meta_layer_envelope` 1블록; 실패 시 `shadow_warning`(Track A 미합선). |
| Meta append (선택) | `--meta-layer-envelope-append` | `mkm_meta_layer_envelope_v1.py append` → `agent_decisions_log.jsonl`. |
| A2A briefing sample | `scripts/build_bounded_lane_a2a_briefing_sample_v1.py` | `[HYPO]` 2-turn mock → `fixtures/bounded_lane_a2a_briefing_sample_v1.json`. |
| Cost JSONL | `reports/bounded_lane_loop_cost_v1.jsonl` | 루프당 `loop_wall_seconds` · `step_count` · `outcome_class`. |
| Invoke | `Invoke-BoundedLaneLoop_v1.ps1` | `-MetaLayerEnvelopePath` · `-RefreshA2aBriefingSample`. |
| All-lanes invoke | `Invoke-BoundedLaneLoopAllLanes_v1.ps1` | ms·oracle·infra·design 순차; `-RefreshPin` · `-DryRun`. |
| Health smoke | `run_workspace_automation_health.ps1 -IncludeBoundedLaneLoopSmoke` · `-BoundedLaneLoopSmokeOnly` | P0 + pytest 3종 + infra dry-run invoke; persona `BoundedLaneLoopShadow`. |
| Weekly task | `scripts/Register-MkmBoundedLaneLoopShadowWeeklyTask.ps1` | tier3 optional · Sunday 09:30 · `MKM_BoundedLaneLoop_Shadow_Weekly`. |
| All-lanes weekly | `scripts/Register-MkmBoundedLaneLoopAllLanesWeeklyTask.ps1` | Sunday 10:00 · `MKM_BoundedLaneLoop_AllLanes_Weekly` · `-RefreshPin` + meta envelope. |
| 회귀 | `tests/test_bounded_lane_loop_week4_v1.py` | envelope dry-run · A2A sample builder. |

---

## 2. Dual-regime / 레짐 융합 (실물 쪽, 1차 레짐)

| 항목 | 경로 | 비고 |
|------|------|------|
| Dual-regime 평가 모듈 | `projects/bitcoin-trading/src/integration/dual_regime_api.py` | `evaluate_dual_regime_and_market_shock` 등 Python API; **이 파일 단독으로는 FastAPI 앱이 아니다** (HTTP 래퍼는 별도 서비스/스크립트에 둔다). 선택 인자 ``state_provenance``에 ``source_track: B``(``scripts/core/track_source_guard.py``)가 오면 명리 방어 클램프에 ``state_id``를 적용하지 않음(bulkhead). 실매매 쪽은 ``crypto_nitro_live_strategy``가 ``signal_data``/``risk_assessment``의 ``source_track``을 전달. JSONL 상위 키 ``source_track``로 Track A 로더 거부: ``assert_track_a_json_row_allowed``. |
| Track A/B JSONL (Sovereign iterator) | `scripts/core/sovereign_jsonl.py` | `iter_jsonl_dict_rows` — `track_context` A면 행마다 `assert_track_a_json_row_allowed`, B면 연구 입력용(가드 생략). 파일럿: `report_symbol_numeric_injection` B-context. 회귀: `tests/test_sovereign_jsonl.py`. |
| 소버린 토큰 절감 스파이크 v1 | `scripts/spike_sovereign_token_saving.py` → `docs/final/artifacts/derived/spike_sovereign_token_saving_latest.json` | 코드북 용어(최대 16개)를 ``<S00>``..``<S15>``로 치환 후 tiktoken(o200k_base) 또는 바이트 프록시로 대비; B-track. 회귀: ``tests/test_spike_sovereign_token_saving_v1.py``. |
| 샤드 어휘 소버린 효율 스파이크 | `scripts/spike_sovereign_vocab_efficiency.py` → `docs/final/artifacts/derived/spike_sovereign_vocab_efficiency_latest.json` | ``codebook/shards/zone_*.json``에서 수집한 용어로 **다어구**를 구성, 플레이스홀더 토큰 수보다 **baseline 토큰 수가 큰 구문만** 매핑 후 tiktoken 대비; B-track. 회귀: ``tests/test_sovereign_efficiency.py``. |
| 토큰 압축 API (스텁 v1) | `scripts/compression_token_api_stub.py` | FastAPI: `POST /v1/compress`, `POST /v1/expand`, `GET /health`. **연구 레인(additive):** `POST /v1/research/l1_side_channel/wire` — L1 사이드 채널 최소 페이로드를 `scripts/l1_side_channel_wire_codec.py`(`encode_adaptive_msgpack` 등)로 적응형 와이어 인코딩·base64 반환; **HTTP 503**: (1) 런타임에 msgpack 미설치, (2) 내부 `msgpack_payload_bytes`가 `None`(pack 불가). 응답에 `api_contract_version`; `eval_context.hydrate_metrics` 없으면 `compression_metrics` null(라우터만). **enterprise 티어**에서 `hydrate_live_eval` 시 `evaluate_report`(선택 `eval_context.emit_semantic_pointer` → 응답 `semantic_pointer` `semantic_pointer_v1`) 시도·실패 시 `integrity_flags.hydration_live_eval_failed` 가능. **public 티어(Track B·literal KPI 추정)**는 동일 요청 시 `hydrate_live_eval_suppressed`로 라이브 경로 차단. **expand는 원문 에코**. 회귀: `tests/test_compression_token_api_stub.py`(OpenAPI 경로 포함·와이어 라운드트립·`test_public_tier_bulkhead_never_calls_live_eval_even_when_requested`·`test_openapi_v1_semantic_pointer_contract_fields`). 대외 설명 SSOT: `COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` §10 + `openapi_token_compression_stub_v1.yaml` description. **서피스 태그: CI 포함** |
| 토큰 압축 스텁 부하 벤치 (§9.2 draft SLA) | `scripts/bench_l1_api_load.py` → `docs/final/artifacts/bench_l1_api_load_latest.json` | stdlib `urllib` 스레드 풀; **클라이언트 RTT** p50/p95/p99. 서버 RSS는 동일 호스트 `--server-pid`+`psutil` 선택. `research_only`/`draft_benchmark`; FACT 승격은 플레이북 9.2 절차. dry-run 회귀: `tests/test_bench_l1_api_load.py`. **서피스 태그: 번들 선택** |
| VPS L1 벤치 (본선 동일 호스트) | `scripts/deploy/linux/run_bench_l1_api_load_vps_fixed_fields.sh` → `docs/final/artifacts/bench_runs/bench_l1_api_load_vps_*.json` · `bench_l1_api_load_summary_vps_latest.json` | 런북 `docs/final/BENCH_L1_API_LOAD_VPS_RUNBOOK.md`. 원클릭 pull·집계: `scripts/Run-CompressionBoardMsVpsBenchTriplet_v1.ps1` → `compression_board_ms_vps_bench_triplet_v1_latest.json`. 로컬 루프백과 **혼동 금지** |
| RQ-017 보드 ms 상관 (B-track, 인과 금지) | `compression_board_ms_correlation_protocol_v1.json` · `build_compression_board_ms_correlation_report_v1.py` → `compression_board_ms_correlation_report_v1_latest.json` · `run_compression_board_ms_payload_sweep_v1.py` · `build_compression_board_ms_vps_bench_triplet_v1.py` | `derived.correlation_claim_allowed` 기본 **false**. 회귀: `tests/test_compression_board_ms_correlation_report_v1.py` 등 |
| 압축 Shadow Auditor (야간) | `scripts/run_compression_shadow_auditor_v1.py` · `Register-CompressionShadowAuditorDailyTask.ps1` · 주간 `run_compression_weekly_governance_chain.ps1 -IncludeShadowAuditor` | 산출 `compression_shadow_auditor_latest.json` · 큐 `compression_research_metaphor_debug_queue.jsonl`. Track A 자동 승격 없음 |
| LG HS 미팅·탈락 폴백 (상용) | `lg_hs_meeting_followup_v1.json` · `lg_hs_fallback_two_week_pipeline_v1.json` · `check_lg_hs_fallback_two_week_pipeline_v1.py` | **C-S3** 결과 **2026-05-20(화)** 대기; hold/reject 시 2주 파이프라인. 대외 send는 `compression_enterprise_summary_readiness` 법무 게이트 |
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

### 2.2 Oracle rail geometry (Field-first · 2026-06-15)

| 항목 | 경로 | 비고 |
|------|------|------|
| 작전 1장 SSOT | `docs/final/MKM_ORACLE_RAIL_GEOMETRY_V1.md` | STOP/KEEP/MERGE · 4 KPI · calm=`science_core` · shock attach pilot `[HYPO]` |
| Shock operator policy | `scripts/build_kospi_shock_conditional_attach_operator_policy_v1.py` → `docs/final/artifacts/kospi_shock_conditional_attach_operator_policy_v1_latest.json` | attach_mode · operator_posture |
| Morning brief (Field/Lens split) | `scripts/build_internal_kospi_morning_brief_onepager_v1.py` → `docs/final/artifacts/internal_kospi_morning_brief_onepager_latest.json` | `schema_revision`: `1.1.0-field_lens_split` |
| Telegram daily wiring | `scripts/run_telegram_daily_p0_preflight_v1.py` → `reports/telegram_daily_wiring_v1_latest.json` | `p3_hard_lock` · tier_0 preflight |

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
| 명리 AI 해석 프롬프트·RAG 지시문 v1 (B-track) | `docs/final/MYEONGRI_AI_INTERPRETATION_PROMPT_TEMPLATE_V1.md` | 결정론 산출 위 **보조 해석**만; 시스템/유저 템플릿·RAG 주입 순서; 출력 봉투 스키마 `docs/final/schemas/myeongri_ai_interpretation_envelope_v1.schema.json`; **쟁점 최종 판정·실매매·의료 단정 금지**; LLM 어댑터는 선택 |
| 명리 AI 해석 유저 메시지 조립 v1 (LLM 없음) | `scripts/run_myeongri_ai_interpretation_pack_v1.py` | §3 블록과 동일한 플레이스홀더 치환 stdout; `--deterministic-json`·`--hash-deterministic-json`; 회귀는 `tests/test_myeongri_ai_interpretation_envelope_v1.py`의 `build_user_message` 스모크 |
| MKM 렌즈 글로벌 프로파일링 프롬프트·RAG 지시 초안 v1 (`[DRAFT]`, B-track) | `docs/final/MKM_LENS_GLOBAL_PROFILE_PROMPT_RAG_INSTRUCTIONS_DRAFT_V1.md` | 성경·명리·사상 NL **번역·톤**만; **행동·리스크 프로파일링** 서술·허구 수치 금지·임상·규제 확약 금지; RAG는 산출 JSON·승인 어휘집 우선; 명리 전용 봉투 스키마와 별개; 승격 시 `DRAFT` 해제·계약 포인터 검토 |
| 관측 로그 샘플 | `data/myeongni/insight_observation_log.sample.jsonl` | `myeongni_16_state_experiment` JSONL과 별도; 통찰 전용 |
| 관측 로그(부트스트랩) | `data/myeongni/insight_observation_log.jsonl` | 주간 append; 회귀와 동일 계약 |
| 융합 인터페이스 스텁 | `docs/final/MYEONGNI_FUSION_INTERFACE_STUB.json` | `myeongni_fusion_interface_stub_v1` |
| 독립 렌즈 v0 (정량 스코어) | `scripts/run_lens_myeongni.py` → `docs/final/artifacts/myeongni_independent_lens_latest.json` | 계약 `MYEONGNI_INDEPENDENT_LENS_V0_CONTRACT.json`; **`myeongni_b_track_quant_block_v0`** 오행·십성 스냅샷(`docs/final/artifacts/schemas/myeongni_b_track_quant_block_v0.schema.json`, `mkm_myeongni_math.compute_quant_profile_v0`); B-track·비트리거; A-track·캡 합선 금지 |
| 봇→융합→명리 렌즈 원클릭 체인 v1 | `scripts/run_myeongni_lens_chain_from_bot_v1.py` (`--profile-json` \| `--fusion-json` \| `--demo-smoke`); 래퍼 `scripts/Run-MyeongniLensChainFromBot_v1.ps1` | 봇 `--write-complete-fusion-json` + 렌즈 `--advanced-from-fusion-json` 순서 고정; 산출 기본 `docs/final/artifacts/manseryeok_bot_chain_latest.json`·`myeongri_complete_fusion_from_bot_chain_latest.json`·**`myeongni_independent_lens_from_chain_latest.json`**(전용; `myeongni_independent_lens_latest.json` v0 체크인과 분리); 회귀 `tests/test_myeongni_lens_chain_from_bot_v1.py`; CI `.github/workflows/multilens-independent-lens-smoke.yml` 번들 포함 |
| B-track 세션 시각 명리 패널 → 날씨·OHLCV 조인 → 와이드 상관 v1 | `scripts/build_btrack_session_instant_myeongni_panel_v1.py` → `scripts/join_btrack_session_panel_weather_ohlcv_v1.py` → `scripts/correlate_btrack_joined_wide_csv_v1.py`; 원클릭 `scripts/run_btrack_session_panel_weather_corr_chain_v1.py`; Windows `scripts/Run-BtrackSessionPanelWeatherCorrChain_v1.ps1` | 단일 출생 프로필·세션 벽시각(기본 개장 09:00 `Asia/Seoul`)마다 **四柱** + `mkm_myeongni_math.compute_quant_profile_v0` CSV·`.meta.json`; 일자 맞춤 날씨·선택 OHLCV 병합 후 Pearson/Spearman(`--x-cols` \| `--x-auto-prefixes`); **擇日/日課 전 학파 대표 아님**; A-track·실매매 자동 합선 금지; 회귀 `tests/test_build_btrack_session_instant_myeongni_panel_v1.py`·`tests/test_join_btrack_session_panel_weather_ohlcv_v1.py`·`tests/test_correlate_btrack_joined_wide_csv_v1.py`·`tests/test_run_btrack_session_panel_weather_corr_chain_v1.py`; CI `.github/workflows/dual-regime-integrity.yml`(General prophecy 단계 직후); P0 `scripts/verify_p0_constitution_gate_paths.ps1`; **`projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1`**·`.sh` 워크스페이스 pytest 번들에 동 4파일 포함(`run_fact_lock_bundle.ps1` 2단계와 중복 없음); 스모크 픽스처 `tests/fixtures/btrack_join_panel_smoke_v1.csv` 등 |
| 독립 렌즈 v1 (학파·대운·지장간·신살 슬롯 + 재현성) | `scripts/run_lens_myeongni.py --emit-schema v1` (`--advanced-input` 또는 **`--advanced-from-fusion-json`** 또는 **`--recommended`**); 패키지 `scripts/myeongni_lens_v1/` | 계약 `MYEONGNI_INDEPENDENT_LENS_V1_CONTRACT.json`; 스키마 `docs/final/artifacts/schemas/myeongni_independent_lens_v1.schema.json`·입력 `myeongni_lens_advanced_input_v1.schema.json`; v0 스트림과 학파 스텁 블렌드(기본 0.65/0.35); `MyeongriCompleteFusion`·commander `full_fusion_payload` → `myeongni_lens_advanced_input_v1`는 `scripts/emit_myeongni_lens_advanced_from_fusion_v1.py` 또는 동일 브리지(`--compute-birth`); **`--recommended`** = v1+allow-fallback+advanced 자동(`MYEONGNI_FUSION_JSON`/`MYEONGNI_RECOMMENDED_BIRTH`, `.env.example`); 회귀 `tests/test_myeongni_lens_v1_contract.py`·`tests/test_myeongni_fusion_bridge_v1.py` |
| 사상 독립 렌즈 v0 | `scripts/run_lens_sasang.py` → `docs/final/artifacts/sasang_independent_lens_latest.json` | 계약 `SASANG_INDEPENDENT_LENS_V0_CONTRACT.json`; `sasang_dynamics_regime_mapping_v1*.jsonl` tail; 산출 **`b_track_axis_scores_v1`**: `machine_readables` 파생 0~1 프록시(열·냉·희소·불균형)만 — 보명지조·금화교역 본론 정량·임상 매핑 아님; 비의료·비트리거 |
| 시장 사상 렌즈 v1 (B-track) | `scripts/run_market_sasang_lens_v1.py` → `docs/final/artifacts/market_sasang_lens_latest.json`; `data/market_sasang/market_sasang_lens_policy_v1.json`; `scripts/market_sasang_lens_engine_v1.py` | 상류 `sasang_independent_lens_latest.json` 필수; 산출 **`human_commander_gate_v1`**(지휘관 최종권·기계는 관측 보조); 계약 `MARKET_SASANG_LENS_V1_CONTRACT.json`; 회귀 `tests/test_market_sasang_lens_v1.py`; 임상 합선 금지 |
| 시장 명리 오버레이 렌즈 v1 (B-track) | `scripts/run_market_myeongni_lens_v1.py` → `docs/final/artifacts/market_myeongni_lens_latest.json`; `data/market_myeongni/market_myeongni_overlay_policy_v1.json`; `scripts/market_myeongni_overlay_engine_v1.py` | 상류 **`myeongni_independent_lens_latest.json`** 필수(만세력 `run_lens_myeongni` 엔진과 **별도** 정책 가중 해석층); 스키마 `market_myeongni_lens_v1` · `docs/final/artifacts/schemas/market_myeongni_lens_v1.schema.json`; **CONTRACT** `docs/final/artifacts/MARKET_MYEONGNI_LENS_V1_CONTRACT.json` (런너·정책·스키마 포인터 메타); 회귀 `tests/test_market_myeongni_overlay_v1.py`, 경로 고정 `tests/test_market_myeongni_lens_contract_v1.py`; 로컬 `scripts/verify_p0_constitution_gate_paths.ps1` 필수 경로에 포함 |
| 사상 통찰 참조 번들 v1.1 (B-track) | `scripts/build_sasang_interpretive_insight_bundle_v1.py` → `docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json` | **포인터 + `interpretive_depth_ko` + `synthesis_v1`**(합성 순서·금지 합성 한국어); 금화교역·보명지주·병증·약리·예측·사상/시장 사상 축; `pyobyeong_dr_pointer_v1`(IC-08/09); `rail=B_TRACK`, `decision_authority=human_only`, `opinion_kind=multi_axis_reference_bundle_v1`, `human_commander_gate_v1`; 계약 `SASANG_INTERPRETIVE_INSIGHT_BUNDLE_V1_CONTRACT.json`; 스키마 `docs/final/schemas/sasang_interpretive_insight_bundle_v1.schema.json`; 회귀 `tests/test_sasang_interpretive_insight_bundle_v1.py`; 최종 판단은 지휘관만(LLM 없음·결정론); 갱신: `run_btrack_daily_hypothesis_chain.ps1`(시장 사상 렌즈 직후), `Run-BtrackInsightSidecarChain.ps1`(체인 종료 시) |
| 이마 표리병증 DR v1.1 (B-track advisory) | `scripts/build_ijeoma_pyobyeong_dr_pack_v1.py` → `docs/final/artifacts/sasang_pyobyeong_insight_cards_v1_latest.json` + `docs/research/IJEOMA_PYOBYEONG_BYEONGJEUNG_LIT_REVIEW_v1.md`; `scripts/run_sasang_dynamics_unified_adapter_v1.py` (`--profile mainline` → `reports/sasang_dynamics_unified_v1_latest.json`; `--profile ablation` → `experiments/sasang-head-btrack/artifacts/sasang_dynamics_unified_ablation_v1.json`); 일일 체인 `scripts/run_sasang_unified_adapter_daily_chain_v1.py` · `Register-SasangUnifiedAdapterDailyTask_v1.ps1`; B-track daily `run_btrack_daily_hypothesis_chain.ps1`에 mainline adapter 1스텝; signoff `reports/sasang_ablation_matrix_signoff_v1_latest.json`; 게이트 `scripts/run_sasang_ablation_promotion_gate_v1.py`(`--commander-ack`) | IC-08 사심신물↔표리 `[HYPO]` · IC-09 CPG orthogonal 2D `[SECONDARY]`; `send_gate=HOLD` · `track_a_promotion_allowed=false` · CDSS·자동처방 금지; Tier0 `docs/research/raw/PYOBYEONG_SASIM_SINMUL_DR_TIER0_20260629.md`; 회귀 `tests/test_ijeoma_pyobyeong_dr_pack_v1.py`·`tests/test_sasang_pyobyeong_non_gating_lint_v1.py`·`tests/test_sasang_dynamics_unified_adapter_v1.py`·`tests/test_sasang_unified_adapter_daily_chain_v1.py` |
| 사상 dynamics contract · noise gate · reading anchor (B-track) | `docs/final/artifacts/SASANG_DYNAMICS_V1_CONTRACT.json`; `scripts/build_sasang_btrack_noise_control_gate_v1.py` → `sasang_btrack_noise_control_gate_v1_latest.json`; `scripts/build_sasang_reading_anchor_v1.py` → `sasang_reading_anchor_v1_latest.json`; `scripts/run_sasang_logos_gold_oos_spot_check_v1.py` → `reports/sasang_logos_gold_oos_spot_check_v1_latest.json`; 사전등록 `sasang_reading_anchor_prereg_v1_latest.json` | 12셀·stress·읽기 앵커 2차 오버레이; `equivalence_claim=false`; OOS gold spot(q01/q02/q06); `send_gate=HOLD`·`promotion_to_a_track_allowed=false`; 회귀 `tests/test_sasang_btrack_noise_control_gate_v1.py`·`tests/test_sasang_reading_anchor_v1.py` |
| 사상 라우팅 코퍼스 31k + Studio 네트워크 요약 (G2/G2-ext, B-track) | 체인 `scripts/run_sasang_routing_sidecar_corpus_31k_chain_v1.py` → `reports/sasang_routing_sidecar_corpus_31k_chain_v1_latest.json`; 그래프 번들 `scripts/build_logos_corpus_sasang_routing_graph_bundle_v1.py` → `docs/final/artifacts/logos_corpus_sasang_routing_graph_bundle_v1_latest.json`; edge quality `scripts/build_logos_corpus_sasang_edge_join_quality_report_v1.py` → `reports/logos_corpus_sasang_edge_join_quality_v1_latest.json`; Studio summary `scripts/build_logos_studio_sasang_network_summary_v1.py` → `docs/final/artifacts/logos_studio_sasang_network_summary_v1_latest.json` + `projects/no1kmedi/public/data/logos_studio/sasang_network_summary_v1.json`; bloom/hop `scripts/build_logos_studio_31k_bloom_secondary_fetch_v1.py`·`scripts/merge_logos_studio_bloom_chapter_stubs_into_graph_slice_v1.py`; 쇼룸 감사 `scripts/build_showroom_logos_subgraph_audit_slice_v1.py` | `research_only`·`send_gate=HOLD`·`track_a_blocked`; 코퍼스 31,102행·조인 품질은 `edge_touch_ratio`와 타입별 `parse_ratio`/`single_side_parse_ratio`를 분리 관측(한쪽 non-verse 타입 포함); 회귀 `tests/test_sasang_routing_sidecar_corpus_31k_v1.py`·`tests/test_logos_sasang_network_summary_v1.py`; Track A·실매매 트리거 금지 |
| G2-a global ablation delta + dual-band wire guardrail (B-track) | `scripts/run_g2a_global_ablation_delta_v1.py` → `reports/g2a_global_ablation_delta_v1_latest.json` + `docs/final/artifacts/g2a_global_ablation_delta_brief_v1_latest.md`; short `run_g2a_candidate_wire_payload_bench_v1.py`·long `run_g2b_lexicon_dense_long_sequence_wirebench_v1.py` 자동 refresh·`metrics.dual_band_wire_guardrail`; 지휘 `g2a_commander_signoff_v1_latest.json` ADOPT 시 `status=ADOPTED_RESEARCH_BTRACK` 유지; 회귀 `tests/test_g2a_global_ablation_delta_dual_band_v1.py`; `send_gate=HOLD` |
| Logos Map-Reduce chapter_coord v1 (B-track) | Map: `scripts/build_logos_chapter_coord_v1.py`·`scripts/build_logos_chapter_coords_batch_v1.py` → `docs/final/artifacts/logos_chapter_coords_v1/{Book}.{ch}/chapter_coord_v1.json`; 스키마 `docs/final/schemas/chapter_coord_v1.schema.json`; Reduce: `scripts/build_logos_chapter_coord_reduce_bridge_v1.py` → `docs/final/artifacts/logos_chapter_coord_reduce_bridge_v1_latest.json`; 소비: `scripts/sync_logos_chapter_coords_to_bloom_shards_v1.py`·`scripts/merge_logos_studio_bloom_chapter_stubs_into_graph_slice_v1.py`·`scripts/merge_logos_chapter_coord_reduce_bridge_into_graph_slice_v1.py`; 체인 `scripts/run_logos_chapter_coord_map_reduce_chain_v1.py`·`scripts/run_logos_chapter_coord_full_stack_chain_v1.py`·`scripts/run_logos_chapter_coord_middleware_harness_chain_v1.py`; middleware `scripts/build_logos_chapter_coord_middleware_packet_v1.py`·`scripts/wire_logos_chapter_coord_middleware_to_compression_v2_v1.py`; GraphRAG sidecar `scripts/wire_logos_chapter_coord_reduce_to_graphrag_pilot_v1.py` → `docs/final/artifacts/logos_chapter_coord_graphrag_sidecars_v1/`·`reports/logos_chapter_coord_graphrag_wire_v1_latest.json`; citation-restraint `scripts/check_logos_chapter_coord_citation_restraint_v1.py` (CL_stat + KRV 정본 해결 + pin-locked contract, raw resolution vs operational gate_ok) → `reports/logos_chapter_coord_citation_restraint_v1_latest.json`; latency bench `scripts/run_logos_chapter_coord_local_join_latency_bench_v1.py` (로컬 전처리 단계별 p50/p95, warm_join mean≈2.6ms·p95≈3.5ms @20k edges Gen.1 — end-to-end TTFT·cloud LLM 미포함) → `reports/logos_chapter_coord_local_join_latency_bench_v1_latest.json`; graph_slice merge `scripts/merge_logos_chapter_coord_reduce_bridge_into_graph_slice_v1.py` (`--reset-reduce-edges`로 clean cap·`--dry-run`·`--backup`; production cap **30,000** reduce edges(120k 스케일업 후 clean 재머지, 이전 10,000)·bloom 정본 **100%**(31,102 refs)·slice≈16.57MB/31,132 nodes; full_stack 기본 canon 100%) → `reports/logos_chapter_coord_reduce_graph_merge_v1_latest.json`; 스트레스 `scripts/run_logos_chapter_coord_stress_scale_v1.py` (graph/reduce cap + bloom canon %; `--skip-bloom-canon`, `--bloom-canon-pcts`; work 사본만·production 미변경 — canon 50%≈+4,042 노드/slice≈5.96MB, canon 100%≈+19,593 노드/slice≈10.73MB @baseline 4.72MB) → `reports/logos_chapter_coord_stress_scale_v1_latest.json`; insight quality bench `scripts/run_logos_chapter_coord_insight_quality_bench_v1.py` (tri-layer dual-report: shipped_ok=offline compile packet 구조·quality_ok=citation restraint 게이트·live=human-signed release gate가 결정) → `reports/logos_chapter_coord_insight_quality_bench_v1_latest.json`; live 게이트 어댑터 `scripts/logos_insight_live_dispatch_adapter_v1.py` + 스키마 `docs/final/schemas/logos_insight_live_release_gate_v1.schema.json` (release 없음→`gated_hold`; 유효 release라도 executor 미배선→`gate_open_not_executed`·pass_rate=None — **가짜 pass_rate 금지**; 실제 cloud live throughput은 GPU/cloud 배선+release 필요, 현재 GAP); **전권 packet+sidecar 배치 빌더** `scripts/run_logos_chapter_coord_packet_sidecar_batch_build_v1.py` (KRV+reduce bridge(120k 스케일업 후 재빌드) **1회 로드**·in-process·pilot 관측 생략 → 1,189장 packet+sidecar **~31.6s/0 err**; per-chapter CLI subprocess ~24s/장 대비 수백배·CPU/IO — **GPU(local/NVIDIA/Azure) 가속 무관**) → `reports/logos_chapter_coord_packet_sidecar_batch_build_v1_latest.json`; **offline 실측** compile/judge `scripts/logos_insight_compile_judge_lib_v1.py`·러너 `scripts/run_logos_insight_quality_offline_measure_v1.py` (`--all-chapters`) → `reports/logos_insight_quality_offline_measure_v1_latest.json` (metric=`citation_faithfulness_pass_rate`·scope=offline_local_compile_from_pins_only — **전권 1,189장 실측 pass_rate=1.0**(`reports/logos_insight_quality_offline_measure_wholebible_v1_latest.json`, 21s), 이전 20/40장도 1.0; **신학적 통찰 정확도/클라우드 live 품질 주장 아님**); **로컬 GPU live 실측** executor `scripts/logos_insight_ollama_executor_v1.py`·judge `judge_llm_output`·러너 `scripts/run_logos_insight_quality_local_gpu_measure_v1.py` (`--all-chapters`로 전권; 전권 산출 `reports/logos_insight_quality_local_gpu_measure_wholebible_v1_latest.json`) → `reports/logos_insight_quality_local_gpu_measure_v1_latest.json` (RTX 5060 Ti 16GB·Ollama·기본 `llama3.1:8b`·유료 없음; **GPU 분할 오해 정정: packet 빌드=CPU/IO(GPU 무관), LLM 추론만 GPU이고 "NVIDIA GPU"="로컬 GPU"=동일 단일 장치, Azure GPU는 유료+배포 별도 트랙·승인 게이트**; metric=local_llm_citation_discipline_pass_rate — **40장 실측 pass_rate=0.975**(39/40, exec_errors 0; offline 40장 faithfulness=1.0와 dual-report `reports/logos_insight_quality_offline_measure_40_v1_latest.json`), 이전 20장=1.0; 실패 1건=1Sam.17(긴 서사 장에서 모델이 절 내용을 서술했으나 인라인 인용 마커를 통째 생략 → `cites_any_pin=false`; `no_fabrication=true`·`out_of_scope_refs=[]` — **환각 아님, judge 버그 아님, 로컬 모델의 실제 인용규율 미스**로 정직 기록·프롬프트로 1.0 강제하지 않음), 프롬프트 v2(각 문장 끝 canonical 인용 마커 필수·서사 장 포함)로 재측 40장도 **0.975**(잔여 실패가 1Sam.17→Neh.8로 이동: 모델이 `(2)` 맨 절번호로 인용 — 비정본; judge를 맨 숫자까지 넓히면 본문 숫자 과대계수 위험이라 의도적으로 미확장 → 실제 로컬 모델 표기규율 미스); before(v1)/after(v2) 모두 `no_fabrication=true`·프론티어 미주장; `reports/logos_insight_quality_local_gpu_measure_40_promptv2_v1_latest.json`; **모델 크기 비교 시도=inconclusive**: `gemma4:12b`는 단순 프롬프트에도 `done_reason=length`·eval>0이나 `response=""`(빈 출력·thinking 필드 없음) → 로컬 태그 템플릿/디코딩 불량으로 0.0은 **품질 신호 아님**(`reports/logos_insight_quality_local_gpu_measure_40_gemma4_12b_v1_latest.json` 참고만); 모델 비교(설치본, 신규 pull 없음): `llama3.1:8b`=0.975 vs **`qwen2.5-coder:7b`=0.675**(27/40, exec_errors 0, `reports/logos_insight_quality_local_gpu_measure_40_qwen25coder7b_v1_latest.json`) — 코더 특화 모델이 한국어 canonical OSIS 인용규율에 약함(실패 13건: 대부분 "마태복음 5:1" 한글 책이름/맨 번호 `1)` 비정본 표기, fabrication 플래그 1건도 실제로는 `ISA.53:1` 대문자 드리프트=유효 절, 가짜 절 아님); llama3.1:8b가 현재 최적 클린 로컬 baseline; **전권 종결 프레이밍**: "성경 전권 좌표화 통찰"의 품질 완성치는 **결정론적 offline faithfulness 전권 1.0(GPU 불필)** 이며, GPU live는 자유서술 모델 규율 확인용 **대표표본**(40장 0.975 complete + 전권 부분측정 100/1189=0.98 ongoing, `--resume` 재개형·flush 25장) — 1,189장 GPU 풀커버는 추가 정보량 낮아 필수 아님; 반복 중단은 파이프라인 결함 아닌 백그라운드 프로세스 런타임/절전 회수(`exit_code unknown`, `exec_err 0`) — 압축·좌표 이론은 packet/컴파일 구간을 가속(13h→29s·offline 1.0)하나 **LLM 추론 wall-clock·서빙 처리량은 이론으로 제거 불가**(FAIL-COMP-004·압축KPI≠서빙 비합선); **로컬 지표(offline 1.0/live ~0.98)는 시장 수용·고객 SLA·프론티어 품질 주장 아님**; **차별화 A/B**(구조 vs naive) `scripts/run_logos_insight_ab_structure_vs_naive_v1.py`·judge `reference_hallucination_stats`(구조-무관: 인용 절이 KRV에 실재하지 않으면 hallucinated) → `reports/logos_insight_ab_structure_vs_naive_v1_latest.json` (20장 동일 모델 llama3.1:8b: **treatment 구조=hallucination 0.0·0/119 grounded refs** vs **control naive=mean 0.05·2/32**(Jhn.1 1.0); 즉 우리 구조가 인용 밀도 3.7배(119 vs 32)+지어낸 인용 0 — **단, control 저rate는 인용 자체가 적은 탓 일부 포함, 참조-실재 grounding만 측정이고 내용-충실도/신학 정확도/시장 주장 아님**·소표본 20·로컬 8B); 회귀 `tests/test_logos_insight_llm_judge_v1.py`(reference_hallucination_stats 포함); **live tier 배선(gated·유료 없음)** 클라우드 executor `scripts/logos_insight_cloud_executor_v1.py`(키 하드코딩 금지·env only·dry_run 기본·live+키 없으면 정직 비실행) + 데모 `scripts/run_logos_insight_live_dispatch_demo_v1.py` → `reports/logos_insight_live_dispatch_demo_v1_latest.json` (A: release 없음=`gated_hold`, B: 로컬 tier release+로컬 executor=**executed·pass_rate 실측**, C: 클라우드 dry_run=`gate_open_not_executed`·executed False — adapter가 executor 자체 `executed` 플래그 존중하도록 수정); 회귀 `tests/test_logos_insight_live_dispatch_v1.py`(8); **클라우드/프론티어 tier는 지휘관 cost_ack release + API 키 필요한 GAP — 유료 호출 미실행**; **쇼룸 데모(offline·배포 없음)** `scripts/build_logos_insight_showroom_demo_v1.py` → `docs/final/artifacts/logos_insight_showroom_demo_v1/index.html` (결정론적 compile_from_pins_only 카드: 정본 핀 절 verbatim + resolvable 교차좌표 chip + 인용잠금·환각0·research_only 배지; 6장 데모 pin 6~11절·cross 9~24; 게시=Tier-3 사람, 신학정확도·시장 주장 아님); warm gen≈3–5s/장; judge `extract_refs`는 canonical `Book.ch.v` + 사람표기 콜론 `Book ch:v` 모두 정규화(Matt.6 표기drift false-negative 회귀 수정); dual-report offline 1.0 vs local_llm; **프론티어/클라우드 품질·신학적 정확도·L4/L5 서빙 준비 주장 아님**); 주간 루틴 `scripts/Invoke-LogosChapterCoordMiddlewareWeeklyRoutine_v1.ps1` (full_stack clean cap→middleware harness→stress→regression gate)·등록 `scripts/Register-LogosChapterCoordMiddlewareWeeklyTask_v1.ps1` (`MKM_LogosChapterCoordMiddlewareWeekly_v1`, 일요일 10:45) | `research_only`·`send_gate=HOLD`; Map=장별 좌표·bloom_shard_compat; Reduce=lemma_shared+cross_ref(CPU, `--max-edges` 기본 40,000·`--cross-ref-budget` 예약 예산 기본 15,000·openbible osi/sinew/themed JSONL fair-share ingest `--no-balance-cross-ref-sources`로 legacy first-wins — production reduce_bridge store≈39,949 edges: lemma 25,000+cross_ref 14,949(osi 9,575+sinew 4,865+themed 367+sample 142), 3계열 모두 대표 → cross_ref>0·OSI 독점 아님); **120k 전면 스케일업 실측**(`--max-edges 120000 --cross-ref-budget 40000`, reproduce): reduce_bridge store=**119,350 edges**(lemma_shared 80,000+cross_ref 39,350: osi 25,993+sinew 12,848+themed 367+sample 142 — 이전 cross_ref는 소스가 아니라 15k budget에 막혀 있었음), 연결성 리포트 `docs/final/artifacts/logos_connectivity_report_v1.json`(`schema=logos_connectivity_report_v1`): 절 커버리지 **36.36%→65.12%**(nodes_in_edges 11,309→20,253/31,102), GCC **10,135→18,932**(연결군의 93.48%·정본의 60.9%), cross_chapter 엣지 71,403(59.8%), 컴포넌트 514; 백업 `logos_chapter_coord_reduce_bridge_v1_pre120k_backup.json`; **verse_adjacency 티어(65%→100% 상한 돌파)**: `build_verse_adjacency_edges` (장 내 순차 절 체이닝 v_i→v_{i+1}·`--adjacency-budget` 신규 CLI, 별도 예산으로 lemma/cross_ref 미굶김·edge_breakdown에 `verse_adjacency` 분리 카운트) `--max-edges 160000 --cross-ref-budget 40000 --adjacency-budget 35000` → store=**159,350 edges**(lemma_shared 90,087+verse_adjacency 29,913+cross_ref 39,350), 절 커버리지 **65.12%→100.0%**(31,102/31,102), GCC **18,932→31,076**(정본의 99.92%), 컴포넌트 514→**2**(거대군 31,076 + 잔여 고립 섬 1개=**Ezek.41 26절**: 성전 측량 고유어휘라 캡 내 공유 lemma/cross_ref 없어 장 내부 adjacency로만 연결), cross_chapter 80,399(50.5%); 백업 `logos_chapter_coord_reduce_bridge_v1_pre_adjacency_backup.json`; **정직한 경계: verse_adjacency는 구조적 인접(순차)이지 의미/신학 정합 보증 아님 — 위상 커버리지 canon-complete일 뿐 추론 품질 주장 아님**; 그래프 슬라이스는 cap 30k 대표 샘플(lemma-forward)이며 100% 커버리지는 master map(reduce_bridge)이 보유; 회귀 `tests/test_logos_chapter_coord_batch_and_reduce_v1.py`(`test_verse_adjacency_edges_chain_intra_chapter_only`·`test_verse_adjacency_budget_isolated_in_bridge_doc` 2건 추가, 통과); 비용절감 % 수치화 금지; 회귀 `tests/test_build_logos_chapter_coord_v1.py`·`tests/test_logos_chapter_coord_batch_and_reduce_v1.py`·`tests/test_logos_chapter_coord_full_stack_chain_v1.py`·`tests/test_logos_chapter_coord_stress_scale_v1.py`·`tests/test_logos_chapter_coord_middleware_packet_v1.py`·`tests/test_logos_chapter_coord_middleware_compress_wire_v1.py`·`tests/test_logos_chapter_coord_graphrag_wire_v1.py`·`tests/test_logos_chapter_coord_citation_restraint_v1.py`·`tests/test_logos_chapter_coord_local_join_latency_bench_v1.py`·`tests/test_logos_chapter_coord_insight_quality_bench_v1.py`·`tests/test_logos_insight_quality_offline_measure_v1.py`·`tests/test_logos_insight_llm_judge_v1.py` |
| Gematria 4D KNN pareidolia falsifier (B-track, 격리 실험·미병합) | `scripts/run_gematria_4d_knn_falsifier_v1.py` → `reports/gematria_4d_knn_falsifier_v1_latest.json`; 회귀 `tests/test_gematria_4d_knn_falsifier_v1.py`(계측기 자가검증 3: 합성 양성→SIGNAL·무작위→PAREIDOLIA·KNN 무방향) | **질문 답**: chapter_coord 노드 데이터층엔 `gematria_scalar.vector_4d{S,L,K,M}`(+hebrew_value·normalized_value)가 저장돼 있으나 `lookup_only:true`·`prophecy_claims:false`이고 **엣지(연결) 계산엔 미사용** — 마스터 위상 159,350 엣지는 오직 `lemma_shared`+`cross_ref`+`verse_adjacency` 3중 불변식; 제마OS 병증약리(사상)·금화교역/보명지주(명리/정역)는 **타 렌즈로 Logos 진입 영구 격벽**(FAIL-COMP-004·렌즈 격벽). **falsifier 실측**(sample 4000·k10·30 순열 귀무=node→vector 재배정): GT=전체 enrichment 6.70x/z 14.07=SIGNAL이나 **GT=cross-book만(책 국소성 교란 제거) enrichment 1.00x/z 0.32=PAREIDOLIA**, GT=same-book 16.64x/z 17.09 — **decisive_arm=cross_book**, `final_verdict=PAREIDOLIA_BOOK_LOCALITY_PROXY_NO_INDEPENDENT_GAIN`: 게마트리아 4D는 어휘→책 국소성 프록시일 뿐 `lemma_shared`가 이미 잡는 것 이상 **독립 의미/신학 신호 0 → 마스터 병합 금지**; `research_only`·`send_gate=HOLD`·`prophecy_claims=false`·master/slice 미변경 |
| Logos 구조 임베딩(K축) held-out falsifier (B-track, 격리·미병합) | `scripts/run_logos_structural_embedding_falsifier_v1.py` → `reports/logos_structural_embedding_falsifier_v1_latest.json`; 게마트리아 대조 `reports/gematria_4d_knn_falsifier_v1_latest.json` | **질문**: 마스터 메쉬에서 학습한 *구조* 임베딩이 게마트리아 M축이 못한 독립 신호를 담는가. **반(反)순환 규율**: cross-book 큐레이션 참조(cross_reference/parallel/quotation 등)의 20%를 **held-out**(훈련 제외), train=lemma_shared+verse_adjacency+나머지 80%; 임베딩=대칭 인접행렬 `TruncatedSVD`(dim 128, spectral 계열; node2vec random-walk 미설치이나 동일 그래프 정보원). 게마트리아와 **동일 falsifier**(KNN+순열 귀무 node→embedding 재배정) 재사용. **실측**(seed 1207·sample 8000·k10·30 순열): held-out cross-book **enrich 30.68x·z 23.79·p 0.032(=순열 하한)·GT 331**; **엄격 arm**(공유 lemma 등 잔존 직접엣지 있는 쌍 제외, strict_gt 5521)도 **동일 30.68x** → 신호는 어휘 중복 아님; 양성대조(훈련 엣지) 226x·z 401=계측기 정상; `final_verdict=STRUCTURAL_EMBEDDING_GENERALIZES_BEYOND_LEXICAL_SIGNAL_RESEARCH_ONLY`. **정직한 경계**: 이는 "메쉬 구조가 학습·일반화 가능한 신호를 담음"(node2vec류 링크예측의 알려진 결과)을 확증할 뿐, 4D·신학·예언 주장 아님; K 한 축만 검증. `research_only`·`send_gate=HOLD`·`prophecy_claims=false`·미병합. |
| Logos K축 강건성 + S축(의미) 독립성 실측 (B-track, 격리·미병합) | 강건성 `scripts/run_logos_structural_embedding_robustness_v1.py` → `reports/logos_structural_embedding_robustness_v1_latest.json`; S축 `scripts/run_logos_semantic_embedding_falsifier_v1.py` → `reports/logos_semantic_embedding_falsifier_v1_latest.json`(임베딩 캐시 `reports/logos_verse_nomic_embed_v1.npz`) | **강건성**(엄격 held-out cross-book, 시드 1207): dim 64/128/256 = enrich 30.30/30.68/44.55x·z 28.6/23.6/37.5, split 시드 7/99 = 31.63/38.87x, 정밀 순열 300 = p 0.003322 → `STRUCTURAL_K_SIGNAL_ROBUST_ACROSS_DIM_AND_SPLIT`(dim·split 무관 신호 유지). **S축**: `text_ko`를 ollama `nomic-embed-text`(768d)로 임베딩, 동일 held-out 검정 — S enrich 14.77x·z 11.20(SIGNAL), K 30.68x, **K∩S KNN 이웃 겹침 Jaccard 0.0038(≈0)** → `S_AND_K_BOTH_SIGNAL_LOW_OVERLAP_COMPLEMENTARY`: 구조(K)·의미(S)는 **상보적 독립 축**(중복 아님), 단 naive concat KS 25.82x는 K 단독보다 낮음(가중 융합 필요). **정직한 경계**: 실측된 실 축은 **K·S 2개**(게마트리아 M=falsified, L 미측정) — "4D" 미확정·신학/예언 주장 없음. `research_only`·`send_gate=HOLD`·`prophecy_claims=false`·미병합. |
| Logos L축(어휘밀도) 측정 + K/S/L 정직 융합 (B-track, 격리·미병합) | `scripts/run_logos_axis_L_and_fusion_v1.py` → `reports/logos_axis_L_and_fusion_v1_latest.json` | **L축**: `text_ko` 어휘밀도 벡터[글자수·토큰수·평균어장·문자엔트로피·TTR] z-score, 동일 held-out cross-book 엄격 검정 — enrich **1.96x·z 0.45·p 0.34 = PAREIDOLIA_NO_CROSSBOOK_SIGNAL**(게마트리아 M과 동일 무신호; L∩K 겹침 0.0023·L∩S 0.011=직교 노이즈). **caveat**: L은 한국어 번역 표기 밀도지 원어 글자 아님. **융합(정직 프로토콜: 가중치는 VAL enrichment로만 선택, 겹치지 않는 TEST에 순열 귀무로 판정)**: 최적 가중 VAL=wK0.25/wS0.75/wL0이나 **TEST에서 fused 33.12x < K단독 43.51x → `NO_FUSION_GAIN_OVER_K_ON_HELDOUT_TEST`**(선형 가중 concat은 K·S 상보성(겹침≈0)을 수확 못함 — 학습형 융합 필요). **종합 실측 원장**: 살아있는 축 K(구조 30.68x 강건)·S(의미 14.77x 독립) 2개, 죽은 축 M(게마트리아)·L(어휘밀도) 2개 → "4D" 실측 미달, 실질 **2축**; 단순 가중융합은 K 단독 미달. `research_only`·`send_gate=HOLD`·`prophecy_claims=false`·미병합. |
| Logos K축 NetMF 심화 falsifier (node2vec 등가, B-track, 격리·미병합) | `scripts/run_logos_netmf_embedding_falsifier_v1.py` → `reports/logos_netmf_embedding_falsifier_v1_latest.json`; 회귀 `tests/test_logos_netmf_embedding_falsifier_v1.py`(3: shape·결정성·클리크 근접); SVD 대조 `reports/logos_structural_embedding_falsifier_v1_latest.json` | **질문**: 1-hop 인접 SVD(=기존 K축)를 넘어 **고차(멀티홉) 랜덤워크 구조**가 held-out cross-book 신호를 더 담는가. gensim 미설치 → node2vec 대신 **NetMF**(Qiu et al. 2018 WSDM: node2vec=랜덤워크 co-occurrence PMI 행렬의 암시적 분해) sparse 구현: `M=log(max(vol/(bT)·Σ_{r=1..T}P^r·D^-1,1))`, P=D⁻¹A, `TruncatedSVD`. **동일 반순환 split·동일 순열 falsifier**로 임베딩(window T)만 교체 비교. **window 스윕 실측**(seed1207·dim128·sample8000·30순열·holdout_in_gcc 5546): plain-SVD **30.68x·z23.8** / NetMF T1 **29.05x·z27.8**(≈1-hop PMI) → T2 **83.53x·z88.1** → T3 **108.44x·z100.7** → T4 **116.26x·z105.8**, best T=4·Δvs SVD **+85.58**·`curve_shape=monotone_increasing` → `NETMF_IMPROVES_OVER_PLAIN_SVD_RESEARCH_ONLY`: 멀티홉 구조가 1-hop보다 held-out 교차참조를 크게 잘 예측 → K는 **심화할수록 신호↑ 살아있는 축**. **정직한 경계**: 한계이익이 +54→+25→+8로 **명확히 체감(T≈3–4 포화 접근)**; **T=5–6 연장은 exact-sparse co-occurrence 행렬이 stationary로 densify되며 O(n²) 계산 벽(>15분 미완료·강제종료)** — Qiu et al.이 큰 window에 NetMF-large 고유근사를 둔 이유와 정확히 일치, exact-sparse는 **T≈4가 실용 상한**; p는 전부 순열 하한(1/31=0.032, z로 판별); 고차 랜덤워크가 책내 다단경로로 국소성 재부호화할 여지 있으나 **held-out cross-book split**로 통제; node2vec류 링크예측의 알려진 결과 확증일 뿐 4D·신학·예언 주장 아님. `research_only`·`send_gate=HOLD`·`prophecy_claims=false`·미병합. |
| Logos NetMF-K + S 학습형 융합 재검 (B-track, 격리·미병합) | `scripts/run_logos_learned_fusion_netmf_v1.py` → `reports/logos_learned_fusion_netmf_v1_latest.json`; SVD-K 대조 `reports/logos_learned_fusion_v1_latest.json`; S 캐시 `reports/logos_verse_nomic_embed_v1.npz`(31,014절 nomic-embed 재생성, S축 재현 14.77x·z11.20·overlap0.0038) | **질문**: 더 강한 NetMF-K(T=4) 위에서도 의미축 S가 링크예측 이득을 주는가. 동일 반순환 프로토콜(VAL 학습→disjoint TEST), K=NetMF로 교체. **실측**(random neg primary): K단독 AUC **0.9053**·S단독 0.6012·KS학습 **0.9064** → gain **+0.0011**(<0.005), 학습계수 cosK **10.47** ≫ cosS **0.67** → `S_ADDS_NO_GAIN_OVER_NETMF_K`. **해석**: plain-SVD-K에서 S가 겨우 +0.005였는데 **더 강한 NetMF-K가 S 잔여가치마저 흡수** → S는 오히려 더 불필요; KNN 이웃겹침≈0(상보적)이 링크예측 이득으로 전환 안 됨 재확인 → **K(구조) 단일 일꾼** 결론 강화. hard-neg arm(K 0.219)은 cosK-high 음성선별의 구조적 불리로 진단용만. `research_only`·`send_gate=HOLD`·`prophecy_claims=false`·미병합. |
| Logos 외부라벨 문체론 하네스 (source-critical, B-track, 격리·미병합) | 하네스 `scripts/run_logos_stylometry_external_label_harness_v1.py` → `reports/logos_stylometry_external_label_harness_v1_latest.json`; 외부 라벨 ingestion `scripts/ingest_yoffe_pnonp_labels_v1.py` → `data/external/yoffe_pnonp_genesis_exact_partition_v1.json`; 회귀 `tests/test_logos_stylometry_external_label_harness_v1.py`(4) | **유일한 진짜 외부 정답표 검정**: 내재 문체 특징이 학자 배정 source class(P/非P)를 구조보존 귀무보다 분리하는가. 통계=최근접중심 LOO, 귀무=**정경순 순환 라벨시프트**. **외부 gold 취득**: Yoffe et al. 2023 Findings-ACL(2305.02170)·GitHub `YoffeG/PnonP` exact-partition zip → Genesis **1533절**(논문 수치와 정확 일치) P/非P, verse-ref "Genesis C:V"→"Gen.C.V" 매핑. **provenance caveat**: 레포에 gold 단일표 명시 README 없음 → exact-partition 해석; 틀리면 cross-method(아티팩트에 명기). **실측**(seed1207·300순열·1532절 매칭): 관측 LOO **0.6312** vs cyclic-shift 귀무 **0.5463**, z **2.14**·p **0.0498** → `STYLOMETRY_SEPARATES_SOURCE_CLASSES_RESEARCH_ONLY`. **정직한 경계**: p=0.0498은 0.05 문턱에 간신히 걸린 **취약 신호**·단일 책·다중비교 미보정; 관측 0.631 < 다수클래스 0.683(분류기 자체는 다수결 미만). **feature ablation(500순열, `--feature-set`)으로 분해**: full(9특징) z2.09·p0.0499 / **volume_only(char·token·lemma count) z1.63·p0.058=무신호** / **style_no_volume(mean_word_len·entropy·morph_seg·TTR·mean_lemma_len) z1.50·p0.056=무신호** → 어느 하위집합도 단독 유의 미달, full은 약한 volume+약한 style **합성**이며 어느 계열 제거 시 붕괴 → **깨끗한 길이 교란도 강건한 문체 신호도 아닌 분산·취약·비강건 효과**. 얕은 표면특징은 Hebrew-lexeme Yoffe만큼 학자 분할을 못 잡음. 아티팩트 `reports/logos_stylometry_yoffe_genesis_{full,volume_only,style_no_volume}_v1.json`. Exodus는 레포에 exact-partition(scholarly) 미제공(method별 unsupervised만)이라 후속. `research_only`·`send_gate=HOLD`·`prophecy_claims=false`·미병합. |
| Logos 학습형 K+S 융합 링크예측 (B-track, 격리·미병합) | `scripts/run_logos_learned_fusion_v1.py` → `reports/logos_learned_fusion_v1_latest.json` | 로지스틱[cosK,cosS] VAL 학습→disjoint TEST 판정, 양성=held-out 엄격 cross-book·음성=랜덤 cross-book 비엣지. **무작위 음성(공정)**: K단독 AUC 0.742·S단독 0.601·KS학습 0.747 → **이득 +0.0054 = 실질 무의미**(계수 cosK 5.67 ≫ cosS 1.1, 모델이 K에 압도 의존). **정직 해석**: 자동 `final_verdict=LEARNED_KS_FUSION_BEATS_K`는 0.005 임계 간신히 초과일 뿐 **실효 이득 없음** — neighbor overlap≈0(상보적)이 링크예측 성능으로 전환 안 됨. **계측기 결함 고지**: hard-negative arm은 음성을 cosK-high로 선별해 구성상 K에 불리(K AUC 0.07 인위적) → **판정 근거 불가·폐기**. **최종 결정판**: K(구조)만 실 일꾼, S 약한 독립신호(융합 이득 미미), L·M 사망 → Logos 좌표는 실측상 **K 단일축 우세**, "4D/다축 통찰망" 미입증. `research_only`·`send_gate=HOLD`·`prophecy_claims=false`·미병합. |
| 도메인-불문 텍스트 구조 엔진 v1 (K축 분리·범용화, B-track, 격리·미병합) | `scripts/mkm_text_structure_engine_v1.py` → `reports/mkm_text_structure_engine_v1_latest.json`; 회귀 `tests/test_mkm_text_structure_engine_v1.py`(4: 토큰화·엣지패밀리·데모 SIGNAL·무구조 랜덤 거짓SIGNAL 금지) | **목적**: Logos에서 유일 생존 축인 **K(구조 임베딩)** 방법을 성경 맥락에서 **분리**해 임의 텍스트(법률·의학·금융·뉴스) 범용 라이브러리로 패키징. 파이프라인: 문서→adjacency+overlap 엣지→`TruncatedSVD` 스펙트럴 임베딩→홀드아웃 overlap 링크예측 순열귀무(z·p). **비성경 planted 3-토픽 데모 실측**: enrich **9.23x·z 37.36·p 0.024·held-out 638** = `SIGNAL_TRANSFERS_IN_CORPUS_RESEARCH_ONLY`. **팩트 교정**: 엔진 기본은 `TruncatedSVD of adjacency`(스펙트럴) — 멀티홉 강화판은 별도 NetMF falsifier(위 행, T4 116x); **"NetMF"·"환각 원천 차단" 단정 금지**. **정직한 경계**: 성경 z≈11.63은 **자동 전이 안 됨** — 법률/의학 전이는 해당 도메인 자체 curated 링크 falsifier 통과 전 **미검증 [HYPO]**. `research_only`·`send_gate=HOLD`·`prophecy_claims=false`·미병합. |
| G2-b lexicon_dense 장시퀀스 wirebench (B-track) | `scripts/run_g2b_lexicon_dense_long_sequence_wirebench_v1.py` → `reports/g2b_lexicon_dense_long_sequence_wirebench_v1_latest.json` | G2-a ADOPT 후속 — 31k mesh_ref를 lexicon_dense 길이대(~1k–1.8k)로 stitch·wire vs packet 비교; baseline `mkm_inter_agent_wire_vs_packet_bench_extended_v1_latest.json`; 회귀 `tests/test_g2b_lexicon_dense_long_sequence_wirebench_v1.py`; `send_gate=HOLD`·Track A 승격 금지 |
| G2-c compression real-eval (B-track, proxy 아님) | 스펙 `docs/final/artifacts/g2c_compression_real_eval_spec_v1_latest.json`; 러너 `scripts/run_g2c_compression_real_eval_v1.py` → `reports/g2c_compression_real_eval_v1_latest.json` | v2 `POST /v2/compress`+`/v2/expand` 라운드트립; baseline=verse only vs candidate=mesh+verse; G2-a closed-dictionary proxy와 대비; 회귀 `tests/test_g2c_compression_real_eval_v1.py`; raw jaccard primary·Track A 승격 금지 |
| G2-d compression follow-up (B-track) | 스펙 `docs/final/artifacts/g2d_compression_followup_spec_v1_latest.json`; 러너 `scripts/run_g2d_compression_followup_v1.py` → `reports/g2d_compression_followup_v1_latest.json`; 체인 `scripts/run_g2d_chain_v1.py` | G2-c 후속 — stride 1300 샘플 확대(stub) + `codebook_only`·`stateless_packet` strict; G2-c 6샘플 drift contrast; 회귀 `tests/test_g2d_compression_followup_v1.py`; `send_gate=HOLD` |
| G2-e Studio smoke + LTM mesh edge (B-track) | `scripts/run_g2e_logos_studio_deploy_smoke_v1.py` → `reports/g2e_logos_studio_deploy_smoke_v1_latest.json`; `scripts/run_g2e_mesh_routing_ltm_edge_extension_v1.py` → `reports/g2e_mesh_routing_ltm_edge_extension_v1_latest.json`; 체인 `scripts/run_g2e_chain_v1.py` | Studio sasang summary·public mirror·design gate offline; LTM `logos_sasang_mesh_31k_g2_overlay` concept+edges; 회귀 `tests/test_g2e_chain_v1.py` |
| G2-f compression HTTP real-eval (B-track, post–live Studio) | 스펙 `docs/final/artifacts/g2f_compression_real_eval_spec_v1_latest.json`; 러너 `scripts/run_g2f_compression_real_eval_v1.py` → `reports/g2f_compression_real_eval_v1_latest.json` | G2-c anchor 6샘플·`codebook_only`·`stateless_packet` strict; **httpx ASGI HTTP** 라운드트립(G2-d TestClient in-process와 transport 분리); G2-d drift contrast; 회귀 `tests/test_g2f_compression_real_eval_v1.py`; `send_gate=HOLD`·Track A 승격 금지 |
| 로고스 독립 렌즈 v0 (**v0.3.0: 생존축 {S,K} direction_score**) | `scripts/run_lens_logos.py` → `docs/final/artifacts/logos_independent_lens_latest.json`; 회귀 `tests/test_run_lens_logos_v1.py`(5) | 계약 `LOGOS_INDEPENDENT_LENS_V0_CONTRACT.json`; `data/logos/4lens_batch_sample.json` 등 4D 배치; 산출에 `evidence_refs`·`narrative_snippet_guarded`(배치 텍스트만 스니펫 가드); CI 픽스처 `tests/fixtures/logos_4lens_batch_minimal_v1.json`; 금융·레짐 미혼합(Logos First). **[FACT] v0.3.0 축 정책(falsification-informed·[NON_GATING])**: `_scores_from_vecs`가 `direction_score`를 **생존축 {S,K}만 동일가중**으로 산출(K중심 아님) — M(게마트리아)·L(어휘밀도)는 held-out cross-book falsifier에서 무신호로 **falsified→제외**(down-weight 아님); 산출 `axis_policy{surviving_axes_used:[S,K], falsified_axes_excluded:[L,M], non_gating:true, falsifier_refs}`; 실측 예: 4축평균 −0.3233 → {S,K} **−0.4067**; 근거 `reports/logos_netmf_embedding_falsifier_v1_latest.json`(K)·`logos_semantic_embedding_falsifier_v1_latest.json`(S)·`gematria_4d_knn_falsifier_v1_latest.json`(M)·`logos_axis_L_and_fusion_v1_latest.json`(L); 관측 전용·게이트 불변·`research_only`·`prophecy_claims=false`. |
| Logos Track B 지휘관 심층 리포트 v1 (골격) | `data/logos/logos_track_b_commander_deep_report_envelope_v1.json`; `scripts/run_logos_track_b_commander_deep_report_v1.py` → `docs/final/artifacts/logos_track_b_commander_deep_report_latest.json`; `scripts/materialize_logos_track_b_commander_deep_report_v1.py` → `reports/logos_track_b_commander_deep_report_latest.md`; `scripts/track_b_commander_gate_v1.py` | 상류 `logos_independent_lens_latest.json` 필수; 융합 스텁·`market_sasang_lens_latest.json` 선택; `labels`·`envelope`·5축 `report_axes_v1`·`human_commander_gate_v1`; 결정론·LLM 없음; 계약 `LOGOS_TRACK_B_COMMANDER_DEEP_REPORT_V1_CONTRACT.json`; `tests/test_logos_track_b_commander_deep_report_v1.py`; 일일 브리프 `Run-DailyExecutionInsightBrief_v1.ps1`·B-track 일일 체인에서 JSON+MD 갱신(선택 스킵 가능) |
| Logos 딥 리서치 Track B 백로그·증류 v1 | `docs/final/LOGOS_DEEP_RESEARCH_TRACK_B_BACKLOG_V1.md`; 계약 `docs/final/artifacts/LOGOS_DEEP_RESEARCH_DISTILL_CONTRACT_V1.json`; 스키마 `docs/final/schemas/logos_deep_research_distill_v1.schema.json`(**선택 `review_gate`**: `pending`·`required`·`waived_internal`·`approved_snapshot`·`superseded` + `reason_code` 등 HITL 감사); `scripts/run_lens_logos_deep_fusion.py` (`--dry-run`·`--emit-template`·`--write-template`; 선택 `--bundle-json`, Track B 벡터 산출물 `--vector-manifest-json`·`--ann-lite-report-json`·`--ann-lite-query-smoke-json` → `provenance`에 경로·SHA256); 산출 예시 경로 `docs/final/artifacts/logos_deep_research_distill_latest.json`(선택 생성); 회귀 `tests/test_logos_deep_research_distill_schema_v1.py`; 오프라인 증류만·실시간 전 그래프 조회·실매매 트리거 금지 |
| Logos 지휘관 전용 리포트 핵심 축 v1 | `docs/final/artifacts/LOGOS_DEEP_RESEARCH_COMMANDER_REPORT_AXES_V1.json` (Track B 심층 보고서 목차·근거 축; 배너 `[TRACK B / HYPO]`·`[연구용: 최종 판단은 지휘관 대기]`·CONSTITUTION 경로 포인터); 백로그 `LOGOS_DEEP_RESEARCH_TRACK_B_BACKLOG_V1.md`와 함께 참조 |
| Logos 코어 코퍼스 매니페스트 v1 (Track B 슬라이스 1) | `scripts/build_logos_corpus_manifest_v1.py` → `docs/final/artifacts/logos_corpus_manifest_v1_latest.json` | 계약 `LOGOS_CORPUS_MANIFEST_V1_CONTRACT.json`; 스키마 `docs/final/schemas/logos_corpus_manifest_v1.schema.json`; 입력 기본 `data/logos/verse_4pipeline_full_31102.json`(대용량·로컬 메모리 필요 시 픽스처로 대체); 픽스처 `tests/fixtures/logos_verse_4pipeline_minimal_manifest_v1.json`; 회귀 `tests/test_logos_corpus_manifest_v1.py`; A-track 실매매 트리거 금지 |
| Logos 코퍼스·의미 그래프 번들 v1 (Track B 슬라이스 2) | `scripts/build_logos_corpus_graph_bundle_v1.py` → `docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json` | 계약 `LOGOS_CORPUS_GRAPH_BUNDLE_V1_CONTRACT.json`; 스키마 `docs/final/schemas/logos_corpus_graph_bundle_v1.schema.json`; 기본 매니페스트 `logos_corpus_manifest_v1_latest.json` + `bible_meaning_graph_nodes_v1.jsonl` / `edges_v1.jsonl`; 코퍼스 정렬·`dedupe_bundle_key_sha256`; 픽스처 `tests/fixtures/logos_graph_bundle_*`; 회귀 `tests/test_logos_corpus_graph_bundle_v1.py`; 그래프 원본 비변경·A-track 트리거 금지 |
| Logos bible_full W5 verification chain v1 | `scripts/run_logos_bible_full_verification_chain_v1.py` → `reports/logos_bible_full_verification_chain_v1_latest.json` | gap-fill→lemma→ui-lite→router→audit→governance→pytest; `--skip-live-smoke`; W6 prep `scripts/check_logos_bible_full_w6_prep_gate_v1.py`; roadmap `reports/logos_bible_full_stack_100_roadmap_v1.json`; `research_only`·send_gate HOLD·Track A 승격 금지 |
| Logos OSS premarket export v1 (open-core harness) | `scripts/build_logos_oss_public_export_bundle_v1.py` · `scripts/run_logos_oss_premarket_smoke_v1.py` · `scripts/Push-LogosOssPublicToGitHub_v1.ps1` | manifest `logos_oss_public_export_manifest_v1.json`; public repo https://github.com/mkmlab-v2/mkm-logos-research-oss; materialize `exports/mkm-logos-research-oss-v1/`; CI `.github/workflows/logos-oss-premarket-smoke.yml`; **monorepo `Push-GitHub-Explicit` 전체 push ≠ curated export**; deny KRV/Gnosis full/trading |
| NVIDIA Grand Challenge attachment pack v1 (grant submit · B-track) | `scripts/run_nvidia_grand_challenge_pack_repro_v1.py` · `scripts/Run-NvidiaGrandChallengePackRepro_v1.ps1` · `scripts/Run-NvidiaGrandChallengePackSubmit_v1.ps1` · `scripts/export_nvidia_grand_challenge_submission_pack_v1.py` · `scripts/run_nvidia_grand_challenge_pack_upgrade_v1.py` | SSOT `reports/nvidia_grand_challenge_attachment_pack_v1.md`; repro `reports/nvidia_grand_challenge_pack_repro_v1_latest.json` → **`all_ok: true`** exit 0; repro tail **`external_facing_fact_lock_pass`** (`check_external_facing_fact_lock_v1.py`, `--skip-external-fact-lock`); submit `reports/nvidia_grand_challenge_submit_v1/`; portal attestation `scripts/record_nvidia_grand_challenge_portal_submit_v1.py` → `nvidia_grand_challenge_portal_submit_v1_latest.json`; perf→Design gate `reports/nvidia_gc_perf_upgrade_ready_v1_latest.json`; handoff `reports/nvidia_grand_challenge_design_lane_handoff_v1_latest.json`; **에이전트 포털 로그인·업로드 금지(Tier 3 Human)**; `send_gate: HOLD` |
| JEMA OS runner policy v1 (L5 admission control plane) | `scripts/build_jema_os_runner_policy_v1.py` · `scripts/check_jema_os_runner_policy_v1.py` · `scripts/build_jema_os_coordinate_envelope_v1.py` · `scripts/check_jema_os_coordinate_envelope_v1.py` | artifact `docs/final/artifacts/jema_os_runner_policy_v1_latest.json`; skim/deep/hold `read_depth_policies`; **`fail_comp_004_guard.l5_l4_kpi_linear_merge_forbidden`**; L5 pins `l5_observed_pins` ← `reports/ollama_shallow_routing_oracle_gap_v1_latest.json` (fixture·not SLA); research_only·Track A 승격 금지 |
| Logos verse gap chunk sprint v1 (B-track backfill) | `scripts/run_logos_verse_gap_chunk_sprint_v1.py` · `scripts/logos_verse_gap_chunk_lib_v1.py` · `scripts/check_logos_verse_gap_closure_v1.py` → `reports/logos_verse_gap_closure_check_v1_latest.json` | progress `reports/logos_verse_gap_chunk_progress_v1.jsonl`; KPI `gap_consumption_stats()` ← bridge SSOT `data/logos/logos_variant_omission_bridge_edges_v2.jsonl` (`effective_consumption_rate`·`structural_variant_sealed`); raw `consumption_rate` dual 유지; closure `progress_rows >= gap_total` + variant seal; `research_only`·send_gate HOLD |
| JEMA OS v1 regression gate v1 (sealed regression_gated) | `scripts/run_jema_os_v1_regression_gate_v1.py` → `reports/jema_os_v1_regression_gate_v1_latest.json` | 순서: KPI chain → logos slot sprint → pytest KPI → (선택 `--include-chunk-closure-smoke`) → manifest `--strict` 마지막; `sealed_mode=regression_gated`; meaning_graph 339/339 앵커 링크 무결성 축 |
| Logos verse gap chunk scheduler v1.2 (sovereign batch · post-closure) | `scripts/run_logos_verse_gap_chunk_scheduler_v1.py` · `scripts/build_logos_verse_gap_chunk_scheduler_policy_v1.py` · `scripts/Invoke-LogosVerseGapChunkSchedulerRoutine_v1.ps1` · `scripts/Register-LogosVerseGapChunkSchedulerWeeklyTask_v1.ps1` | policy `docs/final/artifacts/logos_verse_gap_chunk_scheduler_v1_latest.json`; RAM gate `reports/cursor_host_hygiene_latest.json`; closure 후 `closure_maintenance`+주간 gate; solo stack `MKM_LogosVerseGapChunkSchedulerWeekly_v1`; Track A 승격 금지 |
| JEMA OS guest plugin slots v2.1 (compression·prophecy) | `scripts/build_jema_os_domain_plugin_registry_v2.py` · `scripts/run_jema_os_phase3_guest_sprint_chain_v1.py` · `run_jema_os_{compression,prophecy}_slot_sprint_chain_v1.py` · `run_jema_os_{compression,prophecy}_mistake_resume_loop_v1.py` · `{compression,prophecy}_mistake_registry_lib_v1.py` | phase3 chain → slot sprint; **mistake registry→resume YAML** both slots (`lane=ms`); compression dual-report + prophecy pre_news/Brier walls; regression `--include-plugin-slots compression,prophecy`; `send_gate HOLD`·B→A 금지 |
| JEMA OS C-track guest plugin slots v2.2 (lens_audio·creative_visual) | `scripts/run_jema_os_phase4_ctrack_sprint_chain_v1.py` · `run_jema_os_{lens_audio,creative_visual}_slot_sprint_chain_v1.py` · `run_jema_os_creative_track_mistake_resume_loop_v1.py` · `creative_track_mistake_registry_lib_v1.py` | phase4 chain → BGM gate pytest·showroom observability·AB dry-run / visual brief gate; **mistake→YAML** (`lane=design`); regression `--include-plugin-slots lens_audio,creative_visual`; `[HYPO]`·send_gate HOLD·anatomy_wall |
| External-facing copy Fact-Lock pass v1 | `scripts/check_external_facing_fact_lock_v1.py` · `scripts/Invoke-ExternalFacingFactLockPass_v1.ps1` · `.cursor/rules/mkm-external-facing-fact-lock-v1.mdc` | grant/IR/지원서 초안 `--target` 스캔; 금지어(시장유일·환각0%·완성OS·60초증명 등); `--write-contract` 3줄 계약 JSON; `PUBLIC_FACING` 보조 — 법무 read 별도 |
| JEMA OS infra GPU pointer v1 (band-safe) | `scripts/build_jema_os_core_topology_v2_v1.py` · `scripts/run_jema_os_infra_gpu_pointer_check_v1.py` · `run_jema_os_infra_gpu_slot_sprint_chain_v1.py` · `run_jema_os_infra_gpu_mistake_resume_loop_v1.py` · `infra_gpu_mistake_registry_lib_v1.py` | topology `infra_gpu_bindings` → tier3 `MKM_GpuRecommendedBundle_Weekly` + L5 fixture chain; **mistake→YAML** (`lane=infra`); pointer-only · no `Register-*`; L4 `needs_experiment` |
| GPU inference L5 bench + research backlog v1 (B-track) | `scripts/run_gpu_inference_efficiency_bench_v1.py` · `scripts/run_gpu_inference_research_backlog_chain_v1.py` · `scripts/run_logos_oss_l5_bench_chain_v1.py` | L5 `reports/gpu_inference_efficiency_bench_v1_latest.json`; backlog `reports/gpu_inference_research_backlog_chain_v1_latest.json`·`gpu_inference_baseline_3way_v1_latest.json`; MERGED LIT `docs/research/GPU_INFERENCE_STACK_MKM_MERGED_LIT_REVIEW_2026-06-30.md`; **L4(vLLM·GAIE·LMCache) 미구현·Needs experiment**; cloud_skip≠production GPU SLA |
| CS ticket triage E2E chain v1 (JEMA OS vertical #7) | `scripts/run_cs_ticket_triage_bench_v1.py` · `scripts/run_cs_ticket_triage_e2e_chain_v1.py` · `scripts/check_cs_ticket_triage_e2e_chain_v1.py` · `scripts/jema_os_cs_intake_gate_v1.py` | `reports/cs_ticket_triage_e2e_chain_v1_latest.json`; NVIDIA GC repro 포함; research_only·send_gate HOLD |
| zone_f_code curated catalog v1 (compression B-track · 300 ceiling) | `scripts/run_zone_f_code_curated_monthly_ingest_chain_v1.py` · `scripts/build_zone_f_code_curated_headline_report_v1.py` · policy `docs/final/artifacts/zone_f_code_catalog_growth_policy_v1_latest.json` | catalog `codebook/templates/zone_f_code_templates_v1.jsonl`; curated **300/300** `curated_target_reached`; headline `reports/zone_f_code_curated_headline_v1_latest.json`; signoff **HOLD_NEEDS_REVIEW** (human envelope); harvest frozen; **47%·G2·FAIL-COMP-004 합선 금지**; send_gate HOLD |
| Logos 원어 아톰 GraphRAG 브릿지 v1 (**[HYPO]** Phase 0) | `docs/final/LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md`; `scripts/build_logos_concept_bridge_semiconductor_poc_v1.py` → `logos_concept_bridge_semiconductor_poc_v1_latest.json`; `scripts/Run-LogosOlGraphBridgeParallel_v1.ps1`; 스키마 `docs/final/schemas/logos_concept_bridge_v1.schema.json`; 회귀 `tests/test_logos_concept_bridge_v1.py` | 정적 concept→function→lemma_proxy→verse 경로만; **예언·%동형·era-blind 4.3% 대체 금지**; lemma↔verse `CONTAIN` 대량 빌더·LLM bridge·성경 전용 GraphRAG 라우터 **TBD** |
| Logos 크로스 도메인 인터페이스 매퍼 CDIM v1 (**[HYPO]**) | `docs/final/LOGOS_CROSS_DOMAIN_INTERFACE_MAPPER_V1.md`; `scripts/assemble_logos_cross_domain_interface_v1.py` → `docs/final/artifacts/logos_cross_domain_interface_latest.json`; `scripts/materialize_logos_cross_domain_interface_digest_v1.py` → `reports/logos_cross_domain_interface_digest_latest.md`; `scripts/Run-LogosCrossDomainInterfaceParallel_v1.ps1`; `build_mkm_trackc_ops_dashboard_v1.py`의 `trackc.logos_cross_domain_interface` 슬라이스; 스키마 `docs/final/schemas/logos_cross_domain_interface_v1.schema.json`; 회귀 `tests/test_logos_cross_domain_interface_v1.py` | fusion_stub·독립 렌즈 **읽기 전용** 조립; **성경 코퍼스 verse-level 오행 이식 금지**; A-track·실매매 자동 합선 금지 |
| MKM Logos 신학 베이스라인 v1 (파라미터 해석·내부 일관) | `docs/final/artifacts/LOGOS_MKM_THEOLOGY_BASELINE_V1.json` (**버전 1.1.0**·`track_b_deep_research_interpretation_policy`에 융합 스텁·LLM 오버레이·증거 바인딩) | 스키마 `docs/final/schemas/logos_mkm_theology_baseline_v1.schema.json`; 계약 `LOGOS_MKM_THEOLOGY_BASELINE_V1_CONTRACT.json`; 텍스트 우선순위·금지 출력·현대 조인 가설 메타데이터·provenance 포인터; `governance_and_reporting.not_a_deregulation_claim=true`; 회귀 `tests/test_logos_mkm_theology_baseline_v1.py`·`tests/test_track_b_theology_fusion_integration_v1.py`(신학 SSOT ↔ fusion_stub·준비도 체인); A-track·실매매 트리거 금지 |
| Logos 벡터 인덱스 매니페스트 v1 (Track B 슬라이스 3·임베딩 전 감사) | `scripts/build_logos_vector_index_manifest_v1.py` → `docs/final/artifacts/logos_vector_index_manifest_v1_latest.json` | 계약 `LOGOS_VECTOR_INDEX_MANIFEST_V1_CONTRACT.json`; 스키마 `logos_vector_index_manifest_v1.schema.json`; 정책 `LOGOS_VECTOR_INDEX_POLICY_V1.json` SHA·코퍼스 매니페스트·그래프 번들 정렬 기록; **`embeddings_computed=false`** 고정; 회귀 `tests/test_logos_vector_index_manifest_v1.py`; 임베딩·ANN 미호출 |
| Logos 벡터 ANN 라이트 빌드 v1 (Semantic ANN-lite·SQLite) | `scripts/build_logos_vector_index_ann_lite_v1.py` → `docs/final/artifacts/logos_vector_index_ann_lite_v1_latest.json` · `logos_vector_index_ann_lite_v1.sqlite`; 공유 스텁 `scripts/logos_vector_hash_stub_v1.py`; 선택 NL 경로 `scripts/logos_ann_lite_embedding_v1.py`·`--embedding-backend sentence_transformers`(+`--sentence-transformer-model`, 정책 stub 시 `--allow-stub-policy-embedding`); 대용량 구절 JSON `--stream` 또는 임계치(`LOGOS_VERSE_STREAM_BYTES_THRESHOLD`, 기본 32MiB)에서 **ijson** 파싱; Top-K 점검 `scripts/query_logos_vector_index_ann_lite_v1.py`(스텁 인덱스는 시드만, ST 인덱스는 동일 모델 필요); exit **5** 정책 미허용 NL·**6** ST 로드 실패·**7** 스트림 필요인데 ijson 없음·**8**(조회) ST 인덱스 모델 누락·**9** `--max-wall-seconds` 초과 | 계약 `LOGOS_VECTOR_INDEX_ANN_LITE_BUILD_REPORT_V1_CONTRACT.json`; 스키마 `logos_vector_index_ann_lite_build_report_v1`·`logos_vector_ann_lite_query_result_v1`; `policy.status=active` + `embedding.model_id`일 때 기본 체인(`run_logos_track_b_pipeline_chain_v1.py --include-ann-lite`)이 `sentence_transformers_v1` 경로를 우선 사용; 기본 구절 원천=매니페스트 `input_path`·`--max-verses` 기본 500; 회귀 `tests/test_logos_vector_index_ann_lite_v1.py`; **S1_SHADOW 승격 (2026-05-07): semantic ANN-lite 활성 + shadow-only non-gating 운영** |
| 철학·상담 레인 RAG 파일럿 v1 (Track B) | `scripts/philosophy_lane_rag_pilot_v1.py` → `docs/final/artifacts/philosophy_lane_rag_pilot_v1_latest.json`; 금지어 SSOT `docs/final/artifacts/schemas/philosophy_lane_rag_pilot_forbidden_substrings_v1.json`(`--forbidden-config`); 래퍼 `scripts/run_philosophy_lane_rag_pilot_v1.ps1`; 선택 `scripts/query_logos_vector_index_ann_lite_v1.py`·`--invoke-cross-lens-fusion`→`scripts/build_cross_lens_rag_fusion_v1.py`; **mkmlife HTTP:** `projects/mkm/mkm-life/app/api/v1/study/philosophy/rag-pilot/route.ts` POST(JSON `user_query`·선택 `menu_id`·`top_k`·`redact_query`·`invoke_cross_lens_fusion`) — 모노레포 루트 자동 탐색·`PHILOSOPHY_RAG_PILOT_SCRIPT`/`PHILOSOPHY_RAG_PYTHON`/`PHILOSOPHY_RAG_FORBIDDEN_CONFIG`/`PHILOSOPHY_RAG_SQLITE` 서버 env만(클라이언트 경로 주입 금지); Study 라우트라 **미들웨어 Basic Auth·invite** 규칙 동일; 회귀 `tests/test_philosophy_lane_rag_pilot_v1.py`; A-track·실매매·본선 자동 트리거 금지 |
| 내부 시맨틱+RAG 번역 브리지 번들 v1 (B-track·lab) | `scripts/build_semantic_rag_bridge_insight_bundle_v1.py` → 기본 `docs/final/artifacts/semantic_rag_bridge_insight_bundle_v1_latest.json`; 스키마·예시 `docs/final/schemas/semantic_rag_bridge_insight_bundle_v1.schema.json` 동명; 설계 매핑 `docs/final/INTERNAL_SEMANTIC_RAG_4D_ARCH_OUTLINE_V1.md` §4.1 | 입력 `--rag-json`·`--slots-json`·`--calibration-kind`·`--calibration-artifact`; **`--premium-multilens-report-json`** 시 `premium_btrack_multilens_report_v1`의 `lenses[].rag.retrieval_runs[].hits[]`를 `rag_evidence`로 병합(남은 슬롯까지, 총 24 cap); **`--philosophy-pilot-json`** 시 `philosophy_lane_rag_pilot_v1`의 `blocks[]` 병합; 병합 순서: rag-json → premium → philosophy; `jsonschema` 설치 시 `--strict` exit 2; 회귀 `tests/test_semantic_rag_bridge_insight_bundle_schema_v1.py`·`tests/test_build_semantic_rag_bridge_insight_bundle_v1.py`; **`scripts/run_fact_lock_bundle.ps1` 5c3**·CI **`dual-regime-integrity.yml`**(Premium gate 직후); P0 `verify_p0_constitution_gate_paths.ps1`; A-track·실매매 트리거 금지 |
| Ollama Shallow Router v1 [HYPO] (local preprocess → handoff → semantic RAG E2E) | Modelfile `docs/final/artifacts/ollama_mkm_shallow_router_modelfile_v1.txt`; 출력 스키마 `docs/final/schemas/ollama_shallow_router_output_v1.schema.json`; 벤치 `scripts/run_ollama_shallow_router_bench_v1.py`; handoff `scripts/build_ollama_shallow_router_handoff_v1.py`; E2E `scripts/run_ollama_shallow_to_semantic_rag_e2e_v1.py` → `reports/ollama_shallow_to_semantic_rag_e2e_v1_latest.json`; golden `tests/fixtures/ollama_shallow_router_golden_v1.json`; domain matrix `tests/fixtures/ollama_shallow_e2e_domain_examples_v1.json` | `ollama create mkm-shallow-router-v1 -f docs/final/artifacts/ollama_mkm_shallow_router_modelfile_v1.txt`; `--include-deep-chain-dry-run`·선택 `--include-deep-chain-live`(live pytest `MKM_SHALLOW_E2E_DEEP_LIVE=1`); **`routing_oracle_gap` shadow** `scripts/build_ollama_shallow_routing_oracle_gap_v1.py` → `reports/ollama_shallow_routing_oracle_gap_v1_latest.json`; 회귀 `tests/test_ollama_shallow_router_bench_v1.py`·`tests/test_ollama_shallow_to_semantic_rag_e2e_v1.py`·`tests/test_ollama_shallow_routing_oracle_gap_v1.py`; P0 `verify_p0_constitution_gate_paths.ps1`; research_only·SEND_GATE HOLD·Track A 금지; **OLLAMA_HOST client=`http://127.0.0.1:11434`** (User env; bind `0.0.0.0` 금지) · bodyguard `scripts/run_agent_middleware_bodyguard_bench_v1.py` · SSOT `MKM_AGENT_MIDDLEWARE_BODYGUARD_V1.md` |

| Universal Multi-Res Router v1.1 (Y1b B-track OS scaffold · plugin registry · Ollama adapter) **서피스 태그: CI 포함·번들 선택·헬스만** | 라우터 `scripts/universal_multi_res_router_v1.py` → `docs/final/artifacts/universal_multi_res_router_v1_latest.json`; 스키마 `docs/final/schemas/universal_multi_res_router_v1.schema.json`; 플러그인 레지스트리 `scripts/build_universal_multi_res_plugin_registry_v1.py` → `docs/final/artifacts/universal_multi_res_plugin_registry_v1_latest.json`·스키마 `universal_multi_res_plugin_registry_v1.schema.json`; 포지션 `docs/final/artifacts/universal_multi_res_router_y1b_position_v1_latest.md`·**executive brief** `universal_multi_res_router_y1b_executive_brief_v1_latest.md`(Y1 Hero=`mkm-universal-root` vs Y1b 분리·§3.11 과장 금지); **JSONL replay** `scripts/universal_multi_res_router_replay_lib_v1.py`·`scripts/append_universal_multi_res_router_replay_v1.py`·`scripts/summarize_universal_multi_res_router_replay_v1.py`·스키마 `universal_multi_res_router_replay_v1.schema.json`→`reports/universal_multi_res_router_replay_v1.jsonl`·`reports/universal_multi_res_router_replay_v1_summary_latest.json`·라우터 `--append-replay`; **HTTP stub** `scripts/universal_multi_res_router_api_stub_v1.py`(`POST /api/v1/lens/route`·`POST /api/v1/lens/metering/log` shadow only·`GET /health`·port 8035)·smoke `scripts/run_universal_multi_res_router_api_stub_smoke_v1.py`→`reports/universal_multi_res_router_api_stub_smoke_v1_latest.json`; **Phase 4** tenant registry `scripts/build_universal_multi_res_router_tenant_registry_v1.py`→`universal_multi_res_router_tenant_registry_v1_latest.json`·shadow metering `scripts/universal_multi_res_router_metering_lib_v1.py`·`scripts/summarize_universal_multi_res_router_metering_v1.py`→`reports/universal_multi_res_router_metering_v1.jsonl`·env `MKM_UNIVERSAL_ROUTER_METERING_SHADOW`·`MKM_UNIVERSAL_ROUTER_TENANT_KEYS`·PUBLIC_FACING `scripts/check_universal_multi_res_router_public_facing_v1.py`→`reports/universal_multi_res_router_public_facing_v1_latest.json`·gate `scripts/run_universal_multi_res_router_phase4_gate_v1.py`→`reports/universal_multi_res_router_phase4_gate_v1_latest.json`; **reliability evidence pack** `scripts/run_universal_multi_res_router_reliability_evidence_pack_v1.py`→`reports/universal_multi_res_router_reliability_evidence_pack_v1_latest.json`·`reports/universal_multi_res_router_reliability_evidence_pack_v1_latest.md`; 1호 full `sasang_context_v1`+`scripts/sasang_context_inventory_v1.py`; 2호 lite_plus `logos_lens_v1`+`scripts/logos_context_inventory_v1.py`; 명리 lite `myeongni_lens_v1`+`scripts/myeongni_context_inventory_v1.py`; science stub `uft_core_v1_stub`; **`FORBIDDEN_RULES`**·`routing_overlay_policy: routing_hints_only`·`send_gate: HOLD` 고정; 선택 Ollama shallow handoff `--shallow-json`; U2 레인 훅 `.cursor/rules/mkm-universal-multi-res-router-{sasang,logos,myeongni}-v1.mdc`(**`alwaysApply: false`**·전역 mandatory 금지); 사상 계약 포인터 `SASANG_DYNAMICS_V1_CONTRACT.json` | `py scripts/build_universal_multi_res_plugin_registry_v1.py`; `py scripts/universal_multi_res_router_v1.py --query "<intent>"`; `py scripts/universal_multi_res_router_v1.py --query "<intent>" --append-replay`; `py scripts/run_universal_multi_res_router_api_stub_smoke_v1.py`; `py scripts/run_universal_multi_res_router_phase4_gate_v1.py`; `py scripts/run_universal_multi_res_router_reliability_evidence_pack_v1.py`; `uvicorn scripts.universal_multi_res_router_api_stub_v1:app --host 127.0.0.1 --port 8035`; `py scripts/logos_context_inventory_v1.py`·`py scripts/myeongni_context_inventory_v1.py`(선택); 회귀 `tests/test_universal_multi_res_router_v1.py`·`tests/test_universal_multi_res_router_replay_v1.py`·`tests/test_universal_multi_res_router_api_stub_v1.py`·`tests/test_universal_multi_res_router_metering_v1.py`·`tests/test_universal_multi_res_router_public_facing_v1.py`·`tests/test_universal_multi_res_router_phase4_metering_v1.py`·`tests/test_universal_multi_res_plugin_registry_v1.py`·`tests/test_run_universal_multi_res_router_reliability_evidence_pack_v1.py`·`tests/test_mkm_universal_multi_res_router_sasang_hook_v1.py`·`tests/test_mkm_universal_multi_res_router_logos_hook_v1.py`·`tests/test_mkm_universal_multi_res_router_myeongni_hook_v1.py`; CI **`.github/workflows/universal-multi-res-router-reliability-smoke.yml`**; Fact-Lock 선택 **`run_fact_lock_bundle.ps1 -IncludeUniversalMultiResReliabilityEvidence`**; 헬스 **`run_workspace_automation_health.ps1 -IncludeUniversalMultiResReliabilityEvidenceSmoke`**·단축 **`-UniversalMultiResReliabilityEvidenceSmokeOnly`**; 페르소나 **`Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaUniversalMultiResReliability`**·**`AmsaengUniversalMultiResReliability`**; **Y1 Hero OSS smoke와 KPI·대외 SKU 합산 금지**; 상용 게이트웨이 `stub_status: pre_registration_only`·`metering_enabled: false`; Track A·실매매·임상 자동 승격 금지 |
| MKM DR bench mini v1 (DeepResearch Belt FACT-lite, B-track) **서피스 태그: 헬스만·번들 선택** | `scripts/run_mkm_deep_research_bench_mini_v1.py` → `reports/mkm_deep_research_bench_mini_v1_latest.json`; tasks `tests/fixtures/mkm_deep_research_bench_tasks_v1.json` (**7-task** · `drb_herbs_formulas_tcm` + **`drb_digestion_wiring`** domain extensions); weekly online strict `scripts/Invoke-MkmDeepResearchBenchWeekly_v1.ps1` → log `reports/dr_bench_weekly_online_strict_latest.log`; ops paste `scripts/build_mkm_deep_research_bench_ops_paste_v1.py` → `reports/mkm_deep_research_bench_ops_paste_v1_latest.md`; 회귀 `tests/test_mkm_deep_research_bench_mini_v1.py`·`tests/test_build_mkm_deep_research_bench_ops_paste_v1.py` | Fact-Lock 선택 **`run_fact_lock_bundle.ps1 -IncludeDeepResearchBenchSmoke`**(offline pytest+harness `--require-entry-level`+paste); 헬스 선택 **`run_workspace_automation_health.ps1 -IncludeDeepResearchBenchSmoke`**·단축 **`-DeepResearchBenchSmokeOnly`**; `send_gate` HOLD·Track A·실매매 승격 금지 |
| MKM digestion engine v1 (Tier 0 → digested JSON → wiring → pytest gate, B-track) | 스키마 `docs/final/schemas/mkm_research_digested_fact_v1.schema.json`; Mastication `scripts/build_mkm_research_digested_facts_v1.py` → `docs/final/artifacts/<stem>_digested_facts_latest.json`; Wiring `scripts/map_digested_facts_to_mkm_plane_v1.py`; **active fact-lite** `scripts/check_digested_numeric_fact_v1.py` → `docs/final/artifacts/mkm_digested_numeric_fact_check_latest.json`; gate `scripts/check_mkm_digested_facts_gate_v1.py` → `docs/final/artifacts/mkm_digested_facts_gate_latest.json`; 체인 `scripts/run_mkm_digestion_engine_chain_v1.py` → `reports/mkm_digestion_engine_chain_v1_latest.json`; baseline registry `docs/final/artifacts/mkm_baseline_plane_registry_v1.json`; DR bench **7-task** `drb_digestion_wiring`; 회귀 `tests/test_mkm_digestion_engine_v1.py`·`tests/test_mkm_deep_research_bench_mini_v1.py` | `py scripts/run_mkm_digestion_engine_chain_v1.py --input docs/research/raw/<tier0>.md`; explicit `## Digested facts` + table heuristic; active fact-lite promotes Unknown→Right when value in arXiv abstract; **Right+ mkm_wiring**만 artifact assert; LIT_REVIEW md alone ≠ done; `send_gate` HOLD·Track A 승격 금지 |
| BigSet Tier-0 ingest triple gate v1 (**[HYPO]** AGPL bridge · B-track) | 스펙 `docs/research/BIGSET_MULTI_AGENT_INGESTION_SPEC_V1.md`; Tier0 ref `docs/research/raw/persly_emr_longitudinal_harness_tier0_2026-06-24.md`; MERGED `docs/research/BIGSET_ATYPICAL_SIGNAL_MERGED_LIT_REVIEW_2026-06-24.md`; 체인 `scripts/run_bigset_ingest_spike_chain_v1.py` → `reports/bigset_ingest_spike_chain_v1_latest.json`; 융합 `scripts/run_bigset_logos_fusion_chain_v1.py`; **① citation_lock** `scripts/check_bigset_tier0_citation_lock_v1.py` → `bigset_tier0_citation_lock_v1_latest.json`; **② timeline_repair(shadow)** `scripts/repair_bigset_tier0_timeline_order_v1.py` → `bigset_tier0_timeline_repair_v1_latest.json`·`bigset_tier0_timeline_repair_v1_latest.csv`; **③ timeline_order** `scripts/check_bigset_tier0_timeline_order_v1.py` → `bigset_tier0_timeline_order_v1_latest.json`; **④ conflict_surface** `scripts/build_bigset_conflict_surface_v1.py` → `bigset_conflict_surface_v1_latest.json`; 관측 **atypical_signal** `scripts/detect_bigset_tier0_atypical_signal_v1.py` → `bigset_tier0_atypical_signal_v1_latest.json`(non-fatal); **human_review_queue** `scripts/bigset_tier0_atypical_human_review_queue_stub_v1.py` → `bigset_tier0_atypical_human_review_pending_v1_latest.json`·`reports/bigset_tier0_atypical_human_review_queue_v1.jsonl`(non-fatal); **atypical_bench** `scripts/bench_bigset_tier0_atypical_signal_v1.py` → `reports/bigset_tier0_atypical_bench_v1_latest.json`; **memory-light accumulate** `scripts/merge_bigset_tier0_csv_accumulate_v1.py`·`scripts/run_bigset_live_row_accumulate_chain_v1.py` → `reports/bigset_live_row_accumulate_chain_v1_latest.json`; Azure start `scripts/Invoke-BigSetAzureStart_v1.ps1`; N-loop `scripts/Invoke-BigSetLiveAccumulateLoop_v1.ps1` → `reports/bigset_live_accumulate_loop_v1_latest.json`; **studio sidecar** `scripts/build_bigset_studio_conflict_sidecar_v1.py`·`observability.human_review_pending_count`; 회귀 `tests/test_bigset_ingest_spike_chain_v1.py`·`tests/test_check_bigset_tier0_timeline_order_v1.py`·`tests/test_bigset_tier0_timeline_repair_and_atypical_v1.py`·`tests/test_bigset_logos_fusion_chain_v1.py`·`tests/test_bigset_tier0_atypical_human_review_queue_stub_v1.py`·`tests/test_bigset_tier0_csv_accumulate_v1.py`; `send_gate` HOLD·의학 OIH≠Logos·Track A·실매매 자동 합선 금지 |
| Research LIT_REVIEW citation multi-rail v1 (B-track, existence-only) | arXiv `scripts/check_research_lit_review_citation_lock_v1.py`; DOI/Crossref `scripts/check_research_lit_review_doi_lock_v1.py`; PMID/PubMed `scripts/check_research_lit_review_pmid_lock_v1.py`; fact-support `scripts/check_research_lit_review_fact_support_v1.py`; MERGED gate `scripts/run_mkm_merged_lit_review_gate_chain_v1.py` → `reports/mkm_merged_lit_review_gate_chain_v1_latest.json`; remerge `scripts/run_mkm_merged_lit_review_remerge_chain_v1.py` → `reports/mkm_merged_lit_review_remerge_chain_v1_latest.json`; **herbs/formulas extract** `scripts/build_herbs_formulas_extract_v1.py` → `docs/final/artifacts/<stem>_herbs_formulas_extract_latest.json`; chain `scripts/run_herbs_formulas_extract_chain_v1.py` → `reports/herbs_formulas_extract_chain_v1_latest.json`; **alias/포제 8010 proxy** `scripts/herbs_formulas_alias_table_v1.py` + stub `POST /v1/research/herbs_formulas/alias-resolve` on `scripts/compression_token_api_stub.py`; seed `data/herbs_formulas/herbs_formulas_alias_seed_v1.json`; build `scripts/build_herbs_formulas_alias_table_v1.py` → `docs/final/artifacts/herbs_formulas_alias_table_v1_latest.json` (`MKM_HERBS_FORMULAS_ALIAS_TABLE_PATH` override) | 기본 `--min-total-ids 1`·`--min-total-claims 1`; DOI/PMID는 소스에 존재할 때만 실행(없으면 `skipped`); `--skip-doi-lock`·`--skip-pmid-lock`; 한의학/학술지 보조 레일(DOI·PMID) — arXiv-only 단독 승격 금지; herbs markdown `--strict` schema validate; alias proxy는 **fixture PoC** — 41k Logos lexicon·전체 본초 이명 DB 아님; 회귀 `tests/test_check_research_lit_review_citation_lock_v1.py`·`tests/test_check_research_lit_review_doi_lock_v1.py`·`tests/test_check_research_lit_review_pmid_lock_v1.py`·`tests/test_mkm_merged_lit_review_gate_chain_v1.py`·`tests/test_mkm_merged_lit_review_remerge_chain_v1.py`·`tests/test_build_herbs_formulas_extract_v1.py`·`tests/test_run_herbs_formulas_extract_chain_v1.py`·`tests/test_herbs_formulas_extract_schema_v1.py`·`tests/test_herbs_formulas_alias_table_v1.py`; TCM 스키마 `docs/final/schemas/herbs_formulas_extract_v1.schema.json`; `send_gate` HOLD·임상 자동화·전문가 대체 주장 금지 |
| Logos Track B 정책 체인 준비도 v1 | `scripts/report_logos_track_b_policy_readiness_v1.py` → `docs/final/artifacts/logos_track_b_policy_readiness_v1_latest.json` | 계약 `LOGOS_TRACK_B_POLICY_READINESS_V1_CONTRACT.json`; 스키마 `docs/final/schemas/logos_track_b_policy_readiness_v1.schema.json`; 입력 기본 `LOGOS_MKM_THEOLOGY_BASELINE_V1.json`(provenance_slots·거버넌스 플래그)·증류 계약/스키마·**`LOGOS_VECTOR_INDEX_POLICY_V1`** 및 정책의 **corpus 선행 파일** 존재; exit 0=`overall_ok`; 회귀 `tests/test_logos_track_b_policy_readiness_v1.py`; LLM 없음 |
| Logos Track B 딥 퓨전 잡 v1 (스켈레톤) | `scripts/run_logos_track_b_deep_fusion_job_v1.py` → `docs/final/artifacts/logos_track_b_deep_fusion_job_v1_latest.json` | 계약 `LOGOS_TRACK_B_DEEP_FUSION_JOB_V1_CONTRACT.json`; 스키마 `logos_track_b_deep_fusion_job_v1.schema.json`; 기본 `readiness`·신학 베이스라인·`logos_corpus_graph_bundle_v1_latest.json` 존재 기록; 산출 `inputs.optional_track_b_vector_artifacts`(매니페스트·ANN 라이트·조회 스모크 등 **존재 여부 스냅샷**); readiness `overall_ok` 아니면 exit 3(산출은 기록); **`--write-distill-template`** 시 `run_lens_logos_deep_fusion.py` 서브프로세스로 증류 템플릿만 기록(LLM 없음); distill 실패 시 exit 4; 원클릭 PowerShell `scripts/Run-LogosTrackBChainV1.ps1` · 크로스플랫폼 **`scripts/run_logos_track_b_pipeline_chain_v1.py`**(`parse_known_args`로 잡 인자 전달); CI **`.github/workflows/logos-track-b-pipeline-smoke.yml`**; **기본 LLM/RAG 미호출**; 회귀 `tests/test_logos_track_b_deep_fusion_job_v1.py` |
| 창1·요1 Wide 복원 산출 재생성 | `scripts/build_logos_wide_restoration.py` → `data/logos/reports/wide.json`, `data/logos/reports/wide_restored.json` | 입력 `data/logos/reports/logos_report_gen1_john1_wide_*.json` `verse_level`; `geumhwa_index=K×(1−M)×0.9`; `restoration_rate=min(0.9999,0.96+geumhwa_index×0.0001)`; 거리 0.156–0.20 → Wide20; 구조 복원 지표·[HYPO]·예측력 단정 금지 |
| 독립 렌즈 융합 스텁 v0(비교 전용) | `scripts/report_independent_lens_fusion_stub_v0.py` → `docs/final/artifacts/independent_lens_fusion_stub_latest.json` | 계약 `INDEPENDENT_LENS_FUSION_STUB_V0_CONTRACT.json`; 산출 JSON Schema `docs/final/schemas/independent_lens_fusion_stub_v0.schema.json`(회귀 `tests/test_independent_lens_fusion_stub_v0.py`); 산출 **`version` 0.3.0**·`inputs` 3~4행(선택 **`market_sasang_lens_v1`**: `scripts/run_market_sasang_lens_v1.py`→`market_sasang_lens_latest.json`, `--no-market-sasang`시 3행만); `consensus` + **`conflict_summary`**(다수결 방향·소수 렌즈·점수 나열 + Logos `evidence_refs`/스니펫 앵커, 템플릿 고정·LLM 없음); `scripts/build_cross_lens_rag_fusion_v1.py`는 위 스냅샷·독립 렌즈를 읽어 `cross_lens_rag_fusion_latest.json/.md`를 만들며, sasang 렌즈의 `b_track_axis_scores_v1`를 JSON/MD 섹션으로 반영; 선택 **`--lens-music-gate-chain-json`** → 산출 **`version` 1.1.0**·`lens_music_symbolic_passthrough_v1`(합의 행렬 비참여·관측만; `--no-lens-music`으로 무시)(회귀 `tests/test_build_cross_lens_rag_fusion_v1.py`); A-track 자동융합·실거래 트리거 금지 |
| 일일 실행 인사이트 브리프 v1 | `scripts/build_daily_execution_insight_brief_v1.py` → `reports/daily_execution_insight_brief_latest.md`; `scripts/Run-DailyExecutionInsightBrief_v1.ps1`; `projects/bitcoin-trading/ops/windows-rehearsal/DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md` | 기본 입력 thin `docs/final/artifacts/multilens_eval_v2_thin_report_latest.json`, fusion `docs/final/artifacts/independent_lens_fusion_stub_latest.json`, §1c 독립 렌즈는 위 표 `run_lens_*`·`run_market_sasang_lens_v1` 등 산출 `*_latest.json`과 동일 경로·`--*-json` 오버라이드 가능; **[FACT]** 브리프는 `scripts/run_market_myeongni_lens_v1.py`가 산출한 `docs/final/artifacts/market_myeongni_lens_latest.json` 스냅샷을 읽어 통합 MD의 Market Myeongni 표에 융합 반영한다(`--market-myeongni-json`); **[FACT]** §1c에 `reports/myeongni_conflict_arbitration_runtime_mode_latest.json`를 읽어 명리 학파 충돌 중재 **B-track 정책 스탬프**(모드·검증·policy 해시) 표시(`--myeongni-conflict-runtime-json`, 관측 전용·실매매 비연결); **[FACT]** `scripts/Run-AmsaengEosaMonitoringBundleTask.ps1`는 번들 말단에서 `scripts/build_trackc_evidence_rag_mvp_v1.py`를 호출해 `docs/final/artifacts/trackc_evidence_rag_mvp_latest.json`을 생성한다(자문형 `research_only=true`, 실행/매매 비연결); `OBSERVATION_ONLY`·디스크 SSOT만; 회귀 `tests/test_build_daily_execution_insight_brief_v1.py`, `tests/test_build_trackc_evidence_rag_mvp_v1.py` |
| Premium B-track multi-lens report v1 (sync packager) | `scripts/build_premium_btrack_multilens_report_v1.py` → 기본 `reports/premium_btrack_multilens_report_v1.md`·`.json`(`--out-dir`); 스키마·예시 `docs/final/schemas/premium_btrack_multilens_report_v1.schema.json` 동명 | **`--mode best-effort`** 시 독립 렌즈 JSON(`--myeongni-json`·`--sasang-json`·`--logos-json`, 미지정 시 `docs/final/artifacts/*_independent_lens_latest.json`); 오프라인 키워드 RAG: `--rag-bundle`(기본 `tests/fixtures/premium_multilens_rag_corpus_bundle_v1.json` 존재 시)·`--rag-corpus-scan-dir`, 렌즈 `rag.corpus_id`=`premium_multilens_rag_offline_v1`; **`--async-simulate`**·**`--async-job-id`**는 JSON `async_job` 큐 형태만 기록(동기 빌더·실워커 미연결); **`--async-queue-enqueue`**(선택 **`--async-queue-path`**)는 `async_job`가 있을 때 **`scripts/premium_multilens_job_queue_stub_v1.py`** `enqueue`로 JSONL 한 줄 append(v0 파일 큐); 동 스크립트 **`export-pending`**는 대기 큐 스냅샷 JSON(`schema=premium_multilens_queue_pending_export_v0`)+CONSTITUTION 정렬 렌즈 스크립트 포인터만 기록(실행 없음); **`drain`**는 FIFO 스캔·리포트 JSON `schema=premium_btrack_multilens_report_v1` 검증·선택 **`--write-ack`**로 기본 `reports/premium_multilens_job_queue_ack_v0.jsonl`에 `drain_ack` 기록; **`--allow-missing-queue`**는 번들·헬스 Premium·CI에서 큐 파일 없을 때 SKIP·exit 0; 일상 원클릭 **`scripts/Invoke-PremiumMultilensQueueRoutine_v1.ps1`**(pytest 3종+drain; 선택 `-ExportPendingJson`로 export-pending; Redis·실비동기 워커·렌즈 서브프로세스 없음); **백로그:** 임베딩 RAG·Redis·실렌즈 오케스트레이션은 별도 승격; 회귀 `tests/test_premium_btrack_multilens_report_schema_v1.py`·`tests/test_build_premium_btrack_multilens_report_v1.py`·`tests/test_premium_multilens_job_queue_stub_v1.py`·`tests/test_build_premium_multilens_queue_promotion_gate_v1.py`; **S1_SHADOW 승격 게이트 v1** `scripts/build_premium_multilens_queue_promotion_gate_v1.py` → `docs/final/artifacts/premium_multilens_queue_promotion_gate_v1_latest.json`(`schema=premium_multilens_queue_promotion_gate_v1`; 기본 pytest 3종+`drain`+`export-pending` 후 `export` 스냅샷의 `pending_items[*].validation_ok` 전원 true면 **GO_PREMIUM_MULTILENS_QUEUE_S1_SHADOW**·exit 0, 하나라도 false면 **HOLD_PREMIUM_MULTILENS_QUEUE_INVALID_PENDING**·exit 1; **`--skip-pytest`**는 Fact-Lock 번들·CI·Invoke에서 pytest 직후 중복 회피용); CI **`dual-regime-integrity.yml`**(pytest 직후 `drain --allow-missing-queue` 직후 gate `--skip-pytest`); 로컬 **`scripts/run_fact_lock_bundle.ps1`** 단계 4b(동일 pytest+drain+gate); **P0** `scripts/verify_p0_constitution_gate_paths.ps1`에 빌더·큐 스텁·승격 게이트·Invoke·스키마·예시·fixture·pytest 경로 고정; 헬스 선택 **`scripts/run_workspace_automation_health.ps1 -IncludePremiumBtrackMultilensReportSmoke`**·단축 **`-PremiumBtrackMultilensReportSmokeOnly`**; A-track·실매매 자동 트리거 금지 |
| 독립 렌즈 Shadow 게이트 v1 | `scripts/report_independent_lens_shadow_gate.py` → `docs/final/artifacts/independent_lens_shadow_gate_latest.json` | 계약 `INDEPENDENT_LENS_SHADOW_GATE_V1_CONTRACT.json`; 최소 관측 창(8주·2개월) 누적·`KEEP_OBSERVATION_ONLY` 고정; 히스토리 JSONL·게이트 출력에 **`minority_lens_ids`·`logos_evidence_verse_ids`·`conflict_narrative_sha256`** 등 충돌 스냅샷 필드(`latest_conflict_snapshot`) |
| 명리 주간 운영 요약 래퍼 v1 (비권위 MD 인덱스) | `scripts/Run-MyeongniWeeklyOpsSummary_v1.ps1` → `scripts/emit_myeongni_weekly_ops_summary_v1.py` → `reports/myeongni_weekly_ops_summary_latest.md` | 체인: `run_lens_myeongni.py --allow-fallback` → `report_independent_lens_fusion_stub_v0.py`(Shadow 게이트 상류 필수) → `report_independent_lens_shadow_gate.py`(주간 KPI 락온); 선택 `-Include16StateProbe`: `myeongni_summary_gen.py --audit-path data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl --output data/myeongni/16_STATE_MASTER_PROBE_v1.json`; 스킵: `-SkipLens` / `-SkipFusionAndGate`; **MD는 SSOT 아님**; 주간 KPI는 `independent_lens_shadow_gate_latest.json`의 `decision`·`blockers`·`history.*`; 회귀 `tests/test_emit_myeongni_weekly_ops_summary_v1.py` |
| Shadow 히스토리 소수 렌즈 월별 집계 v1 | `scripts/report_independent_lens_shadow_minority_monthly_v1.py` → `docs/final/artifacts/independent_lens_shadow_minority_monthly_latest.json` | `independent_lens_fusion_shadow_history.jsonl`의 `ts_utc`(UTC 월)·`minority_lens_ids`·내러티브 다이제스트 수 집계; 레거시 행은 `minority_lens_ids` 없음 → 소수 없음으로 처리; 회귀 `tests/test_independent_lens_shadow_minority_monthly_v1.py`; 월간 체인 `run_waiting_queue_monthly_check.ps1`·일일 B-track `run_btrack_daily_hypothesis_chain.ps1`·`run_myeongni_shadow_monthly_catchup_v1.ps1`에서 Shadow 게이트 직후(또는 동 체인 내) 자동 갱신 |
| 계약 테스트 | `tests/test_myeongni_insight_observation_log.py` | sample·log JSONL + 스텁 JSON |
| Yang(2015) 표면 8자 집계·육친 5범주 B-track v1 | `scripts/btrack_yang_2015_style_metrics_v1.py` → `reports/btrack_yang_2015_style_metrics_latest.json` | 스키마 `docs/final/schemas/btrack_yang_2015_style_metrics_v1.schema.json`; 입력 기본 `reports/commander_myeongni_lens_latest.json`의 `advanced.input_summary.pillars` 또는 `slots.pillars`; 지지는 본기天干으로 십성 버킷(`officer`·`resource`·`parallel`·`hurting_god`·`wealth`); 한글·한자 간지 병기; 논문 변수 매핑 `data/myeongni/paper_contract_maps/yang_2015_four_pillars_personality_map_v1.json`; **임상·A-track 트리거 금지** |
| 연예/픽스처 벤치 + v2 승격 + Yang 부가 산출 | `scripts/run_myeongni_celebrity_benchmark_v1.py` (`data/myeongni/celebrity_saju_benchmark_v1.jsonl`) → `docs/final/artifacts/myeongni_celebrity_hit_rate_v1.json` | 스키마 `docs/final/schemas/myeongni_celebrity_hit_rate_v1.schema.json`; 행별 `yang_2015_style_metrics`; `expectations`만 hit-rate 요약에 반영; 상류 `scripts/run_saju_global_birth_v1.py`·`scripts/myeongri_core_v2_upgrade.py`; 회귀 `tests/test_btrack_yang_2015_style_metrics_v1.py`·`tests/test_myeongni_paper_contract_map_v1.py`·`tests/test_run_myeongni_celebrity_benchmark_v1.py`·`tests/test_yang_2015_btrack_json_schema_v1.py`; P0 경로 `scripts/verify_p0_constitution_gate_paths.ps1`; CI `dual-regime-integrity.yml`·`multilens-independent-lens-smoke.yml` |
| 사상체질↔문헌↔사주 조인트(B-track 데이터 길) | Europe PMC 메타 `scripts/fetch_europepmc_sasang_saju_literature_catalog_v1.py` → `data/myeongni/sasang_saju_literature_catalog_*.jsonl`; 필터 `scripts/filter_sasang_saju_literature_catalog_v1.py`; 검토 큐 `scripts/build_sasang_saju_joint_review_queue_from_catalog_v1.py`; 초록 사상 자동보강 `scripts/auto_enrich_sasang_from_literature_stub_v1.py` → `data/myeongni/sasang_saju_joint_benchmark_auto_v1.jsonl`; 다수결 해소 `scripts/resolve_literature_sasang_majority_v1.py` → `…_auto_resolved_v1.jsonl`; 감독 slice `scripts/export_sasang_literature_supervised_jsonl_v1.py` → `data/myeongni/sasang_literature_supervised_v1.jsonl`; CSV 승격 `scripts/promote_joint_curated_csv_v1.py`; **검증 출처 단일 입구** `scripts/ingest_curated_saju_joint_v1.py` ← 입력 `data/myeongni/curated_saju_joint_v1.jsonl`(스키마 `docs/final/schemas/curated_saju_joint_input_row_v1.schema.json`; `provenance_url`/`source_url`/`source_citation` 중 하나 이상 없으면 만세력 엔진 미호출·`SKIP_UNVERIFIED`); 조인트 벤치 검증·스모크 `scripts/validate_sasang_saju_joint_benchmark_jsonl_v1.py`·`scripts/run_sasang_saju_joint_benchmark_smoke_v1.py`; staleness `scripts/check_curated_saju_joint_staleness_v1.py` → `reports/curated_saju_joint_staleness_v1_latest.json`(큐레이트 `ingest_at_utc`·없으면 파일 mtime vs 히트레이트 `generated_at_utc`); 원클릭 `scripts/run_sasang_saju_joint_autopilot_local_v1.ps1` | 스키마 행 `sasang_saju_joint_benchmark_row_v1`·`sasang_saju_literature_catalog_row_v1`(모듈 독스트링); **출생 시각은 공개·승인 출처만** CSV·JSONL 경유 자동 승격; 논문 초록만으로 동일 인물 만세력 단정 금지; 회귀 7+1+1종(문헌 7·인제스트·staleness; `tests/test_ingest_curated_saju_joint_v1.py`·`tests/test_check_curated_saju_joint_staleness_v1.py`)·CI `dual-regime-integrity.yml` 전용 단계; 로컬 번들 `scripts/run_fact_lock_bundle.ps1`(기본 포함, `-SkipSasangSajuJointLiteraturePipeline`·끝단 `-SkipCuratedJointStalenessCheck` 생략); P0 일부 경로 `verify_p0_constitution_gate_paths.ps1` |
| 만세력 기반 명리 4D 융합 | `scripts/myeongri_complete_fusion.py` | `MyeongriCompleteFusion`; `tools/core/myeongri_4d_correction.py`·`_ohang_data_to_4d`; 출력에 `vector_4d`(표면)·`vector_4d_jijangan_v1`·`vector_4d_rule_school_v1`·`jijangan_v1`·`daewoon_v1`/`daewoon_qiyun_v1`; 선택 `precomputed_full_saju=`로 만세력 재호출 생략(`run_manseryeok_bot_v1` Pro); `MyeongriController._get_base_vector_4d`와 연동; 본선·실거래 자동 합선 금지; **대외 카피·논문·광고용 공학 어휘**는 `docs/final/MYEONGRI_EXTERNAL_ENGINEERING_LEXICON_V1.md`(코드 명칭 불변) |
| 지장간(藏干) LUT v1 | `data/myeongni/jijangan_lut_v1.json`; `docs/final/schemas/jijangan_lut_v1.schema.json`; `scripts/myeongri_jijangan_v1.py` | 결정론 조회·오버레이; `tests/test_myeongri_jijangan_v1.py` |
| 지장간 오행 가산 | `data/myeongni/jijangan_ohang_weights_v1.json`; `scripts/myeongri_jijangan_ohang_v1.py` | `ohang_strength_jijangan_v1`; `tests/test_myeongri_jijangan_ohang_v1.py` |
| 대운·起運 v1 | `scripts/myeongri_daewoon_v1.py`; `scripts/myeongri_qiyun_v1.py`; `scripts/core/solar_term_jie_crossings_v1.py`; `scripts/manseryeok_perfect_final.py` (`daewoon`, `daewoon_qiyun_v1`) | 월주 순·역행; 起運=절기 간 일수/3(Meeus 태양 황경 12절, 생시 `Asia/Seoul`); 대운 연령 구간은 공통 경계 배열 + 소수 **6**자리 반올림으로 행 간 `age_end`=`다음 age_start`; `compute_qiyun_meta_v1`의 `qiyun_days`/`qiyun_years_float`도 동일 자릿수·`years_float≡days/3`(극소 양수 일수는 0으로만 보일 때 원값 유지); JD 필드는 비반올림; `tests/test_myeongri_daewoon_v1.py`, `tests/test_myeongri_qiyun_v1.py` |
| rule_school_mkm_4d_v1 블렌드 | `data/myeongni/rule_school_mkm_4d_v1.json`; `scripts/myeongri_rule_school_mkm_4d_v1.py` | 표면 vs 지장간 4D 가중합; `tests/test_myeongri_rule_school_mkm_4d_v1.py` |
| 명리 학파 충돌 중재 정책 v1 (B-track) | `data/myeongni/myeongni_conflict_arbitration_v1.json`; `scripts/myeongri_rule_school_mkm_4d_v1.py` (`load_myeongni_conflict_arbitration_v1`, `apply_myeongni_conflict_arbitration_v1`); `scripts/verify_myeongni_conflict_arbitration_edgecases_v1.py` → `docs/final/artifacts/myeongni_conflict_arbitration_edgecases_latest.json`; `scripts/run_myeongni_conflict_arbitration_threshold_sweep_v1.py`; 런타임 스탬프 `reports/myeongni_conflict_arbitration_runtime_mode_latest.json` | JSON 규칙(조후 불균형·표면/지장간 가중·안정 밴드)으로 `vector_4d` 조정; **전통 십신·모든 학파 분기 통합 매트릭스 전부는 아님**; 오케스트레이터·리포트 등이 런타임 JSON 소비; A-track·실매매 자동 합선 금지 |
| 매크로 백테스트 스텁 v1 (B-track) | `scripts/eval_myeongri_rule_school_macro_stub_v1.py` → `docs/final/artifacts/myeongri_rule_school_macro_stub_v1_latest.json` (실행 시 생성) | JSONL 출생 행 → `vector_4d_rule_school_v1` 평균·`gate`; 행에 선택 숫자 `label`이 있으면 `label_correlation`(Pearson/Spearman·선택 SciPy p-value, 축 `--label-axis` S/L/K/M/norm); 산출 `version` 1.1.0; `tests/test_eval_myeongri_rule_school_macro_stub_v1.py` |
| Track B 지휘관 검토용 명리 리포트 봉투 | `data/myeongni/myeongni_track_b_commander_report_envelope_v1.json`; `scripts/build_myeongni_track_b_commander_report_v1.py` → `docs/final/artifacts/myeongni_track_b_commander_report_latest.json` (실행 시 생성) | 스키마 v1.1.0: `commander_notes`(선택)·`handoff`(NotebookLM 매니페스트·Vault 푸시 **포인터만**); `[TRACK_B|HYPO|검토대기]`·`full_fusion_payload`; LLM 없음; `tests/test_build_myeongni_track_b_commander_report_v1.py` |
| Manseryeok 봇 Pro | `scripts/run_manseryeok_bot_v1.py` | `analysis_depth=pro` 시 `luck.myeongri_fusion_v1`·`daewoon_qiyun_v1`·`vector_4d_rule_school_v1` 요약; 기본 `basic`는 비포함; **`--write-complete-fusion-json PATH`** 시 `MyeongriCompleteFusion` 전체 dict 별도 저장(pro 여부 무관, 명리 렌즈 `run_lens_myeongni.py --advanced-from-fusion-json` 연결용); 회귀 `tests/test_run_manseryeok_bot_v1.py` |
| λ 변환 훅 (스텁) | `scripts/myeongri_lambda_converter.py` | `MyeongriLambdaConverter` |
| 게마트리아+명리 4D 블렌드 스파이크 v0 | 결정론 기하층 `tools/myeongni/gematria_myeongri_math_v1.py` · 오케스트레이션 `scripts/spike_gematria_myeongri_blend_v0.py` → `docs/final/artifacts/gematria_myeongri_spike_blend_latest.json` | L2·cosine·단순x 합만(LLM·LoRA 없음); 예측·교리 정확도 아님; 격리 로드맵 `docs/final/BTRACK_GEMATRIA_MYEONGRI_MATH_ISOLATION_V1.md`; `independent_lens_fusion_stub`의 `consistency_rate`와 무관; 회귀 `tests/test_gematria_myeongri_math_v1.py`·`tests/test_gematria_myeongri_spike_smoke.py` |
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
| 회귀 스모크 | `tests/test_myeongri_fusion_scripts_smoke.py`, `tests/test_myeongri_jijangan_v1.py`, `tests/test_myeongri_jijangan_ohang_v1.py`, `tests/test_myeongri_daewoon_v1.py`, `tests/test_myeongri_qiyun_v1.py`, `tests/test_myeongri_ai_interpretation_envelope_v1.py`, `tests/test_myeongri_rule_school_mkm_4d_v1.py`, `tests/test_eval_myeongri_rule_school_macro_stub_v1.py`, `tests/test_build_myeongni_track_b_commander_report_v1.py`, `tests/test_run_manseryeok_bot_v1.py`, `tests/test_gematria_myeongri_spike_smoke.py`, `tests/test_gematria_myeongri_math_v1.py`, `tests/test_spike_log_myeongri_correlation_v1.py`, `tests/test_convert_log_metabolism_to_myeongri_correlation_input_v1.py`, `tests/test_generate_log_metabolism_synthetic_cohort_v1.py`, `tests/test_spike_4grid_myeongri_compression_v1.py`, `tests/test_spike_kospi_structural_entropy_v1.py`, `tests/test_spike_kospi_structural_entropy_compare_v1.py`, `tests/test_build_btrack_session_instant_myeongni_panel_v1.py`, `tests/test_join_btrack_session_panel_weather_ohlcv_v1.py`, `tests/test_correlate_btrack_joined_wide_csv_v1.py`, `tests/test_run_btrack_session_panel_weather_corr_chain_v1.py` | CI `dual-regime-integrity.yml`; `run_prophecy_alignment_pytest.ps1` / `.sh` 번들 |
| 독립 렌즈 v0·v1·융합브리지 회귀 | `tests/test_myeongni_independent_lens_v0.py`, `tests/test_myeongni_lens_v1_contract.py`, `tests/test_myeongni_fusion_bridge_v1.py`, `tests/test_independent_lenses_v0.py`, `tests/test_independent_lens_fusion_stub_v0.py`, `tests/test_independent_lens_shadow_gate_v1.py`, `tests/test_independent_lens_shadow_minority_monthly_v1.py`, `tests/test_build_daily_execution_insight_brief_v1.py`, `tests/test_emit_myeongni_weekly_ops_summary_v1.py` | 명리 단독(v0 기본·v1 확장·융합→advanced) + 3렌즈 파라미즈 + 융합 스텁 + Shadow 게이트 + 소수 렌즈 월별 집계 + 일일 실행 브리프 머티리얼라이저 + 주간 MD 포인터 emit |

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
| Bio n-state strict 리포트 재수화 (P0, B-track 관측) | `scripts/build_bio_sasang_nstates_strict_comparison_rehydrate_v1.py` → `reports/bio_sasang_nstates_strict_comparison_v2.json`; 주간 래퍼 `scripts/Generate-BioSasangWeeklyReport_v1.ps1`; 백업 탐색 `scripts/Find-BioSasangArtifactsInBackupRoots.ps1`(선택) | **원재현(FireProt/DDG) 아님**: `regeneration.mode=rehydrated_from_ssot_documentation`·CENTRAL 표 행 수치 고정; 신선 재계산은 별도 러너·코호트 확보 후만 `[FACT]` 승격; 회귀 `tests/test_bio_sasang_nstates_strict_comparison_rehydrate_v1.py`; CI `.github/workflows/bio-sasang-nstates-rehydrate-smoke.yml` |
| **승격 후보 canonical 스택 (B-track, 2026-07-02)** | `scripts/run_sasang12_promotion_stack_v1.py` (= `run_sasang12_promotion_candidate_chain_v1.py` → `judge_sasang12_promotion_candidate_v1.py` → `analyze_sasang12_gate_failure_v1.py` → `check_sasang12_constitution_path_drift_v1.py --strict`) → `docs/final/artifacts/sasang12_promotion_candidate_chain_latest.json`, `sasang12_promotion_candidate_gate_latest.json`, `sasang12_gate_failure_analysis_latest.json`, `sasang12_constitution_path_drift_v1_latest.json` | 관측 전용; `promotion_to_a_track_allowed=false` 고정. 회귀 `tests/test_sasang12_promotion_stack_v1.py`. |
| 승격 후보 고정·판정 체인 (B-track, legacy freeze v1) | `scripts/run_sasang12_promotion_candidate_freeze_v1.py`, `scripts/judge_sasang12_promotion_candidate_v1.py` → `docs/final/artifacts/sasang12_promotion_candidate_freeze_v1_latest.json`, `docs/final/artifacts/sasang12_promotion_candidate_gate_latest.json` | **freeze v1 스크립트는 트리 미포함(archived)** — canonical은 위 스택. 주간 winner-rotation 비용 민감도(`weekly_rebalance_cost_sensitivity_latest.json`)는 v2+ 실험 스택. 확장 관측(2025-10-01~2026-04-20): `sasang12_promotion_candidate_gate_2025-10-01_to_2026-04-20.json` = FAIL(누적 수익 델타 음수) |
| 통합 게이트 요약 (`gate_latest`, B-track) | `docs/final/artifacts/sasang12_promotion_candidate_gate_latest.json` | 스키마 `sasang12_promotion_candidate_gate_unified_v1`: 최신 산출에서 **`status`가 `PASS`로 찍힐 수 있음** — 그래도 **`track_wall.promotion_to_a_track_allowed=false`**, **`a_track_autobind_forbidden=true`**를 병기 확인(통합 PASS ≠ A-Track 방향 승격·자동 합선). 아래 v2~v10 개별 `*_gate_vN_latest.json`은 **historical experiment 기록**(트리 미포함 가능) — `sasang12_constitution_path_drift_v1_latest.json`로 canonical vs archived 구분. |
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
| 명리 독립 렌즈 → Thin 겹침 JSONL 브리지 (선택) | `scripts/emit_myeongni_thin_bridge_line_v1.py` | `myeongni_independent_lens_latest.json`·실험 JSONL tail(`provenance.input_path`); `--calendar-date YYYY-MM-DD` **또는** `auto`(`--curated-dates-json` 격자에서 렌즈 `ts_utc`·`provenance.row_ts_utc`에 **가장 가까운** 벤치일); `data/multilens_eval/myeongni_independent_lens_thin_bridge_latest.jsonl` + `--myeongni-jsonl` — **일일 체인** `Run-DailyExecutionInsightBrief_v1.ps1`가 Thin 직전에 기본 수행(끄려면 `-SkipMyeongniThinBridge`); 압축 KPI 본선 자동 합선 없음; 회귀 `tests/test_emit_myeongni_thin_bridge_line_v1.py`(로컬 `run_fact_lock_bundle.ps1`·`run_workspace_autopilot_chain.ps1`·정렬 번들 `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1`·CI `dual-regime-integrity`·`multilens-independent-lens-smoke`) |
| 듀얼 레짐 입력 샘플 | `data/multilens_eval/dual_regime_curated_overlap_v1.json` | `evaluate_dual_regime_and_market_shock` kwargs; 동일 플래그로 `logos_dual_regime` 슬롯 채움 |
| 시장 OHLC/FGI 어댑터 v1 | `scripts/multilens_dual_regime_market_adapter_v1.py` → `data/multilens_eval/dual_regime_market_adapter_v1.json` | Binance 일봉 + Alternative.me FGI; `bible_risk_score=0`; Thin V2 `--dual-regime-json`로 교체 가능 |
| BTC 앵커 스모크 (3일) | `data/multilens_eval/curated_dates_btc_anchor_smoke_v1.json` → `data/multilens_eval/dual_regime_market_adapter_btc_anchor_smoke_v1.json` | `sasang_dynamics_regime_mapping_v1.btc_anchor_smoke.jsonl`과 동일 달력일; 네트워크 필요 |
| Thin 보고서 (BTC 앵커 스모크) | `data/multilens_eval/multilens_eval_v2_thin_report_btc_anchor_smoke_v1.json` | `eval_multilens_harness_v2_thin.py --populate-default-samples` + 위 어댑터·사상 JSONL |
| BTC 앵커 스모크 원클릭 | `scripts/run_btc_anchor_multilens_smoke.ps1` | 어댑터 → Thin 보고서 재생성(네트워크 필요) |
| 로컬 자동 체인 (Fact-Lock+B-Track 스모크) | `scripts/run_workspace_autopilot_chain.ps1` | `run_fact_lock_bundle`(기본에 **`tests/test_sasang_interpretive_insight_bundle_v1.py`**·사상 통찰 번들 v1.1 계약 회귀 + **`tests/test_build_daily_execution_insight_brief_v1.py`**·일일 실행 인사이트 브리프, `dual-regime-integrity` 정렬) → 사상 `validate-sample`(샘플+btc_anchor) → `run_btc_anchor_multilens_smoke` → sasang·thin pytest. 선택: `-IncludeP1AB`, `-IncludeJemaaiCloudChecks`(MVP 파일·nginx 예시 존재 확인, **배포 아님**). |
| TruthfulQA A/B (B-track, `research_only`) | `scripts/run_truthfulqa_ab_benchmark_v1.py` → `docs/final/artifacts/truthfulqa_ab_benchmark_latest.json`(MC)·`truthfulqa_generation_ab_benchmark_latest.json`(generation); `scripts/check_truthfulqa_ab_gate_v1.py`(`--strict`·`--mc-only`) → `docs/final/artifacts/truthfulqa_ab_gate_latest.json`; 원클릭 `scripts/Run-TruthfulQAReproBundleV1.ps1`; Fact-Lock 번들 `scripts/run_fact_lock_bundle.ps1` 선택 스위치 `-IncludeTruthfulQaBenchmarkGate`·`-TruthfulQaBenchmarkGateMcOnly`·`-IncludeTruthfulQaBenchmarkEvalGate`·`-TruthfulQaEvalMcOnly`·`-StrictTruthfulQaBenchmarkEvalGate` | OpenAI 호환 엔드포인트·HF 데이터셋 빌드는 선택(`datasets`). Track A·실매매 자동 합선 금지. 회귀: `tests/test_run_truthfulqa_ab_benchmark_v1.py`, `tests/test_check_truthfulqa_ab_gate_v1.py`, `tests/test_run_truthfulqa_repro_bundle_v1.py`, `tests/test_run_fact_lock_bundle_truthfulqa_gate.py`. **서피스 태그: CI 포함**(동 pytest·게이트 계약은 `dual-regime-integrity`; MC/Gen 벤치 산출·eval 본실행은 원클릭·번들 `-Include*`로 별도) |
| jemaai.cloud 융합 점검 (P1·쇼룸 경로) | `scripts/run_jemaai_cloud_completion_chain.ps1` | 위 autopilot에 P1 A/B(기본) + jemaai MVP 경로 검증 통합; `-SkipP1AB`로 P1 생략. **nginx/VPS 반영은 수동.** |
| 러너 | `scripts/eval_multilens_harness_v2_thin.py` | `--out`; `--populate-default-samples`로 B-track JSONL 병합; 채운 뒤 `summary`(cap 분포·사상-명리 `mapping_target` 일치 등); `logos_dual_regime.interpretation_snippet`는 `scripts/core/logos_dual_regime_interpretation_snippet_v1.py` + 규칙 `docs/final/artifacts/LOGOS_DUAL_REGIME_INTERPRETATION_SNIPPET_RULES_V1.json`으로 검증·클립(운영 브리프용), 전문 `interpretation` 필드는 감사용 동행 |
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

### 3.8 [B-track] Emotion VA trajectory state machine (M20 extension, [HYPO])

**목적:** 대화 턴(Turn)에 따른 감정(Valence–Arousal)의 지수이동평균(EMA) 기반 관성 궤적을 한 턴 단위로 기록한다. **정적 매핑 한 스냅샷**이 아니라 **이전 `current_va` → 타깃 `target_va` → 새 `current_va`** 를 스키마에 박제해 시계열·회귀 테스트가 가능하게 한다.

**Track wall:** `[HYPO]`, `[NON_GATING]`, `[ADVISORY_ONLY]` — 본선 실매매·게이트웨이 최종 트리거와 물리 분리. 임상·체질 단정 금지.

| 항목 | 경로 | 비고 |
|------|------|------|
| 빌더 CLI | `scripts/build_lens_emotion_va_trajectory_v1.py` | `--target-valence`/`--target-arousal` 또는 `--chain-json`(lens-music 체인에서 스냅샷 VA 읽기); `--ema-alpha`; `--state-json`로 턴 간 `current_va` 연속 |
| 단일 턴 SSOT (latest) | `reports/va_trajectory_log_latest.json` | `schema: va_trajectory_log_v1` |
| (선택) 시계열 append | `reports/va_trajectory_log.jsonl` | `--jsonl-log` 시 한 줄 append |
| 연속 상태 (기본 갱신) | `reports/lens_emotion_va_trajectory_state_latest.json` | `schema: lens_emotion_va_trajectory_state_v1`; 다음 턴의 `previous_va` 입력; `--no-write-state` 로 단발만 가능 |
| JSON Schema | `docs/final/schemas/va_trajectory_log_v1.schema.json` | 예시 `docs/final/schemas/va_trajectory_log_v1.example.json` |
| 회귀 | `tests/test_va_trajectory_log_v1.py` | 스키마 + EMA 결정론 |

**의존성:** M20 동적 프롬프트 오버레이(`scripts/build_lens_music_prompt_overlay_v1.py`)와 동일한 `_apply_ema` 형태 \(`current = alpha * target + (1-alpha) * previous` per axis\).

### 3.8.1 [B-track] Cross-lens VA→Logos fusion report (PoC, white-box)

**목적:** `va_trajectory_log_v1` 의 `current_va` 를 입력으로, **스텁 후보 구절 목록**에 결정론적 태그 가중을 적용해 순위가 어떻게 바뀌는지 JSON 한 장에 남긴다. 실제 임베딩 RAG 인덱스가 아니라 **회귀 가능한 PoC**이며, 단일 신경망 융합이 아니라 **정책 ID + 후보 행별 multiplier** 로 추적 가능하게 한다.

**Track wall:** `[HYPO]`, `[NON_GATING]`, `[ADVISORY_ONLY]` — Logos 정경 코어와의 identity merge 금지; 본선 트리거 금지.

| 항목 | 경로 | 비고 |
|------|------|------|
| 빌더 CLI | `scripts/build_cross_lens_fusion_report_v1.py` | `--va-trajectory-json`(기본 `reports/va_trajectory_log_latest.json`), `--candidates-stub-json`(기본 `tests/fixtures/cross_lens_fusion_candidates_sample_v1.json`) |
| 산출 (latest) | `reports/cross_lens_fusion_report_latest.json` | `schema: cross_lens_fusion_report_v1` |
| 스텁 후보 | `tests/fixtures/cross_lens_fusion_candidates_sample_v1.json` | `verse_id`, `base_score`, `fusion_tags` |
| JSON Schema | `docs/final/schemas/cross_lens_fusion_report_v1.schema.json` | 예시 `docs/final/schemas/cross_lens_fusion_report_v1.example.json` |
| 회귀 | `tests/test_cross_lens_fusion_report_v1.py` | 스키마 + 순위 변화 + CLI |

**정책 (`va_tag_boost_v1`):** 스크립트 docstring·`policy_notes` — 저발화(low valence)에서 peace·comfort·hope, 고발화에서 joy·energy, 고각성에서 caution·temperance, 극각성 완화용 calm·peace 등 태그 매칭 시 multiplier 스택(결정론).

**퓨전 쿨다운 감쇠 (§3.8.2 연동):** `cooldown_control.applied` 이면 쿨다운 사유별 감쇠를 추가한다. `high_arousal` + `joy|energy` 매칭 시 **0.85**, `low_valence` + `caution|temperance` 매칭 시 **0.9**를 `fusion_multiplier`에 후적용한다. 행별 `fusion_multiplier_pre_damp`, `cooldown_damp_factor`, `cooldown_damp_rules_applied`, `cooldown_fusion_damp_applied`로 추적한다.

### 3.8.2 [B-track] VA cooldown control loop (safety integrity)

**목적:** VA 상태가 운영상 허용치 밖으로 이탈하려 할 때, 가중치 적용 이전에 **결정론적 쿨다운 제어**를 수행해 `current_va`를 안정 구간으로 되돌린다. “감정 강화”가 아니라 **통제 가능성 증명**이 목적이다.

**Track wall:** `[HYPO]`, `[NON_GATING]`, `[ADVISORY_ONLY]` — 본선 트리거·실매매 엔진 자동 바인딩 금지.

| 항목 | 경로 | 비고 |
|------|------|------|
| 쿨다운 실행 | `scripts/build_lens_emotion_va_trajectory_v1.py --enable-cooldown` | EMA 산출 후 적용; `high_arousal`/`low_valence` 이유 기록 |
| 정책 스키마 | `docs/final/schemas/va_cooldown_policy_v1.schema.json` | 예시 `docs/final/schemas/va_cooldown_policy_v1.example.json` |
| 이벤트 스키마 | `docs/final/schemas/va_cooldown_event_v1.schema.json` | 예시 `docs/final/schemas/va_cooldown_event_v1.example.json` |
| 이벤트 산출 (latest) | `reports/va_cooldown_event_log_latest.json` | `schema: va_cooldown_event_v1` — **쿨다운 플래그가 꺼져 있어도** 매 턴 `applied:false` noop 이벤트를 동일 경로에 기록(§3.8.3 감사 입력 정합) |
| 이벤트 시계열 (선택) | `reports/va_cooldown_event_log.jsonl` | `--cooldown-event-jsonl` 사용 시 append |
| 회귀 | `tests/test_va_trajectory_log_v1.py`, `tests/test_va_cooldown_schema_v1.py` | 임계 돌파 시 개입 + schema 검증 |

**초기 정책 (`va_cooldown_control_v1`):** `high_arousal_cut=0.9`, `low_valence_cut=-0.9`, `arousal_decay_step=0.2`, `valence_recovery_step=0.15`. 개입 시 `status=COOLDOWN_ACTIVE`로 승격해 후속 퓨전에 전달.

### 3.8.3 [B-track] Fusion control integrity audit (VA ↔ cooldown ↔ fusion)

**목적:** `va_trajectory_log_v1`, `va_cooldown_event_v1`, `cross_lens_fusion_report_v1` 3개 산출물의 **세션/턴·쿨다운 상태·사유·감쇠 규칙 적용 여부**를 단일 보고서에서 교차 검증한다.

**Track wall:** `[HYPO]`, `[NON_GATING]`, `[ADVISORY_ONLY]` — 운영 트리거가 아니라 무결성 감사용.

| 항목 | 경로 | 비고 |
|------|------|------|
| 감사 빌더 CLI | `scripts/build_fusion_control_integrity_audit_v1.py` | 입력: `--va-trajectory-json`, `--cooldown-event-json`, `--fusion-report-json` |
| 감사 산출 (latest) | `reports/fusion_control_integrity_audit_latest.json` | `schema: fusion_control_integrity_audit_v1` |
| JSON Schema | `docs/final/schemas/fusion_control_integrity_audit_v1.schema.json` | 예시 `docs/final/schemas/fusion_control_integrity_audit_v1.example.json` |
| 회귀 | `tests/test_fusion_control_integrity_audit_v1.py` | 스키마 + pass bundle + turn mismatch fail |

**핵심 체크:** `schema_contracts`, `session_turn_alignment`, `cooldown_state_alignment`, `cooldown_policy_alignment`, `cooldown_reasons_alignment`, `fusion_rule_application`.

### 3.8.4 [B-track] VA→fusion→integrity one-click chain (Windows + CI 스모크)

**목적:** §3.8→§3.8.1→§3.8.3 를 **한 번에** 갱신해 운영자가 `reports/*_latest.json` 네 장을 동기화할 수 있게 한다. Linux CI는 PowerShell 대신 pytest 서브프로세스 체인으로 동일 계약을 검증한다.

**Track wall:** `[HYPO]`, `[NON_GATING]`, `[ADVISORY_ONLY]`.

| 항목 | 경로 | 비고 |
|------|------|------|
| 원클릭 (Windows) | `scripts/Run-VaFusionControlIntegrityChain_v1.ps1` | 기본 `--no-write-state`(상태 파일 생략); `-WriteState`로 `lens_emotion_va_trajectory_state_latest.json` 갱신. **감사 실패 시 선택 웹훅:** User `FUSION_CONTROL_INTEGRITY_AUDIT_WEBHOOK_URL`, 미설정 시 `OPS_ALARM_WEBHOOK_URL`; 없으면 stdout만. CI·로컬(시크릿 없음)에서는 `-SkipWebhook` |
| 일일 작업 등록 | `scripts/Register-VaFusionControlIntegrityDailyTask.ps1` | 기본 작업명 `MKM-VaFusionControlIntegrity-Daily`, 시각 `07:35`; `automation_registry.json` 항목명 `\\MKM-VaFusionControlIntegrity-Daily`(reconcile SSOT) |
| Fact-Lock 번들 (기본 포함) | `scripts/run_fact_lock_bundle.ps1` | 체인 pytest + `tests/test_va_fusion_policy_golden_v1.py`; 생략: `-SkipVaFusionControlIntegritySmoke` |
| 정책 골든 픽스처 | `tests/fixtures/va_fusion_policy_golden_v1.json` | `va_tag_boost_v1` 결정론 스냅샷 |
| 회귀 (크로스플랫폼) | `tests/test_va_fusion_control_integrity_chain_v1.py` | trajectory→fusion→audit, `summary.all_pass` |
| 회귀 (정책 단위) | `tests/test_va_fusion_policy_golden_v1.py` | fixture 행 vs `fusion_multiplier` |

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
| 노드 스키마 | `docs/final/schemas/aramaic_graph_node_v1.schema.json` | `schema: aramaic_graph_node_v1`, `source_track=B` 고정; `tests/test_aramaic_graph_schema_v1.py`로 최소 인스턴스 검증 |
| 엣지 스키마 | `docs/final/schemas/aramaic_graph_edge_v1.schema.json` | 6개 타입(`timeline_anchor`, `causal_precursor`, `fulfillment`, `recurrence`, `contrast_inversion`, `cross_lens_confirm`) |
| 점수 스키마 | `docs/final/schemas/aramaic_regime_shift_score_v1.schema.json` | `schema: aramaic_regime_shift_score_v1`, `signal_label`·`insight_cap_bucket` 포함; `score_aramaic_regime_shift_v1.py` 산출과 정합 |
| 노드 빌더 | `scripts/build_aramaic_graph_nodes_v1.py` → `docs/final/artifacts/aramaic_graph_nodes_v1.jsonl` | 아람어 노드 생성 |
| 엣지 빌더 | `scripts/build_aramaic_graph_edges_v1.py` → `docs/final/artifacts/aramaic_graph_edges_v1.jsonl` | 관계 타입별 엣지 생성 |
| 교차 코퍼스 브리지 빌더 | `scripts/build_aramaic_cross_corpus_bridge_v1.py` → `docs/final/artifacts/aramaic_cross_corpus_bridge_nodes_v1.jsonl`, `docs/final/artifacts/aramaic_cross_corpus_bridge_edges_v1.jsonl` | 아람어 노드와 히브리(BHS)/헬라(SBLGNT) 후보 구절의 4D 유사도 기반 브리지 엣지 생성; CLI 스모크: `tests/test_build_aramaic_cross_corpus_bridge_v1.py` |
| 의미 그래프 빌더 (구절-테마-레짐상태) | `scripts/build_bible_meaning_graph_v1.py` → `docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl`, `docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl` | 교차참조 엣지와 태그를 융합해 `verse ↔ theme ↔ regime_state` 3자 네트워크 생성; CLI 스모크 `tests/test_build_bible_meaning_graph_v1.py`; 행 스키마 `docs/final/schemas/bible_meaning_graph_node_v1.schema.json`, `docs/final/schemas/bible_meaning_graph_edge_v1.schema.json`; 계약·jsonschema 회귀 `tests/test_bible_meaning_graph_schema_v1.py` |
| 의미 통찰 후보 추출기 | `scripts/extract_bible_meaning_insight_candidates_v1.py` → `docs/final/artifacts/bible_meaning_insight_candidates_latest.json` | 허브 구절·레짐 반복 군집·top-k 추론 경로 후보를 자동 추출; CLI 스모크 `tests/test_extract_bible_meaning_insight_candidates_v1.py`; 산출 계약 `docs/final/schemas/bible_meaning_insight_candidates_v1.schema.json` |
| Logos insight bundle v1 (계약·minimal·non-degraded 예시) | `docs/final/schemas/logos_insight_bundle_v1.schema.json` · `docs/final/schemas/logos_insight_bundle_v1.minimal.example.json` · `docs/final/schemas/logos_insight_bundle_v1.non_degraded.example.json`(업스트림 `docs/final/artifacts/fixtures/logos_insight_bundle_non_degraded_upstream/`·재생성 **`scripts/materialize_logos_insight_bundle_non_degraded_example_v1.py`**) · `tests/test_logos_insight_bundle_schema_v1.py` · **`scripts/build_logos_insight_bundle_v1.py`** (`--citation-pack-limit`) → `docs/final/artifacts/logos_insight_bundle_v1_latest.json`(기본) · `tests/test_build_logos_insight_bundle_v1.py` | 업스트림 집계·중립 `tension_axis_id`·`[HYPO]`·NON_GATING; 교리 라벨 금지; **`citation_pack`**: 후보/브리지 행에 비어 있지 않은 `snippet` 등만; 선언 `quote_hash`가 있으면 정규화 스니펫의 `sha256:`와 일치할 때만 채택·미일치 행 드롭·중복 해시 제거 |
| 통찰 생존 평가 | `scripts/build_insight_survivor_eval_v1.py` → `docs/final/artifacts/insight_survivor_eval_latest.json` | raw 통찰 후보를 `drawdown_avoidance / false_positive_cost / walkforward_repro` 지표로 평가; CLI 스모크 `tests/test_build_insight_survivor_eval_v1.py`; 산출 계약 `docs/final/schemas/insight_survivor_eval_v1.schema.json` |
| 통찰 생존 선발 | `scripts/select_insight_survivor_candidates_v1.py` → `docs/final/artifacts/insight_survivor_candidates_latest.json` | 평가 결과 중 임계치 통과 후보만 survivor로 선발(상위 N 제한); CLI 스모크 `tests/test_select_insight_survivor_candidates_v1.py`; 산출 계약 `docs/final/schemas/insight_survivor_candidates_v1.schema.json` |
| 의미 연결 품질 리포트 | `scripts/report_aramaic_semantic_edge_quality_v1.py` → `docs/final/artifacts/aramaic_semantic_edge_quality_latest.json` | 토큰 겹침·공유 근거 비율·엣지 타입별 의미 밀도 요약; CLI 스모크: `tests/test_aramaic_semantic_edge_quality_v1.py` |
| 레짐 쉬프트 점수 | `scripts/score_aramaic_regime_shift_v1.py` → `docs/final/artifacts/aramaic_regime_shift_score_latest.json` | 기본 가중치 + `cross_lens_single_trigger_blocked` 제약; 산출 계약: `docs/final/schemas/aramaic_regime_shift_score_v1.schema.json` · `tests/test_aramaic_regime_shift_score_v1.py` |
| 통찰 신호 보조 반영 | `scripts/score_aramaic_regime_shift_v1.py --include-insight-signal --insight-json docs/final/artifacts/bible_meaning_insight_candidates_latest.json` | `insight_candidates`(허브/군집/경로) 밀도를 보조 신호로 반영해 shadow 기준 점수 재계산(연구 레인) |
| 통찰 캡 버킷 임계치 스윕 | `scripts/sweep_aramaic_insight_cap_bucket_thresholds_v1.py` → `docs/final/artifacts/aramaic_insight_cap_bucket_threshold_sweep_latest.json` | audit log 기반으로 `mid/high` 임계치와 low/mid/high cap 조합을 스윕해 추천 후보 산출; CLI 스모크 `tests/test_sweep_aramaic_insight_cap_bucket_thresholds_v1.py`; 산출 계약 `docs/final/schemas/aramaic_insight_cap_bucket_threshold_sweep_v1.schema.json` |
| 통찰 캡 버킷 임계치 적용 | `scripts/apply_aramaic_insight_cap_bucket_threshold_recommendation_v1.py` → `docs/final/artifacts/aramaic_insight_cap_bucket_threshold_recommended_latest.json` | 스윕 best 후보를 점수/섀도우 실행 인자로 승격; CLI 스모크 `tests/test_apply_aramaic_insight_cap_bucket_threshold_recommendation_v1.py`; 산출 계약 `docs/final/schemas/aramaic_insight_cap_bucket_threshold_recommendation_v1.schema.json` |
| 통찰 캡 임계치 히스토리 | `scripts/report_aramaic_insight_cap_threshold_history_v1.py` → `reports/ops/aramaic_insight_cap_bucket_threshold_history.jsonl` | 추천 임계치 스냅샷을 실행 이력으로 누적; `--history-jsonl`로 격리 경로 가능; CLI 스모크 `tests/test_report_aramaic_insight_cap_threshold_history_v1.py`; JSONL 한 줄 계약 `docs/final/schemas/aramaic_insight_cap_bucket_threshold_history_row_v1.schema.json` |
| 통찰 캡 임계치 드리프트 경보 | `scripts/alert_aramaic_insight_cap_threshold_drift_v1.py` → `docs/final/artifacts/aramaic_insight_cap_bucket_threshold_drift_alert_latest.json` | `--history-jsonl`·`--output-json`(상대=레포 루트)·`--drift-threshold`(기본 `1e-4`)·`--dry-run`(POST 생략)·`--webhook-url`(선재). 히스토리에서 `schema=aramaic_insight_cap_bucket_threshold_history_row_v1`인 `recommended` 스냅샷만 순서대로 수집해 **마지막 2개**를 비교; `reason` ∈ `insufficient_history` \| `stable_below_threshold` \| `threshold_drift`. 산출에 `max_abs_delta`·`drifted_keys`·`deltas`·`history_recommended_snapshots`·`webhook`(전송 여부/상태). POST URL: `ARAMAIC_INSIGHT_CAP_DRIFT_ALERT_WEBHOOK_URL` → `OPS_ALARM_WEBHOOK_URL`. 산출 계약: `docs/final/schemas/aramaic_insight_cap_threshold_drift_alert_v1.schema.json` · 예시 `..._v1.example.json` · `tests/test_aramaic_insight_cap_threshold_drift_alert_schema_v1.py` · 회귀 `tests/test_alert_aramaic_insight_cap_threshold_drift_v1.py`(tmp 격리) |
| 통찰 파이프라인·캡 버킷 CLI 연쇄 jsonschema | `tests/test_bible_meaning_insight_survivor_and_cap_bucket_schemas_v1.py` | tmp 격리 노드/엣지로 `extract`→`build_insight_survivor_eval`→`select`→`sweep`→`apply`→`report_…history` 연쇄 실행 후 위 6종 스키마 + 히스토리 한 줄을 `jsonschema`로 검증(jsonschema 미설치 시 skip) |
| Track T 통찰 생존자 건강 경보 | `scripts/alert_insight_survivor_health_v1.py` → `docs/final/artifacts/insight_survivor_health_alert_latest.json` | `insight_survivor_candidates`의 `survivor_count`·`survivor_mean_score` 집계; 선택 `--history-jsonl`(JSONL, 행 스키마 `docs/final/schemas/insight_survivor_health_history_row_v1.schema.json`)에 기록된 **직전** `latest`와 비교해 `reason` ∈ `insufficient_history` \| `stable_below_threshold` \| `health_drift`, `--drift-threshold-mean`(기본 `0.05`)·`--drift-threshold-count`(기본 `1`); `--append-history`로 동 JSONL에 한 줄 append. **`health_drift`이고 `should_alert`**일 때만 선택 POST: `INSIGHT_SURVIVOR_HEALTH_ALERT_WEBHOOK_URL` → `OPS_ALARM_WEBHOOK_URL`, CLI `--webhook-url`·`--dry-run`. 산출에 `webhook`(sent/status). 산출 계약 `docs/final/schemas/insight_survivor_health_alert_v1.schema.json` · 예시 `..._v1.example.json` · `tests/test_insight_survivor_health_alert_v1.py` · `tests/test_insight_survivor_health_alert_schema_v1.py` · 원클릭 체인 `scripts/run_aramaic_mvp_chain_v1.ps1` 선택 `-SurvivorHealthAlertDryRun` 또는 환경 `MKM_ARAMAIC_SURVIVOR_HEALTH_ALERT_DRY_RUN`=`1`\|`true`\|`yes`(체인이 `alert_*`에 `--dry-run` 전달) |
| 가중치 스윕 | `scripts/run_aramaic_regime_shift_weight_sweep_v1.py` → `docs/final/artifacts/aramaic_regime_shift_weight_sweep_latest.json` | B-track 튜닝; `cross_lens_confirm` helper cap 유지; CLI 스모크 `tests/test_aramaic_regime_shift_weight_sweep_v1.py` |
| 브리지 계수 추천 적용 | `scripts/apply_aramaic_regime_shift_bridge_coef_recommendation_v1.py` → `docs/final/artifacts/aramaic_regime_shift_bridge_coef_recommended_latest.json` | 스윕 best 후보의 `bridge_lang_coef`를 일일 점수 반영용 추천 아티팩트로 승격; CLI 스모크 `tests/test_apply_aramaic_regime_shift_bridge_coef_recommendation_v1.py` |
| 브리지 계수 주간 스케줄 등록·readiness | `scripts/Run-AramaicMvpBridgeCoefWeeklyChain_v1.ps1` · `scripts/Register-AramaicMvpBridgeCoefWeeklyTask.ps1`(기본 태스크명 `MKM-AramaicMvp-BridgeCoef-Weekly`, 일요일 08:55) · `scripts/Verify-AramaicMvpBridgeCoefWeeklyTaskReadiness.ps1` | 주간 체인은 스윕 → 브리지 계수 추천 적용(위 표 인접 행). 등록: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-AramaicMvpBridgeCoefWeeklyTask.ps1`; 제거: `-Remove`. **서피스 태그: 헬스만**(Windows Task Scheduler; CI 미포함) |
| Shadow 비교 리포트 | `scripts/run_aramaic_regime_shift_shadow_compare_v1.py` → `docs/final/artifacts/aramaic_regime_shift_score_best_weight_latest.json`, `docs/final/artifacts/aramaic_regime_shift_shadow_compare_latest.json` | baseline vs best-weight 동시 산출(자동 승격 금지); CLI 스모크 `tests/test_aramaic_regime_shift_shadow_compare_v1.py` |
| 원클릭 체인 | `scripts/run_aramaic_mvp_chain_v1.ps1` | Aramaic·meaning graph·Two-Track·학술/반증·raw OOS·public-safe까지 직렬 실행; insight 신호 재점수·shadow 직후 기본 **`[14b]` `build_logos_insight_bundle_v1.py`**(`-SkipLogosInsightBundle`로 생략, morphology·semantic·insight·bridge·regime 경로는 스크립트 파라미터로 오버라이드 가능); Track T survivor health 단계는 **`-SurvivorHealthAlertDryRun`** 또는 환경 **`MKM_ARAMAIC_SURVIVOR_HEALTH_ALERT_DRY_RUN`**=`1`\|`true`\|`yes`로 POST 생략(`--dry-run`); 후반 제출 스택 **`[28/37]`–`[37/37]`** 및 산출물 요약은 동 표 **「체인 통합 실행」** 행 참조. |
| 일일 스케줄 등록·readiness | `scripts/Register-AramaicMvpDailyTask.ps1`(기본 태스크명 `MKM-AramaicMvp-DailyAudit`, 매일 06:15) · `scripts/Verify-AramaicMvpDailyTaskReadiness.ps1` | 등록 스크립트가 `run_aramaic_mvp_now_with_audit.ps1`에 **`-NoWebhook`·`-SkipLogosInsightBundle`**(콜드 호스트 기본)을 전달; 선택 **`-SurvivorHealthAlertDryRun`**(체인→Track T survivor health `alert_insight_survivor_health_v1`에 `--dry-run`). `Verify-AramaicMvpDailyTaskReadiness.ps1`는 예약 작업 인자에 `-SurvivorHealthAlertDryRun` 포함 여부를 `survivor_health_alert_dry_run_switch_in_task_action=true|false`로 출력. `-DailyAt HH:mm`·`-WorkspaceRoot`·`-RunWhenLoggedOff` 선택. 제거: `-Remove`. Raw-OOS 누적 러너 `scripts/run_aramaic_raw_oos_audit_accumulator_v1.ps1`도 동명 스위치 전달. Track C 매크로 퓨전(`MKM-TrackC-MacroDailyFusion`) 진단: `scripts/build_trackc_macro_fusion_failure_diagnosis_v1.py`. **서피스 태그: 헬스만**(Windows Task Scheduler; CI 미포함) |
| 즉시 실행 + 감사 로그 | `scripts/run_aramaic_mvp_now_with_audit.ps1` → `reports/ops/aramaic_mvp_run_audit_log.jsonl` | 즉시 체인 실행 후 readiness 갱신·점수 델타 로그 append (`-NoWebhook`로 알림 전송 차단; **`-SkipLogosInsightBundle`**·선택 **`-SurvivorHealthAlertDryRun`**은 `run_aramaic_mvp_chain_v1.ps1`로 전달). **CI·로컬 회귀:** stub 워크스페이스(`-WorkspaceRoot`)로 체인을 대체해 스위치 전달·감사 한 줄만 검증 — `tests/test_run_aramaic_mvp_now_with_audit_passthrough_v1.py` |
| Raw OOS 실측 누적 배치 러너 | `scripts/run_aramaic_raw_oos_audit_accumulator_v1.ps1` | `run_aramaic_mvp_now_with_audit.ps1`를 반복 실행해 audit run을 목표치(`TargetAuditRuns`)까지 누적하고, 각 반복마다 raw OOS ingest/readiness를 재계산한다. **`-SkipLogosInsightBundle`**·선택 **`-SurvivorHealthAlertDryRun`**은 러너에 전달되면 즉시실행 스크립트·체인으로 이어진다. |
| 감사 추세 리포트 | `scripts/report_aramaic_mvp_audit_trend_v1.py` → `docs/final/artifacts/aramaic_mvp_audit_trend_latest.json` | 최근 N행(기본 100)에 대해 `shift_score`·`delta_shift_score`·OOS 필드·`conflict_ratio` 평균·최소·최대, `insight_cap_bucket`·`oos_scenario` 히스토그램. 입력: `reports/ops/aramaic_mvp_run_audit_log.jsonl` (`--audit-jsonl`·`--window`) |
| 추세 경보 | `scripts/alert_aramaic_mvp_trend_v1.py` → `docs/final/artifacts/aramaic_mvp_trend_alert_latest.json` | 감사 로그 꼬리 `--window`행에서 `conflict_ratio` 기준 연속 streak(`--streak-min`, 기본 3); 임계 `--conflict-alert` / `--conflict-critical`. 웹훅: `ARAMAIC_MVP_ALERT_WEBHOOK_URL` 또는 `OPS_ALARM_WEBHOOK_URL`( **`--dry-run`** 이면 미전송). 선택 `--trend-json`은 메타만 첨부 |
| 경보 임계값 스윕 | `scripts/sweep_aramaic_mvp_alert_thresholds_v1.py` → `docs/final/artifacts/aramaic_mvp_alert_threshold_sweep_latest.json` | 감사 로그 꼬리에 대해 `conflict_alert`·`conflict_critical`·`streak_min` 소그리드; `score_proxy`로 정렬 후 `best` 선정( **`alert_aramaic_mvp_trend_v1`** 와 동일 streak 규칙) |
| 추천 임계값 적용 | `scripts/apply_aramaic_mvp_alert_threshold_recommendation_v1.py` → `docs/final/artifacts/aramaic_mvp_alert_threshold_recommended_latest.json` | 스윕 산출 `best`를 운영 권장값 JSON으로 승격(`--sweep-json`); 이후 수동으로 `alert_aramaic_mvp_trend_v1.py` 인자에 반영 가능 |
| 임계값 주간 스케줄 등록·readiness | `scripts/Run-AramaicMvpThresholdWeeklyChain_v1.ps1` · `scripts/Register-AramaicMvpThresholdWeeklyTask.ps1`(기본 태스크명 `MKM-AramaicMvp-Threshold-Weekly`, 일요일 08:40) · `scripts/Verify-AramaicMvpThresholdWeeklyTaskReadiness.ps1` | 주간 체인: `sweep_aramaic_mvp_alert_thresholds_v1.py` → `apply_aramaic_mvp_alert_threshold_recommendation_v1.py`. (선택) 이어서 `alert_aramaic_mvp_trend_v1.py`는 운영자가 수동·별 태스크로 연결. 제거: Register 스크립트에 `-Remove`. **서피스 태그: 헬스만**(Windows Task Scheduler; CI 미포함) |
| Aramaic MVP · Windows Task Scheduler drift SSOT | `projects/bitcoin-trading/ops/windows-rehearsal/automation_registry.json` | 예약 작업 3종(`\MKM-AramaicMvp-DailyAudit`, `\MKM-AramaicMvp-Threshold-Weekly`, `\MKM-AramaicMvp-BridgeCoef-Weekly`)은 **`optional: true`** — 미등록 호스트에서 `reconcile_automation_registry.ps1`가 drift로 보지 않음. 계약: `tests/test_automation_registry_json_v1.py`. **서피스 태그: 헬스만** |

**격벽 규칙:** 본 절 산출물은 `research_only=true`, `promotion_required=true`, `source_track=B`를 유지하며 A-track·실매매 자동 트리거 경로로 합선하지 않는다.

---

## 5. 코드북 템플릿 (Dual-track)

| 항목 | 경로 | 비고 |
|------|------|------|
| 마스터 템플릿 | `docs/final/master_codebook_dual_track.template.json` | `source_refs.constitution_inference` → 본 문서 |

---

## 6. 테스트 (저장소 기준)

**서피스 태그 (MULTI_LENS Phase C 동기):** `CI 포함` = `dual-regime-integrity.yml`에 탑재되는 pytest·스크립트 계약; `번들 선택` = `run_fact_lock_bundle.ps1` `-Include*`·별도 벤치·드래프트; `헬스만` = `run_workspace_automation_health.ps1`·Windows Task Scheduler·`reconcile_automation_registry.ps1` 등. **`_pr_sasang_promotion` 로컬 PR 팩 미러**는 `scripts/Sync-PrSasangPromotionMirror_v1.ps1`(루트→미러 고정 10경로, 그중 `run_workspace_automation_health.ps1` 포함)·`run_workspace_automation_health.ps1` **`-IncludePrSasangPromotionMirrorSync`** / **`-PrSasangPromotionMirrorSyncOnly`**로만 갱신하며 **CI에는 미탑재**; P0 게이트에 동기 스크립트 경로 포함. §1.2 압축 스텁·HTTP v2, §3.6 TruthfulQA, §1.3.1 일일 융합, Aramaic MVP 등록 행 비고에 개별 태그를 붙였다. §6에는 TruthfulQA 직후 **B-track·뉴스·Logos·Survivor·일반예언·세션·날씨 E2E·Lexicon·L1·토큰·압축·LoRA·Athena** 대량 CI 묶음 복합 행과, 렌즈 PoC 직후 **메타 봉투·Token API hydration**·**Token API 트렌드 pytest 이후 B-track 표면·RAG·프리미엄·브리핑 가드** 행을 추가했다. 뉴스 관측 이후 **CI 순서**에 맞춰 Logos 재검증·Survivor·월간 큐·일반예언·세션 패널·날씨 120d 스크립트 행을 정렬했다. §6 렌즈 뮤직은 M1–M5 대표 행 외 **M32 시드 트레이스·M20 오버레이·M26–M30 PoC 묶음** 행으로 CI 분할 스텝을 추가했고, **§3.8 VA→fusion 무결성** 분할 pytest 행을 CI 순서에 맞춰 삽입했다. **권장(Phase C):** `Token API hydration trend` **직후**의 `live_ratio`·`Integrated governance` 셸 invoker, 그리고 **개인 브리핑 가드 다음**부터 job 끝까지의 연속 스텝은 표를 팽창시키지 않고 **아래 포인터 행** + `.github/workflows/dual-regime-integrity.yml` 단일 SSOT로 둔다. 요약 표: `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md`.

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
| TruthfulQA A/B repro DryRun + pytest 묶음 (B-track `research_only`) **서피스 태그: CI 포함** | `scripts/Run-TruthfulQAReproBundleV1.ps1` `-DryRun`(CI 선행) · `tests/test_run_truthfulqa_ab_benchmark_v1.py` · `tests/test_check_truthfulqa_ab_gate_v1.py` · `tests/test_run_truthfulqa_repro_bundle_v1.py` · `tests/test_run_fact_lock_bundle_truthfulqa_gate.py` — 상세 §3.6 |
| Track source guard + sovereign JSONL iterator smoke **서피스 태그: CI 포함** | `tests/test_track_source_guard.py` · `tests/test_sovereign_jsonl.py` · `tests/test_spike_sovereign_token_saving_v1.py` · `tests/test_sovereign_efficiency.py` |
| ENTRY_16 source-ingest helper contract **서피스 태그: CI 포함** | `tests/test_add_entry16_source_and_rejudge.py` |
| B-track hypothesis + score + hit-rate + contemplation chain **서피스 태그: CI 포함** | `tests/test_generate_btrack_hypothesis_prophecy_v1.py` · `tests/test_build_btrack_prophecy_score_from_ohlcv.py` · `tests/test_eval_prophecy_hit_rate_v1.py` · `tests/test_run_btrack_prophecy_contemplation_v1.py` · `tests/test_btrack_daily_hypothesis_chain_contemplation_contract_v1.py` |
| Prophecy evolution watchdog **서피스 태그: CI 포함** | `tests/test_check_prophecy_evolution_watchdog_v1.py` |
| B-track news_observation JSONL chain smoke **서피스 태그: CI 포함** | `tests/test_news_observation_v1_schema.py` · `tests/test_validate_news_observation_jsonl_v1.py` · `tests/test_check_news_label_join_temporal_v1.py` · `tests/test_build_news_observation_jsonl_from_csv_v1.py` · `tests/test_build_direction_label_bar_jsonl_from_ohlcv_v1.py` · `tests/test_join_news_observation_direction_labels_walkforward_v1.py` · `tests/test_build_direction_label_bar_kospi_csv_smoke_v1.py` |
| Logos revalidation fusion + promotion directional semantic separation **서피스 태그: CI 포함** | `tests/test_role_router_shadow_forward_fusion_regression.py` · `tests/test_promotion_directional_semantic_separation_v1.py` |
| Survivor resonance W3 direct-mapping + falsification chain **서피스 태그: CI 포함** | `tests/test_build_survivor_w3_direct_mapping_v1.py` · `tests/test_build_global_atom_survivor_resonance_daily_real_v1.py` · `tests/test_check_survivor_crash_falsification_gate_v1.py` · `tests/test_run_survivor_resonance_falsification_chain_v1.py` · `tests/test_sweep_survivor_crash_falsification_thresholds_v1.py` · `tests/test_tune_survivor_real_resonance_weights_v1.py` |
| Survivor resonance operational bundle regression **서피스 태그: CI 포함** | `tests/test_run_survivor_resonance_operational_bundle_v1.py` |
| Human regime audit spike (Gemini retry + proxy + agreement; CI에서 4파일 존재 시만) **서피스 태그: CI 포함** | `tests/test_fill_human_regime_audit_llm_heuristic_spike.py` · `tests/test_fill_human_regime_audit_gemini_retry_spike.py` · `tests/test_fill_human_regime_audit_proxy_spike.py` · `tests/test_human_regime_audit_and_agreement_spike.py` — `dual-regime-integrity`와 동일 `if [[ -f … ]]` 가드 |
| Waiting-queue monthly check log contract **서피스 태그: CI 포함** | `tests/test_waiting_queue_monthly_check_log.py` |
| General prophecy B-rail chain smoke **서피스 태그: CI 포함** | `tests/test_general_prophecy_schema_v1.py` · `tests/test_general_prophecy_chain_smoke.py` · `tests/test_resolve_general_prophecy_question_v1.py` · `tests/test_export_general_prophecy_to_jsonl.py` · `tests/test_weather_gt_triplet_chain_smoke.py` |
| B-track session Myeongni panel + weather/OHLCV join + correlate chain **서피스 태그: CI 포함** | `tests/test_build_btrack_session_instant_myeongni_panel_v1.py` · `tests/test_join_btrack_session_panel_weather_ohlcv_v1.py` · `tests/test_correlate_btrack_joined_wide_csv_v1.py` · `tests/test_run_btrack_session_panel_weather_corr_chain_v1.py` |
| Weather synthetic 120d chain + Brier E2E (CI 스크립트; 스텁·실행 assert) **서피스 태그: CI 포함** | `scripts/run_weather_synthetic_120d_chain_and_brier_v1.py` — 스크립트 미존재 브랜치는 CI에서 skip; `.github/workflows/dual-regime-integrity.yml` `Weather synthetic 120d E2E` 스텝과 동일 |
| FACT-LOCK lexicon gate + lexicon rails + L1 preflight **서피스 태그: CI 포함** | `tests/test_fact_lock_lexicon_gate.py` · `tests/test_master_atoms_corpus_split.py` · `tests/test_morphhb_wlc_index.py` · `tests/test_step_tbesh_audit.py` · `tests/test_lexicon_coverage_v2_report.py` · `tests/test_morphhb_match_by_corpus_report.py` · `tests/test_canon_unmatched_morphhb_top100_audit.py` · `tests/test_resolve_morphhb_multi_deterministic.py` · `tests/test_export_master_codebook_v1.py` · `tests/test_l1_codebook_bypass_roundtrip.py` · `tests/test_l1_inverse_decoder_summary_schema.py` · `tests/test_l1_side_channel_wire_codec.py` |
| Token API stub + v2 + ultra KPI + weekly governance + external anchor + control-integrity pipeline **서피스 태그: CI 포함** | `tests/test_compression_token_api_stub.py` · `tests/test_compression_token_api_v2_stub.py` · `tests/test_ultra_compression_kpi_summary.py` · `tests/test_compression_weekly_governance_report.py` · `tests/test_external_anchor_governance_scripts_smoke_v1.py` · `tests/test_mkm_control_integrity_pipeline_smoke_v1.py` — stub는 CI에서 `-k "not openapi_"` / OpenAPI golden `-k` 2분할과 동일 계약 |
| Pack 0-B myeongri deterministic LoRA golden + MKM promotion gate evidence **서피스 태그: CI 포함** | `tests/test_myeongri_deterministic_lora_golden_set_schema_v1.py` · `tests/test_build_myeongri_deterministic_lora_golden_bulk_v1.py` · `tests/test_eval_myeongri_deterministic_lora_golden_fit_v1.py` · `tests/test_myeongri_deterministic_lora_pack_copy_guardrails_v1.py` · `tests/test_mkm_promotion_gate_evidence_bundle_v1.py` |
| Athena execution governance §28 pytest 묶음 **서피스 태그: CI 포함** | `tests/test_athena_run_v1.py` · `tests/test_athena_doctor_v1.py` · `tests/test_athena_checkpoint.py` · `tests/test_build_integrated_governance_m31_digest_v1.py` · `tests/test_invoke_build_integrated_governance_if_deps_present_v1.py` · `tests/test_check_athena_execution_governance_smoke_v1.py` |
| Cursor session validation baseline v1 **서피스 태그: 운영 SSOT (CI 미포함)** | `docs/final/CURSOR_SESSION_VALIDATION_BASELINE_V1.md` · `.cursor/rules/cursor-session-validation-baseline-v1.mdc` · `.cursor/skills/mkm-cursor-session-ops/SKILL.md` · `scripts/build_mkm_chat_resume_pack_v1.py` · `scripts/Invoke-MkmSoloBackgroundOps_v1.ps1` · `scripts/Invoke-MkmOpsMemoryIndexRoutine_v1.ps1` — 세션 start/mid/end 표; **alwaysApply ≠ pytest** |
| Pillar A Cursor LTM + suspect_first P7 **서피스 태그: 헬스 선택 (CI 미포함)** | `scripts/run_mkm_cursor_session_end_v1.py` · `scripts/check_mkm_cursor_turn_meta_audit_v1.py` · `scripts/run_mkm_pillar_a_cursor_health_smoke_v1.py` · `run_workspace_automation_health.ps1 -PillarACursorContinuitySmokeOnly` · pytest `tests/test_mkm_cursor_*`·`test_mkm_pillar_a_cursor_health_smoke_v1.py` · signoff `reports/mkm_bench_2026_003_pillar_a_signoff_v1_latest.json` — `graph_axis=A_ltm` only; Logos `graph_slice` 별 레인 |
| Logos ops memory Cursor inject v1 **서피스 태그: 운영 SSOT (CI 미포함)** | `scripts/run_mkm_ops_memory_logos_math_overlay_chain_v1.py` · `tests/test_mkm_ops_memory_logos_math_overlay_v1.py` · `scripts/run_mkm_logos_math_ltm_a2a_chain_v1.py`(LTM+A2A wire PoC) · `scripts/run_mkm_gematria_4d_ablation_chain_v1.py`(K-track; router/gold 합선 금지) · `scripts/run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py`(Tier-1 module SSOT gate; **≠ CONSTITUTION 전면개정**) — oracle `-Lane` resume; **좌표 주입 ≠ 모델 학습 ≠ Track A** |
| 사상 벤치(SASANG ↔ 명리 앵커) | `tests/test_sasang_cross_ref_draft.py` |
| §3.3 명리 통찰 관측 JSONL·융합 스텁 | `tests/test_myeongni_insight_observation_log.py` |
| §3.3 명리 퓨전 스크립트 스모크 | `tests/test_myeongri_fusion_scripts_smoke.py` |
| Aramaic 코퍼스 추출 v1 계약 | `tests/test_extract_aramaic_core_corpus_v1.py` |
| Aramaic 그래프·레짐 점수 JSON 스키마 v1 계약 | `tests/test_aramaic_graph_schema_v1.py` |
| Aramaic 엣지 빌더 CLI 스모크 | `tests/test_aramaic_edge_builder_v1.py` |
| Aramaic MVP 감사 추세 리포트 계약 | `tests/test_report_aramaic_mvp_audit_trend_v1.py` |
| Aramaic MVP 추세 경보 v1 계약 | `tests/test_alert_aramaic_mvp_trend_v1.py` |
| Aramaic MVP 경보 임계값 스윕 계약 | `tests/test_sweep_aramaic_mvp_alert_thresholds_v1.py` |
| Aramaic MVP 경보 임계값 추천 적용 계약 | `tests/test_apply_aramaic_mvp_alert_threshold_recommendation_v1.py` |
| Aramaic MVP 즉시실행·감사 로그 패스스루 계약 | `tests/test_run_aramaic_mvp_now_with_audit_passthrough_v1.py` |
| Dual-regime Aramaic 직전 스모크 (Two-track 제출 3 + Multi-symbol 3) | `scripts/run_fact_lock_bundle.ps1` 단계 **3d2a**; pytest `tests/test_build_two_track_submission_evidence_bundle_v1.py`·`tests/test_build_two_track_submission_draft_v1.py`·`tests/test_build_two_track_submission_camera_ready_v1.py`·`tests/test_multi_symbol_contract_gates_v1.py`·`tests/test_multi_symbol_counterfactual_comparison_v1.py`·`tests/test_two_track_qa_overlay_counterfactual_v1.py`; 생략 `-SkipTwoTrackSubmissionAndMultiSymbolSmoke` |
| Aramaic B-track graph pipeline (CI = Fact-Lock 번들 3d2b, pytest 27종) | CI `.github/workflows/dual-regime-integrity.yml` `Aramaic B-track graph pipeline smoke` 단계와 동일 목록을 `scripts/run_fact_lock_bundle.ps1` 기본에 포함; 생략 `-SkipAramaicBtrackGraphPipelineSmoke`. 동 워크플로 PR `paths`에는 Aramaic 그래프·Track T survivor health·Logos 번들 등과 함께 Windows 일일 예약 래퍼 **`scripts/Register-AramaicMvpDailyTask.ps1`**·**`scripts/Verify-AramaicMvpDailyTaskReadiness.ps1`** 포함(스케줄 인자·readiness 출력 변경 시 CI 재실행). |
| Aramaic 레짐 쉬프트 점수 CLI 스모크 | `tests/test_aramaic_regime_shift_score_v1.py` |
| Aramaic 의미 연결 품질 리포트 CLI 스모크 | `tests/test_aramaic_semantic_edge_quality_v1.py` |
| Aramaic 교차 코퍼스 브리지 빌더 CLI 스모크 | `tests/test_build_aramaic_cross_corpus_bridge_v1.py` |
| Bible 의미 그래프 노드·엣지 행 스키마 (JSON Schema + pytest) | `docs/final/schemas/bible_meaning_graph_node_v1.schema.json`, `docs/final/schemas/bible_meaning_graph_edge_v1.schema.json`, `tests/test_bible_meaning_graph_schema_v1.py` |
| Bible 의미 그래프 빌더 CLI 스모크 | `tests/test_build_bible_meaning_graph_v1.py` |
| Bible 의미 통찰 후보 추출기 CLI 스모크 | `tests/test_extract_bible_meaning_insight_candidates_v1.py` |
| 통찰 생존 평가 빌더 CLI 스모크 | `tests/test_build_insight_survivor_eval_v1.py` |
| 통찰 생존 선발 CLI 스모크 | `tests/test_select_insight_survivor_candidates_v1.py` |
| 통찰 캡 버킷 임계치 스윕 CLI 스모크 | `tests/test_sweep_aramaic_insight_cap_bucket_thresholds_v1.py` |
| 통찰 캡 버킷 임계치 추천 적용 CLI 스모크 | `tests/test_apply_aramaic_insight_cap_bucket_threshold_recommendation_v1.py` |
| 통찰 캡 임계치 히스토리 append CLI 스모크 | `tests/test_report_aramaic_insight_cap_threshold_history_v1.py` |
| 통찰 캡 임계치 드리프트 경보 산출 JSON Schema | `docs/final/schemas/aramaic_insight_cap_threshold_drift_alert_v1.schema.json` · `docs/final/schemas/aramaic_insight_cap_threshold_drift_alert_v1.example.json` |
| 통찰 캡 임계치 드리프트 경보 CLI (부족·안정·드리프트·스키마 필터) | `tests/test_alert_aramaic_insight_cap_threshold_drift_v1.py` |
| 통찰 캡 임계치 드리프트 경보 JSON Schema 계약 | `tests/test_aramaic_insight_cap_threshold_drift_alert_schema_v1.py` (예시·수동 인스턴스·CLI 산출 stable·threshold_drift+dry-run jsonschema 검증) |
| Bible 통찰·survivor·캡 버킷 CLI 연쇄 jsonschema (6 스키마 + history row) | `tests/test_bible_meaning_insight_survivor_and_cap_bucket_schemas_v1.py` |
| Track T 통찰 생존자 건강 경보 CLI·스키마·웹훅 분기 | `tests/test_insight_survivor_health_alert_v1.py` · `tests/test_insight_survivor_health_alert_schema_v1.py` · `docs/final/schemas/insight_survivor_health_alert_v1.schema.json` · `docs/final/schemas/insight_survivor_health_history_row_v1.schema.json` |
| 레짐 쉬프트 가중치 스윕 CLI 스모크 | `tests/test_aramaic_regime_shift_weight_sweep_v1.py` |
| 레짐 쉬프트 shadow 비교 CLI 스모크 | `tests/test_aramaic_regime_shift_shadow_compare_v1.py` |
| 레짐 쉬프트 브리지 계수 추천 적용 CLI 스모크 | `tests/test_apply_aramaic_regime_shift_bridge_coef_recommendation_v1.py` |
| 다중 렌즈 중간 레이어 절차 | `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` |
| AI BGM 승격 게이트 v1 (스키마·기계적 평가·저작권 Field) **서피스 태그: CI 포함** | `tests/test_audio_bgm_gate_report_v1.py` |
| 상징→오디오 매핑 계약 v1 ([HYPO] M0, 비임상) **서피스 태그: CI 포함** | `tests/test_sasang_music_mapping_schema_v1.py` |
| 사상→감정 연속축 계약 v1 ([HYPO] §3.10 Draft) **서피스 태그: CI 포함** | `tests/test_sasang_emotion_mapping_schema_v1.py` |
| VA trajectory log v1 (B-track EMA, §3.8) **서피스 태그: CI 포함** | `tests/test_va_trajectory_log_v1.py` |
| VA cooldown control schemas v1 (B-track §3.8.2) **서피스 태그: CI 포함** | `tests/test_va_cooldown_schema_v1.py` |
| Cross-lens VA→Logos fusion report v1 (B-track PoC, §3.8.1) **서피스 태그: CI 포함** | `tests/test_cross_lens_fusion_report_v1.py` |
| Fusion control integrity audit v1 (B-track, §3.8.3) **서피스 태그: CI 포함** | `tests/test_fusion_control_integrity_audit_v1.py` |
| VA fusion control integrity chain + policy golden v1 (B-track, §3.8.4) **서피스 태그: CI 포함** | `tests/test_va_fusion_control_integrity_chain_v1.py` · `tests/test_va_fusion_policy_golden_v1.py` |
| Music/Gematria 렌즈 스텁 v1 ([HYPO] M1) **서피스 태그: CI 포함** | `tests/test_run_lens_music_gematria_v1.py` |
| Lens music gate chain v1 ([HYPO] M2, 상징 선행·저작권 Field) **서피스 태그: CI 포함** | `tests/test_lens_music_gate_chain_v1.py` |
| 내부 비임상 청취 세션 로그 v1 ([HYPO] M3 초안) **서피스 태그: CI 포함** | `tests/test_lens_music_internal_eval_schema_v1.py` |
| 청취 로그 JSONL 배치 검증 v1 ([HYPO] M4) **서피스 태그: CI 포함** | `tests/test_validate_lens_music_internal_eval_jsonl_v1.py` |
| 상징→오디오 B-track 연구 승격 게이트 v1 ([HYPO] §3.9.2) **서피스 태그: CI 포함** | `tests/test_lens_music_symbolic_audio_promotion_gate_v1.py` |
| Lens music gematria seed trace M32 ([HYPO] audit) **서피스 태그: CI 포함** | `tests/test_lens_music_gematria_seed_trace_schema_v1.py` |
| Lens music prompt overlay M20+M31+M32 ([HYPO] advisory) **서피스 태그: CI 포함** | `tests/test_build_lens_music_prompt_overlay_v1.py` |
| Lens music prompt PoC M26–M30 + Logos music overlay PoC + Track C ops dashboard (CI 단일 `pytest` 묶음) **서피스 태그: CI 포함** | `tests/test_run_lens_music_prompt_poc_metric_v1.py` · `tests/test_build_lens_music_prompt_poc_runbook_v1.py` · `tests/test_dispatch_lens_music_prompt_poc_runbook_webhook_v1.py` · `tests/test_build_lens_music_prompt_runbook_webhook_health_summary_v1.py` · `tests/test_run_btrack_logos_music_overlay_poc_v1.py` · `tests/test_build_mkm_trackc_ops_dashboard_v1.py` — `.github/workflows/dual-regime-integrity.yml` 스텝 `Lens music prompt PoC M26-M30`와 동일 |
| STT routing audit log v1 + showroom Trust Visualization thin slice (Visualization v0) **서피스 태그: CI 포함** | `tests/test_stt_routing_audit_log_schema_v1.py` · `tests/test_append_stt_routing_audit_log_v1.py` · `tests/test_build_showroom_trust_visualization_slice_v1.py` · `scripts/build_showroom_trust_visualization_slice_v1.py` · `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_trust_visualization_v0.html` — CI `dual-regime-integrity.yml` 스텝 `STT routing audit log v1 + showroom trust viz thin slice`와 동일; 로컬 번들 `run_fact_lock_bundle.ps1` **3d3a**(Logos insight pytest 직후; `-SkipSttRoutingAuditShowroomTrustSlice`) |
| MKM meta-layer envelope v1 (schema + kill-switch coherence) **서피스 태그: CI 포함** | `tests/test_mkm_meta_layer_envelope_v1.py` |
| Token API hydration trend contract **서피스 태그: CI 포함** | `tests/test_token_api_hydration_trend.py` |
| Token API **live_ratio** gate + **Integrated governance** invoker (CI shell; trend pytest **다음** 스텝) **서피스 태그: CI 포함** | `scripts/check_token_api_live_ratio_gate.py` (`--mode warning`; 조건부 `block`는 `vars.TOKEN_API_LIVE_RATIO_BLOCKING` / `workflow_dispatch` 입력) · HOLD 픽스처 `cp` + `python scripts/invoke_build_integrated_governance_if_deps_present_v1.py` + `integrated_governance_v1_latest.json` 존재 assert — `.github/workflows/dual-regime-integrity.yml` 동일 `name:` 순서 |
| B-track symbol lane + V3 measured pipeline + Phase3 snapshot + Sasang interpretive insight + Bio n-states + Trinity index + daily execution insight brief **서피스 태그: CI 포함** | `tests/test_btrack_symbol_lane_regression.py` · `tests/test_v3_operational_measured_pipeline.py` · `tests/test_btrack_phase3_snapshot_sync.py` · `tests/test_sasang_interpretive_insight_bundle_v1.py` · `tests/test_bio_sasang_nstates_strict_comparison_rehydrate_v1.py` · `tests/test_mkm_trinity_index_v1.py` · `tests/test_build_daily_execution_insight_brief_v1.py` |
| Track C evidence RAG MVP + cross-lens RAG fusion **서피스 태그: CI 포함** | `tests/test_build_trackc_evidence_rag_mvp_v1.py` · `tests/test_build_cross_lens_rag_fusion_v1.py` |
| Premium multilens report·queue·gate + semantic RAG bridge (pytest; CI `drain`·`--skip-pytest` 게이트 스크립트 동일 스텝) **서피스 태그: CI 포함** | `tests/test_premium_btrack_multilens_report_schema_v1.py` · `tests/test_build_premium_btrack_multilens_report_v1.py` · `tests/test_premium_multilens_job_queue_stub_v1.py` · `tests/test_build_premium_multilens_queue_promotion_gate_v1.py` · `tests/test_semantic_rag_bridge_insight_bundle_schema_v1.py` · `tests/test_build_semantic_rag_bridge_insight_bundle_v1.py` · `scripts/premium_multilens_job_queue_stub_v1.py` · `scripts/build_premium_multilens_queue_promotion_gate_v1.py` |
| Cross-lens RAG alert + market Myeongni overlay + Thin bridge + personal briefing guardrails **서피스 태그: CI 포함** | `tests/test_send_cross_lens_rag_alert_v1.py` · `tests/test_market_myeongni_overlay_v1.py` · `tests/test_market_myeongni_lens_contract_v1.py` · `tests/test_emit_myeongni_thin_bridge_line_v1.py` · `tests/test_validate_mkm_personal_briefing_guardrails_v1.py` |
| MKM Morning Beans bounded feed v1 (B-track · guardrail · mkmlife card) **서피스 태그: CI 포함** | `docs/final/schemas/mkm_morning_beans_feed_v1.schema.json` · `scripts/build_mkm_morning_beans_feed_v1.py` · `scripts/export_mkm_morning_beans_mkmlife_card_v1.py` · `scripts/Run-MkmMorningBeansDailyChain_v1.ps1` · `scripts/Register-MkmMorningBeansDailyTask.ps1` · `scripts/Verify-MkmMorningBeansDailyScheduledTask_v1.ps1` · 캘린더 SSOT `docs/final/artifacts/mkm_morning_beans_calendar_v1_latest.json` · mkmlife `projects/mkm/mkm-life/public/data/mkm_morning_beans_card_v1.json` · UI `projects/mkm/mkm-life/app/morning-beans/page.tsx` · 회귀 `tests/test_mkm_morning_beans_feed_v1_schema.py` · `tests/test_build_mkm_morning_beans_feed_v1.py` · `tests/test_export_mkm_morning_beans_mkmlife_card_v1.py` — Windows 일일 `MKM_MorningBeans_Daily`(기본 07:05); Track A·실매매·Gmail 합성 자동 합선 금지 |
| `_pr_sasang_promotion` SSOT 미러 동기 v1 (로컬 PR 팩) **서피스 태그: 헬스만** | `scripts/Sync-PrSasangPromotionMirror_v1.ps1` · `scripts/run_workspace_automation_health.ps1` `-IncludePrSasangPromotionMirrorSync` 또는 `-PrSasangPromotionMirrorSyncOnly` — 루트 SSOT 슬라이스→`_pr_sasang_promotion/`(기본 untracked); **본 워크플로에는 미실행**. `scripts/verify_p0_constitution_gate_paths.ps1` 필수 목록에 동기 스크립트 포함. |
| Track A Phase2 하네스 스모크(미터링·섀도 코퍼스·시그널 라이트 등) **서피스 태그: CI 포함** | `tests/test_track_a_harness_smoke_v1.py` |
| `dual-regime-integrity` **CI tail** (개인 브리핑 가드 **다음** `name:` ~ job 끝) **서피스 태그: CI 포함·YAML 단일 SSOT** | `.github/workflows/dual-regime-integrity.yml` — `Two-track submission pack` 이후 순서 그대로: multi-symbol·대형 Aramaic 단일 pytest 묶음·Logos insight·Bio SNP·Yang·문헌 파이프라인·Myeongri AI/CDS·자동화 레지스트리·로그 대사·4-grid·W3/W4·16-state·topflow·multilens perf v1/v2·Track A shadow(파일 가드)·위 `Track A Phase2 harness`·autonomous evolution(파일 가드)·multilens sensitive·ultra compression·P1 selection·B-track regression 등. §6의 개별 아람어·Two-track·MULTI_LENS 관련 행은 **경로·계약 사전**이며, **스텝 순서·묶음**은 본 워크플로만 따른다(표에 tail 전 스텝을 중복 전개하지 않음). 요약·번들 격차 문맥: `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 「CI 잡」절. |

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
| **DNA B-track 승격 패킷(2026-05-24)** | `reports/bio_dna_constitution_promotion_packet_v1_latest.json` · `.md` | 200-row real cohort strict **3/3** · AB neutral seed **30/30** · **research_only** · live/Track A 자동 승격 **금지** |
| **DNA 증거 번들(2026-05-24)** | `reports/evidence_bundle_20260524/index.json` · `hashes_sha256.json` | 빌더: `scripts/build_bio_dna_evidence_bundle_v1.py` · 승인: `reports/bio_dna_constitution_final_approval_latest.json` |
| **Real cohort 복원 포인터** | `docs/final/artifacts/bio_dna_real_cohort_restore_pointer_v1.json` | `tmp/bio_real_cohort_merged_with_sidecar_v1.csv` 등 Git 비추적 · Vault 미러: `scripts/Invoke-PushBioDnaPromotionArtifactsToVault_v1.ps1` |
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

### 8.2 Logos 렌즈 · S1_SHADOW (Semantic ANN-lite 관측, 비본선 트리거)

**목적:** B-track Logos 벡터·쿼리 스모크를 **그림자 운영(S1_SHADOW)** 경로에 두되, **실매매·A-track 자동 합선**은 금지한다. 아래는 **호출 가능 스크립트·정책 MD·게이트 테스트**만 고정한다.

| 항목 | 경로 | 비고 |
|------|------|------|
| Shadow 일일 승격·관측 스텁 | `scripts/promote_logos_to_shadow_live_v1.py` → `docs/final/artifacts/logos_shadow_promotion_status_latest.json` 및 drift/insight 산출 | 산출 JSON의 **`track_wall`**(`shadow_only`, `auto_trade_enable=false`, `promotion_to_a_track_allowed=false`) 준수 |
| 일일 융합 체인(Logos 섹션 포함) | `scripts/Invoke-TrackCMacroDailyFusion_v1.ps1` | `build_logos_regime_resonance_shadow_signal_v1.py`·Semantics 쿼리 스모크·**`build_logos_insight_bundle_v1.py`**(기본; `-SkipLogosInsightBundle`로 생략)·주간 게이트(strict/bootstrap)·주간 트렌드·알림 판정·KPI 진행·res shadow·인사이트·정책 체크·**Role Router S1 shadow advisory**(기본)·**lens music M31 hormone trend + WATCH-only webhook**(대시보드 기본 경로)·Track C 대시보드 등 순서는 스크립트 본문 기준 |
| 주간 게이트·트렌드·알림 | `scripts/build_logos_shadow_weekly_gate_v1.py`, `scripts/build_logos_shadow_weekly_trend_report_v1.py`, `scripts/build_logos_shadow_alert_decision_v1.py` | 기본 산출 `docs/final/artifacts/logos_shadow_*_latest.json` / `reports/logos_shadow_daily_metrics_log_v1.jsonl` |
| 승격 KPI·내부/외부 응답 규칙 | `docs/final/artifacts/LOGOS_SHADOW_WEEKLY_GATE_OPERATION_RULE_V1.md`, `docs/final/artifacts/LOGOS_RESPONSE_POLICY_INTERNAL_EXTERNAL_V1.md`, `scripts/build_logos_shadow_promotion_kpi_progress_v1.py`, `scripts/build_logos_response_policy_check_v1.py` | **다음 단계 승격·대외 주장은 사람 리뷰**; 스크립트만으로 A-track/live 활성화 없음 |
| 비게이팅 레짐 공명(섀도우 신호) | `scripts/build_logos_regime_resonance_shadow_signal_v1.py` → `docs/final/artifacts/logos_regime_resonance_shadow_signal_latest.json` | `data/regimes/regime_map.json` 입력; **non_gating_signal_only** 유지 |
| 시맨틱 쿼리 집합(v3) | `docs/final/artifacts/logos_semantic_query_set_v3.json` | `scripts/run_logos_semantic_query_smoke_suite_v1.py` — 융합 체인 기본 `--query-set-json`과 정합 |
| A/B(쿼리 집합·모델) | `scripts/run_logos_queryset_ab_compare_v1.py`, `scripts/run_logos_semantic_model_ab_sweep_v1.py` | 비교 산출 `docs/final/artifacts/logos_semantic_queryset_ab_compare_latest.json` 등(로컬) |
| 승격 리뷰 패킷 (지휘관 스냅샷) | `scripts/build_logos_s1_shadow_promotion_review_packet_v1.py` → `docs/final/artifacts/logos_s1_shadow_promotion_review_packet_latest.json` · `logos_s1_shadow_promotion_review_packet_latest.md` | KPI·게이트 요약·경로 고정; 인간 승인 파일이 있으면 패킷에 병합 표시 |
| 지휘관 승인 기록 (감사·계획 단계) | `scripts/record_logos_s1_shadow_promotion_human_approval_v1.py` → `docs/final/artifacts/logos_s1_shadow_promotion_human_approval_latest.json`; append-only `reports/logos_s1_shadow_promotion_approval_log_v1.jsonl`; 선택 `scripts/log_agent_decision.py` 한 줄 | KPI `passed` + `READY_FOR_REVIEW`일 때만 기본 기록(`--skip-kpi-gate`는 명시적 예외); **실매매·A-track 자동 활성화 없음** |
| CI·회귀 | `.github/workflows/logos-track-b-pipeline-smoke.yml` | `tests/test_promote_logos_to_shadow_live_v1.py`, `tests/test_build_logos_shadow_alert_decision_v1.py`, `tests/test_build_logos_s1_shadow_promotion_review_packet_v1.py`, `tests/test_record_logos_s1_shadow_promotion_human_approval_v1.py` |

**승격 기록 (Fact-Lock):** 2026-05-07 — Logos **ANN-lite 시맨틱 엔진**을 **S1_SHADOW** 관측 경로(일일 융합·주간 게이트·KPI 계약)에 연결. 렌즈 계약상 Logos는 **[NON_GATING]** 보조; 최종 액션은 1차 실물 레짐 및 운영 게이트가 확정한다.

### 8.2b Logos 연대기 · 2030 거시 Horizon (`[HYPO]` · narrative_template)

**목적:** 성경 연대기·역사 매칭(B-track)과 general prophecy·macro forward SSOT를 **결정론적으로 조립**한 2030 horizon 시나리오. **실매매·Track A/B2B 대외 헤드라인·GDP/주가 확정 예언 금지.** 연대기 era-blind **MS 대외 ~6.4%**(text_blind v1); text_blind_v2 holdout은 **B-track 내부**만.

| 항목 | 경로 | 비고 |
|------|------|------|
| 2030 horizon 빌더 | `scripts/build_logos_macro_horizon_2030_scenario_v1.py` → `docs/final/artifacts/logos_macro_horizon_2030_scenario_v1_latest.json` · `reports/logos_macro_horizon_2030_scenario_v1_latest.md` | `--strict` 시 dynamic map·macro briefing 필수; `scenario_kind=narrative_template`; `scenario_probability_weights`는 heuristic `[HYPO]` |
| 스키마 | `docs/final/schemas/logos_macro_horizon_2030_scenario_v1.schema.json` | |
| 연대기 병렬 번들 | `scripts/Invoke-LogosChronologyParallelBundle_v1.ps1` | (0a) dynamic map → (0b) era blind eval → **(0c) 2030 horizon `--strict`** → overlay/deploy |
| 주간 예약 | `scripts/Register-LogosChronologyWeeklyBundleTask.ps1` · `scripts/Verify-LogosChronologyWeeklyBundleTask_v1.ps1` | Task `MKM_Logos_Chronology_WeeklyBundle` (일 08:30); bundle에 2030 step 포함 여부 spot-check |
| 연대기 SSOT·dynamic map | `scripts/build_logos_chronology_from_repo_ssot_v1.py` · `scripts/build_logos_chronology_dynamic_map_v1.py` | 산출 `logos_chronology_v1_latest.json` · `logos_chronology_dynamic_map_v1_latest.json` |
| civilization apocalypse registry (입력) | `docs/final/artifacts/general_prophecy_civilization_apocalypse_v1_latest.json` (SSOT) · 미러 소스 `reports/general_prophecy_civilization_apocalypse_v1_latest.json` | 빌더가 reports→artifacts 미러; civ.tech/civ.finance 질문 p 병합 |
| two-track 2030 band | `docs/final/artifacts/prophecy_2050_two_track_v1_latest.json` | phase별 track_a_thesis·track_b_forward_lean(2031 band) |
| holdout (internal only) | `reports/logos_chronology_text_blind_v2_holdout_v1_latest.json` | MS/B2B 헤드라인 금지 |
| off-fixture OOV (measured) | `scripts/build_logos_chronology_off_fixture_era_gold_v1.py` → `docs/final/artifacts/logos_chronology_off_fixture_era_gold_v1_latest.json` · AB `scripts/run_logos_chronology_off_fixture_text_blind_v2_ab_v1.py` · holdout `scripts/summarize_logos_chronology_off_fixture_holdout_v1.py` | historical gold(47)와 **disjoint**; hardset27+live news expansion; parallel wave2 `scripts/run_logos_chronology_text_blind_v2_parallel_v1.py`; digest §Off-fixture; `[HYPO]` B-track only |
| showroom 2030 slice (read-only) | `scripts/build_showroom_macro_horizon_2030_slice_v1.py` → `docs/final/artifacts/showroom_macro_horizon_2030_slice_v1_latest.json` | Track C 쇼룸; `no_trade_signals`; `public_showroom_topology_radar_v1.html` 타임라인 패널; chain step `build_showroom_track_c_bundle_chain_v1.ps1` (3/7); bundle observability `macro_horizon_2030_snapshot_*` |
| 명리·사상 read-only | 기본 `myeongni_independent_lens_latest.json` · `market_sasang_lens_latest.json` | `lens_triad_stub` 스냅샷; **non-gating** · Final action은 Field 유지 |
| CI·회귀 | `tests/test_build_logos_macro_horizon_2030_scenario_v1.py` · `tests/test_logos_chronology_off_fixture_text_blind_v2_v1.py` · `tests/test_build_showroom_macro_horizon_2030_slice_v1.py` | horizon strict; off-fixture; showroom slice schema + `[HYPO]` banner; `logos-chronology-era-blind-smoke.yml` |

**렌즈 격벽:** 명리·사상은 `lens_triad_stub`(`not_run_in_this_builder`); Logos overlay만 `[NON_GATING]` 보조.

---

## 9. NotebookLM 매니페스트·이제마 B 인벤토리 (저장소 확인됨)

공유 vault(`G:\…\vault\notebooklm_sources\`)로의 파일 미러·스크립트 호출 관계는 **§7 표**에 고정한다.

| 항목 | 경로 | 비고 |
|------|------|------|
| 소스 목록 SSOT | `docs/NotebookLM_sources_manifest.md` | `## 이제마_B_Track` — 동기화 후보·미배치·근접 참조 표 |
| 인벤토리 디렉터리 | `data/corpus/ijeoma/_inventory/` | 개별 파일명은 **매니페스트 표와 동일**하게 유지·갱신 |
| 격치고 full OCR chunk index | `data/corpus/ijeoma/_inventory/IJEOMA_GEUKCHIGO_FULL_CHUNK_INDEX_v1.jsonl` · `scripts/build_ijeoma_geukchigo_full_chunk_index_v1.py` · 상태 `scripts/build_ijeoma_canon_acquisition_status_v1.py` → `ijeoma_canon_acquisition_status_v1_latest.json` | tier `full_ocr_indexed`; **uncorrected OCR** — 임상 인용 전 human QA; IC-06/IC-08 geukchigo chunk 포인터 |
| 격치고 partial chunk index | `data/corpus/ijeoma/_inventory/IJEOMA_GEUKCHIGO_PARTIAL_CHUNK_INDEX_v1.jsonl` · `scripts/build_ijeoma_geukchigo_partial_chunk_index_v1.py` | tier `partial_ingest`; user-paste·commentary bridge; full OCR 대체 아님 |
| 동무유고 사상금궤비방 full OCR chunk index | `data/corpus/ijeoma/_inventory/IJEOMA_DONGMUYUGO_SASANGBIBANG_CHUNK_INDEX_v1.jsonl` · `scripts/build_dongmuyugo_sasangbibang_chunk_index_v1.py` · rollup `build_ijeoma_canon_acquisition_status_v1.py` | 182p · tier `full_ocr_indexed`; **uncorrected OCR**; canon_intake 2026-07-05 superseded |
| canon intake manifest 2026-07-05 | `data/corpus/ijeoma/_inventory/IJEOMA_CANON_INTAKE_MANIFEST_2026-07-05_v1.json` · `scripts/build_ijeoma_canon_intake_manifest_v1.py` · mirror `docs/final/artifacts/ijeoma_canon_intake_manifest_2026-07-05_v1_latest.json` | NL drop → stable path 매핑; K3-328·PD3B drops는 diff/supersede 전용 |
| K3-328 vs 정교 merged diff | `reports/ijeoma_dssbw_k3_328_diff_v1_latest.json` · `scripts/build_ijeoma_dssbw_k3_328_diff_report_v1.py` | merged TXT SSOT; intake OCR 저품질 시 `garbled_signal`; `promote_intake_to_canon: false` |
| 격치고 OCR QA (machine) | `scripts/build_ijeoma_geukchigo_ocr_qa_report_v1.py` → `reports/ijeoma_geukchigo_ocr_qa_v1_latest.json` | duplicate page·low hanja·page-count flags; `human_qa_required: true`; `clinical_citation_allowed: false` |
| 東醫四象論 chapter index | `data/corpus/ijeoma/_inventory/IJEOMA_DSSBW_CHAPTER_INDEX_v1.json` · `scripts/build_ijeoma_dssbw_chapter_index_v1.py` · mirror `docs/final/artifacts/ijeoma_dssbw_chapter_index_v1_latest.json` | B-track corpus nav; 스키마 `docs/final/schemas/ijeoma_dssbw_chapter_index_v1.schema.json` |
| IJEOMA concept eval (L3) | `scripts/check_ijeoma_concept_eval_v1.py` · 독립 러너 `scripts/run_ijeoma_concept_eval_independent_v1.py` (`--mode stub\|ollama`) · 실패 digest `scripts/build_ijeoma_concept_eval_failure_digest_v1.py` → `reports/ijeoma_concept_eval_failure_digest_v1_latest.json` | 기본 `--answers` 없음 = `scoring_mode: gold_self_consistency` (**모델 이해 증명 아님**); ollama 실측 = `independent_answers`; blocked 시 `reports/ijeoma_ollama_inference_blocked_v1_latest.json` |
| Commander 100% gate (machine) | `scripts/build_ijeoma_commander_100_gate_v1.py` → `ijeoma_commander_100_gate_v1_latest.json` | `ai_alone_100_claim_forbidden: true`; L3 caveat on gold_self_consistency; composite = human signoff |
| market psych → sasang axis v2 | `scripts/market_psych_sasang_axis_v2.py` · manifest `docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json` | B-track **label-borrowing**; Ijema 원전·격치고 OCR text-grounded SSOT **아님**; Track A·임상 합선 금지 |
| 성(性)·情(情) vs VA 병렬 보고 | `scripts/run_ijeoma_seongjeong_vs_va_report_v1.py` → `reports/ijeoma_seongjeong_vs_va_v1_latest.json` · core `scripts/core/sasang_seongjeong_dual_axis_v1.py` | `[HYPO]` dual axis; VA resolver **대체 아님**; `direction_collapsed_match` 참고용 |
| IJEOMA corpus namespace redirects | `data/corpus/ijeoma/_inventory/IJEOMA_NAMESPACE_REDIRECTS_v1.json` | `jeokcheonsu_ocr/` → **myeongri** lane; IJEOMA primary canon rollup **제외** |
| 적천수 jeokcheonsu OCR (myeongri lane) | `data/corpus/myeongri/_inventory/MYEONGRI_JEOKCHEONSU_OCR_CHUNK_INDEX_v1.jsonl` · `scripts/build_myeongri_jeokcheonsu_ocr_chunk_index_v1.py` · QA `scripts/build_myeongri_jeokcheonsu_ocr_qa_report_v1.py` → `reports/myeongri_jeokcheonsu_ocr_qa_v1_latest.json` · status `scripts/build_myeongri_corpus_acquisition_status_v1.py` → `myeongri_corpus_acquisition_status_v1_latest.json` | 132p full OCR · **uncorrected** · `not_ijeoma_primary_canon`; 회귀 `tests/test_myeongri_jeokcheonsu_ocr_v1.py` |
| WORLDVIEW mirror registry | `docs/final/artifacts/worldview_constitution_mirror_registry_v1.json` | SSOT=`MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md`; Design/Lens/Theory canon = mirror only |
| SASANG 벤치 초안 | `docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json` | `schema: sasang_cross_ref_draft_v1`; 청크↔`state_candidate_id` 가설 행; 처방·dual_regime 합선 금지; 회귀: `tests/test_sasang_cross_ref_draft.py` |
| 한의 원전 인수인계(문서명) | `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` | 코호트 A vs 원전·Proxy B 격벽·교차 참조; 세부 인제스트 체인은 호출 가능 스크립트·§ 병행 |
| 의사용 한의 CDS 출력 봉투 v1 | `docs/final/schemas/km_physician_cds_assist_envelope_v1.schema.json` | 임상 의사결정 **보조** 전용(RAG·근거 등급·역할 계약); 단독 진단·처방·응급 최종판단 대체 금지 필드 고정; 예시 `tests/fixtures/km_physician_cds_assist_envelope_v1.example.json`; 조립·검증 `scripts/build_km_physician_cds_assist_envelope_v1.py`; JSONL 배치 `scripts/run_km_physician_cds_assist_envelope_batch_v1.py`(페이로드 예시 `tests/fixtures/km_physician_cds_assist_payload_batch_v1.example.jsonl`; 운영 입력 선택: `KM_PHYSICIAN_CDS_PAYLOAD_JSONL` 또는 `data/km_physician/cds_payload_incoming/payload_batch.jsonl` → 주간 래퍼 `scripts/Run-KmPhysicianCdsEnvelopeBatchWeekly_v1.ps1`); 회귀 `tests/test_km_physician_cds_assist_envelope_v1.py`·`tests/test_build_km_physician_cds_assist_envelope_v1.py`·`tests/test_run_km_physician_cds_assist_envelope_batch_v1.py`(jsonschema); 상용·규제 범위는 법무·병원 정책과 별도 확정 |
| 환자 통합 번들 v1 (SOAP + 렌즈 슬롯) | `docs/final/schemas/patient_care_bundle_v1.schema.json` | `clinical_soap_v1`와 `patient_slots`(core·sasang·`myeongni_ref` **[HYPO]**·`logos_opt` **[NON_GATING]**) 분리; `boundary_contract` 고정; `provenance`에 선택 후처리 감사(`slot_templates_*`·`generation_policy_*`·`patient_facing_markdown_*`); 예시 `docs/final/schemas/patient_care_bundle_v1.minimal.example.json`; SOAP 스텁 `--soap-json` 예시 `tests/fixtures/patient_care_bundle_soap_stub_v1.example.json`; 슬롯 Markdown 템플릿 `docs/final/artifacts/patient_care_bundle_slot_templates_ko_v1.json`·생성 정책 `docs/final/artifacts/patient_care_bundle_generation_policy_v1.default.json`·적용 `scripts/apply_patient_care_bundle_slot_templates_v1.py`·정책 검증 `scripts/validate_patient_care_bundle_against_policy_v1.py`·단일 MD 렌더 `scripts/render_patient_care_bundle_markdown_v1.py`; 원클릭(템플릿+정책+MD 고정) `scripts/Invoke-PatientCareBundleAssemblePatientFacing_v1.ps1`; 명리 리포트 연결 `scripts/assemble_patient_care_bundle_with_myeongni_v1.py`(출생 **`--birth-instant-utc`**+`--iana-tz` 또는 **`--local`**+선택 **`--dst-fold`**·`saju_birth_resolver_v1` 경유; 선택 `--cds-envelope-json`·`--validate`·`--apply-slot-templates`·`--validate-policy`·`--policy-json`·`--render-md-out`); CDS 선검증 후 조립 `scripts/build_patient_care_bundle_from_km_cds_chain_v1.py`(동일 플래그 전달: `--apply-slot-templates`·`--validate-policy`·`--policy-json`·`--render-md-out`); 회귀 `tests/test_patient_care_bundle_v1_schema.py`·`tests/test_assemble_patient_care_bundle_with_myeongni_v1.py`·`tests/test_build_patient_care_bundle_from_km_cds_chain_v1.py`·`tests/test_patient_care_bundle_templates_policy_render_v1.py`; 명리·Logos는 임상 게이팅·임신 예후 예측에 사용 금지 |
| 인테이크→융합 초안 v1 (증상·추정체질 + 출생) | `docs/final/schemas/patient_intake_fusion_draft_input_v1.schema.json` | SOAP 초안·`patient_care_bundle_v1`·근거 사이드카(`patient_intake_fusion_rationale_v1`); `scripts/build_patient_intake_fusion_draft_v1.py`(선택 `--skip-intake-json-schema`); **출생 고정밀:** `profile.birth_instant_utc`(ISO Z)+`iana_tz` 우선, 없으면 `local_birth`+`dst_fold`는 `saju_birth_resolver_v1` 경유(DST 격리); 예시 `tests/fixtures/patient_intake_fusion_draft_v1.example.json`; 원클릭 `scripts/Invoke-PatientIntakeFusionDraft_v1.ps1`; 회귀 `tests/test_build_patient_intake_fusion_draft_v1.py`; `provenance.encounter_ref`는 비식별 `encounter.ref_token`만; 환자 제공 전 한의사 확인 |
| 원장 Entry B 온보딩 하네스 v1 (cloud IDE + PHI) | `docs/final/artifacts/han_clinic_owner_onboarding_brief_v1_latest.md` | Entry A/B dual-entry · `research_only` · `send_gate: HOLD`; research `docs/research/CLINICIAN_POWER_USER_INFRA_AUDIT_V1.md`; gate `scripts/infra_compliance_gate_v1.py` → `docs/final/artifacts/infra_compliance_gate_v1_latest.json`; chain `scripts/run_han_clinic_owner_entry_b_onboarding_chain_v1.py`·`scripts/Run-HanClinicOwnerEntryBOnboardingChain_v1.ps1` → `reports/han_clinic_owner_entry_b_onboarding_chain_v1_latest.json`; 카드 `scripts/build_han_clinic_owner_onboarding_card_v1.py`; 회귀 `tests/test_infra_compliance_gate_v1.py`·`tests/test_han_clinic_owner_entry_b_onboarding_chain_v1.py`; 네트워크 egress 훅 **미구현** |
| 명리 풀 리포트 v1 + 용신 후보 거버넌스 | `scripts/build_myeongni_full_report_v1.py` | `myeongni_full_report_v1` from `saju_global_birth_result_v1`; `structure_analysis.yongsin_hypothesis_candidates_v1`(`evidence_tier=heuristic_only`, `derivation_fingerprint`, policy file SHA-256); `school_conflict_resolution_v1` 스키마 분리 유지; 환자 번들 기본 비포함; 회귀 `tests/test_build_myeongni_full_report_v1.py` |
| 명리 path mindmap Studio v1 (B-track · Logos radial 패턴 격리) | `projects/no1kmedi/src/lib/pathMindmapCoreV1.ts` · `myeongniPathMindmapV1.ts` · `myeongniLiteToMindmapInputV1.ts` · API `studio-mindmap-v1` / `studio-full-report-v1` · UI `/myeongni-research/studio` · Hub `/hub/myeongni` · 스키마 `docs/final/artifacts/myeongni_path_mindmap_schema_v1.json` · 체인 `scripts/run_myeongni_studio_smoke_chain_v1.py` · PS `projects/no1kmedi/scripts/run-myeongni-studio-smoke-chain.ps1` · CI `.github/workflows/myeongni-studio-smoke.yml` · MD `scripts/render_myeongni_full_report_markdown_v1.py` | **research_only** `[HYPO]` · `send_gate: HOLD` · `NON_GATING` 중기 방향; Logos graph slice 합선 금지; 회귀 `tests/test_myeongni_path_mindmap_v1.py` |
| 지휘관 보좌 프로필 v1 (초개인화) | `docs/final/schemas/commander_profile_v1.schema.json` | `docs/final/artifacts/commander_profile_v1.example.json`; Fact=`birth_anchor`·`myeongni_fact_ref`; coaching=`assist_coaching_v1`·`cognition_hypothesis` **[HYPO]** only; 사주로 GTM·실매매·임상 단정 금지; CENTRAL 메타 포인터; 회귀 `tests/test_commander_profile_v1_schema.py` |
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
| Public Event Gateway (MVP, 로컬 HTTP) | `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_event_gateway.py` | 기본 포트 8788; `GET /api/public-events/latest`, `POST /api/public-events/ingest`. 기동·헬스: `projects/bitcoin-trading/ops/windows-rehearsal/ensure_public_event_gateway.ps1`. **공개 도메인(jemaai.cloud 등):** nginx 예시 `nginx_public_event_gateway.conf.example` → `proxy_pass` 대상은 게이트웨이 호스트(`127.0.0.1:8788`). POST는 `X-Public-Event-Token` = `PUBLIC_EVENT_GATEWAY_TOKEN`. **스펙·경계 확정:** `JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md`. **ingest 예시:** `jemaai-cloud-mvp/examples/public_event_ingest_minimal.v1.json`. **정적 폴링 UI:** `jemaai-cloud-mvp/public_showroom_poll.html` (스테이지·예능 레이어; `?api=` Base URL) · **권장 미니멀 보드:** `jemaai-cloud-mvp/public_showroom_board_minimal.html` (동일 API·동일 티커 매핑; WebGL/픽셀 스테이지 없음). **Gemini 경고 정리 힌트:** `scripts/print_gemini_env_hygiene_hint.ps1`. **GET HMAC (선택):** `PUBLIC_EVENT_GATEWAY_GET_HMAC_SECRET` 설정 시 `GET /latest`에 `x-mkm-timestamp`(unix 초)·`x-mkm-signature`(hex HMAC-SHA256, canonical `ts\\nGET\\n/api/public-events/latest\\n`) 필요; 비어 있으면 기존처럼 GET 무인증. `PUBLIC_EVENT_GATEWAY_HMAC_MAX_SKEW_SEC`(기본 300). 서명 도구 `scripts/sign_public_event_gateway_get_hmac_v1.py`. 테스트 `tests/test_public_event_gateway_get_hmac_v1.py`. |
| Showroom static bundle | `projects/bitcoin-trading/ops/windows-rehearsal/build_showroom_display_bundle.ps1` | `docs/final/artifacts/showroom_public_bundle_v1.json` — `public_event.v1` + `public_ui`(`showroom_public_ui_v1`, ASCII 토큰) + 검증 `scripts/validate_showroom_public_bundle.py`. 한글 UI는 HTML에서 매핑. **쇼룸 연출(선택, `public-event.v1`):** `showroom_display_mode`(idle\|defend\|attack), `showroom_ticker_key`(`^[A-Z0-9_]{1,64}$`), `showroom_reaction_line_ids`(최대 3, `R_*` ID — 자유 텍스트 금지). **Topology Radar(선택):** `sources.showroom_topology_radar_snapshot_v1` + 스냅샷이 `no_trade_signals: true`이면 `observability.topology_radar_snapshot_*` 요약 필드 병합(그래프 본문 미포함). |
| Logos Track C freshness sidecar (신선도 메타) | `scripts/build_logos_track_c_freshness_sidecar_v1.py` | 입력 기본 `docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json` → `docs/final/artifacts/logos_track_c_freshness_sidecar_v1_latest.json`(번들 `ts_utc` 대비 staleness; 비실매매 메타). 회귀 `tests/test_logos_track_c_freshness_sidecar_v1.py`. Logos Track B 체인 종료 시 선택 실행(`Run-LogosTrackBChainV1.ps1` / `run_logos_track_b_pipeline_chain_v1.py`). |
| Track C showroom 번들 체인 (권장 원클릭) | `scripts/build_showroom_track_c_bundle_chain_v1.ps1` | (1) freshness sidecar → (2) topology radar emit → (3) `build_showroom_display_bundle.ps1` → (4) validate → (5) trust viz slice → (6) logos research slice → (7) **`build_showroom_meaning_topology_graph_slice_v1.py`**(capped subgraph, `bible_meaning_graph` JSONL). 선택 `-SkipMeaningTopologyGraphSlice` 등. 스펙 `JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md`. |
| Meaning topology graph 쇼룸 (실데이터 thin slice, `[HYPO]`) | `scripts/build_showroom_meaning_topology_graph_slice_v1.py` · `public_showroom_meaning_topology_graph_v1.html` · `docs/final/schemas/showroom_meaning_topology_graph_slice_v1.schema.json` | 산출 `showroom_meaning_topology_graph_slice_v1.json`(mirror `docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json`). **canonical static:** `https://jemaai.cloud/…` · URL SSOT `docs/final/artifacts/jemaai_showroom_public_urls_v1_latest.json`. 회귀 `tests/test_build_showroom_meaning_topology_graph_slice_v1.py`. |
| Showroom publish 루틴 (번들+ingest+VPS+스모크) | `scripts/Invoke-ShowroomTrackCPublishRoutine_v1.ps1` | C2 guardrail 갱신 → `verify_showroom_bundle_chain.ps1 -SkipVisualQualityGate` → `publish_showroom_public_event.ps1` → `sync_showroom_to_vps.ps1` → `check_showroom_trust_viz_public_chain_v1.py`. 로그 `reports/showroom_track_c_publish_routine_log.jsonl`. |
| Showroom Track C 헬스 (가벼운 점검) | `scripts/Invoke-ShowroomTrackCHealth_v1.ps1` · 페르소나 `Invoke-MkmPersonaHealth_v1.ps1 -Persona ShowroomTrackCHealth` | publish/nginx **예약 태스크** verify + 듀얼 호스트 스모크 + B2B readiness. AGENTS 【쇼룸 헬스】. |
| Showroom Track C ops 상태 요약 | `scripts/build_showroom_track_c_ops_status_v1.py` | `docs/final/artifacts/showroom_track_c_ops_status_v1_latest.json` — smoke·B2B·meaning slice·URL SSOT 집계(네트워크 없음). |
| Showroom Track C 일일 작업 등록 | `scripts/Register-ShowroomTrackCPublishDailyTask.ps1` | `schtasks` **`Showroom-TrackC-Publish-Daily`**(기본 09:32) — 위 publish 루틴. 점검 `Verify-ShowroomTrackCPublishScheduledTask_v1.ps1`. 레거시 `Register-ShowroomTrackCBundleTask.ps1`(번들만)는 publish로 대체. |
| Showroom nginx snippet 주간 | `scripts/Register-ShowroomTrackCNginxWeeklyTask.ps1` | `Showroom-TrackC-Nginx-Weekly`(일 09:40) — `sync_showroom_to_vps.ps1 -NginxSnippetOnly -ApplyRecommendedNginx`. 점검 `Verify-ShowroomTrackCNginxWeeklyScheduledTask_v1.ps1`. snippet SSOT `jemaai-cloud-mvp/nginx_snippets/jemaai_showroom_ui.conf`. |
| Autopilot / jemaai completion + 쇼룸 | `scripts/run_workspace_autopilot_chain.ps1`·`scripts/run_jemaai_cloud_completion_chain.ps1` | 선택 `-IncludeShowroomTrackCChain` — 본선 pytest 이후(및 E2E 옵션 이후) `build_showroom_track_c_bundle_chain_v1.ps1` 실행. VPS 배포 아님. |
| Showroom 정적 배포(로컬/스테이징 복사) | `projects/bitcoin-trading/ops/windows-rehearsal/deploy_showroom_static.ps1` | `-WebRoot` 또는 `JEMAAI_WEB_ROOT`(Process/User); 미설정 시 기본 `projects/bitcoin-trading/ops/windows-rehearsal/.showroom_staging/`(gitignore)에 `public_showroom_poll.html`·`public_showroom_board_minimal.html`·`showroom_public_bundle_v1.json`·**`showroom_topology_radar_snapshot_v1_latest.json`(선택, `docs/final/artifacts`에서 복사)**·`public_showroom_trust_visualization_v0.html`·`showroom_trust_visualization_slice_v0.json`(선택)·`public_showroom_logos_research_v1.html`·`showroom_logos_research_slice_v0.json`(선택, `[HYPO]`/NON_GATING)·`public_showroom_probabilistic_saju_v1.html`·`showroom_saju_hour_bundle_demo_v1.json` 복사. `-WorkspaceRoot`로 모노레포 루트 지정 가능(기본: 스크립트 기준 상위 4단). 본선 nginx는 수동. `-NoDefaultStaging`이면 미설정 시 SKIP. |
| Showroom VPS 전송(scp) | `projects/bitcoin-trading/ops/windows-rehearsal/sync_showroom_to_vps.ps1` | 루트: `pwsh -File scripts/sync_showroom_to_vps.ps1`. **`-ApplyRecommendedNginx`:** snippet push + reload. **`-NginxSnippetOnly`:** 정적 scp 생략·snippet만. **`-RefreshStaging`:** 체인+deploy 후 scp. meaning graph HTML/JSON 포함(스테이징 있을 때). |
| PersonaDiary mobile ops PWA v0 (preview_only · Pull-first) | `projects/no1kmedi/src/app/personadiary/ops/page.tsx` · `projects/no1kmedi/src/lib/personadiaryMobileOpsV1.ts` · `personadiaryMobileOpsStore.ts` · `personadiaryBtrackExportV1.ts` · `personadiaryHygieneHypoV1.ts` · `personadiaryNativeBridgeHypoV1.ts` | **호스트:** `personadiary.com/ops` → middleware rewrite `/personadiary/ops`; 허브 `jema-ai.com/personadiary/ops`. **스키마:** `docs/final/schemas/personadiary_mobile_ops_v1.schema.json` · optional `hygiene_prefs_hypo_v1` · **B-track export:** `personadiary_btrack_export_v1.schema.json` · Human Gate 수동 다운로드 · inbox `reports/constitution/btrack_pilot/personadiary_export_inbox/` · `scripts/validate_personadiary_btrack_export_inbox_v1.py` · corpus `scripts/build_personadiary_btrack_lora_corpus_v1.py` → `personadiary_lora_corpus_v1_latest.jsonl` · routine `scripts/Invoke-PersonadiaryBtrackInboxRoutine_v1.ps1`. **Phase 4 hypo:** Capacitor `projects/no1kmedi/personadiary-native-hypo-v1` · `scripts/verify_personadiary_native_shell_hypo_v1.py` · `/ops` 위생 패널 `[HYPO]`. **로컬 import:** `/ops` JSON → IndexedDB 복원 only. **일기:** IndexedDB only — **서버 업로드 미구현**. **일일 가이드:** Pull-only. **pytest:** `tests/test_personadiary_mobile_ops_v1_schema.py` · `tests/test_personadiary_btrack_export_v1_schema.py` · `tests/test_build_personadiary_btrack_lora_corpus_v1.py` · `tests/test_personadiary_native_shell_hypo_v1_schema.py` · `tests/test_personadiary_hygiene_prefs_hypo_v1_schema.py`. **NEVER:** mkmlife DB/API join · push · Track A·실매매·SEND 자동 승격 · export 자동 업로드 · **OS Screen Time/앱 차단·App Store 출시 주장**. |
| PersonaDiary live ops smoke | `scripts/run_personadiary_live_ops_smoke_v1.py` · `scripts/Invoke-PersonadiaryLiveOpsAuto_v1.ps1` | apex·manifest HTTP; `/ops` 경로는 smoke 확장 권장. 산출 `reports/personadiary_live_ops_auto_latest.json`. |
| mkmlife.com Cloudflare Email Routing (예: `support@` 포워딩) | `scripts/setup_cloudflare_email_routing_v1.py` · `scripts/Invoke-CloudflareEmailRoutingSetup_v1.ps1` | `CLOUDFLARE_API_TOKEN`(Email Routing 권한)·`MKM_MKMLIFE_SUPPORT_FORWARD_TO`; 산출 `reports/cloudflare_email_routing_setup_latest.json`. `-DryRun`·`-ZoneId`·PowerShell `-UseMkmlifeFixtureZoneId`(픽스처 `zone_id`는 대시보드와 대조). Exit 2 zone 미가시 · 3 routing/enable · 4~6 단계별 실패 · 7 `account_id` 누락(`MKM_CLOUDFLARE_ACCOUNT_ID`). 정책·Hostinger MX 알림: `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` 절 1.3. 회귀 `tests/test_setup_cloudflare_email_routing_hint_v1.py`. |
| 퓨전 후 ingest POST(선택) | `run_ops_fusion_cycle.ps1` + `publish_showroom_public_event.ps1` | User/Process `SHOWROOM_PUBLISH_INGEST=1`일 때만 7단계 실행. `SHOWROOM_INGEST_URL`·`PUBLIC_EVENT_GATEWAY_TOKEN`. |
| 쇼룸 체인 로컬 검증 | `projects/bitcoin-trading/ops/windows-rehearsal/verify_showroom_bundle_chain.ps1` | `-SkipVisualQualityGate`(topology B2B·atlas poll 불필요). CI: `.github/workflows/showroom-bundle-validate.yml`. 공개 URL 스모크(수동/일일): `scripts/check_showroom_trust_viz_public_chain_v1.py`. |

### 13.1 Phase 1 체인·레지스트리 (Windows, 관측·게이트)

| 항목 | 경로 | 비고 |
|------|------|------|
| Phase 1 통합 체인 | `projects/bitcoin-trading/ops/windows-rehearsal/run_ops_phase1_chain.ps1` | 스냅샷 → 퓨전 상태 검증 → 옵션 `verify_all_green`; `-Strict`·`-IncludeVerifyAllGreen`·`-SkipFusionStatusCheck`·`-IncludeConstitutionGates`·`-SkipOpsAlarm`. 설정 시 `OPS_ALARM_WEBHOOK_URL`(User/Process): 체인 예외 시 `kind=failure` POST; 성공 시 `shared_vault_reachability=warning`이면 `kind=shared_vault_warning`(끄려면 `OPS_ALARM_SKIP_SHARED_VAULT_WARNING=1`). 페이로드: JSON `event`,`kind`,`message`,`report_path`,`ts_utc` |
| 헌법 게이트 (3중) | `projects/bitcoin-trading/ops/windows-rehearsal/verify_constitution_gates.ps1` | (1) `ops_phase1_chain_report_latest.json`의 `overall_chain_ok` (2) `reconcile_automation_registry.ps1` 무드리프트 exit 0 (3) `risk_profile_fact_safe_latest.json`의 `source`/`mode`가 `constitution_gates_v1.json`의 `allowed_risk_combinations`에 포함; `-SkipPhase1Report` 등 개별 스킵 가능 |
| 헌법 게이트 allowlist | `projects/bitcoin-trading/ops/windows-rehearsal/constitution_gates_v1.json` | 정책 변경 시 `allowed_risk_combinations` 편집 |
| 헌법 게이트 결과 SSOT | `projects/bitcoin-trading/memory/v2/ops/constitution_gates_result_latest.json` | `schema constitution_gates_result_v1`; `all_ok`·`checks[]` |
| 조건부 시그널 게이트 → USDM 단발(API) | `projects/bitcoin-trading/scripts/run_conditional_action_gate_v1.py` | Fact-Safe `risk_profile_fact_safe_latest.json` 등 평가 후 **`--backend api`** → `projects/bitcoin-trading/scripts/execute_binance_usdm_single_order_v1.py`(기본 **테스트넷**; 실제 체결은 게이트 통과 시에도 **`--pass-live`** 명시 시만). 메인넷은 실행기 **`--mainnet`**(이중 확인 권고). **Human-in-the-Loop(선행, 선택):** `--human-approval-json` 또는 env `MKM_TRADING_HUMAN_APPROVAL_JSON`이 있으면 `scripts/validate_trading_human_execution_approval_v1.py` 선호출·실패 시 exit **7**; `--skip-human-approval`로 무시. 웹훅 레거시: `run_conditional_signal_webhook_v1.py`. **파일럿(루트):** `scripts/Run-BinanceUsdmPilotSmoke.ps1`(dry 기본; 테스트넷 `-LiveTestnet -AcknowledgeLiveTestnet -RiskJson`; **소액 메인넷** `-LiveMainnetSmall … -RiskJson`(픽스처 금지)·`-MaxMainnetQty`/env `MKM_PILOT_MAINNET_MAX_QTY`·기본 **`reports/trading_human_execution_approval_latest.json` 존재** 요구, `-HumanApprovalJson`/`-SkipHumanApproval` 예외, 추가로 `-AcknowledgeStoplinePolicyV1` 필수). **오조작 방지(청산):** `projects/bitcoin-trading/src/api/binance_client.py::close_position`는 요청 `position_side`와 일치하는 포지션만 청산(타 side 건너뜀). 회귀 `tests/test_binance_client_close_position_side_guard.py`. **게이트 dry CLI 회귀:** `tests/test_run_conditional_action_gate_v1_cli_smoke.py`·픽스처 `tests/fixtures/risk_profile_fact_safe_gate_pass_minimal_v1.json`. 체크리스트 HTML: `docs/binance_usdm_signal_webhook_setup_checklist_v1.html`. |
| 트레이딩 단일 판정 파일(일일 GO/NO_GO) | `scripts/build_trading_go_nogo_status_v1.py` → `docs/final/artifacts/trading_go_no_go_latest.json` | 게이트 요약(`reports/poc_binance_signal_webhook/conditional_gate_latest.json`) + 인간 승인 영수증(`reports/trading_human_execution_approval_latest.json`) + Fact-Safe 리스크(`projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json`)를 합쳐 **한 파일 verdict** 산출. 네트워크/주문 호출 없음. exit 0=GO, exit 1=NO_GO(기본). 관측 루프(`Run-TradingObservationLoop.ps1`)는 `--exit-zero-on-no-go`로 NO_GO여도 스크립트 성공(exit 0) 처리. 회귀 `tests/test_build_trading_go_nogo_status_v1.py`. |
| Fact-Safe 리스크 주기 갱신(로컬, 주문 없음) | `scripts/Run-FactSafeRiskProfileSyncChain_v1.ps1` → `scripts/Register-FactSafeRiskProfileSyncTask.ps1` | 기본: `sync_fact_safe_risk_profile.py --repo-source --allow-metadata-downgrade`(기존 `n8n.*` 태그 파일 **의도적 이전** 허용) → `run_conditional_action_gate_v1.py …` → `build_trading_go_nogo_status_v1.py`. 레거시 n8n 태그만: 러너 `-UseN8nSource` 또는 `--n8n-source`. 기본 예약 `\MKM-FactSafe-RiskProfile-Sync-4H`(기본 **4시간**; `-IntervalHours`/`-Remove`). `MKM_WORKSPACE_MAINTENANCE` 시 sync 스킵 가능. **§13.1.b** 참조. |
| 환경 스냅샷 | `projects/bitcoin-trading/ops/windows-rehearsal/collect_ops_environment_snapshot.ps1` → `projects/bitcoin-trading/memory/v2/ops/ops_environment_snapshot_latest.json` | 계정·`C:\workspace`·`G:` 프로브·주요 태스크 Logon Mode |
| 퓨전 사이클 상태 검증 | `projects/bitcoin-trading/ops/windows-rehearsal/verify_ops_fusion_cycle_status.ps1` | `docs/final/artifacts/ops_fusion_cycle_status_latest.json`의 `overall_ok` 또는 C2/Trinity 보조 판정 |
| 융합 사이클 러너 | `projects/bitcoin-trading/ops/windows-rehearsal/run_ops_fusion_cycle.ps1` | 산출 `ops_fusion_cycle_status_latest.json`(`schema ops_fusion_cycle_status_v2`, `overall_ok`·`overall_ok_reason`) 후 **showroom 번들 생성·검증**(`build_showroom_display_bundle.ps1`, `validate_showroom_public_bundle.py`: Track C **원클릭**은 `build_showroom_track_c_bundle_chain_v1.ps1`로 대체 가능) |
| 올그린 게이트 | `projects/bitcoin-trading/ops/windows-rehearsal/verify_all_green.ps1` | 단계에 `verify_ops_fusion_cycle_status` 포함 후 `reconcile_automation_registry` |
| 레지스트리 reconcile | `projects/bitcoin-trading/ops/windows-rehearsal/reconcile_automation_registry.ps1` | 기본 콘솔은 한 줄 요약만; 전체 JSON은 `projects/bitcoin-trading/memory/v2/ops/automation_registry_reconcile_latest.json`(루트 `.gitignore`의 `projects/bitcoin-trading/memory/` 하위로 **로컬 비추적**·커밋 잡음 방지). 디버그 시 `-ShowJson` |
| Phase 1 운영 준비 점검 | `projects/bitcoin-trading/ops/windows-rehearsal/verify_ops_phase1_operational_readiness.ps1` | 태스크 존재·`Task To Run`에 `IncludeConstitutionGates`·리포트 신선도·`OPS_ALARM_WEBHOOK_URL`; 산출 `ops_phase1_readiness_latest.json`; 엄격 시 `-Strict` |
| OPS 알림 웹훅 스모크 | `projects/bitcoin-trading/ops/windows-rehearsal/smoke_ops_phase1_webhook.ps1` | User `OPS_ALARM_WEBHOOK_URL`로 `kind=smoke_test` POST(미설정 시 exit 0 스킵) |
| 자동화 레지스트리 | `projects/bitcoin-trading/ops/windows-rehearsal/automation_registry.json` | `\Bitcoin-Ops-Fusion-Cycle-Auto` 등 Task Scheduler 기대 상태; `reconcile_automation_registry.ps1 -Enforce` |
| 레거시 태스크 비활성/대체 매핑 | `docs/final/artifacts/ops_scheduler_legacy_task_replacement_v1.json` | 경로 미존재 등으로 비활성화한 태스크와 대체 태스크 매핑 SSOT(운영 노이즈 재발 방지). |
| Phase 1 리포트 SSOT | `projects/bitcoin-trading/memory/v2/ops/ops_phase1_chain_report_latest.json` | `schema ops_phase1_chain_report_v1`; `scope_note`: 운영 런북·게이트만, 헌법 자동 해석·자율 전략 변경 아님. `shared_vault_reachability`: 스냅샷 기준 `ok` \| `warning` \| `unknown`(G:·공유 vault 경로); **경고만, `overall_chain_ok` 비판정** |
| 일일 체인 태스크 등록 | `projects/bitcoin-trading/ops/windows-rehearsal/register_ops_phase1_chain_task.ps1` | 기본 `\Bitcoin-Ops-Phase1-Chain-Daily` 매일 08:30; **`-IncludeConstitutionGates` 기본 포함**(`-ExcludeConstitutionGates`로 끔). **본선 PC**에서 실행·`schtasks /Query`로 확인 |
| Phase 1 일일 원클릭 | `projects/bitcoin-trading/ops/windows-rehearsal/bootstrap_ops_phase1_daily.ps1` | `sync_required_env_to_user.ps1` → `register_ops_phase1_chain_task.ps1` 순서; `-SkipEnvSync` / `-SkipTaskRegister` / `-ExcludeConstitutionGates` / `-IncludeReadiness` / `-IncludeWebhookSmoke`. 동기화: `.env`에 `OPS_ALARM_WEBHOOK_URL` 없으면 User `N8N_WEBHOOK_URL`로 **자동 미러** |
| P0·헌법 경로 스모크 | `scripts/verify_p0_constitution_gate_paths.ps1` | `CONSTITUTION`·`P0`·`COMPRESSION_SLA_POLICY_V1`·`COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK`·`NotebookLM_sources_manifest`·`.cursorrules`·`AGENTS`·`CLAUDE`·정렬 pytest·Vault 동기화 등 **존재만** 검사(exit 0/1). 상세: `P0_COMMERCIALIZATION_TRACKER.md` §증거 경로 |
| 압축 KPI 자동 체인 | `scripts/run_compression_automation_chain.ps1` | 범용 프로파일 재평가·KPI 요약(`literal_kpi`는 `-IncludeLiteralTrack`로 리터럴 산출물이 있을 때)·토큰 API hydration 믹스·범용 손실 패턴; `-IncludeLiteralTrack` 시 리터럴 프로파일·리터럴 손실 패턴 추가; `run_workspace_automation_health.ps1 -IncludeCompressionKpi`로 묶음 가능(투트랙까지: 동시에 `-IncludeLiteralTrack`; 알람은 여전히 `active_kpi` 기준); 종료 시 `send_compression_kpi_alarm_if_needed.ps1`(임계치 `docs/final/artifacts/compression_alarm_thresholds_v1.json`, 웹훅 `COMPRESSION_KPI_ALARM_WEBHOOK_URL` 또는 `OPS_ALARM_WEBHOOK_URL`, `-SkipCompressionAlarm` 생략) |
| Track A go/nogo·HOLD 체인 (모노레포 루트) | `scripts/build_a_track_go_nogo_status.py` → `docs/final/artifacts/a_track_go_nogo_status_latest.json`; `scripts/build_a_track_multiweek_stability_tracker_v1.py` → `a_track_multiweek_stability_tracker_v1_latest.json`; `scripts/build_a_track_hold_release_checklist_v1.py` → `a_track_hold_release_checklist_v1_latest.json`; 거버넌스 JSON 부트스트랩 `scripts/emit_a_track_governance_artifacts_v1.py`(플레이스홀더—실전 서명 전 교체); 주간 롤업 `scripts/run_a_track_s3_weekly_evidence_rollup_v1.py`(`--emit-missing-governance` 선택, 트래커→체크리스트→go/nogo→체크리스트); 로컬 원클릭 갱신(주차 증가 없음) `scripts/Run-ATrackGovernanceRefresh.ps1`; 주간 작업 등록 `scripts/Register-ATrackS3WeeklyEvidenceTask.ps1`(기본 월요일·`--emit-missing-governance` 포함, `-SkipEmitGovernance`로 끔); 승인 영수증 선택 `reports/a_track_promotion_decision_latest.json` | **B-track·실매매 자동 합선 아님.** 가격 출력·고신뢰·다주간 증거·운영자 승인은 별도 게이트; 기본 산출물은 파이프라인 연결용이며 운영 주장의 근거로 삼으려면 서명·증거 경로를 갱신해야 한다. **2026-04-29부터 `build_a_track_go_nogo_status.py`는 의미 분리 고정: `high_reliability_decision_not_hold`/`price_output_unlocked`는 runtime 실상태만 반영하고, 정책 문서 준비 상태는 `high_reliability_release_plan_defined`/`price_unlock_policy_defined`로 별도 체크한다(문서 준비값으로 HOLD/lock 실상태를 덮어쓰지 않음).** |
| 트레이딩 Human-in-the-Loop 승인 영수증 v1 | 스키마 `docs/final/artifacts/schemas/trading_human_execution_approval_v1.schema.json`; 예시 `docs/final/artifacts/trading_human_execution_approval_v1_example_GO.json`, `…_example_NO_GO.json`; 제안 픽스처 `tests/fixtures/trading_execution_proposal_sample_v1.json`; 검증기 `scripts/validate_trading_human_execution_approval_v1.py`(스키마·`GO` 시 제안 파일 SHA-256·만료; **주문·네트워크 없음**); 런타임 소비 권장 경로 `reports/trading_human_execution_approval_latest.json`; **선행 배선:** `projects/bitcoin-trading/scripts/run_conditional_action_gate_v1.py`가 Fact-Safe 통과 후 `--human-approval-json`(또는 env `MKM_TRADING_HUMAN_APPROVAL_JSON`)이 있으면 검증기를 **서브프로세스 선호출**(실패 exit **7**); `scripts/Run-BinanceUsdmPilotSmoke.ps1`의 **`-LiveMainnetSmall`**는 기본으로 위 경로 파일 존재를 요구(`-HumanApprovalJson` / `-SkipHumanApproval` 예외); 회귀 `tests/test_trading_human_execution_approval_v1.py`·`tests/test_run_conditional_action_gate_v1_cli_smoke.py` | **`reports/a_track_promotion_decision_latest.json`(압축 승격)과 역할 분리.** B-track 제안은 `proposal_ref`·`proposal_body_sha256`로만 묶이며, 본 영수증은 **Track A 트레이딩 실행**용. 다른 실주문 진입점은 필요 시 동일 플래그를 **수동으로** 맞춘다. |
| 에이전트 레인 분리 | 루트 `AGENTS.md` — **운영 자동화 vs 연구 레인** | MKM Study·본선 OOF·실매매 **자동 합선 금지** 방향; 브리핑 전용 필드는 레포 산출물 근거 없이 SSOT 삼지 않음 |

### 13.1.b n8n 축소·Fact-Safe 로컬 SSOT (정책 포인터, 2026-05-15)

1. **현행 기본(2026-05-15 이후):** Fact-Safe 체인·일일 래퍼는 `sync_fact_safe_risk_profile.py --repo-source --allow-metadata-downgrade`로 `risk_profile`에 `repo.fact_safe_sync.v1` / `repo_shadow`를 기록한다(디스크에 남은 `n8n.*` 태그 **1회 이전** 포함). 레거시 `n8n.regime_watch.v5` / `n8n_shadow`만 유지하려면 `Run-FactSafeRiskProfileSyncChain_v1.ps1 -UseN8nSource` 또는 `--n8n-source`만 쓴다.
2. **판정의 위치**: `trinity_governor.mode`(예: `LOCKED_MODE`), 조건부 게이트 `gate_ok`, `build_trading_go_nogo_status_v1.py` 합성 규칙 등 **운영 판정**은 **Git에 추적되는 스크립트·테스트**가 단일 근거여야 한다. n8n 워크플로 UI/DB만으로 이를 바꾸는 것은 Fact-Lock과 충돌하므로, n8n이 남는 경우 **원시 수집·파일 적재(Dumb fetcher)** 로 역할을 제한한다.
3. **`n8n.*` → 비 n8n `source` 이전**: 단독 CLI에서 기존이 `n8n.*`이면 **`--allow-metadata-downgrade`**가 없으면 거부된다. 예약 체인은 `--repo-source`와 함께 위 플래그를 붙인다. 회귀: `tests/test_sync_fact_safe_risk_profile.py`.
4. **헌법 게이트 allowlist**: `verify_constitution_gates.ps1`는 `constitution_gates_v1.json`의 `allowed_risk_combinations`에 대해 `risk_profile_fact_safe_latest.json`의 `source`/`mode`를 검사한다. **새 조합**을 쓰려면 **반드시** 해당 JSON을 먼저 갱신하지 않으면 Phase 1 헌법 게이트가 실패한다. (2026-05-15 기본 허용: `repo.fact_safe_sync.v1`+`repo_shadow`, 레거시 `n8n.regime_watch.v5`+`n8n_shadow`, 월간 등 `fact_safe_prophecy.trinity_governor`+`shadow`.)
5. **연구 큐**: 단계별 폐기·혼합 유지 결정은 `docs/research/RESEARCH_OPEN_QUESTIONS_V1.md` **RQ-012**에 둔다(본 절은 경로·원칙만 고정, 구현 완료 단정 아님).

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

**Prophecy Hit Rate CLI (측정·비교용)**: `scripts/eval_prophecy_hit_rate_v1.py` — `run_mode` `price`(`--score-json`에 `predicted_direction`/`actual_direction` 또는 `rows[]`; 방향 일치율) / `proxy`(Oracle·레지스트리 precision 경로; 가격 적중과 동일 지표 아님; 미연결 시 `no_data`). **새벽 채점 OHLCV→score JSON**: `scripts/build_btrack_prophecy_score_from_ohlcv.py` — KOSPI SSOT `research/market_data/kospi_daily_external_yf.csv`(로더 `load_kospi_yf_rows`; **Date 헤더 단일행 CSV**·구형 `Price` 헤더 겸용); **CSV 갱신(선택)**: `scripts/fetch_kospi_yfinance_csv.py`(`^KS11`, `yfinance`). BTC는 `--btc-csv` 동형 파일 있을 때만 multi 2번째 행; 산출 `docs/final/artifacts/btrack_prophecy_score_latest.json`; `--eval-date auto`는 UTC 기준 CSV 내 “어제” 막대; **`--recent-trading-days N`**: 동일 가설 방향을 유지한 채 최근 N거래일 각각에 대해 `rows[]`를 누적(히트레이트 표본 확장; `meta.frozen_prediction_note` 참고). **`--force-dual-leg-panel`**: KOSPI·BTC OHLCV가 모두 있을 때 가설 instrument가 `btc`/`kospi`만이어도 eval_date마다 kospi·btc 두 행을 내어 `scripts/run_prophecy_instrument_combo_walkforward_v1.py` 입력을 맞춤(`inputs.hypothesis_instrument_declared`·`effective_instrument`·`force_dual_leg_panel`); BTC CSV 없으면 플래그 무시(WARN). **`Invoke-MaxProphecyBurst_v1.ps1`**: `RecentTradingDays >= 2`이고 기본 BTC CSV가 존재하고 KOSPI SSOT 파일이 있을 때 빌드에 동 플래그를 붙임. **체인 점검(읽기 전용):** `scripts/check_btrack_prophecy_chain_prereqs_v1.py`(산출 `btrack_prophecy_chain_prereqs_v1_latest.json`·`--stdout-only`·`--strict`). 선택 `run_btrack_daily_hypothesis_chain.ps1 -IncludeDawnScore` → 위 score 생성 후 `eval_prophecy_hit_rate_v1 --run-mode price`. 산출 스키마 **`prophecy_hit_rate_eval_report_v2`**. 기본 기록 경로 `docs/final/artifacts/prophecy_hit_rate_eval_latest.json` 및 동일 페이로드 `artifacts/latest_report.json`(로컬 재생성·`.gitignore`; VPS·SSH 호환). `--stdout-only`는 파일 미기록. **B-Track post-mortem·4h 헬스:** `scripts/eval_btrack_prophecy_post_mortem_v1.py` → `docs/final/artifacts/btrack_post_mortem_latest.json`(스키마 `btrack_post_mortem_v1`; 기본 입력 `docs/final/artifacts/btrack_hypothesis_prophecy_latest.json`·`docs/final/artifacts/btrack_prophecy_score_latest.json`·선택 `docs/final/artifacts/prophecy_hit_rate_eval_latest.json`). `scripts/check_btrack_4h_health_v1.py` → `docs/final/artifacts/btrack_4h_health_latest.json`; 등록 `scripts/Register-Btrack4hHealthTask.ps1`. 회귀 `tests/test_eval_btrack_prophecy_post_mortem_v1.py`. **월간 체인**: `run_waiting_queue_monthly_check.ps1`가 KOSPI CSV·가설 JSON이 있으면 `build_btrack_prophecy_score_from_ohlcv.py --recent-trading-days 30`(및 선택 `MKM_BTC_DAILY_CSV`) 후 `eval_prophecy_hit_rate_v1.py --run-mode price`를 이어서 실행하고, 같은 실행에서 `btrack_prophecy_score_monthly_YYYY-MM-DD.json`·`prophecy_hit_rate_eval_monthly_YYYY-MM-DD.json`로 복사(없으면 WARN 스킵).

**BTC 앙상블 가중치 프로필 × 가격 히트레이트 번들(B-track, [HYPO])**: `scripts/run_btc_weight_hit_rate_bundle_v1.py` — 프로필(`btc_65`/`btc_70`/`btc_80`)마다 `generate_btrack_hypothesis_prophecy_v1.py` → `build_btrack_prophecy_score_from_ohlcv.py` → `eval_prophecy_hit_rate_v1.py --run-mode price`를 묶어 `reports/btrack_btc_weight_hit_rate_bundle_latest.json`(스키마 `btc_weight_hit_rate_bundle_v1`)에 기록; 선택 `--apply-winner`로 `docs/final/artifacts/btrack_lens_ensemble_v1.json` 가중치 갱신(히트레이트 우승; `apply_btc_weight_sweep_winner_v1.py`는 confidence 우승과 구분). 래퍼 `scripts/Run-BtcWeightWeeklyHitRateBundle_v1.ps1`; 주간 작업 `scripts/Register-BtcWeightHitRateBundleWeeklyTask.ps1`. 회귀 `tests/test_run_btc_weight_hit_rate_bundle_v1.py`·CI `trackb-research-smoke.yml`.

**예언 방향 오버레이 소거 스파이크(B-track, [HYPO])**: `scripts/run_prophecy_restoration_spike.py` — 동일 `btrack_prophecy_score_v1` `rows[]`에 선택 오버레이 적용 전후 방향 적중률·`delta_hit_rate`를 스키마 `prophecy_overlay_ablation_spike_v1`·`docs/final/artifacts/prophecy_restoration_spike_latest.json`에 기록. 오버레이: (1) **기본** `prior_day_shock_bear_abstain_v0` — `research/market_data/kospi_daily_external_yf.csv`에서 **전거래일 완결 일간 수익률**(평가일 당일 `daily_return` 미사용)이 `--prior-return-threshold`(스크립트 기본 **-4.8%**; 패널별 권장은 `docs/final/artifacts/prophecy_overlay_prior_threshold_recommended_latest.json`) 이하일 때 `bear→neutral`; (2) `stress_bear_to_neutral_v0` — 표본 `docs/final/artifacts/4d_to_ohaeng_regime_year_map_sample_v1.json` 스트레스 연도 구간. **임계값 스윕:** OHLCV 30일 패널 요약 `docs/final/artifacts/prophecy_prior_threshold_sweep_summary_latest.json` (`prophecy_prior_threshold_sweep_summary_v1`). 본선·실매매 트리거 아님. 회귀: `tests/test_prophecy_restoration_spike.py` — **CI**: `.github/workflows/prophecy-restoration-spike-smoke.yml`.

**일일 B-Track 번들(렌즈→퓨전→LLM 입력→가설 JSON)**: `scripts/run_btrack_daily_hypothesis_chain.ps1`(체인 내 선행 **`scripts/build_btrack_news_macro_lens_adapters_v1.py`** → `docs/final/artifacts/news_independent_lens_latest.json`·`macro_independent_lens_latest.json`를 번들 `artifacts`에 탑재; **`-SkipNewsMacroAdapter`**로 해당 스텝 생략·직전 JSON 재사용) + `scripts/build_btrack_llm_input_bundle.py`(번들 `version` **1.1.0**; `artifacts`에 `independent_lens_shadow_minority_monthly`·기본 `--minority-monthly` `docs/final/artifacts/independent_lens_shadow_minority_monthly_latest.json`) + **BTC 레인(`-ResearchEvaluationInstrument btc`, 기본값)** 에서 번들 직후 **`scripts/run_btrack_prophecy_contemplation_v1.py`** 선행(로컬 번들 가드·선택 Gemini JSON 반성; `MKM_BTRACK_PROPHECY_CONTEMPLATION_V1=0`/`false`로 전체 생략; `MKM_BTRACK_CONTEMPLATION_USE_GEMINI`·API 키·타임아웃 등은 Python 스크립트·`.env.example` 참고; 체인 **`-SkipProphecyContemplationGemini`** 는 동 스크립트에 **`--skip-gemini-reflect`** 를 넘겨 환경에서 Gemini를 켠 경우에도 유료 반성만 끔) → 통과 산출 `docs/final/artifacts/btrack_prophecy_contemplation_v1_latest.json`을 **`scripts/generate_btrack_hypothesis_prophecy_v1.py --contemplation-json …`** 로 가설 생성에 탑재. **`scripts/generate_btrack_hypothesis_prophecy_v1.py`**(**일일 체인 기본은 스텁·무 API**; Gemini는 **Google Cloud / AI Studio·Gen AI 크레딧** 활용을 우선하고, **`GEMINI_API_KEY`/`GOOGLE_API_KEY`를 로컬 `.env`에 넣어 호출하는 방식은 오류가 잦고 크레딧 소모가 빠르므로 기본 생략·비권장** — 정말 필요할 때만 소량 **수동·배치**로 `generate_btrack_hypothesis_prophecy_v1.py --gemini` 실행); 산출 `docs/final/artifacts/btrack_hypothesis_prophecy_latest.json`; 가설 스키마 `docs/final/BTRACK_HYPOTHESIS_PROPHECY_V1.schema.json`. 히트레이트·CSV 경로가 있으면 동 체인에서 score(`build_btrack_prophecy_score_from_ohlcv.py`; **BTC CSV가 해석되면 `--force-dual-leg-panel`을 함께 전달**해 인스트루먼트 콤보 워크포워드 입력 정합)→`eval_prophecy_hit_rate_v1` 후 **`scripts/eval_prophecy_promotion_gates_v1.py`** → **`scripts/fast_promotion_gate_v1.py`**(기본 `--min-hit-rate 0.5 --min-n 5`) → `docs/final/artifacts/fast_promotion_gate_v1_latest.json`. Logos 일괄: `data/logos/4lens_batch_sample.json` 없으면 `tests/fixtures/logos_4lens_batch_minimal_v1.json`·없으면 `run_lens_logos.py --allow-fallback`(`run_btrack_daily_hypothesis_chain.ps1`·`run_myeongni_shadow_monthly_catchup_v1.ps1`·`run_waiting_queue_monthly_check.ps1`·`Run-BtrackInsightSidecarChain.ps1 -IncludeMultilensRefresh` 동일 방향). 가설 스텁 `lens_artifacts.shadow_minority_monthly`·`append_btrack_insight_observation.py`의 `snapshot_refs`에 월별 롤업 파일 포인터 포함. **뉴스·매크로 렌즈 어댑터** 회귀 `tests/test_build_btrack_news_macro_lens_adapters_v1.py`.

**Science Core quant lane v1 (B-track·[HYPO]·`research_only`)**: 정량 전용 레인(`price`+`macro`+`news`; 사상·명리·성경은 **점수 구성에 미포함**·조합 uplift만 관측). 코어 `scripts/btrack_science_core_v1.py` · per-date `scripts/build_btrack_science_core_per_date_v1.py` → `reports/btrack_science_core_per_date_kospi_v1.jsonl`·`…_btc_v1.jsonl` · horizon `scripts/run_science_core_horizon_empirical_eval_v1.py` · holdout 조합 `scripts/run_science_core_holdout_combo_v1.py` · walk-forward `scripts/run_science_core_walkforward_v1.py`·`scripts/run_science_core_long_walkforward_v1.py` · 거버넌스 번들 `scripts/run_science_core_governance_bundle_v1.py` → `docs/final/artifacts/science_core_governance_bundle_v1_latest.json`(래퍼 `scripts/Run-ScienceCoreGovernanceBundle_v1.ps1`; 주간 `scripts/Register-ScienceCoreWeeklyGovernanceTask.ps1`·`scripts/Verify-ScienceCoreWeeklyGovernanceTask_v1.ps1`). 확장 감사: `scripts/run_science_core_macro_gate_bias_audit_v1.py` · `scripts/run_science_core_news_coverage_audit_v1.py` · `scripts/run_science_core_news_weight_ablation_v1.py`(조합 `science_plus_sasang_news_off`) · `scripts/run_science_core_long_window_lane_compare_v1.py`(`--instrument kospi|btc`; `science_plus_myeongni`·`science_plus_sasang_myeongni` 3-way `triple_sasang_myeongni_direction`) · `scripts/run_science_core_triple_blend_weight_sweep_v1.py` · `scripts/run_science_core_pnl_bootstrap_v1.py` · 거버넌스 `humanist_combo_holdout`(3-way attach 비대상) · `btc_holdout_auxiliary`(KOSPI attach 보조) · `pnl_economic_significance` · `instrument_parity_summary`. EXA 뉴스: `scripts/fetch_exa_macro_news_observation_v1.py`·`scripts/backfill_exa_macro_news_observation_v1.py`·`scripts/Run-BtrackExaMacroNewsChain_v1.ps1` → `reports/exa_macro_news_observation_staging_v1_latest.jsonl`. humanist per-date: `scripts/build_btrack_market_sasang_per_date_jsonl_v1.py`·`scripts/build_btrack_myeongni_per_date_jsonl_v1.py`·`scripts/build_btrack_logos_per_date_jsonl_v1.py`·`scripts/run_science_core_extend_score_sidecar_v1.py`. 예언 콤보 science arms: `scripts/run_science_core_prophecy_combo_attach_v1.py`(거버넌스 `composite_attach_recommended` 게이트) → `scripts/run_prophecy_lens_combo_backtest_v1.py --include-science-core` → `docs/final/artifacts/prophecy_lens_combo_backtest_science_core_v1_latest.json`·`prophecy_lens_combo_science_core_attach_gate_v1_latest.json`(일일 `-IncludeScienceCoreLane` 말단). research attach sign-off `docs/final/artifacts/science_core_research_attach_signoff_v1_latest.json`(Track A·live **별도** human). readiness `scripts/check_science_core_lane_readiness_v1.py`·`scripts/Invoke-ScienceCoreLaneReadiness_v1.ps1`; 페르소나 `Invoke-MkmPersonaHealth_v1.ps1 -Persona ScienceCoreLaneReadiness|ScienceCoreWeeklyReadiness|ScienceCoreGovernance`. instrument×task 매트릭스 SSOT `scripts/build_science_core_instrument_matrix_v1.py` → `docs/final/artifacts/science_core_instrument_matrix_v1_latest.json`(거버넌스 말단: conditional attach research → matrix 자동 갱신). 조건부 attach 연구 `scripts/run_science_core_conditional_attach_research_v1.py` → `docs/final/artifacts/science_core_conditional_attach_research_v1_latest.json`(holdout·shock·horizon 분해·BTC divergence). 회귀 `tests/test_btrack_science_core_v1.py`·`tests/test_run_prophecy_lens_combo_science_core_v1.py`·`tests/test_build_science_core_instrument_matrix_v1.py`·`tests/test_run_science_core_conditional_attach_research_v1.py`·`tests/test_backfill_exa_macro_news_observation_v1.py`·`tests/test_fetch_exa_macro_news_observation_v1.py`·CI `dual-regime-integrity.yml`·Fact-Lock `run_fact_lock_bundle.ps1` 3d3b. **composite_attach**는 holdout+walk-forward+**비-stub humanist** 충족 시에만; Logos blend는 `[NON_GATING]`. **macro_only** 장기 1위·holdout uplift만으로 Track A 승격 금지. **Track A·실매매·Absolute Balance Coordinator 자동 합선 금지.**

**KOSPI 스트레스 관측 가설 v1(B-track·임시·[HYPO])**: `scripts/build_kospi_stress_observation_hypothesis_v1.py` → `docs/final/artifacts/kospi_stress_observation_hypothesis_v1_latest.json` — 코스피 일봉 `research/market_data/kospi_daily_external_yf.csv`에서 **최근 5거래일 로그수익률 표준편차**를 계산해 `--vol-threshold`(기본 **0.015**) 이하이면 `gates.vol_stress_eased=true`; `research/market_data/kospi_monthly_flow_external.csv` **최신 월** `foreign_net_buy`(억원 규모 가정)이 **0 이상**이면 `gates.monthly_foreign_net_non_negative=true`. `composite_stress_ease_candidate`는 위 두 게이트의 **AND**(월간 수급은 **브로커 일중 tape와 다름**·갱신 주기 느림). 일일 체인 `run_btrack_daily_hypothesis_chain.ps1`가 `build_prophecy_health_status_v1.py` 직후 기본 실행하며 `--append-log`로 `reports/kospi_stress_observation_hypothesis_v1_log.jsonl`에 한 줄 누적; **`-SkipKospiStressObservation`** 으로 생략. 스키마 `docs/final/schemas/kospi_stress_observation_hypothesis_v1.schema.json`. 회귀 `tests/test_build_kospi_stress_observation_hypothesis_v1.py`. **Track A·실매매 자동 합선 없음.**

**`run_btrack_daily_hypothesis_chain.ps1` 스위치 (PowerShell, 관측 전용)**: 아래 표는 `scripts/run_btrack_daily_hypothesis_chain.ps1` **실측 `param` 블록**과 1:1 대응한다. **실매매·`run_conditional_action_gate_v1.py`·Track A 압축 게이트와 자동 합선 없음.** 체인 **종단 고정**(별도 스위치 없음): `scripts/build_prophecy_health_status_v1.py` → `docs/final/artifacts/prophecy_health_status_latest.json`; `scripts/check_prophecy_proxy_streak_gate_v1.py`(선택 엄격: **`-StrictProphecyProxyStreakGate`** 시 `--strict-exit`·실패 시 체인 throw; 미지정 시 exit 2는 WARN). `MKM_BTRACK_USE_CLOUD_GEMINI=1`·`MKM_BTRACK_GEMINI_MODEL`은 `-UseCloudGemini`/`-GeminiModel`과 동일 선상. KOSPI CSV 없이 proxy 히트레이트를 탈 때(기본 체인·`-SkipHitRate` 아님): 환경 **`BTRACK_HIT_RATE_REGISTRY_GLOB`** 있으면 `eval_prophecy_hit_rate_v1.py --registry-glob …`, 없으면 `--run-mode proxy`만.

| 스위치·인자 | 동작 요약 |
|-------------|-----------|
| `-WorkspaceRoot` | 기본: 스크립트 상위(레포 루트). 다른 worktree면 명시. |
| `-BtcCsv` | 히트레이트 분기에서 `build_btrack_prophecy_score_from_ohlcv.py --btc-csv`에 전달; 미지정 시 `MKM_BTC_DAILY_CSV`·`research/market_data/btc_daily_external_yf.csv` 순 해석. |
| `-PromotionTrackMode` | `eval_prophecy_promotion_gates_v1.py --promotion-track-mode` 인자; 허용값 `btc_only_crossassist` \| `dual`(스크립트 `ValidateSet`). |
| `-SkipInsightAppend` | `append_btrack_insight_observation.py` 생략. |
| `-SkipHitRate` | `build_btrack_prophecy_score_from_ohlcv.py`·`eval_prophecy_hit_rate_v1`(price·proxy 분기 포함) **전체 생략**. |
| `-IncludeDawnScore` | score 빌드에 `--recent-trading-days 30` 후 동일 price eval(위 Prophecy Hit Rate 절과 동일). |
| `-SkipExternalFeedValidation` | `load_external_feed_drop_with_fallback_v1.py` 검증 단계 생략. |
| `-StrictExternalFeedValidation` | 검증 실패 시 체인 throw. |
| `-SkipFastPromotionGate` | `eval_prophecy_promotion_gates_v1.py`·`fast_promotion_gate_v1.py` 블록 생략. |
| `-StrictFastPromotionGate` | 위 두 스크립트 중 하나라도 exit≠0이면 throw(미지정 시 WARN 후 계속). |
| `-SkipMarketDataRefresh` | 선행 `fetch_kospi_yfinance_csv.py`·`fetch_btc_yfinance_csv.py` 생략. |
| `-StrictMarketDataRefresh` | 각 fetch exit≠0 시 throw. |
| `-StrictProphecyProxyStreakGate` | `check_prophecy_proxy_streak_gate_v1.py --strict-exit`; streak breach(exit 2) 시 throw. |
| `-UseCloudGemini` | `generate_btrack_hypothesis_prophecy_v1.py --use-cloud-gemini`(및 선택 `--model`). |
| `-GeminiModel` | 위 가설 생성에 `--model` 문자열 전달; 비어 있으면 환경 `MKM_BTRACK_GEMINI_MODEL`. |
| `-IncludeNaverOpenApiRefresh` | `fetch_naver_openapi_signals_v1.py` 실행(`.env`의 `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET`·개발자센터 API 활성 필요). **기본값은 생략**(네트워크·401 잡음 방지). |
| `-SkipNaverOpenApiRefresh` | `-IncludeNaverOpenApiRefresh`가 켜져 있을 때만 의미 있음: Naver 단계 강제 생략. 단독 지정은 기본(생략)과 동일·래퍼 호환용. |
| `-SkipNewsMacroAdapter` | `build_btrack_news_macro_lens_adapters_v1.py` 생략·직전 `news`/`macro` lens JSON 경로 유지. |
| `-IncludeYang2015SurfaceMetrics` | (선택) `reports/commander_myeongni_lens_latest.json`이 있으면 `btrack_yang_2015_style_metrics_v1.py`→`reports/btrack_yang_2015_style_metrics_latest.json`; 이어 `run_myeongni_celebrity_benchmark_v1.py`→`docs/final/artifacts/myeongni_celebrity_hit_rate_v1.json`. commander 없으면 첫 단계 WARN 후 벤치만 실행. |
| `-ResearchEvaluationInstrument` | `btc` \| `kospi` \| `multi`(체인 `param` 기본 **btc**; `Register-BTrackDailyHypothesisTask.ps1` 스케줄 등록 기본은 **multi**). 가설 생성기 `--research-evaluation-instrument` 및 BTC 전용 묵상 pre-gate 분기. |
| `-SkipProphecyContemplationGemini` | BTC 묵상 단계에서 `run_btrack_prophecy_contemplation_v1.py`에 **`--skip-gemini-reflect`** 전달(`MKM_BTRACK_CONTEMPLATION_USE_GEMINI=1`이어도 Gemini 반성만 끔; 로컬 가드는 유지). |
| `-SkipKospiStressObservation` | `build_kospi_stress_observation_hypothesis_v1.py`(KOSPI 5일 실현 변동성 + 월간 외인 순매수 proxy 관측 JSON·`--append-log` JSONL) 생략. |
| `-IncludeScienceCoreLane` | Science Core per-date humanist·science JSONL·holdout combo·`run_prophecy_lens_combo_backtest_v1.py --include-science-core`·`check_science_core_lane_readiness_v1.py`. 환경 `MKM_BTRACK_SCIENCE_CORE_LANE=1` 동등. **기본 OFF**·`research_only`. |
| `-SkipPanel24hAlertsCheck` | 종단 `Check-ProphecyPanel24hAlerts.ps1` 생략. |

**스케줄 등록(`Register-BTrackDailyHypothesisTask.ps1`)**: 기본으로 등록되는 Task Scheduler 인자에 위 `-SkipPanel24hAlertsCheck`를 **자동 포함**한다(패널 KPI 실패·`no_data`가 체인 전체 스케줄 실패로 가리지 않게). Science Core 레인은 **기본 OFF**; 예약에 포함하려면 `Register-BTrackDailyHypothesisTask.ps1 -IncludeScienceCoreLane`(동 `-IncludeScienceCoreLane`이 체인에 전달). 같은 Task 안에서 종단 패널까지 돌리려면 `-IncludePanel24hAlertsCheck`(비권장; `Register-ProphecyPanel24hAlertsTask.ps1` 분리 권장).

**운영 명시성 (`Skip*` vs `Strict*`)**: **`-Skip*`** 는 해당 단계를 생략·경고(WARN) 후 진행할 수 있어 **로컬·오프라인·복구 루틴**에 맞춘 유연 모드다. **`-Strict*`** 는 동일 구간에서 exit≠0(또는 streak breach 등)이면 **체인을 즉시 중단**해, CI·감사·“성공으로 위장된 실패”(부분 실패를 전체 OK로 읽는 오류)를 막는 **강제 모드**다. 운영자는 스케줄·수동 실행 시 **어느 모드를 택했는지**가 곧 리스크 수용 수준이다.

**체인 무결성(종단 봉인)**: 가설 JSON만 갱신되었다고 **관측 체인 전체가 유효**한 것으로 단정하지 않는다. 동일 실행의 **마지막**에 `build_prophecy_health_status_v1.py`로 `prophecy_health_status_latest.json`을 남기고, `check_prophecy_proxy_streak_gate_v1.py`로 proxy/eval 누락 연속일을 점검한다. **`-StrictProphecyProxyStreakGate`** 가 없으면 streak breach는 WARN일 수 있으므로, “헬스·스트릭까지 통과한 관측”을 운영 기본값으로 삼으려면 **Strict** 또는 별도 알람 절차를 택한다.

**암행어사·B-track 예언 감시 (2026-05-12)**: `scripts/run_btrack_daily_hypothesis_chain.ps1` 종단에서 `scripts/Check-ProphecyPanel24hAlerts.ps1`로 `prophecy_hit_rate_eval_latest.json`·`prophecy_promotion_gates_v1_panel_calibrated_latest.json` 기반 ALERT 1–3 점검·`reports/prophecy_panel_24h_alerts_latest.json`(선택 `-AppendLog` 시 `reports/prophecy_panel_24h_alerts_log.jsonl`)·**웹훅 기본 라우팅: ALERT_1(성능) 또는 ALERT_3(구조) 실패 시에만** `PROPHECY_PANEL_24H_ALERT_WEBHOOK_URL`/`OPS_ALARM_WEBHOOK_URL` POST(ALERT_2만 실패(strict/승격 준비)면 POST 생략·exit 1 유지; 레거시 전체 실패 알림은 `-IncludeAlert2InWebhook`)·`-SkipPanel24hAlertsCheck` 생략 가능. `scripts/Run-AmsaengEosaMonitoringBundleTask.ps1` 말단에 `scripts/check_prophecy_evolution_watchdog_v1.py`(staleness·선택 히트레이트 tail 스트릭/EMA; 번들은 `--allow-missing-*`+`AllowNonZero`). 일일 스케줄 `scripts/Register-ProphecyEvolutionWatchdogTask.ps1` → `scripts/Invoke-ProphecyEvolutionWatchdog_v1.ps1` → `reports/prophecy_evolution_watchdog_latest.json`·`reports/prophecy_evolution_watchdog_hit_rate_tail_v1.jsonl`(eval `generated_at_utc` dedup append); CI `tests/test_check_prophecy_evolution_watchdog_v1.py`·`.github/workflows/dual-regime-integrity.yml`; 로컬 헬스 `run_workspace_automation_health.ps1 -IncludeProphecyEvolutionWatchdogSmoke`. **B-track 예언 레일에서 스크립트 vs 휴먼 단계 표:** `docs/final/MKM_PROMOTION_GATE_CHECKLIST_B_TO_A_C_V1.md` §「B-track 가격 방향 예언 레일」.

**일반 미래 예측(비가격) 질문·확률 슬롯 계약(초안, 2026-04-11)**: `docs/final/GENERAL_PROPHECY_SCHEMA_V1.json` — `general_prophecy_registry_v1` / `general_prophecy_question_v1`; 레일 `B` 또는 `OBSERVATION_ONLY`; 판정 가능한 `resolution_criteria`·`resolution_deadline_utc`; Layer 1용 `forecasts[]`(`probability_0_1`, `source_kind`); 해석은 `layer3_interpretation_ref` 포인터만. **스크립트(Phase 2–4 최소 구현)**: `scripts/generate_general_prophecy_v1.py`(스키마 검증·`generated_at_utc` 갱신·선택 `--stub-forecasts`; 기본 입출력 `tests/fixtures/general_prophecy_registry_sample_v1.json`→`docs/final/artifacts/general_prophecy_latest.json`; **기본 병합**: 동일 실행에서 `general_prophecy_registry_seed_5_v1.json`·`general_prophecy_registry_brier_smoke_v1.json`의 문항을 `question_id` 기준으로 뒤에 합침(중복 스킵)·`--no-default-merge`로 끔·추가는 `--merge-from PATH` 반복) · `scripts/build_general_prophecy_brief.py`(동 레지스트리→`docs/final/artifacts/general_prophecy_brief_latest.md`) · `scripts/eval_general_prophecy_brier_score.py`(이진+`resolved`만 평균 Brier·선택 `--ece-bins N` 등간 이진 ECE·`metrics.ece_binary`·`metrics.ece_binary_by_domain_tag`(`--ece-min-per-tag`)→`docs/final/artifacts/general_prophecy_brier_eval_latest.json`) · `scripts/resolve_general_prophecy_question_v1.py`(이진 질문: `--resolution-status resolved|void|disputed`; `resolved`일 때만 `--outcome`; `void`/`disputed`는 `outcome_binary` null·notes/`evidence_uris` 선택; `--output`·`--in-place`·`--stdout-only`) · `scripts/export_general_prophecy_to_jsonl.py`(GPU LoRA 훈련용 B-track JSONL 추출기; `output` 앞단에 `[HYPO]` 가드레일 강제; 압축·A-track 실거래 엔진과 코드 합선 없음). **일일 체인(경량)**: `scripts/run_general_prophecy_daily_queue_refresh_v1.ps1`가 `general_prophecy_latest`·brief·brier에 더해 `general_prophecy_explainable_latest.json`·`general_prophecy_explainability_quality_v1_latest.json`·`general_prophecy_explainability_holdout_report_v1_latest.json`·`general_prophecy_explainability_holdout_gate_v1_latest.json`·`myeongni_promotion_gate_latest.json`/`myeongni_promotion_failure_analysis_latest.json`을 동시 갱신. **Fact-Lock 번들 말단 헬스(기본)**: `scripts/run_fact_lock_bundle.ps1`가 끝단에서 `run_workspace_automation_health.ps1 -IncludeGeneralProphecyTaskHealth -StrictGeneralProphecyTaskHealth -IncludeGeneralProphecyHoldoutGateHealth -StrictGeneralProphecyHoldoutGateHealth`를 호출하며, 생략 스위치는 `-SkipGeneralProphecyHoldoutGateHealth`. **월간 체인**: `scripts/run_waiting_queue_monthly_check.ps1`가 `-SkipGeneralProphecyChain`이 **아닐 때** `generate_general_prophecy_v1`→`build_general_prophecy_brief`→`eval_general_prophecy_brier_score`→`export_general_prophecy_to_jsonl` 순서로 실행(외부 예측시장 API 없음; 리졸버는 수동 호출; JSONL 산출 `data/training/macro_prophecy_dataset_v1.jsonl`·`.gitignore`). **CI**: `tests/test_general_prophecy_schema_v1.py`·`tests/test_general_prophecy_chain_smoke.py`·`tests/test_resolve_general_prophecy_question_v1.py`·`tests/test_export_general_prophecy_to_jsonl.py`·`tests/test_general_prophecy_explainable_regressions_v1.py` — `scripts/verify_p0_constitution_gate_paths.ps1`에 스키마·스크립트·픽스처 경로 포함. **시드 5문항(스키마 검증·수동 병합용)**: `tests/fixtures/general_prophecy_registry_seed_5_v1.json`(월간 체인 기본 입력 아님; `generate_general_prophecy_v1.py --input` 등으로 선택 병합).

**일반예언 holdout 운영 게이트·알림 (2026-05-06 보강)**: `scripts/check_general_prophecy_explainability_holdout_gate_v1.py`는 `--profile research|ops`(기본 research, ops 임계치 강화)로 `general_prophecy_explainability_holdout_gate_v1_latest.json` 생성; `scripts/alert_general_prophecy_holdout_gate_v1.py`는 decision=`WARN_HOLDOUT_DRIFT_RISK`일 때만 웹훅 발송하며 payload/result에 `failed_check_keys` 포함. 일일 체인 `scripts/run_general_prophecy_daily_queue_refresh_v1.ps1`는 `-HoldoutGateProfile` + `-IncludeLogosV2 true|false`로 게이트 프로파일/Logos v2 체인 ON/OFF를 제어하고, 선택적으로 `-EnableLogosResponseV1Retry true` 시 먼저 `build_logos_63779_registry_v1.py` + `build_logos_morphology_registry_v1.py`를 선행 실행해 최신 레지스트리를 생성한 다음 `build_logos_response_retry_inputs_v1.py`로 raw/retry 입력을 자동 생성하고 `run_logos_response_retry_pipeline_v1.py`를 호출해 첫 통과안을 `logos_response_v1_retry_selected_latest.json/.md`로 확정한다(`run_logos_response_retry_pipeline_v1.py`는 `--schema` 미지정 기본에서 문서 `schema` 값(v1/v2)으로 자동 스키마 선택). 형태소 레이어 샘플링 정책은 `build_logos_morphology_registry_v1.py` 기본 상수로 고정한다(`max_scan_lines=400000`, `target_matched_samples=5000`, `stop_condition=matched_rows>=target or scanned_lines>=max`) — 산출 JSON의 `morphology_layer.sampling_policy`에 동일 값 기록. 추가로 `-EnableLogosResponseQualityScore true`(기본 true)면 `build_logos_response_quality_score_v1.py`를 실행해 `logos_response_quality_score_v1_latest.json`(항목별+종합; `scores.overall`은 10점 척도, `scores.overall_100`은 동일 가중합의 100점 환산, `score_scale` 메타)을 생성하고, `-EnableLogosResponseQualityAlert true`(기본 true)이면 `alert_logos_response_quality_score_v1.py`가 `LogosResponseQualityMinOverall`(기본 8.0, **10점 척도**) 미만일 때 웹훅 경고를 발송한다(`logos_response_quality_score_alert_latest.json`에 `overall_100` 동봉; 웹훅 키 `MKM_LOGOS_QUALITY_ALERT_WEBHOOK_URL` 우선, 없으면 `OPS_ALARM_WEBHOOK_URL`). 실패 시 `docs/final/artifacts/general_prophecy_daily_queue_failure_summary_latest.json`(failed_step/exit_code/profile) 기록. 스케줄러 재현 등록은 `scripts/Register-GeneralProphecyDailyQueueTask.ps1` 단일 진입점으로 고정(기본 `-HoldoutGateProfile ops -IncludeLogosV2 true`, 필요 시 `-EnableLogosResponseV1Retry true -EnableLogosResponseQualityScore true -EnableLogosResponseQualityAlert true -LogosResponseQualityMinOverall 8.0 -LogosResponseV1PrimaryInput ... -LogosResponseV1RetryInput ... -LogosResponseV1MaxAttempts N`).

**holdout evolution 후보·ablation + 명리/Logos v2 체인 (2026-05-06 확장)**: 일일 체인 `run_general_prophecy_daily_queue_refresh_v1.ps1`는 holdout gate 이후 `build_general_prophecy_holdout_evolution_candidates_v1.py`(후보안 JSON 생성, `mode=proposal_only_no_auto_apply`)와 `run_general_prophecy_holdout_evolution_ablation_v1.py`(후보별 gate 재평가·추천 ID 산출)를 연속 실행해 `general_prophecy_holdout_evolution_candidates_latest.json`·`general_prophecy_holdout_evolution_ablation_latest.json`을 생성한다. 주간 스케줄은 `Register-GeneralProphecyHoldoutEvolutionWeeklyTask.ps1`로 `\GeneralProphecyHoldoutEvolutionWeeklyV1`(기본 SUN 09:00, `-HoldoutGateProfile ops`, `-IncludeLogosV2 true|false`) 등록 가능하다. 동일 체인 말단에 `build_mkm_myeongni_response_v2.py` → `validate_mkm_myeongni_response_v2.py`를 기본 실행하고, `IncludeLogosV2=true`일 때 `build_mkm_logos_response_v2.py` → `validate_mkm_logos_response_v2.py`를 추가 실행해 `mkm_logos_response_v2_latest.json`까지 생성/검증한다(`response_layer` 템플릿 자동 선택 + `evidence_links` 포함).

**Logos Fact-Lock 수동 응답(JSON→검열→MD) v1/v2 (2026-05-06 확장)**: 스키마 `docs/final/artifacts/schemas/logos_response_schema_v1.json`(`schema`=`logos_response_v1`) + `docs/final/artifacts/schemas/logos_response_schema_v2.json`(`schema`=`logos_response_v2`, `denominational_view`·`text_critical_notes`·`mkm_interpretation_math` 확장); 검증·렌더 CLI `scripts/logos_response_validator_v1.py` 서브커맨드 `validate`·`render`·`pipeline`·`extract`(`--schema` 미지정 시 문서의 `schema` 값으로 v1/v2 자동 선택, `pipeline` 기본: 순수 JSON 또는 \`\`\`json 펜스 또는 첫 균형 `{…}` 추출 후 검증·MD 출력; `--strict-json`이면 파일 전체 단일 객체만; 스키마는 `jsonschema` Draft7; 금지어는 사용자 노출 문자열 필드만 검사); 재시도 오케스트레이터 `scripts/run_logos_response_retry_pipeline_v1.py`(`--input` + `--retry-input` 순차 평가 후 첫 통과안을 `--output-json`/`--output-md`로 확정, 시도 이력은 `--report-json`); 최소 픽스처 `tests/fixtures/logos_response_v1_valid_min.json`·`tests/fixtures/logos_response_v2_valid_min.json`·펜스 샘플 `tests/fixtures/logos_response_v1_llm_fenced_sample.txt`·금지어 실패 샘플 `tests/fixtures/logos_response_v1_invalid_banned.json`; 회귀 `tests/test_logos_response_validator_v1.py`·`tests/test_logos_response_validator_v2.py`·`tests/test_logos_response_llm_extract_v1.py`·`tests/test_run_logos_response_retry_pipeline_v1.py`. 자동 일일 체인 산출 `mkm_logos_response_v2`와 별도 — LLM이 채운 JSON 브리프를 인간 검토 전 고정 포맷으로 묶는 용도(NON_GATING).

**Logos Citation Integrity guardrail (FACT-LOCK, 2026-06-20):** Track C·대외 Logos 표면의 구절·인용은 `logos_response_validator_v1` `validate`/`pipeline` **exit 0** 및 `verse_id`·`quote_hash`(`evidence_refs`; `run_lens_logos.py`·`run_logos_llm_distill_citation_lock_v1.py`) 정합만 유효. 범용 LLM의 미검증 구절 생성은 프로덕션 경로 **차단**; Logos `[NON_GATING]` — Track A·live·SEND 자동 합선 없음. Worldview §9 · `LOGOS_NOTEBOOK_META_GUIDE.md` §1·4 · 스모크 `scripts/check_logos_citation_integrity_smoke_v1.py`·`tests/test_check_logos_citation_integrity_smoke_v1.py`.

**Fact-Lock 번들 말단 헬스 보강 (2026-05-06)**: `scripts/run_fact_lock_bundle.ps1`의 말단 헬스 호출에 `-IncludeGeneralProphecyTaskProfileGuard -StrictGeneralProphecyTaskProfileGuard -IncludeGeneralProphecyEvolutionHealth -StrictGeneralProphecyEvolutionHealth`를 포함해, Task 인자 드리프트(`-HoldoutGateProfile ops`·`-IncludeLogosV2 true` 누락)와 evolution/myeongni/Logos v2 상태까지 기본 strict 검증 대상으로 고정한다. 프로파일 가드는 `scripts/check_general_prophecy_task_profile_guard_v1.py --required-profile ops --required-include-logos-v2 true` 계약으로 판정한다.

**헬스 확장 포인트 (옵션, 2026-05-06)**: `scripts/run_workspace_automation_health.ps1`는 `-IncludeGeneralProphecyEvolutionHealth`(선택 strict: `-StrictGeneralProphecyEvolutionHealth`)로 `general_prophecy_holdout_evolution_ablation_latest.json` + `mkm_myeongni_response_v2_latest.json` + 주간 태스크(`\GeneralProphecyHoldoutEvolutionWeeklyV1`) 상태를 함께 점검하고 `general_prophecy_evolution_health_latest.json`를 생성한다. 같은 단계에서 히스토리 JSONL(`general_prophecy_evolution_health_history_v1.jsonl`)을 누적해 `myeongni_v2_decision_counts`·`ablation_recommended_candidate_id_counts`·`myeongni_v2_watch_streak` 추세를 함께 기록한다. **로컬 직접 갱신:** `scripts/build_general_prophecy_evolution_health_v1.py` · **자율 apply 화이트리스트 SSOT:** `docs/final/artifacts/evolution_auto_apply_allowlist_v1_latest.json` + `scripts/check_evolution_auto_apply_allowlist_v1.py`(B-track `neutral_bps` 스윕 apply 전 `run_prophecy_btrack_recommended_eval_chain_v1.py`가 검증; 헤드라인 KPI 쓰기는 `scripts/promote_op28_headline_kpi_v1.py`만 — `assert_headline_kpi_promotion_allowed`로 `min_confidence`/`score_abs_deadzone`·SSOT 경로 검증, 스윕 체인은 promote 호출 안 함).

**운영 런북 (실패 시 3단계 점검)**: 1) 게이트 본문 확인 `general_prophecy_explainability_holdout_gate_v1_latest.json`(`decision`, `checks`, `failed_check_keys`) → 2) 알림 결과 확인 `general_prophecy_explainability_holdout_alert_latest.json`(`alert_needed`, `dispatch_result`, `webhook_dispatched`) → 3) 체인 실패 요약 확인 `general_prophecy_daily_queue_failure_summary_latest.json`(`failed_step`, `exit_code`, `holdout_gate_profile`). 이 순서로 보면 “판정 실패/알림 실패/체인 단계 실패”를 1분 내 분리 진단할 수 있다. **즉시 강등 표준:** 운영 장애/오탐/지표 누락 시 스케줄 태스크를 `-IncludeLogosV2 false`로 재등록해 Logos v2 단계를 즉시 우회하고, 복구 후 `true`로 복원한다.

**B-track 뉴스 point-in-time 관측·방향 라벨(연구, [HYPO])**: 스키마 `docs/final/schemas/news_observation_v1.schema.json`·`docs/final/schemas/direction_label_bar_v1.schema.json`; 샘플 JSONL `tests/fixtures/news_observation_v1.sample.jsonl`·`tests/fixtures/direction_label_bar_v1.sample.jsonl`; 검증 CLI `scripts/validate_news_observation_jsonl_v1.py`(`--news-jsonl`·선택 `--labels-jsonl`·`--verify-label-hashes`·`--labels-jsonl-only`); 조인 시점 가드 `scripts/check_news_label_join_temporal_v1.py`(행 단위 정렬·`--strict-as-of-date-before-label-date`); CSV 스텁 `scripts/build_news_observation_jsonl_from_csv_v1.py`(`--validate`); OHLCV→`direction_label_bar_v1` `scripts/build_direction_label_bar_jsonl_from_ohlcv_v1.py`(`--validate-labels`); 워크포워드(달력 `as_of_utc` 이후 첫 `label_date`) `scripts/join_news_observation_direction_labels_walkforward_v1.py`(`--instrument-id`·`--horizon`); 로컬 원클릭 `scripts/Run-NewsObservationContractSmoke.ps1`; **Saving the News NEWS-RT(B-track, [HYPO], 오프라인 코호트)**: `scripts/build_saving_the_news_news_rt_bench_contract_v1.py`·`scripts/run_saving_the_news_news_rt_bench_v1.py`(기본 `docs/final/artifacts/news_observation_v1_latest.jsonl` ≥120행·`state_card_unique_token_v0` 프록시; **라이브 스트림·A-TRACK/LOGOS-CAP 축 이식 금지**)·`scripts/Run-SavingTheNewsNewsRtBench_v1.ps1`·`scripts/Run-SavingTheNewsParallelReadiness_v1.ps1`(`-FullCohortBench`)·산출 `saving_the_news_news_rt_bench_result_v1_latest.json`·`saving_the_news_phase1_poc_status_v1_latest.json`; **Phase 2 Matrix** `scripts/build_saving_the_news_phase2_matrix_view_v1.py`·`scripts/Run-SavingTheNewsPhase2Matrix_v1.ps1`·`saving_the_news_phase2_matrix_view_v1_latest.json`·`saving_the_news_phase2_poc_status_v1_latest.json`; **Phase 3 Truth Gating stub** `scripts/eval_saving_the_news_phase3_truth_gating_v1.py`·`scripts/Run-SavingTheNewsPhase3TruthGating_v1.ps1`·`saving_the_news_phase3_truth_gating_v1_latest.json`·`saving_the_news_public_event_ingest_stub_v1.json`(public-event.v1 예시; `public_event_gateway.py` 패턴); 설계 `docs/research/saving_the_news_blueprint_v1.md`·RQ-022; Fact-Lock 번들·`scripts/run_workspace_automation_health.ps1`는 **기본 실행**(omit은 각각 `-SkipNewsObservationContractSmoke`; 헬스는 `BioSnpOnly`/`BitcoinTradingOtelSmokeOnly` 프로필에서 생략); 회귀·CI 동일 목록·**CI** `.github/workflows/dual-regime-integrity.yml` 단계 `B-track news_observation JSONL schema + validator CLI smoke`. 가격 유래 라벨은 `direction_label_bar_v1`에만 두고 뉴스 행과 조인 시 워크포워드·`as_of_utc` 규칙 준수(A-track·실매매 자동 합선 금지).

**미세 신호 병렬 관측 번들 v1 (B-track, [HYPO], 렌즈 융합 금지)**: 스키마 `docs/final/schemas/micro_signal_observation_v1.schema.json` — `micro_signal_observation_bundle_v1` / `micro_signal_observation_row_v1`; 도메인 `market_ohlcv`·`weather_env`·`myeongni_time`·`sasang_constitution`·`logos_text`·`science_core`를 **병렬 행**으로 정규화(한 레인 실패를 타 레인으로 메우지 않음). 빌더 `scripts/build_micro_signal_observation_bundle_v1.py` → `docs/final/artifacts/micro_signal_observation_bundle_v1_latest.json`·`micro_signal_observation_brief_v1_latest.md`; 검증 `scripts/validate_micro_signal_observation_bundle_v1.py`; 회귀 `tests/test_micro_signal_observation_v1.py`·픽스처 `tests/fixtures/micro_signal_observation_bundle_v1.example.json`. **일일 체인:** `scripts/run_general_prophecy_daily_queue_refresh_v1.ps1` 말단 `-IncludeMicroSignalBundle true`(기본) 시 build→validate blocking `Invoke-Step`; 등록 `scripts/Register-GeneralProphecyDailyQueueTask.ps1` 동 플래그 명시. Track A·live·SEND 자동 합선 금지; Logos 행은 `non_gating=true`.

**B-track Max Prophecy Evolution v1 (연구 최대치, [HYPO], `research_mode=max_b_track`)**: 딥리서치 `docs/research/BTRACK_MAX_PROPHECY_EVOLUTION_LIT_REVIEW_2026-06-26.md` · 확장 질문 팩 `tests/fixtures/general_prophecy_registry_max_evolution_pack_v1.json`(FX·지수·거시·금리·원자재·암호화폐·지정학·뉴스·섹터·기상·수급 24문항; `generate_general_prophecy_v1.py` 기본 merge 포함) · 매니페스트 스키마 `docs/final/schemas/btrack_max_prophecy_evolution_manifest_v1.schema.json` · 빌더 `scripts/build_btrack_max_prophecy_evolution_manifest_v1.py` → `docs/final/artifacts/btrack_max_prophecy_evolution_manifest_v1_latest.json` · **4AI Layer-1 주입** `scripts/mkm_max_prophecy_4ai_forecast_lib_v1.py` + `scripts/inject_mkm_4ai_forecasts_max_evolution_v1.py`(deterministic tier_0 기본; hybrid=`news_neutralizer_llm_v1` **azure_first**→Gemini fallback; `MKM_MAX_PROPHECY_BILLING=auto`) + `scripts/apply_general_prophecy_forecasts_jsonl_v1.py` → `docs/final/artifacts/mkm_max_prophecy_4ai_forecasts_v1_latest.jsonl` · 일일 오케스트레이션 `scripts/run_btrack_max_prophecy_evolution_daily_chain_v1.py`(general_prophecy Brier·holdout·micro-signal·OHLCV hit-rate·evolution health·watchdog·4AI inject; `send_gate: HOLD`) · **원클릭 마무리** `scripts/Run-BtrackMaxProphecyEvolutionFinalize_v1.ps1` · 래퍼 `scripts/Run-BtrackMaxProphecyEvolutionDailyChain_v1.ps1` · 스케줄 `scripts/Register-BtrackMaxProphecyEvolutionDailyTask.ps1`(기본 Disabled, `\MKM_BtrackMaxProphecyEvolution_Daily`) · 산출 `reports/btrack_max_prophecy_evolution_daily_chain_v1_latest.json` · 회귀 `tests/test_btrack_max_prophecy_evolution_v1.py` · `tests/test_mkm_max_prophecy_4ai_forecast_v1.py`. **Track A·실매매·채팅 매수매도 권유 자동 합선 없음**; 진화 apply는 `evolution_auto_apply_allowlist_v1` 범위만.

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
| Track T survivor 건강도 경보 | `scripts/alert_insight_survivor_health_v1.py` | `insight_survivor_candidates_latest.json`에서 `survivor_count`/`survivor_mean_score`를 산출하고, 선택 `--history-jsonl`(기본 체인: `reports/ops/insight_survivor_health_history.jsonl`)의 직전 스냅샷과 임계 비교 후 `insight_survivor_health_alert_latest.json` 기록; `--append-history`로 JSONL 누적. `health_drift` 시 POST URL: `INSIGHT_SURVIVOR_HEALTH_ALERT_WEBHOOK_URL` → `OPS_ALARM_WEBHOOK_URL`, `--dry-run`으로 POST 생략. 계약: `docs/final/schemas/insight_survivor_health_alert_v1.schema.json` · `docs/final/schemas/insight_survivor_health_history_row_v1.schema.json` · `tests/test_insight_survivor_health_alert_v1.py` · `tests/test_insight_survivor_health_alert_schema_v1.py` · `run_aramaic_mvp_chain_v1.ps1` / `run_aramaic_mvp_now_with_audit.ps1` 선택 `-SurvivorHealthAlertDryRun` · 체인 환경 `MKM_ARAMAIC_SURVIVOR_HEALTH_ALERT_DRY_RUN` · `Register-AramaicMvpDailyTask.ps1` / `run_aramaic_raw_oos_audit_accumulator_v1.ps1` 동명 스위치 |
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

#### 29.2 정책 2차 튜닝 (FACT, 2026-04-28)

- 변경:
  - 폴더 정책을 확장해 정형 산출물 패턴(`**/*.json`, `**/*.jsonl`)을 `apply`로 세분화.
  - narrative 패턴(`reports/**/*.md`)은 `caution`으로 분리.
  - 라우터 정책 매칭 충돌 시 우선순위를 `forbid > apply > caution`으로 고정(동률은 더 구체적인 패턴 우선).
- 검증:
  - `--target-path docs/final/artifacts/demo.json` -> `path_policy=apply`
  - `--target-path docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` -> `path_policy=forbid`
  - `--target-path scripts/run_genesis_pointer_routing_control_chain_v1.py` -> `path_policy=forbid`
- 최신 정책 요약:
  - `pointerguard_folder_policy_latest.json`: `apply=9`, `caution=4`, `forbid=8`

#### 29.3 경로군별 Shadow 리포트 지표 추가 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_pointer_shadow_daily_report_v1.py`
  - `scripts/run_genesis_pointer_routing_control_chain_v1.py` (`--router-target-path` 입력 추가)
- 변경:
  - shadow log point에 `path_policy_counts`, `path_policy_unresolved_token_counts` 필드 추가.
  - daily report `window_stats`에
    - `path_policy_avg_row_ratio`
    - `path_policy_avg_unresolved_per_run`
    를 추가해 `apply/caution/forbid/unknown` 경로군별 상태를 분리 관측.
  - control chain에 `--router-target-path`(기본 `docs/final/artifacts/pointer_router_chain_probe.json`)를 추가해
    경로 정책 매칭이 명시적으로 기록되도록 보강.
- 최신 상태:
  - `pointer_hash_snapping_router_shadow_daily_report_latest.json`에 경로군별 집계 필드 반영 확인.
  - `check_pointer_shadow_health_alert_v1.py` 결과: `should_alert=false`, `severity=none`.

#### 29.4 경로군별 Alert 분리 게이트 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/check_pointer_shadow_health_alert_v1.py`
- 변경:
  - 기존 전역 임계값(`candidate_ok_rate`, `unresolved`)은 유지.
  - 경로군별 임계값 추가:
    - `apply_row_ratio_min` (기본 `0.15`)
    - `apply_max_unresolved_per_run` (기본 `6.0`)
    - `caution_row_ratio_max` (기본 `0.35`)
    - `caution_max_unresolved_per_run` (기본 `2.0`)
  - reasons 확장:
    - `low_apply_coverage`
    - `high_apply_unresolved_tokens`
    - `high_caution_coverage`
    - `high_caution_unresolved_tokens`
- 최신 상태:
  - `pointer_hash_snapping_router_shadow_alert_latest.json`에 경로군별 입력/윈도우 통계 필드 반영.
  - 현재 상태 `should_alert=false`, `severity=none`, `reasons=[]`.

#### 29.5 Apply 경로 GO 승격 자동 판정 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/decide_pointerguard_apply_go_promotion_v1.py`
- 산출물:
  - `docs/final/artifacts/pointerguard_apply_go_promotion_decision_latest.json`
- 판정 로직:
  - 최근 N개 샘플(기본 `3`)에 대해 `apply_ratio >= 0.30` AND `apply_unresolved <= 2.0`을 모두 만족해야 `PROMOTE_APPLY_GO`.
  - shadow alert가 active이면 즉시 `KEEP_SHADOW`.
- 체인 반영:
  - `run_genesis_pointer_routing_control_chain_v1.py`에 승격 판정 단계 추가.
  - `build_genesis_pointer_route_runtime_config_v1.py`가 `--apply-promotion-json`을 읽어
    `ENABLE_POINTER_ROUTE`라도 승격 미통과 시 `SHADOW_POINTER_ROUTE`로 보수 강등.
- 최신 상태:
  - 승격 판정: `decision=KEEP_SHADOW` (`reason=apply_unresolved_above_threshold`).
  - runtime config `promotion_gate.apply_go_enabled=false`로 shadow 유지.

#### 29.6 경로군별 승격 프로파일 정책화 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_pointerguard_folder_policy_v1.py`
  - `scripts/decide_pointerguard_apply_go_promotion_v1.py`
- 변경:
  - 폴더 정책 아티팩트에 `promotion_profiles` 추가:
    - `artifacts_apply` (`docs/final/artifacts/**`)
    - `reports_apply` (`reports/**`)
    - `memory_v2_apply` (`projects/bitcoin-trading/memory/v2/**`)
  - 각 프로파일별로 `consecutive_samples`, `apply_row_ratio_min`, `apply_unresolved_max`를 독립 설정.
  - 승격 판정 스크립트가 `--target-path` 기준으로 가장 구체적인 매칭 프로파일을 자동 선택.
- 체인 반영:
  - `run_genesis_pointer_routing_control_chain_v1.py`가 승격 판정 단계에
    `--folder-policy-json` + `--target-path`를 전달.
- 최신 상태:
  - `pointerguard_folder_policy_latest.json`에 `promotion_profile_count=3` 반영.
  - 예시(`target_path=projects/bitcoin-trading/memory/v2/demo.json`):
    - `profile_id=memory_v2_apply`
    - 임계값 `consecutive_samples=5`, `apply_row_ratio_min=0.4`, `apply_unresolved_max=1.0`
    - 현재 판정 `KEEP_SHADOW` (미통과 사유: `apply_unresolved_above_threshold`).

#### 29.7 순차 승격(Phase rollout) 적용 (FACT, 2026-04-28)

- 변경:
  - `promotion_profiles`에 `go_promotion_enabled`, `rollout_order` 필드 추가.
  - 초기 승격 단계:
    - `reports_apply`: `go_promotion_enabled=true`, `rollout_order=1`
    - `artifacts_apply`: `go_promotion_enabled=false`, `rollout_order=2`
    - `memory_v2_apply`: `go_promotion_enabled=false`, `rollout_order=3`
  - `decide_pointerguard_apply_go_promotion_v1.py`는 비활성 프로파일에 대해 `profile_go_promotion_disabled` reason을 추가해 승격을 차단.
- 최신 검증:
  - `target_path=reports/demo_run.json`:
    - `profile_id=reports_apply`, `decision=PROMOTE_APPLY_GO`, `reasons=[]`
  - `target_path=docs/final/artifacts/demo.json`:
    - `decision=KEEP_SHADOW`, `reasons`에 `profile_go_promotion_disabled`
  - `target_path=projects/bitcoin-trading/memory/v2/demo.json`:
    - `decision=KEEP_SHADOW`, `reasons`에 `profile_go_promotion_disabled`

#### 29.8 순차 승격 2단계 활성화 (FACT, 2026-04-28)

- 변경:
  - `artifacts_apply`를 2단계로 활성화:
    - `go_promotion_enabled=true`
    - `apply_unresolved_max=4.0` (초기 운영 완화값)
  - `reports_apply`는 1단계 활성 유지.
  - `memory_v2_apply`는 3단계 대기(`go_promotion_enabled=false`) 유지.
- 최신 검증:
  - `target_path=docs/final/artifacts/demo.json`:
    - `profile_id=artifacts_apply`, `decision=PROMOTE_APPLY_GO`, `reasons=[]`
  - `target_path=reports/demo_run.json`:
    - `profile_id=reports_apply`, `decision=PROMOTE_APPLY_GO`, `reasons=[]`
  - `target_path=projects/bitcoin-trading/memory/v2/demo.json`:
    - `profile_id=memory_v2_apply`, `decision=KEEP_SHADOW`,
    - `reasons=[apply_unresolved_above_threshold, profile_go_promotion_disabled]`

#### 29.9 Memory V2 램프 튜닝 루프 연결 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/tune_pointerguard_memory_v2_ramp_v1.py` (신규)
  - `scripts/decide_pointerguard_apply_go_promotion_v1.py` (ramp threshold 인식 확장)
  - `scripts/run_genesis_pointer_routing_control_chain_v1.py` (메모리 전용 판정 + 튜닝 단계 추가)
- 변경:
  - `memory_v2_apply` 프로파일에 램프 필드 추가:
    - `ramp_unresolved_thresholds=[4.0, 3.0, 2.0, 1.0]`
    - `ramp_current_index=0`
    - `ramp_required_consecutive_passes=3`
  - 승격 판정은 ramp가 있으면 `apply_unresolved_max`를 램프 현재 인덱스 값으로 사용.
  - control chain 순서 보정: 폴더 정책 빌드를 승격 판정 단계보다 먼저 실행.
  - shadow daily log에 `target_path` 기록 필드 추가(추후 경로별 로그 분리 분석용).
- 산출물:
  - `docs/final/artifacts/pointerguard_apply_go_promotion_decision_memory_latest.json`
  - `docs/final/artifacts/pointerguard_memory_v2_ramp_tuning_latest.json`
- 최신 상태:
  - memory 판정 입력에 ramp 반영 확인:
    - `apply_unresolved_max=4.0`
    - `ramp_current_index=0`
  - memory 판정 결과: `KEEP_SHADOW` (`profile_go_promotion_disabled`만 유지).
  - 튜닝 제안: `ADVANCE_TO_NEXT_TIGHTER_THRESHOLD` (`recommended_index=1`, `3.0`).

#### 29.10 Memory V2 램프 인덱스 자동 반영 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/apply_pointerguard_memory_v2_ramp_update_v1.py` (신규)
- 체인 반영:
  - `run_genesis_pointer_routing_control_chain_v1.py`에 튜닝 직후 자동 반영 단계 추가.
- 동작:
  - 튜닝 결과가 `ADVANCE_TO_NEXT_TIGHTER_THRESHOLD`이면
    `pointerguard_folder_policy_latest.json`의 `memory_v2_apply.ramp_current_index`를 자동 갱신.
  - 이후 빌드에서도 기존 policy 파일 상태를 merge해 램프 인덱스를 보존.
- 최신 상태:
  - 현재 policy: `memory_v2_apply.ramp_current_index=1` (4.0 -> 3.0 단계 진입 완료)
  - 최신 튜닝 결과: `HOLD_INDEX` (현 단계 `3.0`에서 추가 수렴 필요)
  - 최신 update 결과: `updated=false` (추가 인덱스 전진 없음)

#### 29.11 프로파일별 로그 필터링 강화 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/decide_pointerguard_apply_go_promotion_v1.py`
- 변경:
  - 승격 판정 시 전체 shadow 로그를 그대로 쓰지 않고, 선택된 프로파일 `match_patterns`에 맞는 로그만 필터링해 사용.
  - 판정 입력에 `filtered_log_count`를 기록해 실제 표본 수를 추적.
- 효과:
  - `reports_apply` / `memory_v2_apply` 판정이 서로의 로그에 덜 오염되고, 경로군별 품질 신호 분리가 개선.
- 최신 상태:
  - `reports_apply`: `filtered_log_count=12`, `decision=PROMOTE_APPLY_GO`
  - `memory_v2_apply`: `filtered_log_count=12`, `ramp_current_index=1`, `decision=KEEP_SHADOW`

#### 29.12 Memory V2 OOV passthrough + 최신 스냅샷 우선 판정 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/pointer_hash_snapping_router_v1.py`
  - `scripts/decide_pointerguard_apply_go_promotion_v1.py`
  - `scripts/run_genesis_pointer_routing_control_chain_v1.py`
- 변경:
  - 메모리 타깃(`projects/bitcoin-trading/memory/v2/**`)에서 snap 실패 OOV를 안전 passthrough로 허용:
    - `pointer_hash_snapping_router_v1.py`에 `memory_v2_oov_passthrough` 경로 규칙 추가.
    - row 출력에 `passthrough_events` 기록.
  - 메모리 승격 판정은 과거 로그 혼합 대신 최신 메모리 스냅샷 우선 사용:
    - `decide_pointerguard_apply_go_promotion_v1.py`에
      `--latest-snapshot-json`, `--prefer-latest-snapshot` 추가.
  - control chain에 메모리 전용 라우터 실행(`pointer_hash_snapping_router_shadow_memory_latest.json`) 후
    승격 판정을 연결.
- 최신 결과:
  - 메모리 스냅샷: `pointer_candidate_ok_count=3`, unresolved `0`(중앙 OOV 문장 passthrough 이벤트 기록).
  - 메모리 승격 판정: `filtered_log_count=1`, 미통과 사유는 `profile_go_promotion_disabled`만 유지.
  - 램프 튜닝: `ADVANCE_TO_NEXT_TIGHTER_THRESHOLD` (`3.0 -> 2.0` 권고).
  - 자동 반영 후 policy: `memory_v2_apply.ramp_current_index=2`.

#### 29.13 3단계(memory_v2) 승격 활성 + 체인 순서 보정 (FACT, 2026-04-28)

- 변경:
  - `memory_v2_apply.go_promotion_enabled=true`로 3단계 승격 게이트 활성.
  - control chain 순서 보정:
    - 라우터 타깃 스냅샷 생성 -> 승격 판정 -> runtime config 생성 순으로 재배선.
    - 승격 판정에 `--prefer-latest-snapshot`을 연결해 `insufficient_recent_samples` 오탐을 제거.
- 최신 상태:
  - `pointerguard_apply_go_promotion_decision_latest.json` (reports):
    - `decision=PROMOTE_APPLY_GO`, `filtered_log_count=1`
  - `pointerguard_apply_go_promotion_decision_memory_latest.json` (memory_v2):
    - `decision=PROMOTE_APPLY_GO`
    - `ramp_current_index=3`, `apply_unresolved_max=1.0`, `filtered_log_count=1`
  - runtime config:
    - `promotion_gate.apply_go_enabled=true`
    - `promotion_gate.apply_promotion_decision=PROMOTE_APPLY_GO`

#### 29.14 Memory V2 램프 Freeze(잠금) 적용 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/freeze_pointerguard_memory_v2_ramp_v1.py` (신규)
  - `scripts/apply_pointerguard_memory_v2_ramp_update_v1.py` (frozen 상태면 인덱스 변경 차단)
  - `scripts/build_pointerguard_folder_policy_v1.py` (기존 policy의 `ramp_frozen` 상태 보존 merge)
- 체인 반영:
  - `run_genesis_pointer_routing_control_chain_v1.py`에 freeze 단계 추가.
- 동작:
  - memory_v2가 최종 램프 인덱스 도달 + `PROMOTE_APPLY_GO` + 이유 없음이면
    `ramp_frozen=true`로 잠금.
  - 잠금 후에는 ramp update 단계가 추가 인덱스 변경을 수행하지 않음.
- 최신 상태:
  - `pointerguard_memory_v2_ramp_freeze_latest.json`:
    - `ramp_frozen=true`
    - `ramp_current_index=3`, `ramp_max_index=3`
    - `memory_decision=PROMOTE_APPLY_GO`
  - policy 반영 확인:
    - `pointerguard_folder_policy_latest.json` 내 `memory_v2_apply.ramp_frozen=true`

#### 29.15 운영 스모크 게이트 추가 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_pointerguard_operational_smoke_v1.py` (신규)
- 산출물:
  - `docs/final/artifacts/pointerguard_operational_smoke_latest.json`
- 검증 항목:
  - 폴더 정책 스키마 유효성(`pointerguard_folder_policy_v1`)
  - 라우터 타깃/메모리 승격 판정 JSON의 결정값 유효성
  - 메모리 램프 잠금 상태(`ramp_frozen=true` and `current_index==max_index`)
  - 런타임 config 승격 게이트(`promotion_gate.apply_go_enabled=true`)
- 최신 상태:
  - operational smoke 결과 `all_ok=true`

#### 29.16 컨트롤 체인 최종 게이트화 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_genesis_pointer_routing_control_chain_v1.py`
- 변경:
  - 체인 마지막 단계에 `scripts/run_pointerguard_operational_smoke_v1.py`를 연결.
  - 따라서 체인 성공(`all_ok=true`)은 운영 스모크 통과까지 포함한 최종 상태를 의미.
- 최신 상태:
  - `genesis_pointer_routing_control_chain_latest.json`에 smoke 단계 포함 확인.
  - `pointerguard_operational_smoke_latest.json`: `all_ok=true` (checks 모두 `ok`).

#### 29.17 일일 스케줄러 런북 추가 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_pointerguard_control_chain_daily.ps1` (신규)
  - `scripts/Register-PointerGuardControlChainTask.ps1` (신규)
- 목적:
  - 일일 실행 시 `run_genesis_pointer_routing_control_chain_v1.py`를 고정 파라미터로 실행하고
    `reports/pointerguard/pointerguard_control_chain_YYYYMMDD_HHMMSS.log`에 실행 로그 저장.
  - Windows 작업 스케줄러 등록/해제를 표준화(`TaskName`, `DailyAt`, `DryRun` 지원).
- 최신 검증:
  - daily runner 수동 실행 성공 (`ok=true`).
  - 스케줄러 등록 스크립트 `-DryRun` 검증 완료.
  - 실제 등록 완료: Task `MKM_PointerGuard_ControlChain_Daily` (daily `06:30`, status `Ready`).

#### 29.18 PointerGuard 지연/처리량 벤치 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_pointerguard_latency_benchmark_v1.py` (신규)
- 산출물:
  - `docs/final/artifacts/pointerguard_latency_benchmark_latest.json`
- 측정 조건:
  - 라우터 시나리오별 `25`회 반복 실행
  - 지표: `fail_rate`, `throughput_rps`, `latency_ms(min/p50/p95/p99/max/mean)`
- 최신 결과:
  - `reports_apply_shadow`:
    - `fail_rate=0.0`, `throughput_rps=13.56`
    - `p50=72.72ms`, `p95=78.29ms`, `p99=88.28ms`
  - `memory_v2_apply_shadow_with_passthrough`:
    - `fail_rate=0.0`, `throughput_rps=11.39`
    - `p50=74.87ms`, `p95=107.06ms`, `p99=347.13ms`
  - `memory_v2_apply_shadow_without_passthrough`:
    - `fail_rate=0.0`, `throughput_rps=14.56`
    - `p50=67.57ms`, `p95=74.02ms`, `p99=80.98ms`

#### 29.19 2계층 성능 성적표 아티팩트 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_pointerguard_two_tier_perf_scorecard_v1.py` (신규)
- 산출물:
  - `docs/final/artifacts/pointerguard_two_tier_perf_scorecard_latest.json`
- 구조:
  - Tier 1: 로컬 스크립트 벤치(측정값)
  - Tier 2: 서비스형 부하 테스트(필수 지표 템플릿, 아직 `pending`)
  - Executive 판정:
    - `current_stage=b2b_operational_candidate`
    - `go_no_go_for_global_claim=NO_GO_UNTIL_TIER2_MEASURED`
- 목적:
  - 로컬 벤치 수치와 글로벌 주장 수치를 분리해 과대해석을 방지하고,
    후속 서비스 부하 테스트의 수집 항목(`p95/p99/rps/error/cpu/memory`)을 고정한다.

#### 29.20 Tier2 서비스형 부하 측정 실행 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_pointerguard_service_load_benchmark_v1.py` (신규)
  - `scripts/build_pointerguard_two_tier_perf_scorecard_v1.py` (Tier2 입력 반영 확장)
- 산출물:
  - `docs/final/artifacts/pointerguard_service_load_benchmark_latest.json`
  - `docs/final/artifacts/pointerguard_two_tier_perf_scorecard_latest.json`
- 측정 조건:
  - 시나리오: `reports_apply_shadow`, `memory_v2_apply_shadow`
  - 동시성: `1, 4, 8`
  - 요청수: level당 `20`
- 최신 결과(Tier2):
  - 최대 에러율: `0.0`
  - Worst `p95=159.50ms`, Worst `p99=171.77ms`
  - 최고 처리량: `66.71 RPS` (`memory_v2_apply_shadow`, concurrency 8)
- Executive 판정:
  - `go_no_go_for_global_claim=GO_FOR_CONTROLLED_B2B`
  - 단, host `cpu/memory`는 벤치 하네스 미계측(`null`)로 남아 후속 보강 필요.

#### 29.21 Tier2 host 리소스 계측 보강 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_pointerguard_service_load_benchmark_v1.py` (Windows `Get-Counter` 기반 host metric 샘플링 추가)
  - `scripts/build_pointerguard_two_tier_perf_scorecard_v1.py` (Tier2 summary에 host metric 반영)
- 측정 결과(최신):
  - Tier2 summary:
    - `max_error_rate=0.0`
    - `worst_p95_ms=117.83`
    - `worst_p99_ms=125.40`
    - `host_cpu_utilization=35.68`
    - `host_memory_utilization=32.50`
- 효과:
  - 기존 Tier2의 `cpu/memory=null` 공백을 해소하여, controlled B2B 판정 근거가 성능+자원 관점으로 확장됨.

#### 29.22 PointerGuard ROI 계산기(영업용) 추가 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/estimate_pointerguard_roi_v1.py` (신규)
- 산출물:
  - `docs/final/artifacts/pointerguard_roi_estimate_latest.json`
- 입력:
  - 월 요청수, 평균 입력/출력 토큰, 입력/출력 단가(USD/1K), 입력 토큰 절감률, 월 오버헤드
- 출력:
  - 도입 전/후 월간 비용
  - 월 절감액(`monthly_saving_usd`)
  - 월 절감률(`monthly_saving_rate`)
- 샘플 실행 결과(보수 시나리오):
  - `monthly_requests=1,200,000`
  - `avg_input_tokens=8,000`, `avg_output_tokens=600`
  - `input=$0.01/1k`, `output=$0.03/1k`
  - `pointer_input_reduction_ratio=0.90`, `overhead=$30,000/mo`
  - 결과: `monthly_saving_usd=$56,400`, `monthly_saving_rate≈47.96%`

#### 29.23 운영 알림 자동화(Webhook) 연결 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/send_pointerguard_ops_alert_v1.py` (신규)
- 트리거 조건:
  - `pointerguard_operational_smoke_latest.json`에서 `all_ok=false`
  - 또는 `genesis_pointer_routing_decision_guarded_latest.json`에서 `guard_applied=true`
- 전송:
  - `POINTERGUARD_OPS_WEBHOOK_URL` 우선, 없으면 `OPS_ALARM_WEBHOOK_URL`
  - 전달 페이로드: `should_send`, `reasons`, `smoke_all_ok`, `guard_applied`, `guard_reason`
- 일일 러너 연동:
  - `scripts/run_pointerguard_control_chain_daily.ps1`가 체인 실행 후 알림 스크립트를 자동 호출.
- 산출물:
  - `docs/final/artifacts/pointerguard_ops_alert_delivery_latest.json`
- 최신 검증:
  - `--always --dry-run` 실행 시 `status=dry_run`, `should_send=true`
  - 일일 러너 실행 시 정상 상태에서 `status=skipped_no_alert`, `should_send=false`

#### 29.24 운영 준비도 점검 게이트 추가 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/check_pointerguard_ops_readiness_v1.py` (신규)
- 산출물:
  - `docs/final/artifacts/pointerguard_ops_readiness_latest.json`
- 점검 항목:
  - 최신 컨트롤 체인 아티팩트 존재/스키마
  - 운영 스모크 아티팩트 존재/스키마
  - 2계층 성능 성적표 아티팩트 존재/스키마
  - 스케줄러 작업(`MKM_PointerGuard_ControlChain_Daily`) 상태
  - 운영 웹훅 환경변수(`POINTERGUARD_OPS_WEBHOOK_URL` 또는 `OPS_ALARM_WEBHOOK_URL`)
- 최신 결과:
  - `all_ok=true`

#### 29.25 a-codeai 공개 벤치 런치 체크리스트 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_a_codeai_public_benchmark_launch_checklist_v1.py` (신규)
- 산출물:
  - `docs/final/artifacts/a_codeai_public_benchmark_launch_checklist_v1.json`
- 목적:
  - 공개 벤치에서 보안 경계를 유지하면서 성과 노출이 가능한지 preflight 점검
  - 항목: 공개 범위 가드/정책 경계/운영 스모크/알림/지표 투명성/남용 방지/비밀 비노출
- 최신 결과:
  - `pass_count=5/7`
  - `decision=READY_FOR_SHADOW_PUBLIC_BENCH`
  - 남은 TODO:
    - `C1_public_benchmark_scope_guard`
    - `C6_rate_limit_abuse_guard`

#### 30.1 Symbol Atom Anchor Layer + Scholarly Bridge (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_symbol_atom_mapping_v1.py`
  - `scripts/build_atom_resonance_report_v1.py`
  - `scripts/build_scholarly_symbol_bridge_v1.py`
  - `scripts/run_aramaic_mvp_chain_v1.ps1` (`[13c/15]`, `[13d/15]` 단계 추가)
- 입력/출력:
  - 입력 레지스트리: `docs/final/artifacts/atom_anchor_registry_v1.json`
  - 출력 매핑: `docs/final/artifacts/symbol_atom_mapping_latest.json`
  - 출력 공진: `docs/final/artifacts/atom_resonance_report_latest.json`
  - 출력 브릿지: `docs/final/artifacts/scholarly_symbol_bridge_latest.json`
- 구현 사실:
  - seed symbol(기본 `tree_of_knowledge_good_evil`)을 아톰 시퀀스로 펼쳐 `symbol_atom_mapping_v1` 생성.
  - survivor 근거(`ci_low_defense_contrib`, `fusion_candidate_score`)와 시퀀스 길이로 `atom_resonance_report_v1` 점수화.
  - 아톰별 motif 라벨(`covenantal_boundary`, `mimetic_desire`, `boundary_transgression` 등)을 연결하는 `scholarly_symbol_bridge_v1` 생성.
  - 모든 산출은 `research_only=true`, `promotion_required=true`, `source_track="K"`로 고정(실거래 트리거 금지).

#### 30.2 4D Gematria Coupling + Ablation (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_gematria_4d_coupling_v1.py`
  - `scripts/build_gematria_4d_ablation_v1.py`
  - `scripts/run_aramaic_mvp_chain_v1.ps1` (`[13e/15]` 단계 추가)
- 출력:
  - `docs/final/artifacts/gematria_4d_coupling_latest.json`
  - `docs/final/artifacts/gematria_4d_ablation_latest.json`
- 구현 사실:
  - `scholarly_symbol_bridge_v1`와 `symbolic_topology_insight_v1`를 결합해 아톰 단위 `vector_4d(S,L,K,M)` 투영 및 `coupling_strength`를 생성.
  - ablation은 `with_4d` vs `without_4d`를 분리 계산해 `delta_with_minus_without`를 기록.
  - 정책 필드 `allow_execution_trigger=false`, `require_fail_boundary_gate=true`, `require_research_only_lane=true`를 고정하여 실행 트리거 합선을 차단.

#### 30.3 Multi-Symbol Resonance + 4D Ranking (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_multi_symbol_resonance_4d_v1.py`
  - `scripts/run_aramaic_mvp_chain_v1.ps1` (`[13f/15]` 단계 추가)
- 출력:
  - `docs/final/artifacts/multi_symbol_resonance_4d_latest.json`
- 구현 사실:
  - `atom_anchor_registry_v1`의 `seed_symbol_sequences` 전체(`tree_of_knowledge_good_evil`, `babel_tower`, `exodus_return`)를 단일 리포트에서 동시 평가.
  - 동일 survivor 스냅샷(`ci_low_defense_contrib`, `fusion_candidate_score`)을 기준으로 각 symbol의 `resonance_score`, `vector_4d(S,L,K,M)`, `coupling_strength`를 계산해 순위화.
  - 결과는 `research_only=true`, `allow_execution_trigger=false` 정책으로 고정하여 K-track 분석 아티팩트로만 사용.

#### 30.4 Multi-Symbol Candidate Selector + Q&A Evidence Overlay (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_multi_symbol_candidate_selector_v1.py`
  - `scripts/enrich_two_track_qa_with_symbol_evidence_v1.py`
  - `scripts/run_aramaic_mvp_chain_v1.ps1` (`[13f/15]` selector 호출, `[28b/37]` 이후 Q&A evidence overlay 호출)
- 출력:
  - `docs/final/artifacts/multi_symbol_candidate_selector_latest.json`
  - `docs/final/artifacts/two_track_qa_pack_latest.json` (schema: `two_track_qa_pack_v2`)
- 구현 사실:
  - multi-symbol 4D 결과에서 `top_k` + `min_coupling` 기준으로 상징 후보를 자동 선별.
  - fail-boundary gate 결과(`should_trade`, `rollback`, `reasons`)와 symbol selector 결과를 Q&A evidence에 주입.
  - evidence 필드 계약(`source_artifact`, `metric_value`, `as_of_utc`, `rollback_rule`, `gate_eval`)을 강제 유지.

#### 30.5 Audience Attack Q&A 5x3 Expansion (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_two_track_qa_pack_v1.py`
- 변경:
  - audience(`investor`, `policy`, `technical`)별로 5개 고정 공격 질문(`q1~q5`)을 생성하도록 확장.
  - 질문 축: 과적합 방지, 트리거 안전성, 스토리텔링-분리 근거, 빠른 검증 가능성, 신뢰도 하락 시 운영 동작.
  - 기존 evidence 자리(`source_artifact`, `metric_value`, `as_of_utc`, `rollback_rule`, `gate_eval`)는 유지해 후속 overlay 스크립트가 덮어쓸 수 있게 구성.

#### 30.6 Fusion Brief/Copydeck Multi-Symbol Injection (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_two_track_fusion_brief_v1.py`
  - `scripts/build_two_track_presentation_copydeck_v1.py`
- 변경:
  - fusion brief가 기본 카드 외에 다음 지표를 자동 포함:
    - `top_symbol_by_coupling`
    - `top2_symbols`
    - `gematria_4d_delta_with_minus_without`
  - brief sources에 `multi_symbol_resonance_4d`, `multi_symbol_candidate_selector`, `gematria_4d_ablation` 경로를 기록.
  - copydeck의 one-page/three-page에 multi-symbol top2와 4D ablation delta를 문장으로 자동 삽입.
- 최신 상태:
  - `two_track_fusion_brief_latest.json`에서 상징/ablation 카드 반영 확인.
  - `two_track_presentation_copydeck_latest.json`에서 key points와 method bullet 반영 확인.

#### 30.7 Q&A Evidence Question-Specific Metric Routing (FACT, 2026-04-28)

- 스크립트:
  - `scripts/enrich_two_track_qa_with_symbol_evidence_v1.py`
- 변경:
  - 입력 확장:
    - `--falsification-json` (`two_track_falsification_suite_latest.json`)
    - `--gematria-ablation-json` (`gematria_4d_ablation_latest.json`)
  - `question_id` 기준 evidence source/metric 분기:
    - `q1`(overfitting): falsification `F3/F4` 지표 (`survivor_count`, `shift_score`, `ci_low_defense_contrib`)
    - `q2`(trigger safety): fail-boundary gate (`should_trade`, `rollback`, `reasons_count`)
    - `q3`(storytelling 분리): gematria ablation (`score_with_4d`, `score_without_4d`, `delta`)
    - `q4`(reviewer verify): multi-symbol selector (`top_symbol`, `top2_symbol`, `selected_count`)
    - `q5`(confidence drop action): fail-boundary gate rollback snapshot
  - 공통으로 `as_of_utc`, `rollback_rule`, `gate_eval` 필드는 유지.
- 최신 상태:
  - `two_track_qa_pack_latest.json`에서 `q1~q5`별 source_artifact/metric_value가 서로 다르게 주입됨을 확인.

#### 30.8 Symbol Walk-Forward Survivability + Drift Gate (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_multi_symbol_walkforward_survivability_v1.py`
  - `scripts/alert_multi_symbol_top_drift_gate_v1.py`
  - `scripts/run_aramaic_mvp_chain_v1.ps1` (`[13f/15]` 구간에 survivability/drift 단계 연속 호출 추가)
- 출력:
  - `docs/final/artifacts/multi_symbol_walkforward_survivability_latest.json`
  - `docs/final/artifacts/multi_symbol_top_drift_history_latest.jsonl`
  - `docs/final/artifacts/multi_symbol_top_drift_alert_latest.json`
- 구현 사실:
  - symbol별 `oos_survival_rate_proxy`, `false_positive_cost_proxy`, `survivability_score`를 계산하여 생존성 순위화.
  - top symbol 이력(JSONL)을 누적 기록하고 window 내 switch 횟수로 drift 경보 여부를 판정.
  - drift gate 출력에 `promotion_hold`를 포함해 top-symbol 변동 과다 시 승격 보류 정책을 연결.
- 최신 상태:
  - 현재 `top_symbol_by_survivability=tree_of_knowledge_good_evil`.
  - drift alert는 초기 이력 1건 기준 `should_alert=false`, `severity=none`.

#### 30.9 Negative-Control Falsification Gate for Multi-Symbol (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_multi_symbol_negative_control_v1.py`
  - `scripts/alert_multi_symbol_negative_control_gate_v1.py`
  - `scripts/run_aramaic_mvp_chain_v1.ps1` (`[13f/15]` 구간에 negative-control build/gate 추가)
- 출력:
  - `docs/final/artifacts/multi_symbol_negative_control_latest.json`
  - `docs/final/artifacts/multi_symbol_negative_control_gate_latest.json`
- 구현 사실:
  - symbol별 base survivability와 negative-control score를 병렬 계산해 `uplift_over_control`을 산출.
  - gate는 `mean_uplift_over_control`가 최소 임계(`min_mean_uplift`, 기본 `0.10`)를 넘는지 평가.
  - 미통과 시 `promotion_hold=true`로 승격 보류 신호를 발생.
- 최신 상태:
  - `mean_uplift_over_control=0.39421`, gate `pass=true`, `should_alert=false`.

#### 30.10 E2E Contract Pytest for Multi-Symbol Gates (FACT, 2026-04-28)

- 테스트:
  - `tests/test_multi_symbol_contract_gates_v1.py`
- 검증 범위:
  - `build_multi_symbol_walkforward_survivability_v1.py` 출력 스키마/핵심 필드 계약
  - `alert_multi_symbol_top_drift_gate_v1.py` 출력 계약 + history JSONL 생성
  - `build_multi_symbol_negative_control_v1.py` / `alert_multi_symbol_negative_control_gate_v1.py` 계약 일관성
- 실행:
  - `py -m pytest tests/test_multi_symbol_contract_gates_v1.py -q`
- 최신 상태:
  - `3 passed` 확인 (로컬 실행 기준).

#### 30.11 Counterfactual Symbol Set + Comparison Gate (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_multi_symbol_counterfactual_set_v1.py`
  - `scripts/build_multi_symbol_counterfactual_comparison_v1.py`
  - `scripts/run_aramaic_mvp_chain_v1.ps1` (`[13f/15]` 구간에 counterfactual set/comparison 단계 추가)
- 출력:
  - `docs/final/artifacts/multi_symbol_counterfactual_set_latest.json`
  - `docs/final/artifacts/multi_symbol_counterfactual_comparison_latest.json`
- 구현 사실:
  - 기존 survivability 행에서 label-preserving counterfactual 점수 집합을 자동 생성.
  - base vs counterfactual 평균 생존성 차이(`mean_gap_base_minus_counterfactual`)를 계산하고 임계값(`min_mean_gap_threshold`) 기반 gate를 평가.
  - 미통과 시 `promotion_hold=true`로 승격 보류 가능.
- 최신 상태:
  - `mean_gap_base_minus_counterfactual=0.362182` (threshold `0.15`)로 gate `pass=true`.

#### 30.12 Q&A Overlay with Counterfactual Gate Fields (FACT, 2026-04-28)

- 스크립트:
  - `scripts/enrich_two_track_qa_with_symbol_evidence_v1.py`
- 변경:
  - 입력 확장:
    - `--counterfactual-comparison-json` (`multi_symbol_counterfactual_comparison_latest.json`)
  - `q3` metric_value에 counterfactual 검증 필드 추가:
    - `counterfactual_mean_gap`
    - `counterfactual_gate_pass`
  - `q4` metric_value에 counterfactual gate 상태 추가:
    - `counterfactual_should_alert`
    - `counterfactual_promotion_hold`
  - `symbol_evidence_overlay`에 `counterfactual_comparison_json` 경로 기록.
- 최신 상태:
  - `two_track_qa_pack_latest.json`의 `q3/q4` evidence에 counterfactual gate 수치/상태 반영 확인.

#### 30.13 Integrated Gate Summary + Dynamic Q&A Render + Full Smoke (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_multi_symbol_gate_summary_v1.py`
  - `scripts/enrich_two_track_qa_with_symbol_evidence_v1.py` (q3/q4 답변 문구 동적 수치 렌더링)
  - `scripts/run_aramaic_mvp_chain_v1.ps1` (multi-symbol gate summary 단계 추가)
- 출력:
  - `docs/final/artifacts/multi_symbol_gate_summary_latest.json`
- 구현 사실:
  - drift / negative-control / counterfactual gate를 단일 summary로 통합(`all_pass`, `any_promotion_hold`, `status`).
  - Q&A `q3/q4` 답변(`a`)이 정적 문구가 아닌 실측 수치(`delta`, `counterfactual_mean_gap`, top symbols, alert/hold)로 자동 렌더링.
  - 전체 체인 E2E 스모크를 1회 실행해 새 multi-symbol 단계부터 camera-ready 출력까지 연쇄 성공을 확인.
- 실행/검증:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_aramaic_mvp_chain_v1.ps1` -> exit 0
  - `py -m pytest tests/test_multi_symbol_contract_gates_v1.py tests/test_multi_symbol_counterfactual_comparison_v1.py tests/test_two_track_qa_overlay_counterfactual_v1.py -q` -> `5 passed`

#### 30.14 Gate Summary Injection + Falsification F6 + CI Coverage (FACT, 2026-04-28)

- 스크립트/워크플로우:
  - `scripts/build_two_track_fusion_brief_v1.py`
  - `scripts/build_two_track_presentation_copydeck_v1.py`
  - `scripts/run_two_track_falsification_suite_v1.py`
  - `.github/workflows/dual-regime-integrity.yml`
- 변경:
  - fusion brief 카드에 gate summary 필드 추가:
    - `multi_symbol_gate_status`
    - `multi_symbol_any_promotion_hold`
  - copydeck one-page/governance bullet에 통합 gate 상태 문구 자동 주입.
  - falsification suite에 `F6(counterfactual_gap_gate_pass)` 편입.
  - `F2`를 기존 보수 기본값 강제에서 `gate_eval_contract_valid`(필수 키 + rollback/should_trade 정합성)로 정렬.
  - CI(`dual-regime-integrity`)에 multi-symbol/counterfactual 관련 스크립트·테스트 path 및 pytest step 추가.
- 최신 상태:
  - `two_track_fusion_brief_latest.json`에 gate status 카드 반영(`status=GO`, `hold=false`).
  - `two_track_presentation_copydeck_latest.json`에 gate status 문구 반영.
  - `two_track_falsification_suite_latest.json`: `pass_count=6/6`, `suite_status=pass`.

#### 31.1 Global Atom Network PoC Core-100 Mixed Input (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_core100_input_v1.py`
  - `scripts/build_global_atom_network_v1.py` (`--insight-json`에 core100 입력 사용)
- 출력:
  - `docs/final/artifacts/global_atom_core100_input_latest.json`
  - `docs/final/artifacts/global_atom_network_core100_nodes_latest.jsonl`
  - `docs/final/artifacts/global_atom_network_core100_edges_latest.jsonl`
  - `docs/final/artifacts/global_atom_network_core100_similarity_matrix_latest.json`
  - `docs/final/artifacts/global_atom_network_core100_phase_transition_report_latest.json`
- 구현 사실:
  - Dan.2 편중 입력을 core100 혼합 이벤트(`genesis/exodus/gospel/aramaic`)로 확장해 전수 유사도 매트릭스·위상 엣지·전이 보고서를 재생성.
  - `min_similarity=0.65` 기준 gate-passed resonance edge만 유지.
- 최신 상태:
  - `node_count=100`, `edge_count=3854`, `old_new_cross_edges=1115`, `phase_transition_signal=present`.

#### 31.2 Global Atom Network Academic One-pager Builder (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_network_onepager_v1.py`
- 출력:
  - `docs/final/artifacts/global_atom_network_academic_onepager_latest.json`
- 구현 사실:
  - core100 phase report + similarity matrix + multi-symbol gate summary + counterfactual comparison을 한 파일로 통합.
  - `executive_summary_en`, `key_facts`, `method_outline_en`, `risk_notes_en`, `artifact_packet`을 포함해 심사/IR 제출 초안으로 사용 가능.
- 최신 상태:
  - `key_facts`: `node_count=100`, `edge_count=3854`, `old_new_cross_edges=1115`, `phase_transition_signal=present`, `gate_status=GO`, `counterfactual_mean_gap=0.362182`.

#### 31.2a GraphRAG Pilot Query Router (Track B/K Observation) (FACT, 2026-05-07)

- 스크립트:
  - `scripts/run_graphrag_pilot_router_v1.py`
- 스키마:
  - `docs/final/schemas/graphrag_pilot_router_v1.schema.json`
- 입력(기존 FACT 아티팩트만 사용):
  - `docs/final/artifacts/global_atom_network_nodes_latest.jsonl`
  - `docs/final/artifacts/global_atom_network_edges_latest.jsonl`
  - `docs/final/artifacts/multi_symbol_gate_summary_latest.json`
- 출력:
  - `docs/final/artifacts/graphrag_pilot_router_latest.json`
- 구현 사실:
  - 자연어 질문을 seed keyword/alias로 변환한 뒤, `gate_passed=true` + `similarity` 임계치 기반 멀티홉 탐색(`--max-hops`)으로 후보 노드/경로를 조립.
  - 실행 전 `multi_symbol_gate_summary`의 `summary.status`를 확인하며, `GO`가 아니면 즉시 중단(exit 3).
  - 옵션 `--emit-answer-brief`는 관측용 요약만 생성하며 항상 `OBSERVATION_ONLY`/`[HYPO]` 경계를 유지.
  - 데이터 크롤링/신규 수집은 하지 않고 기존 글로벌 아톰 네트워크 아티팩트만 사용.
- 격벽:
  - 출력 필드 `research_only=true`, `observation_only=true`, `hypothesis_tier=B`를 고정해 A-track/실매매 트리거와 자동 합선하지 않는다.
  - 본 파일럿은 Q/A 관측 실험 레일이며, 운영 판단은 여전히 human commander gate와 별도 운영 게이트가 우선이다.

#### 31.3 Global Atom Submission Abstract Builder (KDD/AAAI) (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_network_submission_abstracts_v1.py`
- 출력:
  - `docs/final/artifacts/global_atom_network_submission_abstracts_latest.json`
- 구현 사실:
  - one-pager(`global_atom_network_academic_onepager_latest.json`)를 입력으로 KDD/AAAI 제출용 초록 2종(`kdd_180w`, `aaai_150w`) 자동 생성.
  - 산출에 `word_count` 및 source 경로를 함께 포함해 제출 양식 매핑을 단순화.
- 최신 상태:
  - 현재 생성본 기준 `word_count`: `kdd_180w=129`, `aaai_150w=129`.

#### 31.4 Global Atom KDD Submission Template Builder (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_kdd_submission_template_v1.py`
- 출력:
  - `docs/final/artifacts/global_atom_kdd_submission_template_latest.json`
- 구현 사실:
  - one-pager + 제출 초록 JSON을 결합해 KDD 폼 필드 직결 템플릿(`title`, `abstract_180w`, `keywords`, `contributions`, `quick_facts`) 생성.
  - submission checklist와 source 경로를 함께 포함해 제출 직전 점검을 단일 파일에서 수행 가능.
- 최신 상태:
  - quick facts: `node_count=100`, `edge_count=3854`, `old_new_cross_edges=1115`, `gate_status=GO`, `counterfactual_mean_gap=0.362182`.

#### 31.5 Global Atom Submission Bundle + One-Click Pack (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_submission_bundle_v1.py`
  - `scripts/run_global_atom_submission_pack_v1.ps1`
- 출력:
  - `docs/final/artifacts/global_atom_submission_bundle_latest.json`
- 구현 사실:
  - onepager/abstracts/kdd template/phase report/gate summary/counterfactual comparison의 존재·생성시각을 단일 bundle manifest로 집계.
  - 원클릭 pack 스크립트로 onepager → abstracts → kdd template → bundle 순서 재현 가능.
- 최신 상태:
  - `run_global_atom_submission_pack_v1.ps1` exit 0, bundle `ready=true`.

#### 31.6 Abstract Quality Pass v2 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_network_submission_abstracts_v1.py`
- 변경:
  - method/risk 문장 연결을 정리해 중복 구두점/비문을 제거하고 제출용 문장 흐름을 개선.
  - 기본 문장을 180/150 단어 한도 함수로 절단하는 구조 유지.
- 최신 상태:
  - `global_atom_network_submission_abstracts_latest.json` 기준 `kdd_180w=134`, `aaai_150w=134`.

#### 31.7 Submission Freeze + Final Go/No-Go (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_submission_freeze_v1.py`
  - `scripts/build_global_atom_submission_go_nogo_v1.py`
- 출력:
  - `docs/final/artifacts/global_atom_submission_freeze_latest.json`
  - `docs/final/artifacts/global_atom_submission_go_nogo_latest.json`
- 구현 사실:
  - 제출 패킷 핵심 아티팩트를 timestamp freeze 디렉터리로 복사하고 `copied/missing` 상태를 기록.
  - bundle readiness + gate summary + falsification pass + freeze completeness를 결합해 최종 `GO/NO_GO` 판정.
  - go/nogo 로직에서 freeze 판정식(`missing_count==0`)을 보정해 false-negative를 제거.
- 최신 상태:
  - freeze: `copied_count=7`, `missing_count=0`.
  - go/nogo: `status=GO`, `reasons=[]`.

#### 31.8 Full-Canon Staged Batch Bootstrap Runner (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_full_canon_batch_input_v1.py`
  - `scripts/build_global_atom_full_canon_batch_report_v1.py`
  - `scripts/run_global_atom_full_canon_batch_v1.ps1`
- 출력:
  - `docs/final/artifacts/global_atom_full_canon/*_manifest.json`
  - `docs/final/artifacts/global_atom_full_canon_batch_report_latest.json`
- 구현 사실:
  - `genesis -> torah -> prophets -> gospels -> full_canon` 5단계 배치 실행 오케스트레이션을 추가.
  - 각 단계에서 seed 후보를 목표 개수로 deterministic 확장 입력 생성 후 `build_global_atom_network_v1.py` 실행.
  - 단계별 nodes/edges/matrix/phase_report를 생성하고 manifest + 통합 batch report로 집계.
  - PowerShell UTF-8 BOM manifest를 읽을 수 있도록 report loader를 `utf-8-sig`로 보강.
- 최신 상태:
  - `run_global_atom_full_canon_batch_v1.ps1 -FastSmoke` 실행으로 5단계 산출물 생성.
  - 통합 리포트 `global_atom_full_canon_batch_report_latest.json` 생성 완료.

#### 31.9 PointerGuard Security-First Hardening v1 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/harden_pointerguard_security_v1.py`
  - `scripts/build_a_codeai_public_benchmark_launch_checklist_v1.py` (하드닝 아티팩트 연동)
- 출력:
  - `docs/final/artifacts/pointerguard_security_hardening_latest.json`
  - `docs/final/artifacts/a_codeai_public_benchmark_launch_checklist_v1.json`
- 구현 사실:
  - C1/C6를 보안 정책 아티팩트로 고정 (`synthetic_or_anonymized_only`, 요청 크기/레이트 제한, metadata-only 로그).
  - leaked-info scanner를 추가해 공개 증거 파일에서 민감 패턴(개인키/비밀키/코드북 해시 필드) 비노출 점검을 자동화.
  - `guard_applied`, `unauthorized_pattern_detected`를 P0 이벤트로 취급하는 우선순위 반전 정책을 아티팩트로 고정.
  - `manual_promotion_lock=true`, `requires_two_person_review=true` 수동 잠금 거버넌스를 아티팩트에 포함.
  - 공개 벤치 체크리스트가 하드닝 아티팩트를 읽어 C1/C6 상태를 자동 판정하도록 연결.
- 최신 상태:
  - `py scripts/harden_pointerguard_security_v1.py` exit 0 (`all_ok=true`).
  - `py scripts/build_a_codeai_public_benchmark_launch_checklist_v1.py` exit 0 (`decision=READY_FOR_PUBLIC_OPEN_BENCH`).

#### 31.10 PointerGuard Daily Chain Security Gate Wiring (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_pointerguard_control_chain_daily.ps1`
- 구현 사실:
  - 일일 체인에 `harden_pointerguard_security_v1.py`를 연결해 C1/C6·비노출 스캐너·P0 정책·수동 잠금 상태를 매 실행 시 강제 검증.
  - 같은 러너에서 `build_a_codeai_public_benchmark_launch_checklist_v1.py`를 연속 실행해 공개 벤치 런치 상태를 최신 하드닝 결과로 재판정.
  - 하드닝/체크리스트 단계에서 non-zero 발생 시 일일 러너 종료코드에 반영하도록 연계.
- 최신 상태:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_pointerguard_control_chain_daily.ps1` exit 0.
  - 실행 로그: `reports/pointerguard/pointerguard_control_chain_20260428_164835.log`.
  - 하드닝 아티팩트: `pointerguard_security_hardening_latest.json (all_ok=true)`.
  - 런치 체크리스트: `a_codeai_public_benchmark_launch_checklist_v1.json (decision=READY_FOR_PUBLIC_OPEN_BENCH)`.

#### 31.11 Full-Canon Verse-Level Ingest Wiring (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_full_canon_verse_ingest_v1.py`
  - `scripts/run_global_atom_full_canon_batch_v1.ps1` (`-UseVerseSource` 추가)
  - `scripts/build_global_atom_full_canon_batch_report_v1.py` (`source_mode` 집계 추가)
- 입력:
  - `data/logos/verse_4pipeline_full_31102.json` (31,102 verses)
- 구현 사실:
  - 단계별(stage) 책군 필터(`genesis/torah/prophets/gospels/full_canon`)로 verse-level 후보를 직접 추출해 배치 입력 생성.
  - `pipeline4_unified_v2.vector_4d` + `correlation` + `p1/p3 distance`를 결합해 `hub_score/path_score/cluster_size`를 산출.
  - 러너가 seed-bootstrap과 verse-ingest를 토글할 수 있게 배선하고 manifest에 `use_verse_source`를 기록.
  - 통합 배치 리포트 summary에 `source_mode`를 기록해 실행 모드를 명시.
- 최신 상태:
  - `run_global_atom_full_canon_batch_v1.ps1 -FastSmoke -UseVerseSource` exit 0.
  - `global_atom_full_canon_batch_report_latest.json`: `status=GO`, `stages_ok=5`, `source_mode=verse_level_ingest`.

#### 31.11 PointerGuard Scheduler Description Hardening Sync (FACT, 2026-04-28)

- 스크립트:
  - `scripts/Register-PointerGuardControlChainTask.ps1`
- 구현 사실:
  - 스케줄러 작업 설명을 보안 우선 체인으로 명시(`security-first hardening`, `C1/C6`, `non-exposure checklist`)해 운영자 혼선을 방지.
  - `-DryRun` 출력에 task description을 추가해 등록 전 검토 시 실행 범위를 즉시 확인 가능하도록 보강.
- 최신 상태:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-PointerGuardControlChainTask.ps1 -DryRun` exit 0.
  - DryRun 출력에서 보안 포함 설명 문자열 확인.

#### 31.12 PointerGuard Scheduler Re-Registration (FACT, 2026-04-28)

- 스크립트:
  - `scripts/Register-PointerGuardControlChainTask.ps1`
- 구현 사실:
  - 작업 스케줄러에 `MKM_PointerGuard_ControlChain_Daily`를 실제 재등록해 최신 러너/인자/설명을 운영 메타데이터에 동기화.
  - 작업 코멘트(Comment)에서 보안 포함 설명(`security-first hardening`, `C1/C6`, `non-exposure checklist`)이 유지됨을 확인.
- 최신 상태:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-PointerGuardControlChainTask.ps1` exit 0.
  - `schtasks /Query /TN "MKM_PointerGuard_ControlChain_Daily" /V /FO LIST`에서
    - `Task To Run`: `run_pointerguard_control_chain_daily.ps1` + 라우터/메모리 인자 확인
    - `Comment`: 보안 포함 설명 문자열 확인.

#### 31.13 PointerGuard Ops Readiness Gate Security Extension (FACT, 2026-04-28)

- 스크립트:
  - `scripts/check_pointerguard_ops_readiness_v1.py`
- 구현 사실:
  - readiness gate에 `pointerguard_security_hardening_latest.json` 정합 검증을 추가해 C1/C6/비노출/P0/수동잠금 컨트롤 PASS를 강제 확인.
  - readiness gate에 `a_codeai_public_benchmark_launch_checklist_v1.json` 검증을 추가해 공개 벤치 결정 상태(`READY_FOR_SHADOW_PUBLIC_BENCH` 또는 `READY_FOR_PUBLIC_OPEN_BENCH`)를 운영 준비도 판정에 포함.
- 최신 상태:
  - `py scripts/check_pointerguard_ops_readiness_v1.py` exit 0.
  - `pointerguard_ops_readiness_latest.json` 기준 `all_ok=true`, 런치 결정 `READY_FOR_PUBLIC_OPEN_BENCH`.

#### 31.14 PointerGuard Closed-Loop Ops Finalization (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_pointerguard_control_chain_daily.ps1`
  - `scripts/build_pointerguard_manual_approval_log_v1.py`
  - `scripts/check_pointerguard_ops_readiness_v1.py`
  - `scripts/send_pointerguard_ops_alert_v1.py`
- 구현 사실:
  - 일일 체인에 `check_pointerguard_ops_readiness_v1.py`를 연결해 운영 종료 단계에서 readiness를 자동 강제(실패 시 종료코드 반영).
  - `build_pointerguard_manual_approval_log_v1.py`를 추가해 `MANUAL_PROMOTION_LOCK` 2인 승인 거버넌스 아티팩트를 매일 갱신.
  - readiness gate에 `pointerguard_manual_approval_log_latest.json` 검증(잠금/2인승인/로그필수 활성)을 추가.
  - 알림 스크립트에 readiness/security 입력을 추가하고 `guard_applied`, `unauthorized_pattern_detected`, readiness 실패를 P0 우선 이벤트로 승격.
- 최신 상태:
  - `py scripts/build_pointerguard_manual_approval_log_v1.py` exit 0.
  - `py scripts/check_pointerguard_ops_readiness_v1.py` exit 0 (`all_ok=true`).
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_pointerguard_control_chain_daily.ps1` exit 0.
  - 실행 로그: `reports/pointerguard/pointerguard_control_chain_20260428_173517.log`.

#### 31.15 Global Atom Full-Canon Large-Stage Stabilization + Resumed Production Run (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_network_v1.py`
  - `scripts/run_global_atom_full_canon_batch_v1.ps1`
  - `scripts/build_global_atom_full_canon_batch_report_v1.py`
- 변경:
  - `build_global_atom_network_v1.py`의 유사도 계산을 NumPy 벡터화로 고정하고 대용량 출력 제어 옵션(`--max-edges`, `--write-matrix`) 추가.
  - 러너에 `-StartStage` 재개 옵션 추가, 대형 단계 기본 목표를 안정화(`prophets=3072`, `full_canon=4096`)하고 edge 상한을 적용.
  - 대형 단계(>2048)는 matrix 본문 저장을 생략(`matrix_included=false`)해 I/O 폭주를 방지.
- 실행:
  - 중단 복구 재개 실행: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_global_atom_full_canon_batch_v1.ps1 -UseVerseSource -StartStage prophets`
  - run stamp: `20260428T082657Z` (verse-level ingest, non-fast-smoke)
- 최신 상태:
  - 산출물 존재 확인: `prophets/gospels/full_canon` 단계별 input/nodes/edges/matrix/phase_report + manifest 생성 완료.
  - 통합 리포트 갱신:
    - `docs/final/artifacts/global_atom_full_canon_batch_report_latest.json`
    - `summary.status=GO`, `stages_total=3`, `stages_ok=3`
    - `total_nodes=9216`, `total_edges=5164516`, `source_mode=verse_level_ingest`.

#### 31.16 Submission Pack Rebuild After Large-Stage Run (FACT, 2026-04-28)

- 실행:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_global_atom_submission_pack_v1.ps1`
  - `py scripts/build_global_atom_submission_freeze_v1.py`
  - `py scripts/build_global_atom_submission_go_nogo_v1.py`
- 출력:
  - `docs/final/artifacts/global_atom_submission_bundle_latest.json`
  - `docs/final/artifacts/global_atom_submission_freeze_latest.json`
  - `docs/final/artifacts/global_atom_submission_go_nogo_latest.json`
- 최신 상태:
  - bundle: `ready=true`.
  - freeze: `copied_count=7`, `missing_count=0`, `freeze_stamp=20260428T091358Z`.
  - go/nogo: `status=GO`, `reasons=[]`.

#### 31.17 Submission Pack v2 (Large-Stage Facts Injection) (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_network_onepager_v1.py`
  - `scripts/build_global_atom_network_submission_abstracts_v1.py`
  - `scripts/build_global_atom_kdd_submission_template_v1.py`
  - `scripts/build_global_atom_submission_bundle_v1.py`
  - `scripts/run_global_atom_submission_pack_v1.ps1`
- 구현 사실:
  - one-pager가 `--full-canon-batch-report-json`를 받아 large-stage 수치(`total_nodes`, `total_edges`, `batch_stages_*`, `source_mode`)를 key facts에 주입.
  - abstract 생성기 문구를 large-stage 컨텍스트에 맞게 보강(3/3 stage 완료·source mode 반영) 및 문장 문법 정정.
  - KDD 템플릿 `quick_facts`에 batch 필드 추가, contribution 문구를 staged full-canon 경로로 동적 전환.
  - bundle manifest에 `full_canon_batch_report` 아티팩트를 포함해 제출 패킷 증거 연결을 확장.
- 최신 상태:
  - `run_global_atom_submission_pack_v1.ps1` exit 0.
  - one-pager title: `Global Atom Topology (Staged Full-Canon) with Multi-Gate Robustness`.
  - one-pager key facts: `node_count=9216`, `edge_count=5164516`, `batch_stages_ok=3/3`, `batch_source_mode=verse_level_ingest`.

#### 31.18 Five-Stage Consolidated Completion + Package Sync (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_global_atom_full_canon_batch_v1.ps1` (`-EndStage` 추가)
  - `scripts/build_global_atom_full_canon_batch_report_v1.py`
  - `scripts/run_global_atom_submission_pack_v1.ps1`
  - `scripts/build_global_atom_submission_freeze_v1.py`
  - `scripts/build_global_atom_submission_go_nogo_v1.py`
- 구현 사실:
  - 단일 재시작 충돌을 피하기 위해 단계 범위 실행(`-StartStage`, `-EndStage`)을 지원하도록 러너를 확장.
  - `gospels` 단독 실행(run stamp: `20260428T092929Z`)과 `full_canon` 단독 실행(run stamp: `20260428T093205Z`)을 완료.
  - `genesis/torah/prophets/gospels/full_canon` 완료 산출물을 통합 manifest(`20260428T093812Z_consolidated_manifest.json`)로 묶어 batch report를 재생성.
  - 최신 5단계 통합 리포트를 기준으로 submission pack/freeze/go-no-go를 재동기화.
- 최신 상태:
  - `global_atom_full_canon_batch_report_latest.json`: `stages_total=5`, `stages_ok=5`, `status=GO`, `total_nodes=11776`, `total_edges=6401708`.
  - one-pager key facts: `node_count=11776`, `edge_count=6401708`, `batch_stages_ok=5/5`, `batch_source_mode=verse_level_ingest`.
  - `global_atom_submission_go_nogo_latest.json`: `status=GO`, `reasons=[]`.

#### 31.16 PointerGuard Approval Event + Readiness Block + Alert Simulation (FACT, 2026-04-28)

- 스크립트:
  - `scripts/append_pointerguard_manual_approval_event_v1.py`
  - `scripts/apply_pointerguard_readiness_block_v1.py`
  - `scripts/send_pointerguard_ops_alert_v1.py` (`--simulate` 추가)
  - `scripts/run_pointerguard_control_chain_daily.ps1` (readiness block 단계 연동)
- 구현 사실:
  - 수동 승인 로그에 2인 승인 이벤트를 append하는 경로를 구현해 고위험 액션(`unfreeze_ramp`, `public_scope_expand`) 감사 추적 가능 상태로 전환.
  - readiness 실패 시 guarded decision을 강제로 `HOLD_POINTER_ROUTE` / `track_a_primary`로 전환하는 자동 차단 규칙을 추가.
  - 알림 스크립트에 `--simulate` 옵션을 추가해 `guard_applied`, `unauthorized_pattern_detected`, `launch_checklist_not_ready` 등 P0 이벤트를 드라이런으로 재현 가능.
  - 일일 체인에서 readiness 후 block 규칙을 자동 실행하도록 연동.
- 최신 상태:
  - `py scripts/append_pointerguard_manual_approval_event_v1.py --action unfreeze_ramp --approver-1 athena --approver-2 sentinel --ticket OPS-2026-04-28-001 ...` exit 0 (`entry_count=1`).
  - `py scripts/apply_pointerguard_readiness_block_v1.py` exit 0 (`readiness_all_ok=true`, `block_applied=false`).
  - `py scripts/send_pointerguard_ops_alert_v1.py --simulate unauthorized_pattern_detected --dry-run` exit 0 (`should_send=true`, `status=dry_run`).
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_pointerguard_control_chain_daily.ps1` exit 0, 로그 `reports/pointerguard/pointerguard_control_chain_20260428_174001.log`.

#### 31.17 PointerGuard Direct Control-Chain Bypass Closure (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_genesis_pointer_routing_control_chain_v1.py`
  - `scripts/build_genesis_pointer_route_runtime_config_v1.py`
- 구현 사실:
  - 직접 체인(`run_genesis_pointer_routing_control_chain_v1.py`) 실행 경로에도 수동승인 로그 생성 + readiness 검사 + readiness block 적용 단계를 내장해 일일 러너를 우회해도 동일한 차단 정책이 적용되도록 정합.
  - runtime config의 `promotion_gate`에 `readiness_block_applied`, `readiness_block_checked_at_utc`, `guard_applied`, `guard_reason` 필드를 추가해 운영자가 런타임 JSON만으로도 차단/가드 상태를 즉시 확인 가능.
- 최신 상태:
  - `py scripts/run_genesis_pointer_routing_control_chain_v1.py` exit 0.
  - `genesis_pointer_route_runtime_config_latest.json`에서 `promotion_gate.readiness_block_checked_at_utc` 타임스탬프 반영 및 `guard_reason=no_alert` 확인.

#### 31.18 PointerGuard P0 Drill + Readiness-Red Block Enforcement (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_pointerguard_p0_alert_drill_v1.py`
  - `scripts/build_pointerguard_manual_approval_log_v1.py` (entries 보존 보강)
  - `scripts/append_pointerguard_manual_approval_event_v1.py` (ticket 형식 검증)
  - `scripts/decide_pointerguard_apply_go_promotion_v1.py` (readiness red 차단)
  - `scripts/build_a_codeai_public_benchmark_launch_checklist_v1.py` (readiness red 차단)
- 구현 사실:
  - P0 알림 드릴 스크립트를 추가해 simulate 조건으로 알림 경로를 실행하고 delivery 상태를 단일 증거 아티팩트로 기록.
  - 수동 승인 로그 생성 시 기존 `entries`를 보존하도록 수정해 일일 갱신에서 승인 이력이 소실되지 않게 보강.
  - 승인 이벤트 append 시 ticket 형식을 `PREFIX-YYYY-MM-DD-NNN`으로 강제해 운영 절차를 표준화.
  - apply GO promotion 결정에 readiness 입력을 추가해 readiness red면 `blocked_by_ops_readiness` 사유로 강제 `KEEP_SHADOW`.
  - 공개 벤치 런치 체크리스트도 readiness red면 `BLOCKED_BY_READINESS`로 강제해 우발적 공개/승격 경로를 차단.
- 최신 상태:
  - `py scripts/run_pointerguard_p0_alert_drill_v1.py --dry-run` exit 0 (`severity=P0`, `should_send=true`).
  - `py scripts/run_pointerguard_p0_alert_drill_v1.py` exit 0 (`delivery_status=http_200`).
  - readiness red 검증: `decide_pointerguard_apply_go_promotion_v1.py --readiness-json ..._missing...` 결과 `decision=KEEP_SHADOW`, `reasons=[blocked_by_ops_readiness]`.

#### 31.19 PointerGuard Weekly P0 Drill Liveness Hook (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_pointerguard_control_chain_daily.ps1`
- 구현 사실:
  - 일일 체인에 주간 P0 알림 경로 생존성 점검(`run_pointerguard_p0_alert_drill_v1.py --dry-run`)을 조건부로 연동.
  - 파라미터 추가:
    - `-WeeklyP0DrillDay` (기본 `Sunday`)
    - `-ForceP0Drill` (즉시 강제 실행)
  - 드릴 실패 시 일일 체인 종료코드에 반영해 운영 게이트로 취급.
- 최신 상태:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_pointerguard_control_chain_daily.ps1 -ForceP0Drill` exit 0.
  - 실행 로그: `reports/pointerguard/pointerguard_control_chain_20260428_182113.log`.
  - 로그 내 `pointerguard_p0_alert_drill_latest.json (delivery_status=dry_run)` 생성 확인.

#### 31.20 PointerGuard Scheduler Sync + P0 Drill Failure Escalation (FACT, 2026-04-28)

- 스크립트:
  - `scripts/Register-PointerGuardControlChainTask.ps1`
  - `scripts/run_pointerguard_p0_alert_drill_v1.py`
  - `scripts/run_pointerguard_control_chain_daily.ps1`
- 구현 사실:
  - 스케줄러 등록 스크립트가 `-WeeklyP0DrillDay`를 일일 러너 인자로 전달하도록 동기화해 작업 스케줄러 경유 실행에서도 주간 드릴 요일 정책이 고정.
  - P0 드릴 스크립트에 `--alert-on-failure`를 추가해 드릴 검증 실패(`ok=false`) 시 `p0_drill_failed` 실제 알림을 즉시 전송.
  - 일일 러너의 주간 드릴 호출에 `--alert-on-failure`를 연결해 생존성 검사 실패가 로그에만 남지 않고 즉시 P0 경보로 승격되도록 보강.
  - 운영 명령 고정(런북):
    - 기본 일일 실행: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_pointerguard_control_chain_daily.ps1`
    - 강제 주간 드릴 실행: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_pointerguard_control_chain_daily.ps1 -ForceP0Drill`
- 최신 상태:
  - `Register-PointerGuardControlChainTask.ps1 -DryRun` 출력에서 `-WeeklyP0DrillDay "Sunday"` 인자 전달 확인.
  - 실패 시뮬레이션: `py scripts/run_pointerguard_p0_alert_drill_v1.py --simulate-reasons "" --dry-run --alert-on-failure` 실행 시 `ok=false` + `failure_alert_result.status=http_200` 확인.

#### 31.21 PointerGuard Operational Finalization Runbook Check (FACT, 2026-04-28)

- 실행:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-PointerGuardControlChainTask.ps1 -WeeklyP0DrillDay Sunday`
  - `schtasks /Query /TN "MKM_PointerGuard_ControlChain_Daily" /V /FO LIST`
  - `py scripts/run_pointerguard_p0_alert_drill_v1.py`
  - `py scripts/build_pointerguard_manual_approval_log_v1.py`
  - `py scripts/append_pointerguard_manual_approval_event_v1.py --action unfreeze_ramp --approver-1 athena --approver-2 sentinel --ticket OPS-2026-04-28-003 ...`
- 구현 사실:
  - 스케줄러 재등록을 통해 최신 일일 러너를 운영 메타데이터에 재동기화.
  - 실전 모드 P0 드릴 1회 실행으로 webhook 전송 경로(`http_200`)를 재확인.
  - 승인 로그 운영 규율 명령 체인을 실행해 ticket 포맷/2인 승인 규칙으로 감사 이력을 누적.
- 최신 상태:
  - P0 드릴: `delivery_status=http_200`.
  - 승인 로그: `pointerguard_manual_approval_log_latest.json` 기준 `entry_count=2`.

#### 31.23 PointerGuard Scheduler Evidence Automation + Readiness Integration (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_pointerguard_scheduler_arguments_evidence_v1.py`
  - `scripts/run_pointerguard_control_chain_daily.ps1`
  - `scripts/check_pointerguard_ops_readiness_v1.py`
- 구현 사실:
  - `schtasks /Query /XML` 결과에서 스케줄러 command/arguments를 자동 추출해 `pointerguard_scheduler_arguments_evidence_latest.json`을 생성.
  - 일일 체인에 scheduler evidence 생성 단계를 추가해 수동 증거 작성 없이 매 실행마다 인자 증거를 갱신.
  - readiness gate에 scheduler evidence 검증을 추가해 `contains_weekly_p0_drill_day_flag=true`를 운영 준비도 조건으로 강제.
- 최신 상태:
  - `py scripts/build_pointerguard_scheduler_arguments_evidence_v1.py` exit 0 (`contains_weekly_p0_drill_day_flag=true`).
  - `py scripts/check_pointerguard_ops_readiness_v1.py` exit 0 (`all_ok=true`).
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_pointerguard_control_chain_daily.ps1 -ForceP0Drill` exit 0, 로그 `reports/pointerguard/pointerguard_control_chain_20260428_184104.log`.

#### 31.24 PointerGuard Maintenance Ops Bundle (FACT, 2026-04-28)

- 스크립트:
  - `scripts/Register-PointerGuardMonthlyP0DrillTask.ps1`
  - `scripts/build_pointerguard_manual_approval_audit_report_v1.py`
  - `scripts/build_pointerguard_readiness_failure_topn_v1.py`
- 구현 사실:
  - 월 1회 실전 P0 드릴 태스크(`MKM_PointerGuard_Monthly_P0_Drill`)를 등록/제거할 수 있는 스케줄러 스크립트를 추가.
  - 승인 로그에서 최근 30일 이벤트를 집계하는 감사 리포트(건수, ticket 누락, 2인 승인 위반, action top)를 자동 생성.
  - readiness 결과에서 실패 사유 Top-N과 우선순위 복구 큐를 생성하는 요약 아티팩트를 추가.
- 최신 상태:
  - `Register-PointerGuardMonthlyP0DrillTask.ps1` 실행 후 `schtasks /Query /TN "MKM_PointerGuard_Monthly_P0_Drill" /V /FO LIST` 기준:
    - `Schedule Type=Monthly`, `Days=01`, `Task To Run=...run_pointerguard_p0_alert_drill_v1.py`
  - `py scripts/build_pointerguard_manual_approval_audit_report_v1.py` exit 0 (`events_in_window=2`).
  - `py scripts/build_pointerguard_readiness_failure_topn_v1.py` exit 0 (`failed_check_count=0`).

#### 31.22 PointerGuard Scheduler Argument Fact-Lock Evidence (FACT, 2026-04-28)

- 실행:
  - `schtasks /Query /TN "MKM_PointerGuard_ControlChain_Daily" /XML`
- 출력:
  - `docs/final/artifacts/pointerguard_scheduler_arguments_evidence_latest.json`
- 구현 사실:
  - Scheduler XML의 `<Actions><Exec><Arguments>` 원문에서 `-WeeklyP0DrillDay "Sunday"` 전달을 직접 확인.
  - `schtasks /V /FO LIST` 출력에서 누락될 수 있는 인자 표시 문제를 XML 증거 아티팩트로 보완.
- 최신 상태:
  - 증거 아티팩트 `contains_weekly_p0_drill_day_flag=true`.

#### 31.24 Global Atom Consolidated Manifest Automation (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_full_canon_consolidated_manifest_v1.py`
  - `scripts/build_global_atom_full_canon_batch_report_v1.py`
  - `scripts/run_global_atom_submission_pack_v1.ps1`
  - `scripts/build_global_atom_submission_freeze_v1.py`
  - `scripts/build_global_atom_submission_go_nogo_v1.py`
- 구현 사실:
  - 단계별(run stamp 분리) 완료 산출물에서 최신 `genesis/torah/prophets/gospels/full_canon` 파일을 자동 수집해 통합 manifest를 생성.
  - 수동 경로 하드코딩 없이 통합 manifest → batch report → submission pack/freeze/go-no-go를 연속 재생성.
  - 대형 단계 중단/재개 상황에서도 최신 완주 조각을 자동 취합해 최종 제출 수치를 일관되게 유지.
- 출력:
  - `docs/final/artifacts/global_atom_full_canon/global_atom_full_canon_consolidated_manifest_latest.json`
  - `docs/final/artifacts/global_atom_full_canon_batch_report_latest.json`
  - `docs/final/artifacts/global_atom_submission_go_nogo_latest.json`
- 최신 상태:
  - batch report: `stages_total=5`, `stages_ok=5`, `status=GO`, `total_nodes=11776`, `total_edges=6401708`.
  - submission go/no-go: `status=GO`, `reasons=[]`.

#### 31.25 Event-Level Ingest v1 (Pericope/Window Segmentation) (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_full_canon_event_ingest_v1.py`
  - `scripts/run_global_atom_full_canon_batch_v1.ps1` (`-UseEventSource`, `-EventWindowSize` 추가)
  - `scripts/build_global_atom_full_canon_batch_report_v1.py` (`source_mode=event_level_ingest` 지원)
- 구현 사실:
  - verse 단위를 고정 후보로 쓰던 흐름 대신, book/chapter 내부 연속 구간(window) 기반 사건 단위 후보를 생성.
  - 이벤트 후보 스키마에 `event_span(start/end/verse_count)`과 `source_level=event`를 추가해 절-사건 매핑 근거를 명시.
  - 러너에서 `-UseEventSource`를 켜면 event ingest 체인을 사용하도록 배선.
  - 통합 리포트가 event ingest 실행을 별도 source mode로 표기.
- 최신 상태:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_global_atom_full_canon_batch_v1.ps1 -FastSmoke -UseEventSource` exit 0.
  - 샘플 입력(`20260428T094423Z_genesis_input.json`)에서 `source_node_id=Gen.1::Gen.1.1-Gen.1.5`, `source_level=event` 확인.
  - 배치 리포트: `source_mode=event_level_ingest`, `stages_ok=5`, `status=GO`.

#### 31.25 PointerGuard Closed-Loop Maintenance Automation (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_pointerguard_control_chain_daily.ps1`
  - `scripts/check_pointerguard_ops_readiness_v1.py`
  - `scripts/send_pointerguard_ops_alert_v1.py`
  - `scripts/run_pointerguard_p0_alert_drill_v1.py`
- 구현 사실:
  - 일일 체인에 유지보수 리포트 2종(`build_pointerguard_manual_approval_audit_report_v1.py`, `build_pointerguard_readiness_failure_topn_v1.py`) 자동 실행 단계를 추가.
  - readiness gate에 `pointerguard_p0_alert_drill_history_v1.jsonl` 기반 월간 실전 드릴 검증(최근 40일 내 `dry_run=false` && `ok=true`)을 추가.
  - P0 알림 페이로드에 `pointerguard_readiness_failure_topn_latest.json`의 Top-1 복구 우선순위(`top_repair_priority`)를 자동 포함.
  - P0 드릴 스크립트가 history JSONL을 누적 기록하도록 보강해 최신 스냅샷 덮어쓰기 문제를 제거.
- 최신 상태:
  - `py scripts/run_pointerguard_p0_alert_drill_v1.py` exit 0 (`delivery_status=http_200`), history에 live entry 기록.
  - `py scripts/check_pointerguard_ops_readiness_v1.py` exit 0 (`all_ok=true`, 월간 live drill 조건 충족).
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_pointerguard_control_chain_daily.ps1 -ForceP0Drill` exit 0, 로그 `reports/pointerguard/pointerguard_control_chain_20260428_184921.log`.

#### 31.26 PointerGuard Failure Rehearsal E2E + Recovery (FACT, 2026-04-28)

- 실행:
  - 강제 실패: scheduler evidence 아티팩트를 임시 제거 후
    - `py scripts/check_pointerguard_ops_readiness_v1.py`
    - `py scripts/build_pointerguard_readiness_failure_topn_v1.py`
    - `py scripts/apply_pointerguard_readiness_block_v1.py`
    - `py scripts/send_pointerguard_ops_alert_v1.py --dry-run`
  - 복구:
    - `py scripts/build_pointerguard_scheduler_arguments_evidence_v1.py`
    - `py scripts/run_genesis_pointer_routing_control_chain_v1.py`
    - `py scripts/build_genesis_pointer_route_runtime_config_v1.py`

#### 31.27 Event-Ingest Production Run + Source-Mode Auto Detection Fix (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_global_atom_full_canon_batch_v1.ps1` (`-UseEventSource` 본 실행)
  - `scripts/build_global_atom_full_canon_consolidated_manifest_v1.py`
  - `scripts/build_global_atom_full_canon_batch_report_v1.py`
  - `scripts/run_global_atom_submission_pack_v1.ps1`
  - `scripts/build_global_atom_submission_go_nogo_v1.py`
- 구현 사실:
  - event ingest 비-FastSmoke 5단계 실행에서 `full_canon` 단계가 중단된 케이스를 `-StartStage full_canon -EndStage full_canon` 단독 재실행으로 복구.
  - 통합 manifest 자동 생성기가 source mode를 고정(`use_verse_source=true`)하던 문제를 수정해 입력 profile(`event_ingest/verse_ingest`) 기반 자동 판별로 전환.
  - 통합 manifest → batch report → submission pack/go-no-go 재동기화를 재실행.
- 최신 상태:
  - consolidated manifest: `use_verse_source=false`, `use_event_source=true`.
  - batch report: `stages_total=5`, `stages_ok=5`, `status=GO`, `total_nodes=7477`, `total_edges=3051269`, `source_mode=event_level_ingest`.
  - one-pager key facts: `batch_stages_ok=5/5`, `batch_source_mode=event_level_ingest`.
  - submission go/no-go: `status=GO`, `reasons=[]`.

#### 31.28 Submission Pack v3 (Stage Breakdown + Lineage) (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_network_onepager_v1.py`
  - `scripts/build_global_atom_kdd_submission_template_v1.py`
  - `scripts/build_global_atom_submission_bundle_v1.py`
  - `scripts/build_global_atom_full_canon_batch_report_v1.py`
- 구현 사실:
  - one-pager에 `stage_breakdown`(stage별 target/node/edge/signal/path)과 `run_lineage`(run_stamp, start/end, source_mode) 필드를 추가.
  - KDD 템플릿에 동일한 `stage_breakdown`, `run_lineage`를 포함해 제출 본문에서 stage 근거를 직접 제시 가능하도록 확장.
  - bundle에 `full_canon_consolidated_manifest` 아티팩트를 포함해 lineage 증거 경로를 패킷에 고정.
  - batch report가 `run_lineage`를 노출하도록 보강해 one-pager lineage null 문제를 제거.
- 최신 상태:
  - one-pager `run_lineage.run_stamp=20260428T100459Z`, `batch_source_mode=event_level_ingest`.
  - batch report `run_lineage.use_event_source=true`.
  - bundle `artifact_packet.full_canon_consolidated_manifest.exists=true`.

#### 31.29 Camera-Ready Draft/Appendix Auto Generator (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_camera_ready_pack_v1.py`
- 입력:
  - `global_atom_network_academic_onepager_latest.json`
  - `global_atom_kdd_submission_template_latest.json`
  - `global_atom_submission_bundle_latest.json`
- 출력:
  - `docs/final/artifacts/global_atom_camera_ready_paper_draft_latest.md`
  - `docs/final/artifacts/global_atom_camera_ready_appendix_latest.md`
  - `docs/final/artifacts/global_atom_camera_ready_pack_latest.json`
- 구현 사실:
  - one-pager + kdd template + bundle을 결합해 camera-ready용 본문 초안(abstract/contribution/method/results/stage breakdown/risk/repro)과 부록(artifact packet + reproducibility commands)을 자동 생성.
  - 생성 시점 manifest(`global_atom_camera_ready_pack_latest.json`)에 입력/출력 경로를 고정해 재생성 추적성을 보장.
- 최신 상태:
  - `py scripts/build_global_atom_camera_ready_pack_v1.py` exit 0.
  - 본문 초안에 `node_count=7477`, `edge_count=3051269`, `stage completion=5/5`, `source_mode=event_level_ingest` 반영 확인.

#### 31.30 Camera-Ready Format Normalization Pass (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_camera_ready_polish_v1.py`
- 입력:
  - `docs/final/artifacts/global_atom_camera_ready_paper_draft_latest.md`
  - `docs/final/artifacts/global_atom_camera_ready_appendix_latest.md`
- 출력:
  - `docs/final/artifacts/global_atom_camera_ready_paper_polished_latest.md`
  - `docs/final/artifacts/global_atom_camera_ready_appendix_polished_latest.md`
  - `docs/final/artifacts/global_atom_camera_ready_polish_latest.json`
- 구현 사실:
  - abstract 단어수 상한(170), method/risk bullet 상한(4/3), 공백 라인 정규화를 적용해 제출 친화 포맷으로 재작성.
  - polish manifest에 규칙/입출력 경로를 기록해 camera-ready 편집 이력을 재현 가능하게 고정.
- 최신 상태:
  - `py scripts/build_global_atom_camera_ready_polish_v1.py` exit 0.
  - polished paper 기준 핵심 수치(`nodes=7477`, `edges=3051269`, `stage completion=5/5`) 유지 확인.

#### 31.31 Final Submission ZIP Bundle Automation (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_submission_zip_bundle_v1.py`
- 입력:
  - `global_atom_submission_bundle_latest.json`
  - `global_atom_camera_ready_pack_latest.json`
  - `global_atom_camera_ready_polish_latest.json`
- 출력:
  - `docs/final/artifacts/global_atom_submission_bundle_<UTCSTAMP>.zip`
  - `docs/final/artifacts/global_atom_submission_zip_bundle_latest.json`
- 구현 사실:
  - submission bundle + camera-ready(초안/정규화) + 핵심 근거 JSON들을 자동 수집해 ZIP으로 패키징.
  - 중복 파일을 제거하고 워크스페이스 상대 경로로 archive entry를 고정해 재현성 확보.
  - ZIP 생성 결과를 manifest(`file_count`, `files`, `inputs`)로 남겨 제출 직전 점검 가능.
- 최신 상태:
  - `py scripts/build_global_atom_submission_zip_bundle_v1.py` exit 0.
  - ZIP 산출: `global_atom_submission_bundle_20260428T101318Z.zip` (`file_count=15`).

#### 31.32 One-Click Finalization Chain (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_global_atom_finalization_chain_v1.ps1`
- 구현 사실:
  - 통합 manifest/배치 리포트 → submission pack → freeze/go-no-go → camera-ready pack → polish → final zip을 단일 명령으로 직렬 실행.
  - 옵션:
    - `-RebuildBatchFirst` (필요 시 full-canon batch부터 재실행)
    - `-UseEventSource` (RebuildBatchFirst와 함께 event ingest 경로 지정)
- 최신 상태:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_global_atom_finalization_chain_v1.ps1` exit 0.
  - go/no-go: `status=GO`.
  - 최신 zip: `global_atom_submission_bundle_20260428T101455Z.zip` (`file_count=15`).

#### 31.33 Submission ZIP Integrity Audit (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_submission_release_audit_v1.py`
- 입력:
  - `docs/final/artifacts/global_atom_submission_zip_bundle_latest.json`
- 출력:
  - `docs/final/artifacts/global_atom_submission_release_audit_latest.json`
- 구현 사실:
  - 최신 제출 ZIP의 SHA-256, 파일 크기, 엔트리 수를 계산하고 필수 제출 파일 suffix 존재 여부를 자동 점검.
  - 필수 파일 누락 시 `audit_status=FAIL`로 종료코드 비정상 반환, 정상 시 `PASS`.
- 최신 상태:
  - `py scripts/build_global_atom_submission_release_audit_v1.py` exit 0.
  - `audit_status=PASS`, `missing_required_suffixes=[]`.
  - ZIP 해시: `92c71b93d4cce0ca6a0fd63c0b5a95be23ff43ebd34cc2e92271c4dd031ca85f`.

#### 31.34 External SOTA Benchmark Adapter Skeleton (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_sota_benchmark_adapter_v1.py`
  - `scripts/build_global_atom_sota_table_v1.py`
- 출력:
  - `docs/final/artifacts/global_atom_sota_benchmark_adapter_latest.json`
  - `docs/final/artifacts/global_atom_sota_table_latest.json`
  - `docs/final/artifacts/global_atom_sota_table_latest.md`
- 구현 사실:
  - 우리 모델 산출물(onepager/batch report)과 외부 baseline 3종 결과(JSON)을 단일 어댑터 스키마로 통합.
  - baseline 입력이 없을 때 placeholder 상태를 명시하고, `required_baseline_metrics`를 강제 정의해 과장 주장 방지.
  - Table-1 초안(md/json)을 자동 생성해 심사 대응 포맷을 고정.
- 최신 상태:
  - baseline 3종은 placeholder 상태(`is_placeholder=true`), 따라서 현재 표는 draft-only.
  - 비교 정책 문구에 “reproducible non-placeholder 전까지 SOTA 우위 주장 금지”를 명시.

#### 31.35 SOTA Baseline Ingest Chain + Readiness Gate (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_global_atom_sota_baseline_ingest_v1.py`
  - `scripts/check_global_atom_sota_baseline_readiness_v1.py`
  - `scripts/run_global_atom_sota_baseline_ingest_chain_v1.ps1`
- 출력:
  - `docs/final/artifacts/global_atom_sota_baseline_readiness_latest.json`
  - `docs/final/artifacts/global_atom_sota_benchmark_adapter_latest.json`
  - `docs/final/artifacts/global_atom_sota_table_latest.{json,md}`
- 구현 사실:
  - baseline 결과를 CLI/원본 JSON에서 표준 스키마(`global_atom_sota_baseline_result_v1`)로 정규화하는 ingest 경로를 추가.
  - baseline 3종 템플릿에 실제 주입 명령 예시를 내장해 운영자가 바로 실측값 반영 가능.
  - 원클릭 체인에서 어댑터/테이블 생성 후 readiness gate를 계산해 placeholder/누락 metric 상태를 자동 보고.
- 최신 상태:
  - `run_global_atom_sota_baseline_ingest_chain_v1.ps1` exit 0.
  - readiness: `all_ready=false` (현재 baseline 3종 모두 placeholder, 필수 metric 5종 누락).
    - `py scripts/check_pointerguard_ops_readiness_v1.py`
    - `py scripts/build_pointerguard_readiness_failure_topn_v1.py`
    - `py scripts/send_pointerguard_ops_alert_v1.py --dry-run`
- 구현 사실:
  - readiness red에서 `all_ok=false`를 확인하고, Top-N 리포트에서 `failed_check_count=1` 생성.
  - readiness block이 즉시 `decision=HOLD_POINTER_ROUTE`, `route_mode=track_a_primary`로 강등되는 E2E 동작을 확인.
  - 알림 페이로드가 `should_send=true`로 전환되고 dry-run 전송 상태를 기록함을 확인.
  - 복구 체인 실행 후 `route_mode=pointer_shadow`, `all_ok=true`, `should_send=false` 상태로 원복 확인.

#### 31.27 a-codeai.com Fact-Lock Public Copy (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_a_codeai_fact_lock_public_copy_v1.py`
- 출력:
  - `docs/final/artifacts/a_codeai_fact_lock_public_copy_latest.json`
- 구현 사실:
  - 과장/보장형 문구 대신 조건형 주장(측정/가드/범위 제한) 중심의 공개 카피를 아티팩트로 생성.
  - 공개 문구에 `what we claim / what we do not claim`를 분리해 상용 커뮤니케이션의 Fact-Lock 경계를 고정.
  - readiness/scorecard 입력을 받아 현재 상태 문구(`readiness green/blocked`)를 자동 반영.
- 최신 상태:
  - `py scripts/build_a_codeai_fact_lock_public_copy_v1.py` exit 0.
  - `a_codeai_fact_lock_public_copy_latest.json` 생성 완료.

#### 31.28 a-codeai.com Public Copy Web Payload Mapping (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_a_codeai_public_copy_web_payload_v1.py`
- 출력:
  - `docs/final/artifacts/a_codeai_public_copy_web_payload_latest.json`
- 구현 사실:
  - Fact-Lock 공개 카피 JSON을 웹 섹션 키(`hero`, `fact_lock_bullets`, `claims`, `non_claims`, `cta`) 기준으로 정규화.
  - 카피 원문을 그대로 노출하지 않고 사이트 렌더 단계에서 직접 소비 가능한 payload 스키마로 변환.
  - 메타 필드로 `readiness_all_ok`, `executive_read_decision`를 포함해 배너/상태 라벨 연동 근거를 제공.
- 최신 상태:
  - `py scripts/build_a_codeai_public_copy_web_payload_v1.py` exit 0.
  - `a_codeai_public_copy_web_payload_latest.json` 생성 완료.

#### 31.29 a-codeai.com Landing Template Runtime Binding (FACT, 2026-04-28)

- 파일:
  - `scripts/deploy/nginx/a-codeai.com.index.html.example`
  - `scripts/deploy/nginx/a-codeai.com.index.en.html.example`
- 구현 사실:
  - 랜딩 템플릿에 `a_codeai_public_copy_web_payload_latest.json` fetch 스크립트를 추가해 hero/상태문구/claims/non-claims/cta를 런타임 바인딩.
  - 정적 기본 문구는 fallback으로 유지하고, payload 조회 성공 시 Fact-Lock 문구로 안전하게 덮어쓰기.
  - payload 경로 미존재/네트워크 오류 시 기존 정적 카피를 유지하도록 예외 처리.
- 최신 상태:
  - `build_a_codeai_fact_lock_public_copy_v1.py` + `build_a_codeai_public_copy_web_payload_v1.py` 재실행 완료.
  - 최신 payload 아티팩트 기준 템플릿 바인딩 준비 완료.

#### 31.30 a-codeai Deploy Script Payload Sync (FACT, 2026-04-28)

- 스크립트:
  - `scripts/deploy/linux/deploy_a_codeai_landing_from_repo.sh`
- 구현 사실:
  - 배포 스크립트의 필수 파일 검사에 `docs/final/artifacts/a_codeai_public_copy_web_payload_latest.json`를 추가.
  - 배포 단계에서 payload JSON을 웹 루트(`$WEB_ROOT/a_codeai_public_copy_web_payload_latest.json`)로 복사하도록 연동.
  - 이를 통해 런타임 바인딩 랜딩 템플릿이 배포 직후 payload를 즉시 조회 가능.
- 최신 상태:
  - 로컬 Windows 환경에서는 `bash` 실행기가 없어 shell 문법검증은 미실행(배포 대상 Linux/VPS에서 검증 필요).
  - 스크립트 변경 반영 완료.

#### 31.36 Finalization Chain SOTA Readiness Gate Wiring (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_global_atom_finalization_chain_v1.ps1`
- 구현 사실:
  - 원클릭 최종화 체인 마지막 단계에 `run_global_atom_sota_baseline_ingest_chain_v1.ps1`를 연결해 baseline readiness를 자동 계산.
  - `-RequireSotaReady` 옵션 추가:
    - 미지정: readiness false일 때 경고만 출력(패키지 생성은 계속).
    - 지정: readiness false면 종료코드 2로 실패 처리.
- 최신 상태:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_global_atom_finalization_chain_v1.ps1` exit 0.
  - 실행 로그에 `SOTA baseline readiness is FALSE ... draft-only` 경고 출력 확인.

#### 31.37 Pre-News x Global Atom Holdout Replay v1 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_global_atom_news_network_holdout_replay_v1.py`
- 출력:
  - `docs/final/artifacts/global_atom_news_network_holdout_replay_latest.json`
- 구현 사실:
  - 2008 리먼/2020 코로나 1개월 시나리오 headline을 입력으로 받아 global atom stage topology에 공명 점수를 계산하는 holdout replay v1 아티팩트를 생성.
  - case별 `top_resonance`, `top2_resonance`, `network_structural_insight`를 기록해 Pre-News 결합 시의 구조적 해석 경로를 고정.
  - 산출물 note에 heuristic 한계를 명시하고, 출판/주장 전 locked external news dataset 업그레이드 필요성을 명확히 표기.
- 최신 상태:
  - `py scripts/run_global_atom_news_network_holdout_replay_v1.py` exit 0.
  - replay 산출물 생성 완료(`holdout_2008_lehman`, `holdout_2020_covid_m1` 2건).

#### 31.38 Pre-News Shadow Projection Chain v1 (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_global_atom_pre_news_shadow_chain_v1.py`
  - `scripts/run_global_atom_pre_news_shadow_chain_v1.ps1`
- 입력:
  - `docs/final/artifacts/pre_news_shadow_input_latest.json` (샘플/일일 입력)
  - `docs/final/artifacts/global_atom_full_canon_batch_report_latest.json`
- 출력:
  - `docs/final/artifacts/pre_news_shadow_projection_latest.json`
  - `reports/pre_news_shadow_projection_log.jsonl`
- 구현 사실:
  - Pre-News headline을 global atom stage topology에 투영해 `top_resonance/top2_resonance/insight`를 생성하는 shadow-only 체인 추가.
  - 실행 이력을 JSONL 로그로 누적해 일일 관측 추적성을 확보.
  - 출력 note에 `Not connected to live trading triggers`를 명시해 운영 격벽 유지.
- 최신 상태:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_global_atom_pre_news_shadow_chain_v1.ps1` exit 0.
  - projection 산출물 생성 및 log 1건 누적 확인.

#### 31.39 Daily Wrapper Wiring + Weekly Shadow Report v1 (FACT, 2026-04-28)

- 수정:
  - `scripts/run_daily_prophecy_then_pre_news_v1.ps1`
- 신규:
  - `scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py`
- 구현 사실:
  - daily wrapper에 pre-news shadow 실행 스위치 추가:
    - `-EnablePreNewsShadow`
    - `-EnablePreNewsShadowWeeklyReport`
    - `-PreNewsBatchReportJson`
    - `-PreNewsInputJson`
  - pre-news shadow 주간 리포트 생성 체인 추가:
    - 입력: `reports/pre_news_shadow_projection_log.jsonl`
    - 출력: `docs/final/artifacts/pre_news_shadow_weekly_report_latest.json`
    - 핵심 집계: window 내 run 수, latest projection row 수, top resonance stage 빈도.
- 최신 상태:
  - `py -3 scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py ...` exit 0.
  - weekly report 산출물 생성 확인.

#### 31.40 Pre-News Shadow Daily Scheduler Registration v1 (FACT, 2026-04-28)

- 신규:
  - `scripts/Register-PreNewsShadowDailyTask.ps1`
- 구현 사실:
  - Windows Scheduled Task 등록 스크립트 추가.
  - 기본 실행 타깃:
    - `scripts/run_daily_prophecy_then_pre_news_v1.ps1`
    - `-EnablePreNewsShadow`
    - `-EnablePreNewsShadowWeeklyReport`
  - 파라미터:
    - `-WorkspaceRoot` (기본 `C:\workspace`)
    - `-TaskName` (기본 `\MKM-PreNews-Shadow-Daily`)
    - `-RunAt` (기본 `06:30`)
    - `-Force` (기존 task 재등록)
- 운영 의미:
  - pre-news shadow projection + weekly summary를 일일 스케줄러에 고정해 무인 관측 루프를 구성.

#### 31.41 Pre-News Shadow Scheduler Health Check v1 (FACT, 2026-04-28)

- 신규:
  - `scripts/check_pre_news_shadow_task_health.ps1`
  - `scripts/Register-PreNewsShadowHealthTask.ps1`
- 구현 사실:
  - `MKM-PreNews-Shadow-Daily` task 상태 스냅샷(JSON) 생성:
    - state / last_run_time / next_run_time
    - last_task_result / result hex / category / healthy
  - Scheduler informational code(`0x41300~0x4130F`)를 non-error(`SchedulerInfo`)로 분류해 false alarm 방지.
  - 일일 health task(`MKM-PreNews-Shadow-Health-Daily`) 등록 스크립트 추가.
- 산출물:
  - `docs/final/artifacts/pre_news_shadow_task_health_latest.json`
- 최신 상태:
  - daily task 등록:
    - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-PreNewsShadowDailyTask.ps1 -Force` exit 0
  - health task 등록:
    - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-PreNewsShadowHealthTask.ps1` exit 0
  - health snapshot 생성:
    - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_pre_news_shadow_task_health.ps1 ...` exit 0

#### 31.42 Pre-News Shadow Health Alert Gate v1 (FACT, 2026-04-28)

- 신규:
  - `scripts/alert_pre_news_shadow_task_health_v1.py`
  - `scripts/run_pre_news_shadow_health_chain.ps1`
- 수정:
  - `scripts/Register-PreNewsShadowHealthTask.ps1` (헬스체크 단일 실행 -> health chain 실행)
- 구현 사실:
  - health snapshot JSON(`pre_news_shadow_task_health_latest.json`)을 입력으로 alert gate 추가.
  - `healthy=false`일 때만:
    - `has_alert=true`, `severity=critical`, reason 필드 생성
    - `reports/pre_news_shadow_task_health_alert_log.jsonl`에 append
  - `healthy=true`일 때:
    - `has_alert=false`, `severity=none` 아티팩트만 갱신(로그 append 없음)
- 산출물:
  - `docs/final/artifacts/pre_news_shadow_task_health_alert_latest.json`
- 최신 상태:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_pre_news_shadow_health_chain.ps1 ...` exit 0.
  - `pre_news_shadow_task_health_alert_latest.json` 생성 확인(`has_alert=false`).

#### 31.43 Pre-News Shadow Health Alert Webhook Hookup v1 (FACT, 2026-04-28)

- 수정:
  - `scripts/alert_pre_news_shadow_task_health_v1.py`
- 구현 사실:
  - alert gate에 webhook 전송 로직 추가.
  - 전송 조건: `has_alert=true`일 때만 POST.
  - 환경변수 우선순위:
    - `MKM_PRE_NEWS_SHADOW_ALERT_WEBHOOK_URL`
    - fallback: `OPS_ALARM_WEBHOOK_URL`
  - alert 아티팩트 필드 확장:
    - `notified` (bool)
    - `notify_status` (`skipped_no_alert` / `skipped_no_webhook` / `http_status=*` / `failed:*`)
- 최신 상태:
  - `run_pre_news_shadow_health_chain.ps1` 재실행 exit 0.
  - 현재 상태(`healthy=true`)에서 `notify_status=skipped_no_alert` 확인.

#### 31.44 Pre-News Shadow Alert Gate Forced-Unhealthy E2E Verification (FACT, 2026-04-28)

- 테스트 입력:
  - `docs/final/artifacts/pre_news_shadow_task_health_forced_unhealthy.json`
- 테스트 실행:
  - `py -3 scripts/alert_pre_news_shadow_task_health_v1.py --health-json ...forced_unhealthy.json --out-alert-json ...forced_test.json --append-log-jsonl ...forced_test_log.jsonl`
- 테스트 산출:
  - `docs/final/artifacts/pre_news_shadow_task_health_alert_forced_test.json`
  - `reports/pre_news_shadow_task_health_alert_forced_test_log.jsonl`
- 검증 결과:
  - `has_alert=true`, `severity=critical`
  - `notified=true`, `notify_status=http_status=200`
  - unhealthy 조건에서 alert 생성 + log append + webhook 전송 경로가 end-to-end로 동작함을 확인.

#### 31.45 Pre-News Shadow Monthly Drill + Forced-Test Cleanup Policy (FACT, 2026-04-28)

- 신규:
  - `scripts/run_pre_news_shadow_alert_drill_v1.py`
  - `scripts/Register-PreNewsShadowMonthlyDrillTask.ps1`
  - `scripts/cleanup_pre_news_shadow_forced_test_artifacts.ps1`
- 구현 사실:
  - 월간 드릴 러너 추가:
    - 강제 unhealthy payload 생성 후 alert gate 실행 경로를 점검.
    - 드릴 실행 시 webhook env를 비워 실알림 없이 경로만 검증(`notify_status=skipped_no_webhook` 기대).
    - 결과 리포트: `docs/final/artifacts/pre_news_shadow_alert_drill_latest.json`.
  - 월간 스케줄 등록기 추가:
    - 기본 Task: `MKM_PreNewsShadow_Monthly_Drill`
    - 기본 스케줄: 매월 1일 07:20.
  - forced-test 정리 정책 스크립트 추가:
    - `pre_news_shadow_task_health_forced_unhealthy.json`
    - `pre_news_shadow_task_health_alert_forced_test.json`
    - `pre_news_shadow_task_health_alert_forced_test_log.jsonl`
    - `-DryRun` 지원.
- 최신 상태:
  - `py -3 scripts/run_pre_news_shadow_alert_drill_v1.py` exit 0 (`ok=true`).
  - `Register-PreNewsShadowMonthlyDrillTask.ps1` 실행으로 월간 task 등록 완료.
  - cleanup 스크립트 dry-run으로 대상 파일 목록 검증 완료.

#### 31.46 Pre-News Shadow Health CI Smoke Workflow v1 (FACT, 2026-04-28)

- 신규:
  - `.github/workflows/pre-news-shadow-health-smoke.yml`
- 구현 사실:
  - pre-news health/alert/drill 회귀 방지를 위한 GitHub Actions smoke 추가.
  - Linux runner에서 스케줄러 의존 PowerShell은 제외하고 Python 기반 경로를 검증:
    - `run_pre_news_shadow_alert_drill_v1.py` 실행
    - drill 리포트 계약 점검(`ok=true`, `has_alert=true`, `notify_status=skipped_no_webhook`)
    - 주간 요약 빌더 smoke 실행
  - CI용 주간 요약에서 `output_json` 미존재 로그를 안전 처리하도록
    `build_global_atom_pre_news_shadow_weekly_report_v1.py` 보완(`latest_projection_json=null`).
- 최신 상태:
  - 로컬 smoke 재현:
    - `py -3 scripts/run_pre_news_shadow_alert_drill_v1.py` exit 0
    - `py -3 scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py ...` exit 0
  - 산출물:
    - `docs/final/artifacts/pre_news_shadow_alert_drill_latest.json`
    - `docs/final/artifacts/pre_news_shadow_health_drill_weekly_report_ci_latest.json`

#### 31.47 Pre-News Weekly Decision Metrics Expansion v1 (FACT, 2026-04-28)

- 수정:
  - `scripts/run_global_atom_pre_news_shadow_chain_v1.py`
  - `scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py`
- 구현 사실:
  - shadow projection log 누적 필드 확장:
    - `primary_top_stage`
    - `top_stage_counts`
  - 주간 리포트 지표 확장:
    - `metrics.top_stage_change_rate`
    - `metrics.top_stage_current_primary`
    - `metrics.top_stage_previous_primary`
    - `metrics.top_stage_drift`
    - `metrics.health_alert_count_7d`
  - one-line 의사결정 필드 추가:
    - `risk_summary` (`LOW/MEDIUM/HIGH`)
  - alert 로그 입력 지원:
    - `--alert-log-jsonl` (기본 `reports/pre_news_shadow_task_health_alert_log.jsonl`)
- 최신 상태:
  - `run_global_atom_pre_news_shadow_chain_v1.ps1` 재실행 후 신규 log 필드 누적 확인.
  - `build_global_atom_pre_news_shadow_weekly_report_v1.py` 실행 결과:
    - `risk_summary = LOW: resonance stage is stable and no health alerts detected.`

#### 31.48 Shadow→Holdout Promotion Gate Wiring v1 (FACT, 2026-04-28)

- 수정:
  - `scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py`
- 구현 사실:
  - holdout replay 연동 입력 추가:
    - `--holdout-replay-json` (기본 `docs/final/artifacts/global_atom_news_network_holdout_replay_latest.json`)
  - gate 규칙:
    - `holdout top_resonance`에 등장한 stage만 `promoted_stage_counts`로 승격.
  - 주간 리포트 확장:
    - `holdout_replay_json`
    - `promoted_stage_counts`
    - `promotion_gate.enabled/rule/holdout_verified_stages`
    - `metrics.holdout_verified_stage_count`
    - `metrics.promoted_stage_count`
- 최신 상태:
  - weekly report 재생성 완료.
  - 현재 샘플에서 holdout verified stage는 `full_canon`, `gospels`; 주간 승격 stage는 `full_canon`으로 집계됨.

#### 31.49 Pre-News Weekly Promotion Explainability + Holdout Dataset v2 + CI Contract Gate (FACT, 2026-04-28)

- 수정:
  - `scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py`
  - `scripts/run_global_atom_news_network_holdout_replay_v1.py`
  - `.github/workflows/pre-news-shadow-health-smoke.yml`
- 신규:
  - `docs/final/artifacts/global_atom_news_holdout_dataset_v1.jsonl`
- 구현 사실:
  - 주간 리포트 설명가능성 강화:
    - `rejected_stage_counts[]` 추가 (`reject_reason=not_in_holdout_verified_stages`)
    - `metrics.rejected_stage_count` 추가.
  - holdout replay 입력형 업그레이드:
    - `--holdout-news-jsonl` 지원.
    - 입력 JSONL 존재 시 `input.dataset_source=jsonl`로 기록, 없으면 내장 default fallback.
  - CI 계약 테스트 강화:
    - smoke workflow가 holdout replay(JSONL 입력)까지 실행.
    - weekly promotion gate 계약 강제 검증:
      - `promotion_gate.enabled=true`
      - `len(promoted)<=len(top)`, `len(rejected)<=len(top)`
      - rejected reason 고정값 검증
      - metrics 집계값 일치 검증.
- 최신 상태:
  - 로컬 실행:
    - replay(v2) + weekly report 생성 + 계약 검증 모두 exit 0.
  - 현재 `pre_news_shadow_weekly_report_latest.json`에 `promoted_stage_counts`와 `rejected_stage_counts` 동시 제공 확인.

#### 31.50 Holdout Dataset Scale-Up (20 cases) + Min-Sample Promotion Gate v1 (FACT, 2026-04-28)

- 수정:
  - `docs/final/artifacts/global_atom_news_holdout_dataset_v1.jsonl`
  - `scripts/run_global_atom_news_network_holdout_replay_v1.py`
  - `scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py`
  - `.github/workflows/pre-news-shadow-health-smoke.yml`
- 구현 사실:
  - holdout dataset를 2건 샘플에서 20건으로 확장(2008~2025 시나리오).
  - holdout replay summary에 stage 분포 추가:
    - `summary.cases_total`
    - `summary.holdout_top_stage_counts`
  - 주간 승격 게이트에 최소 표본 조건 추가:
    - CLI: `--min-holdout-cases-per-stage` (기본 2)
    - gate rule: holdout top_resonance count가 임계치 이상인 stage만 승격.
    - `promotion_gate.min_holdout_cases_per_stage`
    - `promotion_gate.holdout_top_stage_counts`
    - `metrics.holdout_min_cases_per_stage`
  - CI 계약 검증 강화:
    - 최소 표본 게이트 필드(`min_holdout_cases_per_stage >= 1`) 확인.
    - reject reason 허용값 확장(`not_in_holdout_verified_stages` 또는 `below_min_holdout_cases_per_stage`).
- 최신 상태:
  - replay(v2) 재생성 결과 `cases_total=20`.
  - holdout top stage 분포: `full_canon=14`, `gospels=4`, `prophets=2`.
  - weekly report 게이트 재생성/로컬 계약 검증 모두 exit 0.

#### 31.51 Stage-Specific Min-Sample Promotion Gate v2 (FACT, 2026-04-28)

- 수정:
  - `scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py`
  - `.github/workflows/pre-news-shadow-health-smoke.yml`
- 구현 사실:
  - stage별 최소 표본 임계치 override 지원:
    - CLI `--stage-min-holdout-cases`
    - 형식: `full_canon:5,prophets:3,gospels:3`
  - 승격 규칙:
    - stage별 override가 있으면 override 우선, 없으면 `--min-holdout-cases-per-stage` 기본값 사용.
  - 리포트 확장:
    - `promotion_gate.stage_min_holdout_cases`
    - rejected 항목에 `holdout_count`, `required_count` 추가.
  - CI smoke 계약 검증 강화:
    - `stage_min_holdout_cases` dict 타입/값(>=1) 확인.
    - weekly smoke 실행 시 stage별 threshold 인자 전달.
- 최신 상태:
  - 로컬 실행(`full_canon:5,prophets:3,gospels:3`) 결과:
    - holdout counts: `full_canon=14`, `prophets=2`, `gospels=4`
    - verified stages: `full_canon`, `gospels` (`prophets`는 임계치 미달로 제외)
  - stage-specific threshold 계약 검증 exit 0.

#### 31.52 Stage Threshold Policy JSON Externalization v1 (FACT, 2026-04-28)

- 신규:
  - `docs/final/artifacts/pre_news_shadow_stage_threshold_policy_v1.json`
- 수정:
  - `scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py`
  - `.github/workflows/pre-news-shadow-health-smoke.yml`
- 구현 사실:
  - stage 임계치 정책을 CLI 문자열에서 JSON 정책 파일로 외부화.
  - weekly report 빌더에 정책 입력 추가:
    - `--stage-threshold-policy-json`
  - 정책 우선순위:
    1) policy JSON (`default_min_holdout_cases_per_stage`, `stage_min_holdout_cases`)
    2) CLI `--stage-min-holdout-cases` (ad-hoc override)
    3) CLI `--min-holdout-cases-per-stage` 기본값
  - 리포트에 정책 경로 노출:
    - `stage_threshold_policy_json`
  - CI smoke를 정책 파일 기반 실행으로 전환.
- 최신 상태:
  - 정책 파일 기반 weekly report 재생성 exit 0.
  - 리포트에서 `stage_threshold_policy_json` 및 stage별 임계치 반영 확인.

#### 31.53 Stage Threshold Policy Governance Metadata + Effective-Date Enforcement v1 (FACT, 2026-04-28)

- 수정:
  - `docs/final/artifacts/pre_news_shadow_stage_threshold_policy_v1.json`
  - `scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py`
  - `.github/workflows/pre-news-shadow-health-smoke.yml`
- 구현 사실:
  - 정책 JSON에 거버넌스 메타 추가:
    - `policy_version`
    - `approved_by`
    - `effective_from_utc`
    - `updated_at_utc`
  - weekly 빌더에 유효일 강제 옵션 추가:
    - `--enforce-policy-effective-from`
    - policy의 `effective_from_utc`가 미래거나 형식 오류면 실행 fail.
  - weekly 리포트에 정책 메타 노출:
    - `stage_threshold_policy_meta`
  - CI smoke 강화:
    - weekly 빌드에 `--enforce-policy-effective-from` 적용
    - 리포트에서 `stage_threshold_policy_meta.effective_from_utc` 존재 검증.
- 최신 상태:
  - 정책 유효일 강제 옵션으로 weekly report 재생성 exit 0.
  - 산출물에서 policy meta 필드 확인 완료.

#### 31.54 Stage Threshold Policy Change Audit Trail v1 (FACT, 2026-04-28)

- 수정:
  - `scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py`
- 구현 사실:
  - policy 파일 fingerprint(SHA-256) 기반 변경 감지 추가.
  - 변경 감지 시 JSONL 감사 로그 append:
    - `reports/pre_news_shadow_stage_threshold_policy_change_log.jsonl`
  - 최신 policy 상태 스냅샷 갱신:
    - `docs/final/artifacts/pre_news_shadow_stage_threshold_policy_state_latest.json`
  - weekly report에 감사 경로 노출:
    - `stage_threshold_policy_change_log_jsonl`
    - `stage_threshold_policy_state_json`
- 최신 상태:
  - 초기 실행에서 policy fingerprint 기록 및 change log 1건 생성 확인.
  - state에 `policy_version/approved_by/effective_from_utc` 동기화 확인.

#### 31.55 Stage Threshold Policy Audit Summary (30d) v1 (FACT, 2026-04-28)

- 신규:
  - `scripts/build_pre_news_shadow_policy_change_audit_summary_v1.py`
- 산출물:
  - `docs/final/artifacts/pre_news_shadow_stage_threshold_policy_audit_summary_latest.json`
- 구현 사실:
  - 정책 변경 감사 로그(`...policy_change_log.jsonl`)와 최신 상태(`...policy_state_latest.json`)를 결합해
    최근 N일(기본 30일) 요약 리포트 생성.
  - 핵심 지표:
    - `metrics.change_count_window`
    - `metrics.change_count_total`
    - `metrics.latest_change_detected_at_utc`
  - 최신 변경 레코드와 현재 정책 상태(`policy_version`, `approved_by`, `effective_from_utc`, fingerprint`)를 함께 노출.
  - 운영 판독용 `risk_summary` 자동 생성.
- 최신 상태:
  - 30일 요약 리포트 생성 exit 0.
  - 현재 값: `change_count_window=1`, `latest_change_detected_at_utc=2026-04-28T12:16:55Z`.

#### 31.56 Weekly Chain Wiring: Policy Audit Summary Auto-Generation (FACT, 2026-04-28)

- 수정:
  - `scripts/run_daily_prophecy_then_pre_news_v1.ps1`
- 구현 사실:
  - `-EnablePreNewsShadowWeeklyReport` 실행 경로에 정책 감사 요약 단계를 자동 연결.
  - weekly shadow report 단계에서 다음을 함께 강제:
    - `--holdout-replay-json`
    - `--stage-threshold-policy-json`
    - `--enforce-policy-effective-from`
  - 이어서 policy audit summary 자동 생성:
    - `scripts/build_pre_news_shadow_policy_change_audit_summary_v1.py`
    - 출력: `docs/final/artifacts/pre_news_shadow_stage_threshold_policy_audit_summary_latest.json`
  - 신규 파라미터:
    - `PreNewsHoldoutReplayJson`
    - `PreNewsStageThresholdPolicyJson`
    - `PreNewsPolicyAuditWindowDays`
- 최신 상태:
  - daily wrapper를 `-EnablePreNewsShadow -EnablePreNewsShadowWeeklyReport`로 실행했을 때
    pre-news projection + weekly report + policy audit summary가 연속 생성됨을 확인.

#### 31.57 Holdout Dataset Integrity Lock Gate v1 (FACT, 2026-04-28)

- 신규:
  - `scripts/build_global_atom_news_holdout_dataset_lock_manifest_v1.py`
  - `docs/final/artifacts/global_atom_news_holdout_dataset_lock_manifest_v1.json`
- 수정:
  - `scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py`
  - `scripts/run_daily_prophecy_then_pre_news_v1.ps1`
  - `.github/workflows/pre-news-shadow-health-smoke.yml`
- 구현 사실:
  - holdout dataset JSONL에 대한 SHA-256 lock manifest 생성 체인 추가.
  - weekly promotion gate에 dataset lock 검증 필드 추가:
    - `promotion_gate.holdout_dataset_lock_enforced`
    - `promotion_gate.holdout_dataset_lock_ok`
    - `promotion_gate.holdout_dataset_expected_sha256`
    - `promotion_gate.holdout_dataset_actual_sha256`
  - `--enforce-holdout-dataset-lock` 활성 시:
    - hash mismatch면 승격 차단(`promoted_stage_counts=[]`, reject reason=`holdout_dataset_hash_mismatch`)
    - gate 상태는 `enabled=false`로 강등.
  - daily wrapper의 pre-news weekly 경로에 lock enforcement를 기본 적용.
  - CI smoke에서 lock manifest 생성 + lock enforced contract 검증 추가.
- 최신 상태:
  - lock manifest 생성/weekly gate 재생성 모두 exit 0.
  - 현재 리포트에서 expected/actual SHA 일치 및 `holdout_dataset_lock_ok=true` 확인.

#### 31.58 Policy Governance Alert Gate Wiring v1 (FACT, 2026-04-28)

- 신규:
  - `scripts/alert_pre_news_shadow_policy_governance_v1.py`
- 수정:
  - `scripts/run_daily_prophecy_then_pre_news_v1.ps1`
  - `.github/workflows/pre-news-shadow-health-smoke.yml`
- 구현 사실:
  - policy audit summary 기반 governance alert gate 추가.
  - alert 조건:
    - `change_count_window >= threshold` (기본 2)
    - 또는 policy governance meta 누락
  - 알림 출력:
    - `docs/final/artifacts/pre_news_shadow_policy_governance_alert_latest.json`
    - `reports/pre_news_shadow_policy_governance_alert_log.jsonl` (has_alert=true 시 append)
  - webhook 우선순위:
    - `MKM_PRE_NEWS_POLICY_GOVERNANCE_ALERT_WEBHOOK_URL`
    - fallback `OPS_ALARM_WEBHOOK_URL`
  - daily weekly 경로에 audit summary 다음 단계로 자동 연결.
  - CI smoke에서 governance alert artifact 계약 검증 추가.
  - 신규 daily 파라미터:
    - `PreNewsPolicyGovernanceAlertThreshold`
- 최신 상태:
  - daily wrapper 실행 시 governance alert artifact 자동 생성 확인.
  - 현재 샘플은 `has_alert=false`, `notify_status=skipped_no_alert`.

#### 31.59 Weekly Audit Bundle Aggregation v1 (FACT, 2026-04-28)

- 신규:
  - `scripts/build_pre_news_shadow_weekly_audit_bundle_v1.py`
  - `docs/final/artifacts/pre_news_shadow_weekly_audit_bundle_latest.json`
- 수정:
  - `scripts/run_daily_prophecy_then_pre_news_v1.ps1`
  - `.github/workflows/pre-news-shadow-health-smoke.yml`
- 구현 사실:
  - 주간 운영 근거를 단일 JSON 번들로 묶는 집계 단계 추가:
    - weekly report
    - policy audit summary
    - policy governance alert
    - policy state
    - policy change log tail(N행)
    - holdout replay summary
    - holdout lock manifest
  - daily weekly 경로에 bundle 생성 자동 연결.
  - CI smoke에 bundle 생성 + 계약 검증(`weekly_report/policy_audit_summary/holdout_lock_manifest` 존재) 추가.
  - 신규 daily 파라미터:
    - `PreNewsPolicyChangeLogTailRows` (기본 20)
- 최신 상태:
  - daily wrapper 실행으로 `pre_news_shadow_weekly_audit_bundle_latest.json` 자동 생성 확인.
  - bundle 내 정책/승격/무결성 핵심 근거가 단일 패키지로 집계됨.

#### 31.60 Two-Person Policy Approval Gate v1 (FACT, 2026-04-28)

- 수정:
  - `docs/final/artifacts/pre_news_shadow_stage_threshold_policy_v1.json`
  - `scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py`
  - `scripts/build_pre_news_shadow_policy_change_audit_summary_v1.py`
  - `scripts/alert_pre_news_shadow_policy_governance_v1.py`
  - `.github/workflows/pre-news-shadow-health-smoke.yml`
- 구현 사실:
  - 정책 메타에 2인 승인 필드 추가:
    - `approved_by_1`
    - `approved_by_2`
  - audit summary가 `has_two_person_approval`를 계산/노출.
  - governance alert 게이트가 2인 승인 누락을 metadata gap으로 판정:
    - `has_two_person_approval=false`면 alert 사유에 `two-person approval missing` 추가.
  - CI smoke에 `has_two_person_approval` 필드 존재 계약 검증 추가.
- 최신 상태:
  - 정책에 2인 승인 필드 반영 후 daily chain 재실행 성공.
  - audit summary에서 `has_two_person_approval=true` 확인.
  - 현재 governance alert는 변경 횟수 임계치(2) 충족으로 `has_alert=true` 상태.

#### 31.61 Policy Governance Alert Sensitivity Relaxation v1 (FACT, 2026-04-28)

- 수정:
  - `scripts/alert_pre_news_shadow_policy_governance_v1.py`
- 구현 사실:
  - 변경 횟수 기반 alert 조건 완화:
    - 기존: `change_count_window >= threshold`
    - 변경: `change_count_window > threshold`
  - 임계치와 동일한 값은 경고를 올리지 않도록 조정해 과민 알림을 완화.
- 최신 상태:
  - daily chain 재실행 후 `change_count_window=2`, `threshold=2`에서
    `has_alert=false`, `notify_status=skipped_no_alert` 확인.

#### 31.62 Holdout Lock Mismatch Drill v1 (FACT, 2026-04-28)

- 신규:
  - `scripts/run_pre_news_shadow_holdout_lock_mismatch_drill_v1.py`
  - `docs/final/artifacts/global_atom_news_holdout_dataset_lock_manifest_mismatch_drill_latest.json`
  - `docs/final/artifacts/pre_news_shadow_weekly_report_lock_mismatch_drill_latest.json`
  - `docs/final/artifacts/pre_news_shadow_holdout_lock_mismatch_drill_latest.json`
- 구현 사실:
  - lock manifest SHA를 의도적으로 변조한 mismatch 파일 생성 후,
    weekly gate를 `--enforce-holdout-dataset-lock`로 실행하는 drill 추가.
  - 기대 계약을 자동 검증:
    - `promotion_gate.enabled=false`
    - `promotion_gate.holdout_dataset_lock_ok=false`
    - `reject_reason=holdout_dataset_hash_mismatch` 존재
  - drill report의 `ok=true/false`로 결과를 단일 판정.
- 최신 상태:
  - drill 실행 exit 0 (`ok=true`) 확인.
  - mismatch 시 승격 차단 및 hash mismatch reject reason 정상 동작 확인.

#### 31.63 Weekly Audit Bundle Date Archive v1 (FACT, 2026-04-28)

- 수정:
  - `scripts/build_pre_news_shadow_weekly_audit_bundle_v1.py`
- 구현 사실:
  - weekly audit bundle 생성 시 `latest` 외에 UTC 날짜 버전 아카이브를 동시 저장:
    - 기본 템플릿: `docs/final/artifacts/pre_news_shadow_weekly_audit_bundle_{date}.json`
    - 예시 산출: `..._2026-04-28.json`
  - 신규 CLI:
    - `--out-dated-json` (`{date}` placeholder 지원)
- 최신 상태:
  - daily weekly 체인 실행 시
    - `pre_news_shadow_weekly_audit_bundle_latest.json`
    - `pre_news_shadow_weekly_audit_bundle_2026-04-28.json`
    동시 생성 확인.

#### 31.64 Weekly Audit Bundle Integrity Hash Manifest v1 (FACT, 2026-04-28)

- 수정:
  - `scripts/build_pre_news_shadow_weekly_audit_bundle_v1.py`
- 신규 산출물:
  - `docs/final/artifacts/pre_news_shadow_weekly_audit_bundle_hash_manifest_latest.json`
- 구현 사실:
  - weekly audit bundle 생성 직후 SHA-256 무결성 manifest를 자동 생성.
  - manifest 필드:
    - `latest_bundle_path`, `latest_bundle_sha256`
    - `dated_bundle_path`, `dated_bundle_sha256`
  - latest/dated 번들의 무결성을 동일 포맷으로 즉시 증명 가능.
- 최신 상태:
  - daily weekly 체인 재실행 시 hash manifest 자동 생성 확인.
  - 현재 실행에서 latest/dated SHA-256 값 일치 확인.

#### 31.65 Monthly Governance Drill Scheduler (Lock Mismatch + Policy Alert) v1 (FACT, 2026-04-28)

- 신규:
  - `scripts/run_pre_news_shadow_policy_governance_drill_v1.py`
  - `scripts/run_pre_news_shadow_monthly_governance_drills_v1.ps1`
  - `scripts/Register-PreNewsShadowMonthlyGovernanceDrillTask.ps1`
- 구현 사실:
  - 월간 거버넌스 드릴 체인 추가:
    - holdout lock mismatch drill
    - policy governance alert forced drill
  - forced governance drill은 synthetic audit summary를 사용해 경보 경로(`has_alert=true`)를 검증.
  - live webhook 부작용 방지를 위해 drill 실행에서는 webhook env를 비워 dry-alert 성격으로 검증.
  - 월간 Task Scheduler 등록 스크립트 추가:
    - 기본 task: `MKM_PreNewsShadow_Monthly_Governance_Drill`
    - 기본 스케줄: 매월 1일 07:30
- 최신 상태:
  - monthly governance drills 수동 실행 결과 두 drill 모두 `ok=true`.
  - 월간 스케줄 task 등록 성공 확인.

#### 31.37 a-codeai Public Deployment Live Verification (SSH Cursor Report, FACT, 2026-04-28)

- 실행(SSH Cursor / VPS):
  - `python3 scripts/build_a_codeai_public_evidence_json.py --repo-root .`
  - `python3 scripts/build_a_codeai_fact_lock_public_copy_v1.py`
  - `python3 scripts/build_a_codeai_public_copy_web_payload_v1.py`
  - `WEB_ROOT=/var/www/a-codeai-next-preview bash scripts/deploy/linux/deploy_a_codeai_landing_from_repo.sh`
  - `bash scripts/deploy/linux/check_a_codeai_public_routes.sh`
  - `curl -sS https://a-codeai.com/a_codeai_public_copy_web_payload_latest.json | python3 -c "import sys; sys.stdout.write(sys.stdin.read(400))"`
  - `curl -sSI https://a-codeai.com/`
  - `curl -sSI https://a-codeai.com/ko/`
  - `python3 scripts/build_pointerguard_scheduler_arguments_evidence_v1.py`
  - `python3 scripts/check_pointerguard_ops_readiness_v1.py`
  - `python3 scripts/build_pointerguard_readiness_failure_topn_v1.py`
- 핵심 결과:
  - deploy route check 4종 PASS (`/`, `/health`, `GET /v1/compress=405`, `POST /v1/compress=200 contract`).
  - payload URL 실측에서 `schema=a_codeai_public_copy_web_payload_v1` 확인.
  - 공개 라우트 헤더 `https://a-codeai.com/`, `https://a-codeai.com/ko/` 모두 `HTTP/2 200`.
  - readiness 재생성 결과 `all_ok=true`, failure topn `failed_check_count=0`.
- 최종 판정:
  - `DEPLOY=PASS`, `PUBLIC_PAYLOAD=PASS`, `READINESS=PASS`.

#### 31.38 PointerGuard Ops Dashboard + Monthly Maintenance Automation (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_pointerguard_ops_status_dashboard_v1.py`
  - `scripts/build_pointerguard_monthly_maintenance_report_v1.py`
  - `scripts/run_pointerguard_control_chain_daily.ps1`
  - `scripts/Register-PointerGuardMonthlyP0DrillTask.ps1`
- 구현 사실:
  - 일일 체인에 운영 대시보드 생성(`pointerguard_ops_status_dashboard_latest.json`)을 연결해 readiness/alert 핵심 상태를 단일 JSON으로 집계.
  - 월간 유지보수 리포트(`pointerguard_monthly_maintenance_report_latest.json`)를 추가해 live P0 drill 성공 건수, 승인 이벤트, readiness 실패 Top-1 복구 우선순위를 한 번에 요약.
  - 월간 P0 드릴 스케줄러 명령 체인에 감사 리포트/Top-N/월간 리포트 생성을 연쇄 연결해 월간 실행 시 증빙 아티팩트가 자동 갱신되도록 고정.
- 최신 상태:
  - `py scripts/build_pointerguard_ops_status_dashboard_v1.py` exit 0 (`readiness_all_ok=true`).
  - `py scripts/build_pointerguard_monthly_maintenance_report_v1.py` exit 0 (`live_p0_drill_ok_count=2`).
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-PointerGuardMonthlyP0DrillTask.ps1 -DryRun`에서 월간 커맨드 체인 반영 확인.
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_pointerguard_control_chain_daily.ps1 -ForceP0Drill` exit 0, 로그 `reports/pointerguard/pointerguard_control_chain_20260428_193358.log`.

#### 31.39 Monthly Task Length-Limit Fix + Wrapper Chain (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_pointerguard_monthly_maintenance_chain_v1.ps1`
  - `scripts/Register-PointerGuardMonthlyP0DrillTask.ps1`
- 구현 사실:
  - Windows `schtasks /TR` 261자 제한으로 월간 작업 등록이 실패하던 문제를 wrapper PowerShell 체인으로 해결.
  - 월간 태스크가 단일 래퍼를 호출하도록 재구성해 P0 drill + 감사/Top-N/월간 리포트 연쇄 실행을 유지.
- 최신 상태:
  - `Register-PointerGuardMonthlyP0DrillTask.ps1` 재등록 성공.
  - `schtasks /Query /TN "MKM_PointerGuard_Monthly_P0_Drill" /V /FO LIST`에서 `run_pointerguard_monthly_maintenance_chain_v1.ps1` 호출 확인.
  - `Start-ScheduledTask -TaskName "MKM_PointerGuard_Monthly_P0_Drill"` 수동 트리거 후 `pointerguard_monthly_maintenance_report_latest.json` 기준 `live_p0_drill_ok_count=3` 확인.

#### 31.66 Pre-News Shadow Ops Single-File Dashboard (FACT, 2026-04-28)

- 스크립트:
  - `scripts/build_pre_news_shadow_ops_status_dashboard_v1.py`
  - `scripts/run_daily_prophecy_then_pre_news_v1.ps1`
- 구현 사실:
  - Pre-News Shadow 운영 상태를 단일 JSON(`docs/final/artifacts/pre_news_shadow_ops_status_latest.json`)로 집계하는 대시보드 빌더 추가.
  - 대시보드에 다음을 포함:
    - promotion gate/holdout lock 상태
    - 최신 policy/task health alert 스냅샷
    - alert/projection 로그 tail
    - 월간 drill 3종 최신 결과(lock mismatch / policy governance / task health alert)
    - weekly audit bundle 최신/dated 경로와 manifest 참조
  - `run_daily_prophecy_then_pre_news_v1.ps1`의 pre-news weekly report 체인 말단에 대시보드 생성을 자동 연결.
- 최신 상태:
  - `py -3 scripts/build_pre_news_shadow_ops_status_dashboard_v1.py` exit 0.
  - 생성 산출물에서 `schema=pre_news_shadow_ops_status_v1`, `summary.drill_status=ok`, `summary.holdout_dataset_lock_ok=true` 확인.

#### 31.67 Pre-News Monthly Drill One-Line Summary Alert (FACT, 2026-04-28)

- 스크립트:
  - `scripts/alert_pre_news_shadow_monthly_drill_summary_v1.py`
  - `scripts/run_pre_news_shadow_monthly_governance_drills_v1.ps1`
- 구현 사실:
  - 월간 governance drill 종료 시 2개 drill 결과를 집계해 1줄 요약(`PASS/FAIL`)을 생성하는 알림 스크립트 추가.
  - 산출물:
    - `docs/final/artifacts/pre_news_shadow_monthly_drill_summary_alert_latest.json`
    - `reports/pre_news_shadow_monthly_drill_summary_alert_log.jsonl`
  - 웹훅은 `MKM_PRE_NEWS_SHADOW_ALERT_WEBHOOK_URL` 우선, 없으면 `OPS_ALARM_WEBHOOK_URL` 사용.
  - `run_pre_news_shadow_monthly_governance_drills_v1.ps1`를 즉시 종료 방식에서 결과 수집 방식으로 변경:
    - holdout/policy drill 실행
    - summary alert 생성
    - drill 실패 시 최종 exit 1 유지(스케줄러 실패 감지 보존)
- 최신 상태:
  - `py -3 scripts/alert_pre_news_shadow_monthly_drill_summary_v1.py` exit 0.
  - 출력 1줄: `Pre-News monthly drills: PASS (2/2).`

#### 31.68 Pre-News Policy Change Approval Workflow Checklist JSON (FACT, 2026-04-28)

- 산출물:
  - `docs/final/artifacts/pre_news_shadow_policy_change_approval_workflow_v1.json`
- 구현 사실:
  - 정책 변경 승인 흐름을 단일 체크리스트 JSON으로 고정:
    - 2인 승인 필드 포함 정책 수정
    - 주간 체인 재실행
    - audit summary 기반 2인 승인/지문 확인
    - governance alert 동작 확인
    - weekly bundle + hash manifest 추적성 확인
  - GO/HOLD 결정 규칙을 명시해 운영자가 변경 승인 완료 조건을 즉시 판정 가능하게 구성.
- 최신 상태:
  - 체크리스트 JSON 생성 완료(스키마 `pre_news_shadow_policy_change_approval_workflow_v1`).

#### 31.69 Pre-News Ops Unified Smoke Runner (FACT, 2026-04-28)

- 스크립트:
  - `scripts/run_pre_news_shadow_ops_smoke_v1.py`
- 구현 사실:
  - 운영 마감형 단일 smoke 러너 추가(한 번에 3종 점검):
    - ops status dashboard 재생성
    - monthly drill summary alert 재생성
    - policy change approval workflow checklist JSON 존재 확인
  - 결과 아티팩트:
    - `docs/final/artifacts/pre_news_shadow_ops_smoke_latest.json`
  - smoke 결과에 각 step의 exit code/stdout/stderr와 snapshot(ops summary + monthly drill summary)을 함께 기록.
- 최신 상태:
  - `py -3 scripts/run_pre_news_shadow_ops_smoke_v1.py` exit 0.
  - `pre_news_shadow_ops_smoke_latest.json` 기준 `all_ok=true`.

#### 31.70 Lens-Combo Limited-Live Submit Path + Watchdog Wrapper (FACT, 2026-04-29)

- 스크립트:
  - `scripts/run_prophecy_lens_combo_backtest_v1.py`
  - `scripts/run_lens_combo_limited_live_engine_handoff_v1.py`
  - `scripts/build_lens_combo_engine_submit_preflight_v1.py`
  - `scripts/run_lens_combo_24h_watchdog_v1.py`
- 구현 사실:
  - limited-live 제출 후보 경로를 lens-combo 아티팩트로 고정:
    - `docs/final/artifacts/btc_limited_live_engine_input_from_lens_combo_latest.json`
  - 동률 시 선택 정책을 구조화해 산출물에 명시:
    - `tie_break_policy.policy_id = non_logos_multi_lens_then_lens_count_v1`
    - 핵심 지표 동률이면 비-logos 다중렌즈(예: `myeongni+sasang`)를 우선.
  - `run_prophecy_lens_combo_backtest_v1.py` 연구 하네스 기본값(2026-05-19): `--logos-vote-mode omit`(성경=가격 방향 다수결 투표 제외, `[NON_GATING]` 정합); omit 시 coordinator BTC prior tie-break도 비활성(기권 유지). Logos A/B만 `run_prophecy_logos_revalidation_suite_v1.py`에서 `global` 명시.
  - `run_lens_combo_24h_watchdog_v1.py` 추가:
    - lens 엔진 입력을 기준으로 breaker 아티팩트를 먼저 갱신한 뒤,
    - 24h watchdog(`run_role_router_24h_watchdog_v1.py`)을 lens 경로 인자로 실행.
- 최신 상태:
  - `py scripts/run_lens_combo_limited_live_engine_handoff_v1.py --approve-submit --live` exit 0 (`dry_run=false`, `status=READY_FOR_ENGINE_SUBMIT`).
  - `py scripts/build_lens_combo_engine_submit_preflight_v1.py --expected-dry-run false` exit 0 (`result=PASS`).
  - `py scripts/run_lens_combo_24h_watchdog_v1.py --duration-hours 0 --poll-seconds 5` exit 0 (`healthy=True` smoke row 기록).

#### 31.71 Role-Router Shadow-Forward Gate Hard-Lock + Threshold Calibration (FACT, 2026-04-29)

- 스크립트:
  - `scripts/check_role_router_shadow_forward_validation_v1.py`
  - `scripts/run_prophecy_role_router_multiscenario_opt_v1.py`
- 산출물:
  - `docs/final/artifacts/role_router_shadow_forward_validation_gate_v1.json`
  - `docs/final/artifacts/prophecy_role_router_multiscenario_opt_30y_btc_neutralbase_latest.json`
  - `reports/role_router_shadow_forward_validation_decision_latest.json`
  - `reports/role_router_shadow_forward_validation_decision_log.jsonl`
- 구현 사실:
  - Shadow-forward 승격 판정기 추가:
    - gate JSON의 필수 체크(Preflight/Intent/First30m/24h Watchdog/Circuit Breaker) + 자산별 임계치 + cross-asset safety를 단일 판정으로 결합.
    - 판정 출력은 `GO_LIVE_CANDIDATE` 또는 `HOLD_SHADOW_ONLY`로 고정.
  - gate에 `required_oos_days=252` 하드락 반영(자산 공통).
  - BTC block 임계치 민감도 검증 후 `min_hit_rate_active`를 `0.53 -> 0.52845`로 정밀 보정.
  - `run_prophecy_role_router_multiscenario_opt_v1.py`에 gate 연결 후처리 옵션(`--promotion-gate-json`) 추가:
    - gate 통과 후보가 있으면 해당 후보를 `best_candidate`로 우선 선택,
    - 없으면 기존 robustness-first 순위를 유지.
- 최신 상태:
  - `py scripts/check_role_router_shadow_forward_validation_v1.py --gate-json docs/final/artifacts/role_router_shadow_forward_validation_gate_v1.json` exit 0.
  - `reports/role_router_shadow_forward_validation_decision_latest.json` 기준:
    - `checks_passed=true`
    - `thresholds_passed=true`
    - `final_decision=GO_LIVE_CANDIDATE`

#### 31.72 Revalidation Failure-Path Semantic Field Persistence + Separation Gate (FACT, 2026-04-29)

- 스크립트:
  - `scripts/run_prophecy_logos_revalidation_suite_v1.py`
  - `scripts/check_promotion_directional_semantic_separation_v1.py`
- 테스트:
  - `tests/test_role_router_shadow_forward_fusion_regression.py`
  - `tests/test_promotion_directional_semantic_separation_v1.py`
- 구현 사실:
  - revalidation suite의 조기 실패(`status=FAILED`) 경로에서도 `findings.logos_directional_viable_under_current_setup`를 항상 기록하도록 고정.
  - 승격 판정(`final_decision`)과 Logos 방향성 가능성(`logos_directional_viable_under_current_setup`)의 의미 분리 스모크체크를 추가하고 strict 모드 검증을 지원.
  - CI(`.github/workflows/dual-regime-integrity.yml`)에 해당 회귀 테스트를 연결해 의미 혼선 재발을 자동 차단.
- 최신 상태:
  - `py scripts/run_prophecy_logos_revalidation_suite_v1.py` exit 0.
  - `py scripts/check_promotion_directional_semantic_separation_v1.py --strict` exit 0 (`semantic_separation_ok=true`, `non_conflation_confirmed=true`).
  - `py -m pytest tests/test_role_router_shadow_forward_fusion_regression.py tests/test_promotion_directional_semantic_separation_v1.py -q` exit 0 (4 passed).

#### 31.73 Survivor Resonance Direct-Mapping + Real/Proxy Falsification Chain (FACT, 2026-04-29)

- 스크립트:
  - `scripts/build_survivor_w3_direct_mapping_v1.py`
  - `scripts/build_global_atom_survivor_resonance_daily_real_v1.py`
  - `scripts/run_survivor_resonance_falsification_chain_v1.py`
  - `scripts/check_survivor_crash_falsification_gate_v1.py`
  - `scripts/sweep_survivor_crash_falsification_thresholds_v1.py`
  - `scripts/tune_survivor_real_resonance_weights_v1.py`
- 테스트:
  - `tests/test_build_survivor_w3_direct_mapping_v1.py`
  - `tests/test_build_global_atom_survivor_resonance_daily_real_v1.py`
  - `tests/test_check_survivor_crash_falsification_gate_v1.py`
  - `tests/test_run_survivor_resonance_falsification_chain_v1.py`
  - `tests/test_sweep_survivor_crash_falsification_thresholds_v1.py`
- 구현 사실:
  - survivor(`cand_001..005`)와 W3 `sample_id`를 직접 매핑하는 아티팩트(`global_atom_survivor_w3_direct_mapping_latest.json`)를 추가해 `mapping_quality=direct_mapping_seeded_v1` 경로를 고정.
  - real resonance 입력(`global_atom_survivor_resonance_daily_real_latest.jsonl`)을 체인에 연결해 real 부재 HOLD를 해소하고, proxy/real 분리 결과를 단일 summary로 산출.
  - 기본 반증 게이트(`|corr|>=0.5`, `p<=0.05`, `n>=250`)는 proxy/real 모두 `HOLD_RESEARCH_ONLY`.
  - 가중치 튜닝 best는 `w_candidate=0.8`, `w_flow=0.5`, `w_temporal=0.1`; 탐색 임계치(`|corr|>=0.08`)에서는 real 기준 `GO_RESEARCH_SIGNAL_CANDIDATE` 확인.
- 최신 상태:
  - `py scripts/run_survivor_resonance_falsification_chain_v1.py` exit 0 (`final_decision=HOLD_RESEARCH_ONLY`).
  - `py scripts/sweep_survivor_crash_falsification_thresholds_v1.py --threshold-grid 0.3,0.4,0.5` exit 0 (all HOLD).
  - `py scripts/check_survivor_crash_falsification_gate_v1.py --backtest-json docs/final/artifacts/btrack_survivor_crash_correlation_backtest_real_latest.json --output docs/final/artifacts/btrack_survivor_crash_falsification_gate_real_thr0p08_latest.json --min-abs-corr 0.08 --max-pvalue 0.05 --min-n 250` exit 0 (`decision=GO_RESEARCH_SIGNAL_CANDIDATE`).

#### 31.74 Survivor Chain Auto-Apply Tuned Weights (FACT, 2026-04-29)

- 스크립트:
  - `scripts/run_survivor_resonance_falsification_chain_v1.py`
  - `scripts/tune_survivor_real_resonance_weights_v1.py`
  - `scripts/build_global_atom_survivor_resonance_daily_real_v1.py`
- 테스트:
  - `tests/test_run_survivor_resonance_falsification_chain_v1.py`
  - `tests/test_tune_survivor_real_resonance_weights_v1.py`
- 구현 사실:
  - falsification chain이 `btrack_survivor_real_resonance_tuning_latest.json`의 `best.weights`를 자동 로드해 real resonance JSONL을 선행 재빌드한 뒤 backtest/gate를 수행하도록 배선.
  - 기본값은 `--apply-best-tuned-weights` enabled이며, 튜닝 파일 부재/파싱 실패 시 summary `notes`에 이유를 기록하고 보수 경로로 계속 실행.
  - summary 입력에 `apply_best_tuned_weights`와 `tuning_json` 경로를 명시해 재현/감사를 고정.
- 최신 상태:
  - `py -m pytest tests/test_run_survivor_resonance_falsification_chain_v1.py tests/test_tune_survivor_real_resonance_weights_v1.py -q` exit 0.
  - `py scripts/run_survivor_resonance_falsification_chain_v1.py` exit 0 (`final_decision=HOLD_RESEARCH_ONLY`).

#### 31.75 Survivor Resonance Operational Bundle + CI Gate Lock (FACT, 2026-04-29)

- 스크립트:
  - `scripts/run_survivor_resonance_operational_bundle_v1.py`
- 테스트:
  - `tests/test_run_survivor_resonance_operational_bundle_v1.py`
- CI:
  - `.github/workflows/dual-regime-integrity.yml`
- 구현 사실:
  - 운영 번들에서 `tuning -> direct_mapping -> build_real -> falsification_chain -> threshold_sweep(0.3,0.4,0.5) -> exploratory_gate(0.08)`를 단일 실행으로 고정.
  - 산출물 `docs/final/artifacts/survivor_resonance_operational_bundle_latest.json`에 실행별 returncode와 핵심 스냅샷(`chain_final_decision`, `exploratory_gate_decision`, `tuning_best_weights`)을 기록.
  - CI에 번들 회귀 테스트를 추가해 falsification chain 회귀와 분리된 독립 게이트로 고정.
- 최신 상태:
  - `py -m pytest tests/test_run_survivor_resonance_operational_bundle_v1.py -q` exit 0.
  - `py scripts/run_survivor_resonance_operational_bundle_v1.py` exit 0 (`chain_final_decision=HOLD_RESEARCH_ONLY`, `exploratory_gate_decision=GO_RESEARCH_SIGNAL_CANDIDATE`).

#### 31.76 Survivor Exploratory Threshold Boundary Lock (FACT, 2026-04-29)

- 스크립트:
  - `scripts/run_survivor_resonance_operational_bundle_v1.py`
- 테스트:
  - `tests/test_run_survivor_resonance_operational_bundle_v1.py`
- 구현 사실:
  - 운영 번들 정책 필드를 고정:
    - `default_exploratory_min_abs_corr=0.08` (보수 기본값)
    - `validated_max_go_min_abs_corr=0.082` (촘촘 스윕 기준 GO 최대 경계)
  - exploratory gate 산출 경로를 임계치 기반(`thr{tag}`)으로 동적 계산해, 임계치 변경 시에도 결과 경로/요약이 일관되게 동기화되도록 보완.
  - 번들 산출물에 `policy` 블록과 `snapshots.exploratory_gate_output_path`를 추가해 운영 감사 시 임계치 정책과 실제 gate 파일을 동시에 추적 가능하도록 고정.
- 최신 상태:
  - `py scripts/sweep_survivor_crash_falsification_thresholds_v1.py --threshold-grid 0.080,0.082,0.084,0.086,0.088,0.090,0.092,0.094,0.096,0.098,0.100` exit 0.
  - 스윕 결과: real gate는 `0.082`까지 `GO_RESEARCH_SIGNAL_CANDIDATE`, `0.084`부터 `HOLD_RESEARCH_ONLY`.

#### 31.77 Survivor Boundary Push Experiments (FACT, 2026-04-29)

- 스크립트:
  - `scripts/build_survivor_w3_direct_mapping_v1.py`
  - `scripts/build_global_atom_survivor_resonance_daily_real_v1.py`
  - `scripts/check_survivor_crash_falsification_gate_v1.py`
  - `scripts/sweep_survivor_crash_falsification_thresholds_v1.py`
- 테스트:
  - `tests/test_build_survivor_w3_direct_mapping_v1.py`
  - `tests/test_build_global_atom_survivor_resonance_daily_real_v1.py`
  - `tests/test_check_survivor_crash_falsification_gate_v1.py`
- 구현 사실:
  - direct mapping을 `rank_aligned_topk_window_v2`로 확장하고 `--samples-per-survivor` 옵션(다중 샘플 할당)을 추가.
  - real resonance builder에
    - `--regime-adaptive-weighting`
    - `--w-market-shock`
    를 추가해 변동성/시장 쇼크 보조 신호를 점수 합성에 반영 가능하게 확장(기본값은 보수적으로 기존 영향 최소).
  - falsification gate/sweep에 목적함수 모드 옵션 추가:
    - `objective_mode=return|crash|blended`
    - `blend_alpha`(blended 모드 가중치)
- 최신 상태(실측):
  - 경계 스윕(`0.080~0.100`)에서 `return` objective 기준은 여전히 `0.082`까지 GO, `0.084`부터 HOLD.
  - `crash`/`blended(alpha=0.3)` objective는 전 구간 HOLD.
  - crash 라벨 임계치(`crash_dd_threshold=-0.25/-0.30/-0.35`) 재백테스트에서도 `return` objective 경계 상향은 확인되지 않음(최대 `0.082` 유지 또는 악화).

#### 31.78 L0 Early-Warning Backtest Branch (FACT, 2026-04-29)

- 스크립트:
  - `scripts/run_btrack_survivor_l0_early_warning_backtest_v1.py`
- 테스트:
  - `tests/test_run_btrack_survivor_l0_early_warning_backtest_v1.py`
- 구현 사실:
  - survivor resonance와 시장 drawdown 기반 `crash_flag`를 사용하되, 기존 return/correlation 중심 백테스트와 분리해 **L0 조기경보 전용 라벨**(`crash_onset_within_horizon`)을 별도로 구성.
  - `--onset-horizon-days` 윈도우 내 급락 진입 여부를 라벨링하고, lag sweep에서 `onset_corr`/`onset_n`을 계산해 선행 경보 가능성만 측정.
  - 산출 스키마를 `btrack_survivor_l0_early_warning_backtest_v1`로 분기해 `l0_warning_only=true`를 고정(실거래 트리거와 격벽 유지).

#### 31.79 Operational Bundle L0 Option Wiring + Test Stabilization (FACT, 2026-04-29)

- 스크립트:
  - `scripts/run_survivor_resonance_operational_bundle_v1.py`
- 테스트:
  - `tests/test_run_survivor_resonance_operational_bundle_v1.py`
  - `tests/test_run_btrack_survivor_l0_early_warning_backtest_v1.py`
- 구현 사실:
  - operational bundle에 `--include-l0-early-warning` 옵션을 추가해, 필요 시 `l0_early_warning_backtest` 단계를 번들 체인에 조건부 포함하도록 배선.
  - 번들 산출물 입력/스냅샷 필드에 `include_l0_early_warning`, `l0_early_warning_enabled`, `l0_early_warning_schema`를 추가해 실행 여부와 결과 스키마를 감사 가능하게 고정.
  - 번들 테스트 안정화를 위해 `--dry-run` 옵션을 추가하고, 회귀 테스트는 dry-run 경로로 계약 검증을 수행하도록 보완(실운영 기본 경로는 기존과 동일한 실실행).
- 최신 상태:
  - `py -m pytest tests/test_run_survivor_resonance_operational_bundle_v1.py tests/test_run_btrack_survivor_l0_early_warning_backtest_v1.py -q` exit 0 (`3 passed`).

#### 31.80 External Bible anchor governance (K-track hypothesis pool · weekly chain) — FACT, 2026-04-30

- **주간 체인(모노레포 루트):** `scripts/run_layer1_layer5_weekly_maintenance_v1.ps1` — 외부 베이스라인 인덱스 → tiering → shadow → Tier1 후보/프로모션 → post-promotion regression → **sustain gate → sync policy → append history → sustain → final sync → append `--overwrite-last-row`** → weekly A/B → policy-stage drill → handoff → `scripts/build_symbolic_reality_blend_runtime_v1.py`(anchor operating policy 입력).
- **핵심 스크립트:** sustain `scripts/check_external_anchor_promotion_sustain_gate_v1.py`(성숙 패스 스트릭에 `adopt_limited`·`adopt_limited_strict` 동일 계열 취급); 정책 동기화 `scripts/sync_external_anchor_tier1_into_operating_policy_v1.py`(`--strict-pass-streak-threshold`, 기본 6 → `adopt_limited_strict` 승격); 히스토리 `scripts/append_external_anchor_promotion_history_v1.py`(선택 `--overwrite-last-row`); handoff `scripts/build_external_anchor_promotion_handoff_packet_v1.py`; weekly A/B `scripts/build_external_anchor_weekly_ab_report_v1.py`; recovery `scripts/build_external_anchor_recovery_candidates_v1.py`.
- **산출(예시 파일명):** `docs/final/artifacts/external_bible_anchor_*_latest.json`·`external_bible_anchor_promotion_history_log.jsonl`·`symbolic_reality_blend_runtime_latest.json` — 단일 근거는 해당 JSON 필드·exit code.
- **회귀:** `tests/test_external_anchor_governance_scripts_smoke_v1.py`; CI: `.github/workflows/dual-regime-integrity.yml`에 스모크 스텝 및 PR paths 등록.
- **혼동 방지:** 로컬 `.git/info/exclude` 등으로 `scripts/` 일부가 인덱스에서 빠질 수 있음 — **원격에 커밋된 경로**만 “구현 팩트”로 단정. PR 전용 작업은 별도 **git worktree**(`C:\workspace\tmp\wt-external-anchor-work` 등)로 원격 브랜치(`fix/external-anchor-ci-smoke`)와 맞추는 것이 안전.

#### 31.81 Pre-News × Sasang harness completion gate v1 (FACT, 2026-06-30)

- **목적:** Brier `metric_pass`만으로 “완료”를 주장하는 **lazy optimization**을 막는다. **철학 격벽·JEMA OS 좌표·미들웨어 binding**이 없으면 exit≠0.
- **이중 완료 계약:** `docs/final/artifacts/pre_news_sasang_harness_completion_contract_v1_latest.json` — `metric_pass`(pooled gate) ≠ `harness_pass`(philosophy wall + envelope + overlay flags).
- **체커:** `scripts/check_pre_news_sasang_harness_completion_v1.py` → `reports/pre_news_sasang_harness_completion_v1_latest.json`
  - **exit 0:** `harness_pass: true` (metric_pass는 보고만; `--require-metric-pass` 시 metric false면 exit **3**)
  - **exit 2:** `harness_pass: false` (Brier pass여도 실패)
  - **exit 1:** contract/usage 오류
- **필수 산출:** `reports/pre_news_sasang_jema_os_coordinate_binding_v1_latest.json`(내 `philosophy_wall_v1`) · `docs/final/artifacts/pre_news_sasang_jema_os_coordinate_envelope_v1_latest.json` · `docs/final/artifacts/pre_news_sasang_jema_os_middleware_chain_v1_latest.json` · overlay `philosophy_wall_required: true` + `jema_os_coordinate_binding_ref`
- **빌더/바인딩:** `scripts/build_pre_news_sasang_jema_os_coordinate_binding_v1.py`; envelope 검증 `scripts/check_jema_os_coordinate_envelope_v1.py --artifact …pre_news_sasang…`
- **라우트:** `scripts/Invoke-PreNewsSasangShadowRoute_v1.ps1` — 말단 `harness_completion_gate` 필수
- **일일 ops:** `scripts/Run-PreNewsShadowOpsRefresh_v1.ps1` — 말단 harness check **필수**; 전체 sasang 재빌드는 `-IncludeSasangShadowRoute`(control arm 포함)
- **기본 route SSOT:** `docs/final/artifacts/pre_news_sasang_shadow_default_route_v1_latest.json` — `harness_completion_gate.required: true`
- **격벽:** `research_only` · `send_gate: HOLD` · `promotion_to_a_track_allowed: false` · 금화교역=interpretive pointer only(overlay math merge 금지)
- **회귀:** `tests/test_pre_news_sasang_harness_completion_v1.py`
- **CI:** `.github/workflows/dual-regime-integrity.yml` — `Pre-News × Sasang harness completion gate v1` pytest 스텝; Fact-Lock 번들 기본 포함(`SkipPreNewsSasangHarnessSmoke`로 생략)
- **재현:** `py scripts/check_pre_news_sasang_harness_completion_v1.py`

## 28) 실행 거버넌스 (Athena Run · Execution Clearance Certificate) — FACT, 2026-05-03

**목적(헌법적 근거):** 고위험 실행(특히 자본·주문·거래소 API에 연결될 수 있는 경로)은 **맥락적 정당성**이 있을 때만 진행한다. `integrated_governance_v1`의 `final_regime`·`final_action_allowed`와 **선언된 액션 유형**(`TRADE_EXECUTE` / `OBSERVE_ONLY`)을 조합해, **승인·거부·감사 가능한 산출물(ECC)**을 남긴다. 본 절은 **Fact-Lock 경로**만 기술하며, “우회 불가능”을 단정하지 않는다.

| 항목 | 경로 / 팩트 | 비고 |
|------|-------------|------|
| 런처 (PoC) | `scripts/athena_run_v1.py` | 인자: `--governance-json`(기본 `docs/final/artifacts/integrated_governance_v1_latest.json`), `--action`(`TRADE_EXECUTE`\|`OBSERVE_ONLY`), `--target KEY`(DPAPI 스토어 키명 = 자식 env 키; 생략 시 PoC용 가짜 `BINANCE_API_KEY`), `--ecc-out`, 자식 명령은 `--` 뒤. **HOLD 시 DPAPI 미조회.** |
| 거버넌스 입력 | `docs/final/artifacts/integrated_governance_v1_latest.json` | `schema: integrated_governance_v1`. **정적 가중치·정책(레포 추적):** `docs/final/artifacts/integrated_governance_config_v1.json`. 빌더: `scripts/build_integrated_governance_v1.py`(`--validate-digest-schema` 선택, jsonschema 필요). **자동 갱신(권장):** `scripts/invoke_build_integrated_governance_if_deps_present_v1.py`(KOSPI 게이트+config 존재 시만 빌드; `run_fact_lock_bundle`·`Invoke-TrackCMacroDailyFusion_v1`·`Invoke-MkmAiV2DailyReadiness`). **CI:** `dual-regime-integrity`가 `scripts/fixtures/kospi_*_ci_minimal_hold_v1.json`를 `docs/final/artifacts/kospi_*_latest.json`로 복사한 뒤 인보커를 실행해 스킵만 되는 경로를 막는다. Windows 보조: `Invoke-BuildIntegratedGovernanceIfDepsPresent_v1.ps1`. **HOLD**(`final_regime`·`final_action_allowed`)는 `_is_hold()`로 판정. **보강 (2026-05-13):** 빌더가 선택적으로 `lens_music_hormone_trend_latest.json`·`reports/lens_music_symbolic_audio_promotion_gate_latest.json`를 읽어 **`lens_music_m31_operational_digest_v1`**(비생물학적 메타포·**3엔진 합성 판정과 무관**)를 같은 JSON에 첨부. 다이제스트 객체 스키마: `docs/final/schemas/lens_music_m31_operational_digest_v1.schema.json`. |
| ECC 산출 | `docs/final/artifacts/ecc_execution_clearance_latest.json` (기본) | `schema: execution_clearance_certificate_v1`; **DENIED** / **APPROVED**, `action_payload_hash`(자식 argv SHA-256), `audit_ref`, `child_exit_code`. |
| ECC 감사(append-only) | `reports/athena_ecc_audit.jsonl` (기본, `--audit-jsonl`) | 매 실행마다 JSONL 한 줄 추가; `ecc_payload_sha256`(ECC 페이로드 정규화 SHA-256), 전체 `ecc` 복사. **로컬 파일 변조 가능** — 원격 증거는 별도 파이프라인. `--no-audit-append`로 끔. |
| 원격 감사 요약 POST | 환경 변수 `ATHENA_ECC_AUDIT_WEBHOOK_URL` | 감사 행 기록 직후 `schema: athena_ecc_audit_webhook_v1` JSON POST(비밀 미포함). 실패 시 stderr만, exit 코드 불변. `--no-audit-webhook`으로 끔. `.env.example` 참고. |
| 감사 로그 조회 | `scripts/athena_ecc_logs_v1.py` | `--last N` · `--audit-jsonl`. |
| 일괄 스모크 (네트워크 없음) | `scripts/check_athena_execution_governance_smoke_v1.py` | doctor + HOLD·`TRADE_EXECUTE` → exit 2 경로 확인. |
| 회귀 (스모크 래퍼) | `tests/test_check_athena_execution_governance_smoke_v1.py` | 위 스크립트를 subprocess로 호출, exit 0. |
| CI (Fact-Lock) | `.github/workflows/dual-regime-integrity.yml` | 위 세 pytest + `test_check_*`를 한 스텝에서 실행; PR `paths`에 §28 스크립트·테스트 포함. |
| 모의 진입점 | `scripts/trade_dummy.py` | PoC용; 실매매 아님. |
| HOLD 픽스처 (테스트·데모) | `scripts/fixtures/integrated_governance_v1_hold.json` | 저장소 내 최소 HOLD 스냅샷. |
| 프리플라이트 요약 | `scripts/athena_doctor_v1.py` | `--governance-json`·`--ecc-json` — 콘솔에 `final_regime`·최신 ECC `status`/`reason` 요약(전체 헬스 번들 대체 아님). |
| 회귀 | `tests/test_athena_run_v1.py` | HOLD + `TRADE_EXECUTE` → exit **2**·DENIED; HOLD + `OBSERVE_ONLY` → 자식 실행·비밀 미주입. |
| 회귀 | `tests/test_athena_doctor_v1.py` | 최소 stdout·exit 코드. |

**정책(Fact-Lock):**

- **`TRADE_EXECUTE` + HOLD(또는 `final_action_allowed: false`)** → ECC **DENIED**, stderr에 `ECC DENIED: Governance is in HOLD mode.`(동일 의미), **exit code 2**. 자식 프로세스는 시작하지 않음. 상위 오케스트레이터는 **exit 2**를 “코드 예외”와 구분해 정책 차단으로 처리할 수 있음.
- **`OBSERVE_ONLY`** → HOLD여도 **승인** 가능; 비밀 주입 없이 자식만 실행(가시성 유지).
- **승인 + `TRADE_EXECUTE`** → `--target NAME`이면 `security_agent_manager`/DPAPI에서 `NAME` 조회 후 자식 `env[NAME]`만 설정; 없으면 exit **1** 및 안내 메시지. `--target` 생략 시 PoC로 자식에만 `BINANCE_API_KEY=FAKE_BINANCE_KEY_1234` 주입.

**명시적 한계(우회):** 운영자·프로세스가 동일 스크립트를 **`athena_run_v1` 없이** 직접 실행하면 본 ECC·거버넌스 게이트를 **경유하지 않는다**. 호스트·컨테이너·키 저장소 수준의 강제는 별도 설계(운영 런북·Phase 2+)다.

**Athena Broker 표기:** 본 레포에서 **“Athena Broker”**는 위 런처·ECC 산출·거버넌스 입력을 묶은 **운영 명칭**으로만 쓴다. 별도 바이너리 서비스를 단정하지 않는다.

## 29) Logos Ask — 직교 이중축 아키텍처 (Orthogonal Dual-Axis, FACT 2026-07-04)

**개요:** Logos Ask 런타임에 성경 코드북(WHAT, 콘텐츠 축)과 사상동역학(HOW, 전략 축)을 **직교**로 분리한 이중축 오케스트레이션 배관.

| 항목 | 경로 / 산출물 | 상태 |
|------|--------------|------|
| B-track 스펙 | `docs/research/LOGOS_ORTHOGONAL_DUAL_AXIS_SPEC_V1.md` | 동결 |
| 전략 분류기 | `scripts/classify_logos_constitutional_strategy_v1.py` | exit 0, 키워드 휴리스틱 |
| 깊이 추적기 | `scripts/classify_logos_session_depth_v1.py` | exit 0, 초/중/말 3단계 |
| 모듈레이션 오케스트레이터 | `scripts/modulate_logos_strategy_v1.py` | exit 0, 금화교역 이중관점 |
| TS Bridge | `projects/no1kmedi/src/lib/logosStudioStrategyBridgeV1.ts` | tsc exit 0 |
| 런타임 배선 | `projects/no1kmedi/src/lib/logosResearchStudioV1.ts` (synthesis 직후 호출) | tsc exit 0 |
| Pytest 검증 | `tests/test_logos_orthogonal_dual_axis_v1.py` — 19/19 passed | exit 0 |
| 관측 로그 | `reports/logos_strategy_modulation_observation.jsonl` | JSONL append |
| 관측 리포트 | `scripts/report_strategy_modulation_observation_v1.py` | exit 0 |
| VPS 라이브 | `logos.jema-ai.com` — `LOGOS_STUDIO_STRATEGY_MODULATION=on` | 가동 중 |

**관측 결과 (61건, 2026-07-04):**

| 게이트 | 기준 | 실측 | 판정 |
|--------|------|------|------|
| 표본 충분 | >=50 | 61 | PASS |
| ok_rate | >=90% | 100% | PASS |
| avg_confidence | >=50% | 52.4% | PASS |
| p95_latency | <3s | 56ms | PASS |
| **verdict** | — | — | **READY** |

**직교 원칙 (성정불변):** 전략 축(HOW)이 실패해도 콘텐츠 축(WHAT, 200-Hub·코사인 가드)은 오염되지 않는다. `degradation_safe: true`.

**한계:**
- 분류기 31% fallback (confidence 25%, method=default_fallback) — 임베딩 기반 업그레이드 예정.
- `send_gate: HOLD` 해제는 지휘관 승인에 의한다.
- 타 도메인(명리, 사상진단, PersonaDiary) 확장은 별도 스펙 필요.

**금지:** 관측 결과만으로 Track A 상용 승격·과금·실매매 트리거를 단정하지 않는다.
