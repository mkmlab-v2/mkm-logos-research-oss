# CLAUDE.md — Cursor/Claude용 마스터 컨텍스트 (슬림)

**목적**: 세션 초기에 **한 화면**으로 방향을 맞춘다. 장문 가이드는 각 규칙·문서에 둔다.

## 에이전트 동작

- **TITAN**: 루트 `.cursorrules` 최상단 — 자율 기동, **이항 선택([A]/[B]) 강요 금지**, 고위험만 승인 요청.
- **세션 핸드오프 (선택):** 새 채팅에서 직전 작전 팩트만 이어 붙일 때 `@docs/final/CURRENT_OPS_SNAPSHOT.md`를 첨부한다. 불변 SSOT가 아니며 압축 파이프라인(A/B Track)과 역할을 섞지 않는다. **종료 조건·로컬 체크리스트**만 남길 때는 `MISSION_LOG.template.md` → **`MISSION_LOG.md`**(비추적); 스냅샷과 동일 내용 이중 기술 금지. 상세: 루트 `AGENTS.md` 동명 절.
- **병렬 작전:** 사업·공고 / B-track / 레포 편집은 **채팅·브랜치를 나눌 것** — 루트 `AGENTS.md` **「병렬 작전 권장」**.
- **원격 게시 기본값:** internal-first. `origin`/`hq`(GitHub)는 `no_push` 기본 차단을 유지하고, 예외 공개는 명시 승인형 스크립트(`scripts/Push-GitHub-Explicit.ps1 -Acknowledge`)로만 수행한다.
- **크로스 채팅 정체성:** `docs/final/CENTRAL_AGENT_MEMORY_V1.md`(지속 SSOT) · `.cursor/rules/central-agent-memory.mdc`(핵심 5줄 `alwaysApply`). 세션 로그 자동 병합 없음. 상세: 루트 `AGENTS.md` 「중앙 메모리」. **질문 유형별 답변 라우팅(권장 복붙)**은 동 CENTRAL 파일 본문 절을 SSOT로 둔다.
- **중앙 지휘부 규칙**: `.cursor/rules/sovereign-central-command.mdc` (`alwaysApply`).
- **코드/추론 “구현 여부”**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 를 호출 가능한 `.py`와 대조한다. **Multi-Lens·TOE 비단정**은 동 문서 §1.1; **예언 성능 우선·도메인 사례 격리 [VISION]**는 **§1.1.1**. **Windows OPS Phase 1 체인·리포트·운영/연구 레인**은 §13.1 (`verify_constitution_gates.ps1`, `constitution_gates_v1.json`, `bootstrap_ops_phase1_daily.ps1`, `verify_ops_phase1_operational_readiness.ps1`)·루트 `AGENTS.md`.
- **12AI vs 코드북**: **12AI**는 Cursor 작업 라우팅용 오케스트레이션 라벨이며, 코드북 도메인·샤드 개수와 **1:1로 묶지 않는다.** (보통 복잡·고위험 작업만 2~4 전문 에이전트로 분산.) 상세: 루트 `AGENTS.md`, `.cursor/skills/auto-12ai-routing/SKILL.md`.
- **하네스 정밀 하드닝(요약):** 래칫은 `임시→후보→영구` 3단계 승격으로 운영하고, 장기 작업은 생성/평가 루프를 분리한다. 컨텍스트는 SLO(상한·요약 주기·오프로드)로 관리하며, 성공은 `heartbeat`만 남기고 실패만 상세 재주입한다. HaaS/프레임워크 사용 시에도 핵심 게이트 검증은 로컬 스크립트·아티팩트·exit code(Fact-Lock)로 고정한다.
- **MKM AI 명명 고정:** MKM은 **4AI core**(태양/소양/태음/소음) + **Absolute Balance Coordinator Mode**로 표기한다. 조율 모드는 상태(state)이며 **제5 AI/체질이 아니다**.
- **LLM Wiki (개인 지식 누적):** 규약 `docs/final/LLM_WIKI_SCHEMA.md` — 작업 트리 `memory/obsidian_vault/llm_wiki/raw/`(불변)·`wiki/`(합성). 코드 구현 팩트와 혼동 금지; 구현 SSOT는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`.
- **Prism 색인 (Grand Indexing 2.0):** 가독 `docs/final/MKM12_GRAND_INDEX_MAP.md`, 머신 레지스트리 `docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json` — 코드 4D 벡터 축과 혼동 금지; 상세 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §14.

### 렌즈 명칭/역할 고정 (크로스 채팅)

- 렌즈는 `사상/명리/성경(Logos)` 3개로만 말한다. `Macro/Regime`는 렌즈명이 아니라 운영 레이어다.
- 역할은 성경=`거시 게이트`, 명리=`중기 방향`, 사상=`단기 강도`로 고정한다.
- A-track 최종 액션은 항상 1차 실물 레짐 + 운영 리스크 게이트가 확정한다. 3렌즈는 보조 입력이다.
- 보고는 `Field → Lens(3개) → Conflict → Final Action` 순서를 고정하고, 성경 렌즈는 `[NON_GATING]` 태그를 유지한다.

### 개발 검증 진입점 (권장)

- **구현 여부·경로 판정**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`와 호출 가능한 `.py`/pytest만 SSOT로 삼는다. 기획·NotebookLM·비전 문서만으로 “이미 구현”을 단정하지 않는다 (**Multi-Lens·격벽·TOE 비단정**: 동 문서 §1.1; **예언·델타·격리 우선순위 [VISION]**: §1.1.1).
- **로컬 Fact-Lock 번들(CI에 가까운 순서)**: 저장소 루트에서 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_fact_lock_bundle.ps1`. 기본에 CI `dual-regime-integrity.yml`과 동일 **Two-track + Multi-symbol**(pytest 6, 생략 `-SkipTwoTrackSubmissionAndMultiSymbolSmoke`)·**Aramaic**(pytest 27, 생략 `-SkipAramaicBtrackGraphPipelineSmoke`). 절차·맥락: `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 하단 “한 번에 돌리는 명령”.
- **Aramaic MVP · Track T survivor health POST 생략 (Windows):** `Register-AramaicMvpDailyTask.ps1 -SurvivorHealthAlertDryRun` 재등록, `run_aramaic_raw_oos_audit_accumulator_v1.ps1 -SurvivorHealthAlertDryRun`, 또는 체인 `run_aramaic_mvp_chain_v1.ps1 -SurvivorHealthAlertDryRun` / 환경 **`MKM_ARAMAIC_SURVIVOR_HEALTH_ALERT_DRY_RUN`** truthy — `Verify-AramaicMvpDailyTaskReadiness.ps1`가 `survivor_health_alert_dry_run_switch_in_task_action`를 출력. SSOT: `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` Aramaic 표·`.env.example`.
- **Control-Integrity Golden/LoRA eval (B-track, 번들 포함):** 동 번들에 pytest 스모크가 **기본 포함**; 로컬에서만 생략 시 `-SkipMkmControlIntegritySmoke`. 헬스 체인만: `scripts/run_workspace_automation_health.ps1 -IncludeMkmControlIntegritySmoke`(단축 `-MkmControlIntegritySmokeOnly`). 표: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.2.1.
- **Track C macro fusion smoke (헬스 선택):** `scripts/run_workspace_automation_health.ps1 -IncludeTrackCMacroFusionSmoke` 또는 단축 `-TrackCMacroFusionSmokeOnly`(Invoke에 `-SkipGateAlert -SkipExodusSourceFetch` 고정). Logos `insight_bundle` 단계 생략: **`-SkipLogosInsightBundle`** 또는 User/머신 **`MKM_HEALTH_FUSION_SKIP_LOGOS_INSIGHT_BUNDLE`** truthy(`1`/`true`/`yes`/`on`). 표: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.3.1.
- **Premium B-track multi-lens report v1 (헬스 선택):** `pwsh scripts/run_workspace_automation_health.ps1 -IncludePremiumBtrackMultilensReportSmoke` 또는 단축 `-PremiumBtrackMultilensReportSmokeOnly`(스키마·빌더 subprocess·큐 스텁·승격 게이트 pytest + **`drain --allow-missing-queue`** + **`build_premium_multilens_queue_promotion_gate_v1.py --skip-pytest`**; CI·Fact-Lock 번들 4b와 동일). 큐 스냅샷+렌즈 포인터(비실행): `premium_multilens_job_queue_stub_v1.py export-pending`. 일상 **프리미엄+큐만:** `Invoke-MkmPersonaHealth_v1.ps1 -Persona PremiumMultilensQueue` → `Invoke-PremiumMultilensQueueRoutine_v1.ps1`(`-ExportPendingJson` 선택; `-SkipPromotionGate`로 게이트 생략). 표: `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` Premium 행. **운영 권장 루틴**(아테나 번들 vs 암행어사 기본)은 루트 **`AGENTS.md`** 「Fact-Lock + 프리미엄 멀티렌즈 권장 루틴」.
- **AI BGM 게이트 v1:** `AGENTS.md` 「로컬 검증 진입점」·`scripts/Run-AudioBgmEconomyChain_v1.ps1`(드라이 선행·선택 `-Live`; 오프라인 톤 `tone_external_generator_v1.py`/드라이 확장+톤 `expand_tone_external_generator_v1.py`/ffmpeg 베드 `ffmpeg_bed_external_generator_v1.py`)·`scripts/audio/check_audio_gate_optional_deps_v1.py`(선택 `--require-all`)·CI `.github/workflows/audio-bgm-gate-smoke.yml`·헌법 헤더 AI BGM 보강.
- **MKM 렌즈 글로벌 프로파일링 프롬프트·RAG 초안 ([DRAFT], B-track)**: `docs/final/MKM_LENS_GLOBAL_PROFILE_PROMPT_RAG_INSTRUCTIONS_DRAFT_V1.md` — 성경·명리·사상 NL 번역층 지시; 상세·표는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §3.3.
- **TruthfulQA A/B (B-track, `research_only`)**: 벤치 `scripts/run_truthfulqa_ab_benchmark_v1.py`, 게이트 `scripts/check_truthfulqa_ab_gate_v1.py`, 재현 `scripts/Run-TruthfulQAReproBundleV1.ps1`; 번들 옵션 `-IncludeTruthfulQaBenchmarkGate`·`-TruthfulQaEvalMcOnly` 등은 `run_fact_lock_bundle.ps1`. 상세 표·경로: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §3.6.
- **보조 번들(Prophecy 정렬)**: `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1`는 해당 디렉터리에서 실행. 워크스페이스 테스트 목록을 CI `dual-regime-integrity`와 맞출 때는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §6 표를 확인한다.
- **하이브리드 포인터 라우팅 체인(연구·PoC):** `py scripts/run_genesis_pointer_routing_control_chain_v1.py --go-cut 0.9 --watch-cut 0.5` → 결정/런타임/shadow/alert/guard/드릴 아티팩트 갱신. 외부 문구는 조건부·아티팩트 근거형만 허용.

### 도메인 핸드오프 (경로·배포, 혼동 방지)

- **로컬 vs VPS 역할 분리 (한 원칙)**: `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md` (**「VPS 배치 (권장)」** = 모노레포 루트 `cwd` + `projects/bitcoin-trading/start_live_trading.py`) · 5줄: `projects/bitcoin-trading/AGENTS.md` · `projects/bitcoin-trading/로컬_VPS_운영원칙.txt`
- **대외 웹·제안서·쇼룸 카피·IP·비밀 비노출:** `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` — 상용·법무 상한은 `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` 와 정합; 구현 팩트는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`만 SSOT.
- **도메인별 쇼룸·랜딩 역할:** `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` §1.1·§1.1b — 전광판·제품·허브 배치 및 **CTA 라벨 초안**; 동 파일 §1 도메인 표와 혼동 금지.
- **jema-ai.com (레포 `projects/no1kmedi`)·mkmlife.com**: `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` — 문서 파일명 `NO1KMEDI`는 레거시; 공개 호칭은 **jema-ai.com**.
- **jema12.com 본선**: `docs/final/SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md`, `docs/final/JEMA12_PUBLIC_DOMAIN_AND_DEPLOY_HANDOFF_2026-04-07.md` (no1kmedi/mkmlife SSOT와 **절차 혼용 금지**.)
- **일반 예언(B 레일, 비가격)**: SSOT는 **모노레포 루트** — `docs/final/GENERAL_PROPHECY_SCHEMA_V1.json`, 체인 `scripts/generate_general_prophecy_v1.py` → `build_general_prophecy_brief.py` → `eval_general_prophecy_brier_score.py`(선택 `--ece-bins`·`--ece-min-per-tag`·`ece_binary_by_domain_tag`), 판정 `scripts/resolve_general_prophecy_question_v1.py`. 월간 러너 `scripts/run_waiting_queue_monthly_check.ps1`에 포함(`-SkipGeneralProphecyChain` 생략 시). **서브트리(예: mkm-life)에 스키마·스크립트를 이중 복제하지 않는다** — 루트 경로만 따른다. **기상 관측 라벨→`general_prophecy` 트리플**(B-track 교정·[HYPO] 전용, 체인 기본 JSONL 검증; `--auto-forecasts-sidecar` 또는 `--forecasts-jsonl`; 합성 120일 벤치 `scripts/run_weather_synthetic_120d_chain_and_brier_v1.py`·eval 기본 `--ece-bins 10`·`--ece-min-per-tag 5`): `scripts/run_weather_gt_to_prophecy_triplet_chain_v1.py`·`docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 해당 단락·루트 `AGENTS.md`.

### B-track 성능 모드 전환 규칙

- B-track에서 분리검증 단계가 끝났거나 유의미한 uplift 신호가 보이면, **탐색 우선 모드**로 즉시 전환한다.
- 기본 실행은 `scripts/run_btrack_full_explore.ps1`를 사용하고, 결과는 `docs/final/artifacts/trackb_full_explore_latest.json`로 확인한다.
- **Track B 주간 semantic/OOV/action-layer/게이트** 원클릭: `scripts/Run-TrackBWeeklyRefresh.ps1` (`-SkipSsmSmoke` / `-SkipCosine` / `-IncludeExtendedStressGrid` 선택); 산출 요약 예시 `docs/final/artifacts/trackb_weekly_formula_utility_report_2026-04-08.md`.
- 과도한 사전 제한으로 탐색을 지연하지 않는다. 안전선은 격벽/재현성/시간·비용 상한으로 최소화한다.
- 성능 비교는 동일 seed/표본 조건에서 수행해 과대해석을 방지한다.
- **B-track → Track A / 압축 승격:** SSOT 체크리스트 `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` §9 + `docs/final/P0_COMMERCIALIZATION_TRACKER.md` 증거 표. OOV·BERTScore·Mamba 등 전방 벤치는 §9 밖 **연구 태스크**로 두고 상용 주장과 합선하지 않는다.
- **LLM 검증 티어:** 벤치·게이트는 **로컬·자체 호스팅 우선**; 상용·대외 품질 확정 전에만 **고급 클라우드 소표본 섀도우** — 동일 파일 `P0_COMMERCIALIZATION_TRACKER.md` **「LLM 검증 티어」**.

### AI-Ops 거버넌스 ↔ 외부 프레임워크 (Miessler 등)

외부에서 말하는 “의도·투명성·자율 개선”은 아래처럼 **이 레포의 운영 팩트**에 대응한다. 외부 수치·수사(예: ‘스캐폴딩 비율’)는 **내부 헌법에 하드코딩하지 않는다.**

| 외부 프레임 (요지) | MKM 아키텍처 (운영 팩트) | 에이전트 실무 체크 |
| --- | --- | --- |
| **Intent-based engineering** | `quality_gate`, `sensitive_integrity_ok` 등 이진 게이트 | 목표가 **통과/실패로 측정 가능**한가? |
| **Transparency** | `docs/final/artifacts/*.json`, exit code, 리포트 체인 | 실패·품질이 **수치·로그·산출 경로**로 남는가? |
| **Autoresearch / 자율 개선** | 연구(B-track)·본선·실거래 **격벽**; `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` | **관측·연구 레일**과 **실거래·프로덕션**이 무단 합선되지 않았는가? |

- 에이전트는 **실거래·본선 트리거를 단독으로 확정하지 않으며**, 측정 가능한 eval·게이트·지휘관 승인 경로에 맡긴다.

## 환경

- **압축 주간 거버넌스(스케줄·갱신 일자 리포트):** `scripts/run_compression_weekly_governance_chain.ps1` → `docs/final/artifacts/compression_weekly_governance_report_latest.json` · `reports/compression_weekly_governance_log.jsonl`; 작업 등록 `scripts/Register-CompressionWeeklyGovernanceTask.ps1`(기본 일요일 07:00).
- **Track A 상용 하네스:** 비용 시뮬 `run_track_a_conversational_cost_simulation.py`, 섀도우 코퍼스 `run_track_a_shadow_corpus_eval.py`, 스텁 계량 `POST /v1/metering/log`·`eval_context.meter_log`, 미터링 집계 `run_track_a_metering_summary.py`(`Run-TrackAMeteringSummary.ps1`)·7일 관측 `run_track_a_metering_weekly_report.py`(`Run-TrackAMeteringWeeklyReport.ps1`)·밴드 게이트 `check_track_a_metering_band_gate.py`·신호등 리포트 `build_track_a_signal_light_report.py`·데일리 체인 `run_track_a_commercialization_daily_chain.ps1`(`Register-TrackACommercializationDailyTask.ps1`·`Verify-TrackACommercializationDailyScheduledTask_v1.ps1`, 기본 `GateMode=warning`), SLA 초안 `docs/final/TRACK_A_SLA_DRAFT.md` — 집계는 `P0_COMMERCIALIZATION_TRACKER.md`.
- **Pre-News Shadow 운영 체인:** 일일 `scripts/run_daily_prophecy_then_pre_news_v1.ps1 -EnablePreNewsShadow -EnablePreNewsShadowWeeklyReport`, 헬스/알림 `scripts/run_pre_news_shadow_health_chain.ps1`, 월간 드릴 `scripts/run_pre_news_shadow_monthly_governance_drills_v1.ps1`; 회귀 고정 CI `.github/workflows/pre-news-shadow-health-smoke.yml`.
- **Git / SSH 재발 방지:** `scripts/Verify-GitWorkspaceSanity.ps1`(`.git/info/exclude`의 `tools/*`·`scripts/*` 무방지 차단, `origin`/upstream 알림; `origin/main` drift는 `-CheckOriginMainSync`) 또는 `scripts/run_workspace_automation_health.ps1 -IncludeGitSanity`(실패 게이트: `-StrictGitSanity`). drift 전용: Linux `scripts/verify_git_origin_main_sync.sh`, 헬스 체인 `-IncludeGitOriginMainSync` / `-StrictGitOriginMainSync`. SSH 터미널 cwd·pull 순서: `docs/final/SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md` §2.0·§2.2.
- **경로**: `C:/workspace` — 주기 점검: `scripts/run_workspace_automation_health.ps1`(Vault는 `MKM_VAULT_ROOT` 또는 G: 마운트 시 미러). **Bio 논문 SNP 사이드카 조인(§8.1, 선택):** 동 스크립트 `-IncludeBioPaperSnpJoinSmoke`(join/apply + sidecar chain CLI + EPMC CLI 3종 pytest) 또는 단축 `-BioSnpOnly`; CI `.github/workflows/bio-paper-snp-sidecar-smoke.yml` 및 `dual-regime-integrity`의 해당 pytest. **Control-Integrity Golden/LoRA(선택, GPU 불필요):** `-IncludeMkmControlIntegritySmoke` 또는 `-MkmControlIntegritySmokeOnly`(§1.2.1). **압축 KPI·투트랙(선택):** 동 스크립트에 `-IncludeCompressionKpi` — 리터럴 트랙은 `-IncludeLiteralTrack`, 연구용 극정밀(ultra-literal)은 `-IncludeUltraLiteralTrack`(시간 증가; `run_compression_automation_chain.ps1` in-process 호출). **E:/F: 역할·중복 감시(선택):** `scripts/Invoke-ExternalDrivesGovernance.ps1` → `reports/drive_governance_latest.json` (용량: `-FullFolderSizesPriorityOnly` 권장, 전체 루트는 `-FullFolderSizes` 매우 느림); 헬스 체인에 포함 시 `-IncludeExternalDriveGovernance`. **`F:\workspace_archive` 오프로드:** `scripts/Migrate-FWorkspaceArchiveToE.ps1` (`-WhatIfSizesOnly`로 해석 경로 확인; E: 전부 거부 시 `C:\workspace\storage\MKM_ARCHIVE_FROM_F` 폴백, 대용량은 `.gitignore`로 제외). **C:/E/F/G 요약(삭제·이동 없음):** `scripts/Invoke-SystemDiskHygieneReport.ps1` → `reports/system_disk_hygiene_latest.json` (용량 이상 시 `-WithWorkspaceFileSumFallback`). **워크스페이스 SLKM+포스트잇 초안:** `scripts/Bootstrap-WorkspaceLayoutRegistry.ps1` → `reports/workspace_layout_registry_bootstrap.json` (`-WithSizesFileSumFallback` 정밀·느림). **C: 여유(안전·실행):** `scripts/Invoke-CWorkspaceSafeCleanup.ps1` (C: 휴지통 + `__pycache__`/pytest 등). **워크스페이스 내부 정리(승인 후):** `scripts/Invoke-WorkspaceDeepCleanup.ps1` (`-RemoveNodeModules` 시 `npm`/`pnpm` 재설치 필요). **프로필 캐시·`.venv`(승인 후):** `scripts/Invoke-ApprovedUserCacheCleanup.ps1` — `bitcoin-trading` 등 `.venv` 삭제 후 `py -m venv .venv`·`pip install -r …` 재실행. **C: 루트 비프로젝트 이동:** `scripts/Move-CNonProjectRootsToE.ps1` — `workspace`·`projects`·`repos` 제외, 기본 `F:\BACKUP\C_ROOT_MIGRATED_FROM_C` (E: mkdir 거부 환경 대비). **압축 KPI 알람(선택):** User `COMPRESSION_KPI_ALARM_WEBHOOK_URL` → 없으면 `OPS_ALARM_WEBHOOK_URL`; 임계치 `docs/final/artifacts/compression_alarm_thresholds_v1.json` — Track A `active_kpi` 기준; 투트랙 정책 `docs/final/COMPRESSION_SLA_POLICY_V1.md` — `P0_COMMERCIALIZATION_TRACKER.md` 압축 절·루트 `.env.example`.
- **Cursor 3.0 (2026-04)**: Agents Window·Design Mode·Agent Tabs — **병렬 에이전트·UI 정밀 피드백**; 헌법·Fact-Lock·TITAN 우선순위는 변경 없음(루트 `.cursorrules`, `AGENTS.md`).
- **Python**: Windows에서는 `py` 사용(프로젝트 규칙과 동일).
- **멀티렌스 P1 / o200k 청구 스파인**: 로컬에서 `evaluate_report`·P1 A/B·관련 pytest를 돌릴 때는 `pip install tiktoken` 필요(CI `dual-regime-integrity` 워크플로에 포함).
- **로컬 비밀·설정 허브**: `C:\workspace\.env`(커밋 금지) — 키 목록·섹션은 `.env.example`; User 환경 변수 반영은 `projects/bitcoin-trading/ops/windows-rehearsal/sync_required_env_to_user.ps1`(bootstrap OPS 동기화와 동일).
- **Ollama·Gemma4**: 구버전에서 `ollama pull` 시 레지스트리 **412** 가능 → 해당 호스트에서 **Ollama 업그레이드** 후 재시도. 로컬·본선 태그 맞춤: **`OLLAMA_MODEL=gemma4:e2b`**(`.env.example` 주석).
- **공유 B-track SSOT(팩트 우선)**: `G:\공유 드라이브\MKM_DATA_VAULT\vault\btrack_artifacts_verified` — 로컬 산출물 동기화: `scripts/push_local_artifacts_to_vault.ps1`
- **NotebookLM / 금융 Hub B 주간 준비(실험 체인)**: `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`를 감싼 `scripts/Invoke-HubBWeeklyMirror.ps1` → 감사 로그 `reports/hub_b_weekly_mirror_log.jsonl` 한 줄·스키마 `hub_b_weekly_mirror_v1`; 주간 작업 등록 `scripts/Register-HubBWeeklyMirrorTask.ps1`(토요일 기본). 클라우드 `source_add`는 별도(MCP/UI). **MCP 설정이 녹색이어도 “이 채팅에 도구 주입”과는 별개** — `.cursor/rules/notebooklm-mcp-session-bridge.mdc`. **웹(내장 브라우저) 로그인 ≠ MCP `setup_auth` 인증**(전용 Chrome 프로필). 점검: `scripts/check_notebooklm_mcp_prereqs.ps1`.
- **B-track Swarm 심리 메트릭**: 더미 + `[HYPO]` 샘플(`docs/final/hypo_test_sentiment.jsonl`) 일괄 검증 `scripts/Validate-SwarmSentimentBTrack.ps1`; 단일 `py scripts/validate_swarm_sentiment_dummy.py [--jsonl …]`; CI `.github/workflows/swarm-sentiment-schema-validate.yml`.
- **B-track 소셜 원천(격리)**: Bluesky/ATProto 샘플 수집 `scripts/test_atproto_bluesky_bridge.py` (`--dry-run`으로 의존성·경로만 확인; 실수집은 `BSKY_HANDLE`·`BSKY_APP_PASSWORD`). 출력은 `memory/v2/btrack/raw_feeds/atproto/` — 스키마 정규화·MiroFish는 별도 단계·본선 합선 금지.
- **어휘 계약**: `docs/final/MASTER_Linguistic_Contract_2026.md` — 외부 사전 수신: `scripts/setup/fetch_external_lexicons.ps1`, 승격: `scripts/push_external_lexicon_to_vault.ps1`

## 더 읽을 때

- 상용화·작업 순서: `docs/final/P0_COMMERCIALIZATION_TRACKER.md` (해당 작업 시). no1kmedi/mkmlife **경로·VPS·Hostinger 수동 배포**는 `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md`.
- 에이전트 역할 요약: 루트 `AGENTS.md`.
- 압축·해석 Fact-Lock + 투트랙 SLA: `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`, `docs/final/COMPRESSION_SLA_POLICY_V1.md`.
- **Gemini MCP vs 배치 CLI 라우팅·비용 통제**: 루트 `AGENTS.md` 섹션 **「Gemini 멀티모달: MCP vs 배치 CLI」**.
