# CLAUDE.md — Cursor/Claude용 마스터 컨텍스트 (슬림)

**목적**: 세션 초기에 **한 화면**으로 방향을 맞춘다. 장문 가이드는 각 규칙·문서에 둔다.

## 에이전트 동작

- **TITAN**: 루트 `.cursorrules` 최상단 — 자율 기동, **이항 선택([A]/[B]) 강요 금지**, 고위험만 승인 요청.
- **중앙 지휘부 규칙**: `.cursor/rules/sovereign-central-command.mdc` (`alwaysApply`).
- **코드/추론 “구현 여부”**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 를 호출 가능한 `.py`와 대조한다. **Multi-Lens·TOE 비단정**은 동 문서 §1.1. **Windows OPS Phase 1 체인·리포트·운영/연구 레인**은 §13.1 (`verify_constitution_gates.ps1`, `constitution_gates_v1.json`, `bootstrap_ops_phase1_daily.ps1`, `verify_ops_phase1_operational_readiness.ps1`)·루트 `AGENTS.md`.
- **12AI vs 코드북**: **12AI**는 Cursor 작업 라우팅용 오케스트레이션 라벨이며, 코드북 도메인·샤드 개수와 **1:1로 묶지 않는다.** (보통 복잡·고위험 작업만 2~4 전문 에이전트로 분산.) 상세: 루트 `AGENTS.md`, `.cursor/skills/auto-12ai-routing/SKILL.md`.
- **LLM Wiki (개인 지식 누적):** 규약 `docs/final/LLM_WIKI_SCHEMA.md` — 작업 트리 `memory/obsidian_vault/llm_wiki/raw/`(불변)·`wiki/`(합성). 코드 구현 팩트와 혼동 금지; 구현 SSOT는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`.
- **Prism 색인 (Grand Indexing 2.0):** 가독 `docs/final/MKM12_GRAND_INDEX_MAP.md`, 머신 레지스트리 `docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json` — 코드 4D 벡터 축과 혼동 금지; 상세 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §14.

### 개발 검증 진입점 (권장)

- **구현 여부·경로 판정**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`와 호출 가능한 `.py`/pytest만 SSOT로 삼는다. 기획·NotebookLM·비전 문서만으로 “이미 구현”을 단정하지 않는다 (**Multi-Lens·격벽·TOE 비단정**: 동 문서 §1.1).
- **로컬 Fact-Lock 번들(CI에 가까운 순서)**: 저장소 루트에서 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_fact_lock_bundle.ps1`. 절차·맥락: `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 하단 “한 번에 돌리는 명령”.
- **보조 번들(Prophecy 정렬)**: `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1`는 해당 디렉터리에서 실행. 워크스페이스 테스트 목록을 CI `dual-regime-integrity`와 맞출 때는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §6 표를 확인한다.

### 도메인 핸드오프 (경로·배포, 혼동 방지)

- **로컬 vs VPS 역할 분리 (한 원칙)**: `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md` (**「VPS 배치 (권장)」** = 모노레포 루트 `cwd` + `projects/bitcoin-trading/start_live_trading.py`) · 5줄: `projects/bitcoin-trading/AGENTS.md` · `projects/bitcoin-trading/로컬_VPS_운영원칙.txt`
- **no1kmedi / mkmlife.com**: `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md`
- **jema12.com 본선**: `docs/final/SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md`, `docs/final/JEMA12_PUBLIC_DOMAIN_AND_DEPLOY_HANDOFF_2026-04-07.md` (no1kmedi/mkmlife SSOT와 **절차 혼용 금지**.)

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
- **Track A 상용 하네스:** 비용 시뮬 `run_track_a_conversational_cost_simulation.py`, 섀도우 코퍼스 `run_track_a_shadow_corpus_eval.py`, 스텁 계량 `POST /v1/metering/log`·`eval_context.meter_log`, 미터링 집계 `run_track_a_metering_summary.py`(`Run-TrackAMeteringSummary.ps1`)·7일 관측 `run_track_a_metering_weekly_report.py`(`Run-TrackAMeteringWeeklyReport.ps1`)·밴드 게이트 `check_track_a_metering_band_gate.py`·신호등 리포트 `build_track_a_signal_light_report.py`·데일리 체인 `run_track_a_commercialization_daily_chain.ps1`(`Register-TrackACommercializationDailyTask.ps1`, 기본 `GateMode=warning`), SLA 초안 `docs/final/TRACK_A_SLA_DRAFT.md` — 집계는 `P0_COMMERCIALIZATION_TRACKER.md`.
- **Git / SSH 재발 방지:** `scripts/Verify-GitWorkspaceSanity.ps1`(`.git/info/exclude`의 `tools/*`·`scripts/*` 무방지 차단, `origin`/upstream 알림; `origin/main` drift는 `-CheckOriginMainSync`) 또는 `scripts/run_workspace_automation_health.ps1 -IncludeGitSanity`(실패 게이트: `-StrictGitSanity`). drift 전용: Linux `scripts/verify_git_origin_main_sync.sh`, 헬스 체인 `-IncludeGitOriginMainSync` / `-StrictGitOriginMainSync`. SSH 터미널 cwd·pull 순서: `docs/final/SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md` §2.0·§2.2.
- **경로**: `C:/workspace` — 주기 점검: `scripts/run_workspace_automation_health.ps1`(Vault는 `MKM_VAULT_ROOT` 또는 G: 마운트 시 미러). **압축 KPI·투트랙(선택):** 동 스크립트에 `-IncludeCompressionKpi` — 리터럴 트랙은 `-IncludeLiteralTrack`, 연구용 극정밀(ultra-literal)은 `-IncludeUltraLiteralTrack`(시간 증가; `run_compression_automation_chain.ps1` in-process 호출). **E:/F: 역할·중복 감시(선택):** `scripts/Invoke-ExternalDrivesGovernance.ps1` → `reports/drive_governance_latest.json` (용량: `-FullFolderSizesPriorityOnly` 권장, 전체 루트는 `-FullFolderSizes` 매우 느림); 헬스 체인에 포함 시 `-IncludeExternalDriveGovernance`. **`F:\workspace_archive` 오프로드:** `scripts/Migrate-FWorkspaceArchiveToE.ps1` (`-WhatIfSizesOnly`로 해석 경로 확인; E: 전부 거부 시 `C:\workspace\storage\MKM_ARCHIVE_FROM_F` 폴백, 대용량은 `.gitignore`로 제외). **C:/E/F/G 요약(삭제·이동 없음):** `scripts/Invoke-SystemDiskHygieneReport.ps1` → `reports/system_disk_hygiene_latest.json` (용량 이상 시 `-WithWorkspaceFileSumFallback`). **워크스페이스 SLKM+포스트잇 초안:** `scripts/Bootstrap-WorkspaceLayoutRegistry.ps1` → `reports/workspace_layout_registry_bootstrap.json` (`-WithSizesFileSumFallback` 정밀·느림). **C: 여유(안전·실행):** `scripts/Invoke-CWorkspaceSafeCleanup.ps1` (C: 휴지통 + `__pycache__`/pytest 등). **워크스페이스 내부 정리(승인 후):** `scripts/Invoke-WorkspaceDeepCleanup.ps1` (`-RemoveNodeModules` 시 `npm`/`pnpm` 재설치 필요). **프로필 캐시·`.venv`(승인 후):** `scripts/Invoke-ApprovedUserCacheCleanup.ps1` — `bitcoin-trading` 등 `.venv` 삭제 후 `py -m venv .venv`·`pip install -r …` 재실행. **C: 루트 비프로젝트 이동:** `scripts/Move-CNonProjectRootsToE.ps1` — `workspace`·`projects`·`repos` 제외, 기본 `F:\BACKUP\C_ROOT_MIGRATED_FROM_C` (E: mkdir 거부 환경 대비). **압축 KPI 알람(선택):** User `COMPRESSION_KPI_ALARM_WEBHOOK_URL` → 없으면 `OPS_ALARM_WEBHOOK_URL`; 임계치 `docs/final/artifacts/compression_alarm_thresholds_v1.json` — Track A `active_kpi` 기준; 투트랙 정책 `docs/final/COMPRESSION_SLA_POLICY_V1.md` — `P0_COMMERCIALIZATION_TRACKER.md` 압축 절·루트 `.env.example`.
- **Cursor 3.0 (2026-04)**: Agents Window·Design Mode·Agent Tabs — **병렬 에이전트·UI 정밀 피드백**; 헌법·Fact-Lock·TITAN 우선순위는 변경 없음(루트 `.cursorrules`, `AGENTS.md`).
- **Python**: Windows에서는 `py` 사용(프로젝트 규칙과 동일).
- **멀티렌스 P1 / o200k 청구 스파인**: 로컬에서 `evaluate_report`·P1 A/B·관련 pytest를 돌릴 때는 `pip install tiktoken` 필요(CI `dual-regime-integrity` 워크플로에 포함).
- **로컬 비밀·설정 허브**: `C:\workspace\.env`(커밋 금지) — 키 목록·섹션은 `.env.example`; User 환경 변수 반영은 `projects/bitcoin-trading/ops/windows-rehearsal/sync_required_env_to_user.ps1`(bootstrap OPS 동기화와 동일).
- **Ollama·Gemma4**: 구버전에서 `ollama pull` 시 레지스트리 **412** 가능 → 해당 호스트에서 **Ollama 업그레이드** 후 재시도. 로컬·본선 태그 맞춤: **`OLLAMA_MODEL=gemma4:e2b`**(`.env.example` 주석).
- **공유 B-track SSOT(팩트 우선)**: `G:\공유 드라이브\MKM_DATA_VAULT\vault\btrack_artifacts_verified` — 로컬 산출물 동기화: `scripts/push_local_artifacts_to_vault.ps1`
- **NotebookLM / 금융 Hub B 주간 준비(실험 체인)**: `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`를 감싼 `scripts/Invoke-HubBWeeklyMirror.ps1` → 감사 로그 `reports/hub_b_weekly_mirror_log.jsonl` 한 줄·스키마 `hub_b_weekly_mirror_v1`; 주간 작업 등록 `scripts/Register-HubBWeeklyMirrorTask.ps1`(토요일 기본). 클라우드 `source_add`는 별도(MCP/UI). **MCP 설정이 녹색이어도 “이 채팅에 도구 주입”과는 별개** — `.cursor/rules/notebooklm-mcp-session-bridge.mdc`.
- **B-track Swarm 심리 메트릭**: 더미 + `[HYPO]` 샘플(`docs/final/hypo_test_sentiment.jsonl`) 일괄 검증 `scripts/Validate-SwarmSentimentBTrack.ps1`; 단일 `py scripts/validate_swarm_sentiment_dummy.py [--jsonl …]`; CI `.github/workflows/swarm-sentiment-schema-validate.yml`.
- **B-track 소셜 원천(격리)**: Bluesky/ATProto 샘플 수집 `scripts/test_atproto_bluesky_bridge.py` (`--dry-run`으로 의존성·경로만 확인; 실수집은 `BSKY_HANDLE`·`BSKY_APP_PASSWORD`). 출력은 `memory/v2/btrack/raw_feeds/atproto/` — 스키마 정규화·MiroFish는 별도 단계·본선 합선 금지.
- **어휘 계약**: `docs/final/MASTER_Linguistic_Contract_2026.md` — 외부 사전 수신: `scripts/setup/fetch_external_lexicons.ps1`, 승격: `scripts/push_external_lexicon_to_vault.ps1`

## 더 읽을 때

- 상용화·작업 순서: `docs/final/P0_COMMERCIALIZATION_TRACKER.md` (해당 작업 시). no1kmedi/mkmlife **경로·VPS·Hostinger 수동 배포**는 `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md`.
- 에이전트 역할 요약: 루트 `AGENTS.md`.
- 압축·해석 Fact-Lock + 투트랙 SLA: `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`, `docs/final/COMPRESSION_SLA_POLICY_V1.md`.
- **Gemini MCP vs 배치 CLI 라우팅·비용 통제**: 루트 `AGENTS.md` 섹션 **「Gemini 멀티모달: MCP vs 배치 CLI」**.
