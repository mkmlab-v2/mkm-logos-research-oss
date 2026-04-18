# AGENTS — 워크스페이스 에이전트 SSOT 포인터

**역할**: Cursor/Athena 에이전트가 먼저 읽는 **짧은 진입점**이다. 상세 규칙은 아래 파일이 주도한다.

## 중앙 메모리 (크로스 채팅 정체성)

- **지속 SSOT:** `docs/final/CENTRAL_AGENT_MEMORY_V1.md` — Athena 정체성·격벽·Fact-Lock·「분기별 한 줄」.
- **자동 주입:** `.cursor/rules/central-agent-memory.mdc` (`alwaysApply`)에 **SSOT 핵심 5줄**이 매 에이전트 턴 컨텍스트에 포함된다. `@` 없이도 원칙 정렬은 가능하다.
- **한계:** 채팅 로그는 세션 간 공유되지 않는다. “지난 작업” 맥락은 **본 파일·커밋**으로 누적한다. 표 전체·깊은 동기화가 필요하면 작업 시작 시 `@docs/final/CENTRAL_AGENT_MEMORY_V1.md` 또는 에이전트 `Read`를 쓴다.

## 세션 핸드오프 (선택)

새 채팅에서 직전 작전의 팩트만 이어 붙일 때 `@docs/final/CURRENT_OPS_SNAPSHOT.md`를 첨부한다. **불변 SSOT가 아니며** 필요 시 갱신·비운다. 압축 파이프라인(A/B Track)과 역할을 섞지 않는다.

다단계 임무의 **종료 조건·로컬 체크리스트**만 디스크에 남길 때는 `MISSION_LOG.template.md` → **`MISSION_LOG.md`**(로컬 전용,`.gitignore`). **작전 요약·세션 핸드오프**는 `docs/final/CURRENT_OPS_SNAPSHOT.md`가 우선이며, 동일 SSOT를 스냅샷과 `MISSION_LOG`에 **이중 서술하지 않는다**. 순서·상용 게이트 SSOT는 `P0_COMMERCIALIZATION_TRACKER.md`이다.

## 필수 우선순위

1. **루트 `.cursorrules`** — 최상단 **TITAN · 자율 기동(Command-by-Negation)**. 예외가 아니면 권장 조치를 질문 없이 수행·사후 보고; 끝맺음은 [A]/[B] 선택 강요 없이 **완료 보고 + 잔여 리스크(있을 때만)**.
   - 실무 해석 고정: 명시적 STOP/승인 필요 예외(파괴적 삭제·실거래·비용 유발·비가역 근본 변경) 외에는 파일 편집/터미널/검증을 자율 연속 수행한다.
   - 모호성 처리 고정: 저위험 모호성은 질문 대신 합리적 기본값으로 구현/검증 후 사후 보고한다.
2. **`.cursor/rules/sovereign-central-command.mdc`** — Vault·NotebookLM·보안·운영(3문장 요약 + **§4 마무리**). §4에서 **폐지**: “Next Action 2가지”, `[A]`/`[B]`·a/b 강요. **대체**: TITAN 마무리 또는 고위험 시 **승인 범위만** 명시(루트 `.cursorrules`와 동일 방향).
3. **구현 팩트(환각 차단)**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` — 기획·NotebookLM만 보고 “이미 구현” 단정 금지. P0·헌법 핵심 경로 존재 여부: `scripts/verify_p0_constitution_gate_paths.ps1`.
4. **Prism 색인 (논리 레이어, 선택)**: 물리 이동 없이 경로·역할만 묶은 **Grand Indexing 2.0** — `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` **§14**, 가독 색인 초안 `docs/final/MKM12_GRAND_INDEX_MAP.md`, 중앙 레지스트리 `docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json`. 코드 4D 벡터 축 `(S,L,K,M)`과 혼동하지 말 것.
5. **정체성 (Multi-Lens):** 단일 TOE·통일장 “완성” 선언 금지 — §1.1. 레짐·로고스·명리·외경은 **격벽·교차 참고** (§2.1·§4).
6. **Cursor Cloud Sandbox · 본선 분리:** Cloud Agent/Sandbox는 검증·병렬 가속 전용; 실매매·프로덕션 쓰기·실키 주입은 로컬/VPS 본선과 분리. 상세 `.cursor/rules/cursor-cloud-sandbox-boundary.mdc`.

## 로컬 검증 진입점 (개발·PR 전 권장)

- **만세력 Phase B 스모크 (Meeus vs Swiss 立春 Reference B + 59-case ganji 코호트 + 충돌 사전 네이티브 검증):** `python scripts/run_manseryeok_validation_smoke_v1.py` (B-2만: `--skip-ephemeris`; 충돌 생략: `--skip-collision-dict`). 단독: `python scripts/validate_collision_dictionary_v1.py`. CI: **`main` 푸시마다** + 경로 맞는 PR + 수동 — `.github/workflows/manseryeok-validation-smoke.yml`. 대조 템플릿·채집 절차: `docs/final/artifacts/manseryeok_collision_dictionary_v1.json` (`collection_howto`).
- **구현 판정**은 (3)의 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`와 호출 가능 스크립트·테스트로만 한다. 브리핑·노트만으로 경로를 확정하지 않는다.
- **번들 한 방**: `scripts/run_fact_lock_bundle.ps1` — 루트에서 실행; 맥락·완료 정의는 `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 하단.
- **보조**: `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1` (bitcoin-trading 디렉터리에서). CI 정합은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §6.
- **LLM 검증 티어:** 기본은 **로컬·자체 호스팅 모델**로 게이트·벤치; 상용·대외 품질 확정 전에만 **고급 클라우드 모델 소표본 섀도우**(드리프트 방지). 상세: `docs/final/P0_COMMERCIALIZATION_TRACKER.md` **「LLM 검증 티어」**.

## Cursor 3.0 · 규칙 스택 (2026-04)

- **제품**: Cursor 3 — **Agents Window**(로컬·워크트리·클라우드·SSH 병렬 에이전트), **Design Mode**(브라우저 UI 타겟), **Agent Tabs**(다중 채팅). IDE 명령 팔레트에서 “Agents Window” 등(공식 Changelog 2026-04-02).
- **워크스페이스 규칙(SSOT)**: 루트 `.cursorrules`, `.cursor/rules/*.mdc`, 본 `AGENTS.md`, `CLAUDE.md`, `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` — **Git으로 버전 관리**.
- **User Rules**: Cursor **Settings → Rules**에만 있는 문구는 **레포에 자동 동기화되지 않음**; 팀·본선 기준은 반드시 위 SSOT 파일에 반영한다.

## 로컬 Cursor vs SSH VPS (한 원칙)

- **SSOT**: `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md` — 코드·규칙은 **로컬에서만 편집·푸시**; VPS는 **`git pull` + 런북의 재시작/배포만**; 비밀은 **`.env`를 호스트마다** (Git 비추적). bitcoin-trading 본선 **권장 배치**는 동 문서 **「VPS 배치 (권장)」** — 모노레포 루트를 **PM2 `cwd`**, **`projects/bitcoin-trading/start_live_trading.py`** 진입.
- **bitcoin-trading 운영 5줄:** `projects/bitcoin-trading/AGENTS.md` · `projects/bitcoin-trading/로컬_VPS_운영원칙.txt` — **`pm2 restart <이름>`만**, **`restart all` 금지**(런북 예외만), **VPS 직수정 → 레포로 되돌리기**, `.env` 위치는 팀 규칙 한 곳.

## 압축 파이프라인 투트랙 (Fact-Lock 요약)

- **정책**: `docs/final/COMPRESSION_SLA_POLICY_V1.md` — Track A(범용)·Track B(리터럴), 산출 JSON, 손실 패턴 리포트, 웹훅은 `active_kpi`(Track A) 기준.
- **실행**: `scripts/run_ultra_compression_default.py` / `--mode literal` / `--mode ultra-literal`(연구·극정밀); `scripts/run_compression_automation_chain.ps1 -IncludeLiteralTrack` / `-IncludeUltraLiteralTrack`; 헬스: `scripts/run_workspace_automation_health.ps1 -IncludeCompressionKpi [-IncludeLiteralTrack]`(체인은 in-process 호출).
- **주간 거버넌스(갱신 일자 리포트)**: `scripts/run_compression_weekly_governance_chain.ps1` → SSOT `docs/final/artifacts/compression_weekly_governance_report_latest.json`, 동일 페이로드의 일자 파일 `compression_weekly_governance_report_YYYY-MM-DD.json`(UTC·로컬/스케줄러; `.gitignore`로 날짜별 파일은 저장소 비추적), 로그 `reports/compression_weekly_governance_log.jsonl`. Windows 작업 스케줄 등록: `scripts/Register-CompressionWeeklyGovernanceTask.ps1` (기본 일요일 07:00; `-Remove`로 해제).
- **Track A 상용화 하네스(시뮬·섀도우·계량·SLA 초안):** `run_track_a_conversational_cost_simulation.py` · `run_track_a_shadow_corpus_eval.py` / `Run-TrackAShadowJsonlSample.ps1` · `compression_token_api_stub.py`의 `POST /v1/metering/log`·`eval_context.meter_log`·`run_track_a_metering_summary.py` (`Run-TrackAMeteringSummary.ps1`)·`run_track_a_metering_weekly_report.py` (`Run-TrackAMeteringWeeklyReport.ps1`)·`check_track_a_metering_band_gate.py`·`build_track_a_signal_light_report.py`·`run_track_a_commercialization_daily_chain.ps1` (`Register-TrackACommercializationDailyTask.ps1`, 기본 `GateMode=warning`) · `docs/final/TRACK_A_SLA_DRAFT.md` — 상세·경로는 `docs/final/P0_COMMERCIALIZATION_TRACKER.md` 압축·L2 절.
- **해석 파이프라인**: `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` — NotebookLM·브리핑은 **참고**; 구현·KPI는 스크립트·산출물만 SSOT.
- **Multilens P1 A/B**: 본선 갱신 `py scripts/run_multilens_p1_production_chain.py`(또는 `scripts/Run-MultilensP1ProductionChain.ps1`); B-track 샌드박스 `py scripts/run_multilens_p1_btrack_chain.py`(또는 `Run-MultilensP1BTrackSuite.ps1`, `-IncludeBalancedWeightsSweep` 선택). 명령만 확인: `--dry-run`; JSON 실행 계획만 출력: `--json-plan`(서브프로세스 미실행, schema `multilens_p1_chain_plan_v1`).

## 도메인 핸드오프(참고)

- **jema12.com 본선(SSH Cursor)**: `docs/final/SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md` — 원격 워크스페이스에서 `git pull` → `scripts/deploy/linux/apply_jema12_nginx_snippet.sh` · 검증 스크립트 경로. 도메인·스냅샷: `docs/final/JEMA12_PUBLIC_DOMAIN_AND_DEPLOY_HANDOFF_2026-04-07.md`.
- **no1kmedi / mkmlife.com 경로·VPS PM2·Hostinger 수동 배포**: `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` — 로컬 `C:\workspace` 트리와 분리된 `E:\workspace\mkm-life\deploy-to-hostinger.ps1` 등 **실측 경로** 정리; **UI 면책 배지·컴포넌트/폴백 초안**은 동 문서 **§10**(`§10.3` 부록). jema12 런북과 혼용 금지.
- **다도메인 포트폴리오·미확정(jema-ai.com, personadiary.com 등):** `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` — 표·NotebookLM 기준; 전용 포인터 `JEMA_AI_DOMAIN_POINTER_V1.md`, `PERSONADIARY_DOMAIN_POINTER_V1.md`.
- **일반 예언(B 레일)**: 스키마·스크립트·월간 체인은 **저장소 루트**(`GENERAL_PROPHECY_SCHEMA_V1`, `scripts/generate_general_prophecy_v1.py` 등, `run_waiting_queue_monthly_check.ps1`) — **별도 서브트리에 복제본을 두지 않고** 루트 SSOT를 따른다.
- 한의 원전·코호트: `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` (라벨 A vs 원전 B 혼선 금지).
- NotebookLM 소스: `docs/NotebookLM_sources_manifest.md`.
- **NotebookLM MCP (재발방지)**: Settings에서 녹색·N tools여도 **현재 채팅에 도구가 주입되지 않으면** 에이전트는 호출 불가 — UI 연결 ≠ 세션 사용 가능. SSOT: `.cursor/rules/notebooklm-mcp-session-bridge.mdc`, 스킬 `.cursor/skills/notebooklm-refresh/SKILL.md` §세션 vs UI.

## 운영 자동화 vs 연구 레인

- **본선 OPS** (`projects/bitcoin-trading/ops/windows-rehearsal`, `verify_all_green`, `automation_registry.json`): **관측·스케줄·게이트** 전용. 헌법·백서를 LLM이 매 실행마다 해석해 본선을 바꾸는 **자율 전략 엔진**으로 단정하지 않는다. 구현 여부는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 호출 가능 스크립트로만 말한다.
- **Phase 1 통합 리포트 SSOT**: `projects/bitcoin-trading/memory/v2/ops/ops_phase1_chain_report_latest.json` — **exit_code·타임스탬프·산출 경로** 중심. 브리핑 전용 필드(예: `go_no_go`)는 **레포 산출물에 없으면** 근거 없는 수치로 쓰지 않는다.
- **헌법 게이트(옵션)**: `run_ops_phase1_chain.ps1 -IncludeConstitutionGates` → `verify_constitution_gates.ps1` → `projects/bitcoin-trading/memory/v2/ops/constitution_gates_result_latest.json`; allowlist `constitution_gates_v1.json`. 상세 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §13.1.
- **Phase 1 일일 원클릭**: `projects/bitcoin-trading/ops/windows-rehearsal/bootstrap_ops_phase1_daily.ps1` — User 환경 동기화 후 `\Bitcoin-Ops-Phase1-Chain-Daily` 등록(헌법 게이트 기본 켬). 점검·웹훅 스모크: `-IncludeReadiness`, `-IncludeWebhookSmoke`.
- **MKM Study**(예: `projects/mkm/mkm-study`): **연구·프로토타입·학습** 레인. 실매매·본선 OOF·올그린 게이트와 **자동 합선하지 않는다** (NotebookLM·A/B 격벽과 동일 방향).

## B-track 실행 기본값 (탐색 우선)

- **기본 모드**: B-track은 보수 게이트 우선이 아니라 **성능 탐색 우선**으로 운영한다.
- **원클릭 진입점**: `scripts/run_btrack_full_explore.ps1`를 기본 실행 경로로 사용한다.
- **최소 안전선만 유지**: `B-track 아티팩트 경로`, `재현 seed 기록`, `시간/비용 상한`, `A-track 자동 합선 금지`.
- **전환 규칙**: 유망 uplift가 확인되면(예: short-bucket 개선) 동역학 결합 모델까지 포함해 즉시 비교 벤치를 확장한다.
- **금지**: B-track 실험 결과를 승인 없이 실거래/프로덕션 게이트에 자동 반영하지 않는다.
- **승격 (압축·복원 연구 → 상용/프로덕션 주장):** `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` §9 + `docs/final/P0_COMMERCIALIZATION_TRACKER.md` — `projects/bitcoin-trading/docs/final/STAGING_TO_PRODUCTION_PROMOTION_CHECKLIST_2026-03-25.md`(거래 스테이징)와 **절차·범위 혼동 금지**.
- **Track B 주간 메트릭·게이트(연구 레인, 압축 엔진과 별도)**: `scripts/Run-TrackBWeeklyRefresh.ps1` — 도메인 쌍·semantic(Jaccard/cosine_tokens)·`build_trackb_semantic_eval_by_domain.py`·OOV 스윕·action layer·결정성·선택 상태 시뮬·`trackb_weekly_gate_recheck_latest.json` 등. `-SkipSsmSmoke` / `-SkipCosine` / `-IncludeExtendedStressGrid`(확장 Length/OOV 스트레스, 시간 증가) 선택; 요약 MD 예시 `docs/final/artifacts/trackb_weekly_formula_utility_report_2026-04-08.md`.

## 12AI vs 코드북 도메인

- **12AI**는 Cursor 작업 라우팅용 **오케스트레이션 라벨**이다. 코드북 **도메인·샤드 개수**(파일럿 4존부터 확장 등)와 **1:1로 묶지 않는다.**
- 복잡·고위험 작업만 전문 서브에이전트로 분산하며, 보통 **2~4** 범위가 권장이다. 상세: `.cursor/skills/auto-12ai-routing/SKILL.md`.

## 경로

- **LLM Wiki (Karpathy 패턴, 로컬 누적):** 규약 `docs/final/LLM_WIKI_SCHEMA.md` — 원본 `memory/obsidian_vault/llm_wiki/raw/` (불변), 합성 `memory/obsidian_vault/llm_wiki/wiki/`. 실행 런타임은 기본 **Cursor**; 별도 로컬 에이전트 앱 필수 아님.
- 작업 루트: `C:/workspace` (Windows). Python 실행은 `py` 권장.
- **B-track 파일럿 벤치 SSOT:** `data/logos/btrack_pilot/bench/CANONICAL_BENCH_POINTER_V1.json` — 공식 의도 벤치는 포인터의 `canonical_builder_script`가 갱신하는 `a_track_eval.jsonl` / `b_track_eval.jsonl` 슬롯이다. direct·cross_ref 부트스트랩 빌더는 기본적으로 `*_direct_v1.jsonl` / `*_cross_ref_bootstrap_v1.jsonl`에 쓰며 canonical을 덮어쓰지 않는다. 경로 상수: `tools/myeongni/btrack_bench_paths.py`.
- **Git 로컬 exclude 주의:** `.git/info/exclude`에 `tools/`·`scripts/` 등으로 디렉터리 **전체**를 막으면 하위 추적 파일이 조용히 제외된다. 필요 시 `tools/*` + `!tools/myeongni/**`, `scripts/*` + `!scripts/**`처럼 내용만 막고 트리는 예외로 되돌리거나, 해당 줄을 제거한다(원격 `.gitignore`에는 루트 `tools/`·`scripts/` 무시 규칙이 없음).
- **만세력 정밀(제2계층) SSOT 포인터:** `docs/final/MANSE_PRECISION_RUNTIME_POINTER_V1.json` — 에이전트 공식 배선은 Path B(MCP stdio, `athena-manseryeok`); 배치는 동일 엔진·per-row MCP 금지는 포인터 참조; 구현 팩트 표는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §3.4.
- 공유 SSOT 확인 경로(1순위): `G:\공유 드라이브\MKM_DATA_VAULT\vault\btrack_artifacts_verified` (미존재 시 `...\vault` 하위 경로 확인).
- B-track 핵심 산출물 승격(로컬 `reports/...` → G:): `scripts/push_local_artifacts_to_vault.ps1`
- 어휘·코퍼스 FACT-LOCK 계약: `docs/final/MASTER_Linguistic_Contract_2026.md` — 외부 사전 스테이징 `C:\workspace\vault\external_lexicon` → G: `...\vault\external_lexicon`: `scripts/setup/fetch_external_lexicons.ps1` (수신·MANIFEST) 후 `scripts/push_external_lexicon_to_vault.ps1` (승격)

## Gemini 멀티모달: MCP vs 배치 CLI (교전 수칙)

**목적**: 대화형(MCP)과 자동화(배치)의 **역할 분리**와 **비용·지연 통제**. 동일 질문을 MCP와 배치로 **중복 호출하지 않는다.**

| 상황 | 사용 |
|------|------|
| Cursor 안에서 즉시 판단, 파일 첨부·멀티턴, 에이전트가 도구로 호출 | **Google AI Studio MCP** (`aistudio-mcp`, `generate_content` 계열) |
| 스케줄러·CI·디스크에 결과 저장·재현·키 없는 회귀 | **`scripts/gemini_multimodal_batch.py`** (`research` / `image` / `crosscheck` / `check`). 래퍼: `scripts/Invoke-GeminiMultimodalBatch.ps1` |
| SDK·환경만 점검(API 호출 없음) | `py scripts/gemini_multimodal_batch.py check` |

**화력 통제(배치·MCP 공통)**: Google Search·코드 실행·Thinking(또는 장시간 추론)은 **기본 전부 켜지 말 것**. 배치에서는 `--google-search` / `--code-execution` / `--thinking-budget`를 **필요할 때만** 지정한다. 장시간·대용량 입력은 `--timeout`으로 상한을 둔다.

**인증**: `GEMINI_API_KEY`(우선)·`GOOGLE_API_KEY`. 키는 저장소·채팅에 넣지 않는다.

**CI**: `.github/workflows/gemini-multimodal-batch-cli.yml` — 키 없이 `check` + `pytest tests/test_gemini_multimodal_batch_cli.py`.

**권장 경로(운영 고정)**: 배치 이미지 저장은 `reports/gemini_batch/out/` (`image --out-dir ...`). PDF·원본 드롭은 작업별로 `reports/gemini_batch/in/` 등 하위에 두고, 대용량·민감 파일은 Git에 올리지 않는다.

**환경 변수**: `GEMINI_API_KEY`만 쓸 경우 **사용자 환경 변수의 `GOOGLE_API_KEY`(레거시)** 를 비우면 google-genai 경고가 줄어든다.

**월간 브리프(선택)**: `scripts/run_waiting_queue_monthly_check.ps1` — `docs/final/P0_COMMERCIALIZATION_TRACKER.md` 월간 루틴. 산출물·JSONL·로그 **대량 갱신**·**장시간** 가능하므로 **필요 시 수동 실행**; 자동 스케줄은 지휘관 환경에 맞게 별도 설정.

## Logos 메타·리추얼 (12AI: Logos Sage 메타데이터 / 격벽)

- **레지스트리 SSOT:** `data/logos/meta/manifest.json` — `VERSE_MAPPING_RITUAL_*` 등 리추얼 메타 경로·`role_tags`·`is_quant_isolated`.
- **보안 규정:** Logos 리추얼 메타데이터는 `data/logos/meta/manifest.json` 대장을 통해 `RITUAL_MODE` 세션에서만 제한적으로 로드되며, MKM Quant의 실거래 타격 파이프라인과는 물리적/논리적으로 완벽히 격리(Air-gapped)된다.

- **픽셀 부대 · Night Watchman 마감 점검:** `scripts/PIXEL_BATTALION_NIGHT_WATCHMAN_CHECKLIST.md` — Hostinger/CDN, `PIXEL_BATTALION_BASE_URL`, `build_pixel_battalion_public_map.py`, `send_night_watchman_character_alert.py` 검증 순서.

## jemaai.cloud · 공개 쇼룸 vs 실매매 관제

- **하이브리드 대시보드 스펙(SSOT):** `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md` — 공개(전광판) vs 비공개(조종실), `public-event.v1` 필드·경계선.
- **MVP 게이트웨이:** `public_event_gateway.py` — `GET/POST` 경로·토큰은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 동 디렉터리 nginx 예시 참고.
- **로컬 융합 점검 (비배포):** `scripts/run_jemaai_cloud_completion_chain.ps1` — Fact-Lock·Thin·BTC 앵커·P1(기본)·MVP 파일 존재 확인; `-SkipP1AB`로 P1 생략. VPS/nginx 반영은 본선 일정에서 수동.

## SSH Cursor · VPS 실매매 (전제)

- **Git 재발 방지 점검:** `scripts/Verify-GitWorkspaceSanity.ps1` 또는 `scripts/run_workspace_automation_health.ps1 -IncludeGitSanity`(`-StrictGitSanity`는 exclude/원격 오류 시 exit 1). `.git/info/exclude`에 `tools/`·`scripts/`만 두고 `!` 예외 없이 막으면 추적 파일이 조용히 제외된다(루트 `AGENTS.md` 본 절과 동일 경고).
- **`origin/main` 대비 drift:** Linux·SSH는 `scripts/verify_git_origin_main_sync.sh`(`--strict` 권장 후 `git pull --ff-only origin main`). Windows는 동일 로직을 `Verify-GitWorkspaceSanity.ps1 -CheckOriginMainSync`로 실행; 헬스 체인은 `run_workspace_automation_health.ps1 -IncludeGitOriginMainSync`(`-StrictGitOriginMainSync` 선택).
- **SSH로 연 원격 폴더**를 열면 그쪽 `AGENTS.md` / `.cursor/rules`가 적용된다. 로컬 `C:/workspace`와 동시에 쓰면 **git 동기화**로 규칙을 맞춘다.
- 로컬 트리는 **개발·테스트·문서** 우선. **실매매 런타임**은 VPS 등 별도 배포본일 수 있으므로, 코드·설정이 자동 동일하다고 가정하지 않는다.
- 질문·답변에서 **로컬만**인지 **배포(VPS) 후**인지 구분한다. VPS 경로·PM2 앱 이름 등은 **지휘관이 확정한 값**으로만 서술하고, 미확인이면 “확인 필요”로 표기한다.
- **Ollama (VPS/본선)**: `gemma4:e2b` 등 최신 모델 풀 시 구버전은 레지스트리 **412** 가능 → **Ollama 업그레이드** 후 `ollama pull`. 로컬 `C:\workspace` Cursor 세션은 **VPS 셸이 아님**; 업그레이드·모델 설치는 **서버 셸(또는 SSH Cursor가 연 그 호스트)** 에서 수행. 태그 정렬: **`OLLAMA_MODEL=gemma4:e2b`**(로컬 `.env` 등).
- 로컬 **SITREP → 공유 Vault 보급**(Windows, G: 마운트 시): `scripts/titan-sync.ps1` — **VPS 실매매 배포와는 별 작업**이다.
- **리스크 프로필 소스 고정(n8n 등):** Windows 사용자 환경변수 `RISK_PROFILE_SOURCE_NAME` / `RISK_PROFILE_MODE_NAME`을 설정하면 `projects/bitcoin-trading/ops/windows-rehearsal/ensure_daemon_running.ps1`의 Fact-Safe 동기화가 매 기동 시 동일 라벨을 넘긴다(미설정 시 기존 `memory/v2/risk/risk_profile_fact_safe_latest.json`의 source/mode를 보존).
