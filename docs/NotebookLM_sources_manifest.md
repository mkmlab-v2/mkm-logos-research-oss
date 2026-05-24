# NotebookLM 소스 매니페스트 (A/B 이원)

**작성일**: 2026-03-29 · **갱신**: 2026-05-14 (**렌즈별 RAG 맵** + **외부 CLI·LLM Wiki 대조 표** + **외부 RAG·CLI 연동 원칙 Fact-Lock** — 노트북 1목적·Core 혼입 금지) · 2026-05-13 (A 표·`sync_notebooklm_sources_to_mkm_data_vault.ps1` $SourceFiles: MSME **AI+ OpenData 제2026-327** 과제① SSOT 4파일 + `business_registration_plan_v1.md`) · 2026-05-12 (Lens music M31·§3.9·Track C fusion·CI 브리프 `NOTEBOOKLM_OPS_COMMAND_BRIEF_LENSMUSIC_M31_TRACKC_2026-05-12.md` + 매니페스트 지휘부 패킷 표) · 2026-05-11 (지휘부 동기화: `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.11 플랫폼 GTM·밸류에이션 냉정 정렬 + `CENTRAL_AGENT_MEMORY_V1.md` 분기 표·nl_sync·M30 `lens_music_prompt_runbook_webhook_health` 경로; 레포 SSOT 우선·NL 단독 승격 금지) · 2026-05-06 (Gemini 실사용 3종 표준 세트 고정: `00_MASTER_TRACKC_BOARD_2026Q2` + `10_OPS_MKM_CORE_INTELLIGENCE_2026Q2` + `03_P3P4_명리_성경_해설형_허브_2026Q2`; 숫자 접두 혼선 방지용 명명 규칙 추가) · 2026-05-06 (S2W 기사 체화 반영: `logos_symbolic_paid_user_brief_latest.md`의 `S2W 기사 기반 체화 팩` 기준으로 NotebookLM 브리핑 질문을 `문제 1개 -> 최소 온톨로지 -> 근거 추적(XAI) -> 행동 가이드` 순으로 고정) · 2026-05-05 (Track C agentic 방향성 고정: `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §12 반영, NotebookLM 브리핑 질의 프레임을 `governance/authority/audit` 우선으로 통일) · 2026-05-02 (MCP `notebooklm-mcp` 전용 Chrome 프로필 vs 내장 브라우저 로그인 **비동기** 문서화) · 2026-04-23 (Vault 미러: 원어 특이점 글로스 v3·히브리 오버라이드·`master_codebook_lexicon_v1` **포인터** JSON 추가; 동기화 스크립트 `$SourceFiles` 반영) · 이전 갱신 2026-04-12 (A 표: `MKM_CORE_THEORY_V1` · 압축·복원·예언 **통합 노트** `MKM_CORE_INTELLIGENCE_V1` · `COMPRESSION_EVALUATE_REPORT_DATA_FLOW_V1`·`MKM_LESSONS_LEARNED_V1`·`COMPRESSION_RESTORATION_EVOLUTION_INDEX_V1` · **LOG_METABOLISM 전용** `MKM_LOG_METABOLISM_REFINERY_V1` · **CORE↔Refinery 격벽 포인터** `NOTEBOOKLM_LOG_METABOLISM_CORE_BRIDGE_POINTER_V1.md` · 보조 NotebookLM 앵커 2건 · Vault 미러에 `CURRENT_OPS_SNAPSHOT` 포함) · **추가(같은 2026-05-14):** `RESEARCH_HISTORY_V1.md` = MCP **현행** 노트 목차만; 41개 과거=`docs/final/artifacts/research_history_notebooklm_snapshot_2026-04-12.md`; Vault `$SourceFiles` + `build_notebooklm_lens_source_packs_v1` OPS 팩 동기.  
**정의**: **A = Fact-Lock(팩트 고정)**, **B = Creative-Lock(통찰·가설)**. B는 본선 OOF·실매매 트리거와 A를 혼선 없이 적용.

**Cursor 3.0–3.4 (2026-04→05)**: NotebookLM과 동일하게 **브리핑·질의·소스 아카이브** 레이어다. **Agents Window·PR 검토·Cloud dev env**는 제품 기능이며, **압축 엔진·헌법·실매매 SSOT는 여전히 레포의 `.py`/JSON**이다. Cloud/Sandbox 격벽: `AGENTS.md`·`.cursor/rules/cursor-cloud-sandbox-boundary.mdc`.

**연구 서사 인덱스 (B, 비-SSOT):** `docs/final/RESEARCH_HISTORY_V1.md` — MCP `list_notebooks` 등으로 모은 **현행** 노트북 제목·ID·소스 프로브(구현·게이트 팩트 아님). **2026-04-12 전량(41개)** 아카이브: `docs/final/artifacts/research_history_notebooklm_snapshot_2026-04-12.md`. 갱신 시 현행 파일을 먼저 고친 뒤 Vault 동기화.

**Vault 동기화**: `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`가 이 표를 `notebooklm_sources/`로 복사(SSOT 반영). 공유 Vault 루트는 환경의 `MKM_VAULT_ROOT` 또는 스크립트 `-VaultRoot`로 지정.

### 동기화 오해 · 재발 방지 (2026-05-11)

“NotebookLM 동기화”는 **한 줄 파이프가 아니라 서로 독립한 3채널**이다. 한쪽이 성공해도 다른 쪽은 실패할 수 있다 — 이걸 섞어 말하면 “자꾸 깨진다”로 느껴진다.

| 채널 | 하는 일 | 성공 기준 | 자주 나는 착각 |
|------|---------|-----------|----------------|
| **A — Vault 미러** | 레포 파일 → `MKM_DATA_VAULT\vault\notebooklm_sources` 복사 | 스크립트 exit 0 · `_LAST_SYNC.txt` 갱신 | “G에 복사됐으니 NotebookLM 웹에 올라갔다” (**아님**) |
| **B — Google NotebookLM (클라우드)** | 노트북에 소스 등록·인제스트 | 웹/API에서 해당 소스 보임 | “매니페스트만 고치면 클라우드가 따라온다” (**아님** · UI `source_add` 또는 전용 푸시 작업 별도) |
| **C — Cursor MCP** | IDE 채팅에서 `notebooklm` 도구·세션 | 이 **채팅**의 도구 목록에 도구가 있고 `get_health` 성공 | “설정에 MCP 녹색 = 지금 채팅에서도 됨” (**아님** · 채팅 시작 시 도구 카탈로그 고정) |

### 렌즈별 RAG — 노트북 1목적 매핑 (미니멀 v1, 2026-05-14)

**문제:** 한 노트(예: MKM Core)에 **압축·사업·명리·이벤트** 소스를 한꺼번에 넣으면, NotebookLM이 **질문과 무관한 문단을 인용**해 답하는 경우가 생긴다(Fact-Lock 위반에 가까운 “근거 있는 착시”).

**원칙 (3줄)**  
1. **Google NL 노트북 1개 = RAG 코퍼스 1목적** — 렌즈·이벤트·Ops를 **섞지 않는다**.  
2. **구현·수치·경로**는 항상 Git의 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·스크립트·`artifacts` — NL은 **B/Creative-Lock·브리핑**만.  
3. **장기기억 체화**는 `docs/final/CENTRAL_AGENT_MEMORY_V1.md` + 커밋; NL 출력은 **이관·검증 후**에만 본 파일에 쓴다.

| 구분 | 노트북 이름 권장 (Google에서 생성·이름 맞춤) | 인제스트할 소스 (아래는 **시작 세트**; 늘리면 같은 목적 안에서만) | `ask_question` 용도 |
|------|----------------------------------------------|-------------------------------------------------------------------|---------------------|
| **Ops / Fact 앵커** | `OPS_COMMAND_ANCHOR` | `CURRENT_OPS_SNAPSHOT.md`, `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`(또는 §1.1~§2 요약 1파일), `P0_COMMERCIALIZATION_TRACKER.md`, `RESEARCH_HISTORY_V1.md`(NotebookLM **현행** 노트 목차; 과거 41개는 `artifacts/research_history_notebooklm_snapshot_2026-04-12.md`) | 경로·게이트·우선순위 |
| **Track C / 사업** | `TRACKC_BIZ` | `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md`, `artifacts/business_registration_plan_v1.md`, `artifacts/ai_opendata_challenge_2026_327_business_plan_overview_v1.md`, `artifacts/ai_opendata_challenge_2026_327_market_expansion_summary_v1.md`, `artifacts/moksori_mega_commercialization_roadmap_from_repo_ssot_v1.md` | 사업·GTM·대외 수치 경계 |
| **명리 Myeongni (B)** | `LENS_MYEONGNI` | `CONSTITUTION` **§3.3** 표·절, `MYEONGRI_INSIGHT_SSOT.md`, `MKM_LENS_GLOBAL_PROFILE_PROMPT_RAG_INSTRUCTIONS_DRAFT_V1.md`, `artifacts/MANSE_SAJU_STAGE_LAW_CONTRACT_V0.json`, `data/myeongni/16_STATE_MASTER_PROBE_v1.json` | `[HYPO]`·교육 자문; **개인 사주·실명·주민번호는 업로드 금지**(질문 본문에만 최소 입력) |
| **사상 Sasang (B)** | `LENS_SASANG` | `docs/final/schemas/sasang_emotion_mapping_v1.schema.json` + `CONSTITUTION` **§3.8**·§3.10 인접 절(스키마만 단정 금지 문구 포함) | 체질·감정 VA `[HYPO]` |
| **성경 Logos (B, NON_GATING)** | `LENS_LOGOS` | 루트 `AGENTS.md` **렌즈 역할 계약** 절, `CONSTITUTION` 중 Logos·`[NON_GATING]` 관련 절 요약 1파일 | 해설·운영 비게이트 |
| **압축·예언 허브 (A)** | `MKM_CORE_FACT` | `COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`, `MKM_LESSONS_LEARNED_V1.md`, `MKM_CORE_THEORY_V1.md`, `COMPRESSION_SLA_POLICY_V1.md`, `docs/final/artifacts/mkm_inter_agent_encoding_sota_map_v1.md`, `docs/final/artifacts/lg_compression_trust_packet_onepager_v1.md`, `docs/final/artifacts/mkm_inter_agent_wire_profile_v0.json`, `docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json`, `docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.md`, `docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.json`, `docs/final/artifacts/mkm_inter_agent_first_message_live_http_v1.json`, `docs/final/artifacts/fixtures/mkm_inter_agent_compress_request_v1.json`, `docs/final/artifacts/fixtures/mkm_inter_agent_expand_request_v1.json`, `docs/final/openapi_token_compression_v2_draft.yaml` | Inter-Agent RQ-019; live HTTP curl fixtures + `mkm_inter_agent_first_message_live_http_v1.json` |
| **예언 전용 (A/B)** | `07_PROPHECY_BTRACK_2026Q2` · MCP `07-prophecy-btrack-2026q2` | `NOTEBOOKLM_PROPHECY_LENS_INDEX_V1.md` + 팩 `LENS_PROPHECY` · 푸시 `py scripts/push_notebooklm_prophecy_lens_pack_v1.py` — UUID `3e95ca50-66f8-4b54-b0ef-81821c199518` | **예언 질의 SSOT**; 레거시 `9de651e6` → `90_ARCHIVE_P2_PROPHECY_migrated_2026Q2` 아카이브; Track A·실매매 합선 금지 |
| **이벤트 한정** | `EVENT_<slug>` | 해당 이벤트 소스 **1~3개만** (예: 발표 스크립트 단일 진본) | 기간 끝나면 소스 정리·아카이브 |
| **스마트팜·금산 IoT** | `06_스마트팜_진도관광농원_사업화_2026Q2` | MCP id `06-2026q2` · URL `96865180-769e-4a77-89bb-5f03a8083ac3` · `reports/notebooklm_smartfarm_geumsan_sync_pack_v1/`(15 files · incl. `notebooklm_golden40_compression_watch_v1.md` **ops WATCH only**) · `compression_track_a_headline_policy_v1_latest.json` · `docs/final/artifacts/smartfarm_geumsan_*` · `reports/smartfarm_vendor_outreach_log_v1.jsonl` · `https://farm.jema-ai.com/smartfarm` | 금산 300평 반쪽 턴키·벤더 RFQ·아웃리치 — **압축 KPI headline은 06에 WATCH 스니펫만**(MS paste 47.5%/0.890 유지) · 소스 **~105** · Pro 한도 **300/노트** — **웹 UI 정리=선택**(주제 분리·`notebooklm_06_source_cleanup_guide_v1.md`) |

**금지:** `MKM_CORE_FACT`에 명리·사업·이벤트 원본을 **추가로** 섞어 넣기.

**실행:** Vault 미러 → `sync_notebooklm_sources_to_mkm_data_vault.ps1` → (선택) PATH에 **`nlm`** 있으면 `Push-NotebooklmLensPacks_v1.ps1`로 렌즈 팩 일괄 `source add`(최초 `-InitMap` → `notebook_ids.json` UUID 편집; FusionHubBulk·Athena onefile과 동일 CLI 스택) → 없으면 NL 웹 **`source_add`**(행별 소스만; MCP `add_source` 실패 시 한국 UI 앵커: `scripts/apply_notebooklm_mcp_ko_selectors_patch_v1.py` + Reload) → MCP 질의 시 **`notebook_id` 고정**.

**자동(로컬):** `py scripts/build_notebooklm_lens_source_packs_v1.py` → `reports/notebooklm_lens_packs_v1/<렌즈>/`에 매니페스트 행 기준 파일 복사 + `index.json` — 이후 NL 웹에서 **렌즈별 노트**에 폴더 단위 업로드. 원클릭: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-NotebookLmLensPacksAndVaultMirror_v1.ps1` (Vault 없으면 팩만 생성). **권장 하이브리드(팩+Vault + 수동 NL/MCP + 선택 레포 퓨전 스모크 + 체크리스트 JSON):** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-NotebookLmMkmHybridRecommendedRoutine_v1.ps1` (`-SkipVaultMirror`, `-SkipLocalDeterministic`, `-IncludeTrackCMacroFusionSmoke` 등 상단 `.SYNOPSIS` 참고).

**교차 브리핑:** 여러 렌즈를 한 번에 묻지 말고, **질문마다 노트를 바꾸거나** 문서의 **Fusion Hub** 노트를 쓸 경우에도 **소스 폴더/태그로 렌즈 분리**를 유지한다(아래 URL 노트는 “허브”일 뿑, 만능 RAG 아님).

**기존 노트 정리:** `MKM_CORE_INTELLIGENCE_V1`(URL `aba1f8b1-…`)은 **본 표의 `MKM_CORE_FACT` 행과 동일 역할**로만 유지하고, 명리·사업·이벤트 원본이 섞여 있으면 **`LENS_MYEONGNI` / `TRACKC_BIZ` / `EVENT_*`로 이관**한다.

### 외부 플로우 참고 (CLI·Obsidian·LLM Wiki, 비-SSOT)

커뮤니티·영상에서 흔한 **“NotebookLM으로 조사 → 터미널/CLI로 가져오기 → Obsidian에 LLM 위키로 적재”** 흐름과 본 레포를 **한 화면에서만** 맞춘다. 아래는 **브리핑용**이며 구현·게이트 팩트는 여전히 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·스크립트만 SSOT다.

| 외부에서 말하는 흐름 | MKM 레포에서의 대응 | 주의 |
|---------------------|---------------------|------|
| NL 조사 후 CLI로 회수·정리 | Cursor MCP `notebooklm` (`get_health`·`ask_question` 등) + 로컬 팩 `scripts/build_notebooklm_lens_source_packs_v1.py` | 클라우드 노트 **소스 일괄 업로드**는 MCP `add_source`(url·text) 및 웹 UI 한계 — 본 문서 **「동기화 오해 · 재발 방지」** 3채널 표 |
| Obsidian·**LLM Wiki** 장기 저장 | `docs/final/LLM_WIKI_SCHEMA.md`, `memory/obsidian_vault/llm_wiki/raw/`·`wiki/` (`CLAUDE.md` 포인터) | 장기기억 **체화·승격**은 `docs/final/CENTRAL_AGENT_MEMORY_V1.md` + Git; NL·Obsidian 단독 근거 금지 |
| 서드파티 “NotebookLM Python” 등 별도 CLI 레포 | **미포함** — 도입 시 B-track·개인 도구로만, 본선·실매매·게이트와 **합선 금지** | 외부 스택을 SSOT에 박지 말 것 |

**외부 RAG·CLI 연동 원칙 (Fact-Lock)** — 위 표와 중복 없이 **시스템 경계**만 고정한다.

1. **레포가 지원하는 연동 표준은 MCP** (`notebooklm-mcp`, 전용 Chrome·`get_health`/`ask_question` 등). 에이전트·문서가 가리키는 **기본 진입점**을 서드파티 CLI·UI 매크로로 바꾸지 않는다.  
2. **커뮤니티 NotebookLM CLI·스크래핑 계열**은 UI·정책 변경에 취약하므로 **`verify_p0`·CI·본선 자동화에 직접 하드와이어 금지**; 개인·B-track 실험은 레포 밖 또는 **합선 없는** 로컬만.  
3. **구현·경로·게이트 판정**은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·호출 가능 **`.py`·exit code**만 SSOT — NL·Obsidian·유튜브·외부 브리핑 **단독 근거 금지**.  
4. **Obsidian / `LLM_WIKI_SCHEMA.md` / `memory/obsidian_vault/llm_wiki/`** 로 이관할 때 **NL 답변 자동 덤프 금지**; `CONSTITUTION`·스크립트와 **충돌 없음**을 확인한 뒤 **`CENTRAL_AGENT_MEMORY_V1.md`·커밋**으로 체화한다.  
5. **할당·ToS·계정 한도**는 구글 제품 측 정책 — “무료 무제한 연산” 가정으로 설계·문서화하지 않는다.  
6. **Logos B-track 번들** 등 본류 아티팩트: **degraded(업스트림 결손)** 예시 `docs/final/schemas/logos_insight_bundle_v1.minimal.example.json`, **비-degraded(업스트림 전부 존재)** 예시 `docs/final/schemas/logos_insight_bundle_v1.non_degraded.example.json`(업스트림 `docs/final/artifacts/fixtures/logos_insight_bundle_non_degraded_upstream/`·재생성 `py scripts/materialize_logos_insight_bundle_non_degraded_example_v1.py`)·회귀 `tests/test_logos_insight_bundle_schema_v1.py` — NL과 **역할 분리**.

**원샷 점검 (로컬만, Google 호출 없음):** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-NotebookLmSyncTriage_v1.ps1` → 콘솔 요약 + `reports/notebooklm_sync_triage_latest.json`. Vault까지 실제 미러하려면 같은 스크립트에 `-RunMirror`.

**MCP만 재발하면:** `scripts/check_notebooklm_mcp_prereqs.ps1` → `scripts/repair_notebooklm_mcp_auth_stuck.ps1` → Cursor Reload · 필요 시 **새 채팅**. 규칙: `.cursor/rules/notebooklm-mcp-session-bridge.mdc`.

### 지휘부 동기화 패킷 (2026-05-12)

NotebookLM·지휘부 브리핑을 레포 Fact-Lock과 맞출 때 **아래를 한 세트**로 본다(구현 판정은 여전히 `CONSTITUTION_*`·스크립트).

| 구분 | 경로 | 비고 |
|------|------|------|
| A | `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.11 | 미들웨어 포지션·단일 앵커 리스크·2nd customer·빅테크 내재화·수직·대외 수치 Fact-Lock |
| A | `docs/final/CENTRAL_AGENT_MEMORY_V1.md` | 장기기억·`nl_sync`·분기별 한 줄·운영 체크포인트 |
| A | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` | M30·**M31** 등 구현 경로·pytest |
| A | `docs/final/NOTEBOOKLM_OPS_COMMAND_BRIEF_LENSMUSIC_M31_TRACKC_2026-05-12.md` | **Lens music M31·§3.9 번들·Track C fusion·CI** 핸드오프(NotebookLM `source_add` 1파일용) |
| A | `docs/final/artifacts/business_registration_plan_v1.md` | 사업자등록 주종목·KSIC SSOT (OpenData·R&D 신청 정합) |
| A | `docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_overview_v1.md` | MSME AI+ OpenData **제2026-327** 과제① 사업계획 개요·일정·체크리스트 |
| A | `docs/final/artifacts/ai_opendata_challenge_2026_327_market_expansion_summary_v1.md` | 동 공모 **3-2** 붙여넣기용 Phase 1–2 시장 요약 |
| A | `docs/final/artifacts/moksori_mega_commercialization_roadmap_from_repo_ssot_v1.md` | 레포 SSOT 기반 상용화 로드맵(Phase 0–5) |
| B | `docs/final/artifacts/lens_music_prompt_runbook_webhook_health_latest.json` | M30 헬스 집계(재생성: `scripts/build_lens_music_prompt_runbook_webhook_health_summary_v1.py`) |

**NotebookLM 질의 스타터 (Creative-Lock, 본선 합선 금지):** “§3.11 기준으로 단일 앵커 리스크를 줄이기 위한 **다음 분기 파일럿 산업 2개**를 제안하라. 각안에 (i) PoC 주기 (ii) 규제 대비 (iii) 우리 레포에서 인용할 **아티팩트 경로** 후보를 한 줄씩 붙여라. 의료 효능·실매매·자동 승격 단정은 금지.”

**운영:** 로컬에서 매니페스트 파일 갱신 후 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1` 실행 → 공유 Vault `notebooklm_sources` 미러. 클라우드 노트북에 소스 추가(`source_add`)는 별도.

## Solo 운영 Quickstart (2026-05-03)

복잡한 폴더 탐색 없이, 아래만 따르면 현재 운영 컨텍스트를 안정적으로 재현할 수 있다.

1. **업로드 1파일(권장)**  
   - `docs/final/artifacts/ATHENA_UPLOAD_ONEFILE_LATEST.md`  
   - 원본 JSON을 이동/복사하지 않고 핵심 `path/key/value` 실값만 단일 파일로 제공한다.
   - BTC 우선 섀도우 루프 지시문: `docs/final/artifacts/ATHENA_SHADOW_LOOP_BTC_FIRST_COMMAND_V1.md`
   - 신뢰성/SPOF/복구 드릴: `docs/final/artifacts/ATHENA_RELIABILITY_SPOF_DRILL_V1.md`
   - 자동 재생성: `scripts/build_athena_upload_onefile_latest.py`
   - 일일 갱신 작업: `AthenaUploadOnefileRefreshDaily` (`scripts/Register-AthenaUploadOnefileRefreshTask.ps1`)
   - NotebookLM 자동 업로드 작업: `AthenaUploadOnefileNotebooklmPushDaily` (`scripts/Register-AthenaUploadOnefileNotebooklmPushTask.ps1`)

2. **아테나 최종 점검 기준 파일(원본 SSOT, 이동 금지)**  
   - `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json`  
   - `docs/final/artifacts/integrated_governance_v1_latest.json`  
   - `docs/final/artifacts/a_track_go_nogo_status_latest.json`  
   - `docs/final/artifacts/kospi_myeongri_standalone_commercial_gate_v1_latest.json`  
   - `docs/final/artifacts/kospi_sasang_single_lane_commercial_gate_v1_latest.json`  
   - `docs/final/artifacts/kospi_biblical_single_lane_commercial_gate_v1_latest.json`

3. **운영 고정 규칙(아테나 출력)**  
   - `Path/Key/Value` 형식만 사용 (`[cite:숫자]` 단독 인용 금지)  
   - `meta.high_reliability_decision=="HOLD"` 또는 `meta.price_output_locked==true`면 Final Action은 HOLD  
   - 충돌 시 `most_conservative_wins`

4. **값 충돌 처리**  
   - NotebookLM 과거 맥락 vs 최신 실값 충돌 시, `ATHENA_UPLOAD_ONEFILE_LATEST.md`와 원본 JSON 실값을 우선한다.

### MCP `notebooklm-mcp` 인증 — 웹 로그인과 자동 동기화되지 않음 (2026-05)

- **원인:** Cursor 내장 브라우저·일반 Chrome에서 NotebookLM에 로그인한 것과, MCP 서버가 띄우는 **자동화 Chrome**은 **서로 다른 Chrome 프로필**이다(레포는 `node`+고정 `dist/index.js`·`MKM_NOTEBOOKLM_MCP_PINNED_VERSION` 사용, `npx … @latest` 비권장). Windows에서는 통상 **`%LOCALAPPDATA%\notebooklm-mcp\Data\chrome_profile`**(잠금 정리는 `scripts/repair_notebooklm_mcp_auth_stuck.ps1` 출력 기준)에만 MCP 쿠키가 저장된다. 그래서 “이미 브라우저에서 로그인됨”이어도 **`get_health`의 `authenticated`는 false일 수 있다** — 오류가 아니라 **격리 설계**다. **Settings MCP 초록 점**과 **로그인 완료**는 별개이며, 토글·`mcp.json` 변경 후에는 **Reload Window → 새 채팅 → `get_health`** 순을 권장한다(에이전트 규칙 `notebooklm-mcp-session-bridge.mdc` 동일).
- **조직 기본 계정(고정):** NotebookLM·MCP 자동화에는 **`admin@no1kmedi.com`(Google Workspace)** 만 사용한다. 다른 Google 계정이 보이면 MCP에서 **`re_auth`**(계정 전환 권장) 또는 **`setup_auth`**로 전용 프로필에 `admin@no1kmedi.com`으로 재로그인한다.
- **완화(레포):** `.cursor/mcp.json`의 `notebooklm` 항목에 **`HEADLESS`=`false`** 를 두어 로그인 창이 보이게 한다(패키지 기본은 headless). MCP 프로세스를 **Reload Window / Cursor 재시작** 후에만 환경 변수가 반영된다.
- **1회 설정:** MCP 도구 **`setup_auth`** 로 위 전용 프로필에 한 번 로그인하면 이후 같은 프로필을 재사용한다. 계정 전환·세션 꼬임 시 **`re_auth`** / **`cleanup_data`** 가 필요하다. 패키지 정의상 **`NOTEBOOKLM_PROFILE=standard`면 위 두 도구가 아예 노출되지 않으므로**, 레포 `.cursor/mcp.json`은 **`NOTEBOOKLM_PROFILE`=`full`** 로 두어 복구 도구를 켠다. 그다음 **Reload Window** 후 새 채팅에서 `cleanup_data`(미리보기→실행)→`setup_auth` 순을 권장한다.
- **Fact-Lock:** NotebookLM 웹 UI 브리핑은 **참고**이며, 구현·게이트 확정은 여전히 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·스크립트·아티팩트만 SSOT다.

#### 노트북당 소스 한도 (플랜별 · 2026-05-23)

Google Help [Usage limits](https://support.google.com/notebooklm/answer/16206866?hl=en) 기준 **노트북당 소스 개수** (MCP `50 queries/day`와 별개):

| 플랜 | 소스/노트 |
|------|-----------|
| Standard (무료) | 50 |
| Plus | 100 |
| Pro | **300** |
| Ultra | 600 |

**MKM 운영 가정:** 지휘관 Workspace **Pro → 300**. `06_스마트팜…` 노트는 **~105건**이면 **한도 여유** — 웹 UI 삭제는 **주제 분리용 선택** (`reports/notebooklm_06_source_cleanup_guide_v1.md`). 레거시 문서의 “무료 50 한도” 표기는 **Standard 기준**이며 Pro와 혼동 금지.

#### MCP 재발 방지 (로컬 자동·수동, 2026-05)

- **수동 점검·수리 (비용 낮음):** `scripts/check_notebooklm_mcp_prereqs.ps1` → `scripts/repair_notebooklm_mcp_auth_stuck.ps1` (또는 원클릭 `scripts/invoke_notebooklm_mcp_auth_recovery_v1.ps1`). **쿠키/로그인을 대체하지 않음** — 오래된 node·Chrome·lockfile만 정리.
- **원샷 프로브 (자동화·암행어사용 JSON):** `scripts/Invoke-McpHygieneProbe.ps1` → 표준 출력 및 선택 `-OutJson` 경로에 **`mcp_hygiene_probe_notebooklm_v1`** 요약(prereq exit·stale 카운트·선택 `-Repair`). MCP `get_health`의 `authenticated`는 포함하지 않음(Cursor 전용).
- **주간 자동 (권장):** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-NotebookLmMcpWeeklyHygieneTask.ps1` — 기본 **일요 07:00(로컬)** 에 stale 프로세스 정리. 제거: `-Remove`.
- **일일 프로브 (선택, Repair 없음 기본):** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-McpHygieneProbeDailyTask.ps1` — 기본 **매일 08:30(로컬)** 에 `Invoke-McpHygieneProbe` → `reports/mcp_hygiene_probe_latest.json` 및 로그 `reports/mcp_hygiene_probe_daily.log`. **헬스 번들 수동:** `scripts/run_workspace_automation_health.ps1 -IncludeMcpHygieneProbe` 또는 `-McpHygieneProbeOnly` — 선택 **VPS 스모크:** `-IncludeVpsOpsSmoke` (기본 SoftFail; 실패를 헬스 실패로 올리려면 `-IncludeVpsOpsSmokeHardFail`). P0+MCP+VPS만: `-McpHygieneProbeOnly -IncludeVpsOpsSmoke`.
- **VPS SSH 스모크 (디스크 증거, Cursor MCP와 별개):** `scripts/Invoke-VpsOpsSmoke_v1.ps1` — `MKM_VPS_HOST`·`MKM_VPS_USER`(선택)·`MKM_VPS_SSH_KEY_PATH` 또는 `SSH_KEY_PATH`·`hostinger_mkmlife` 탐색이 될 때만 `ssh -o BatchMode=yes`로 짧은 원격 명령 1회 → `reports/vps_ops_smoke_latest.json`. **변수 미설정 시 스킵·exit 0.** 대화형 에이전트용 **devops-mcp**(`execute_vps_command` 등)과 역할이 다르다(번들·스케줄은 스크립트로 재현).
- **암행어사 번들 꼬리 (비차단):** `scripts/Run-AmsaengEosaMonitoringBundleTask.ps1` 말단에서 위 VPS 스모크를 `-SoftFail`로 호출(SSH 실패해도 번들 전체는 성공 처리).
- **로그오프 시 자동 (선택):** `scripts/register_notebooklm_mcp_repair_logoff_task.ps1` — Winlogon 이벤트에 repair 연동.
- **Cursor 재시작 뒤:** Settings → MCP에서 `notebooklm` **토글 off/on** 또는 **새 채팅** — 도구 목록이 세션 시작 시 고정되는 경우가 있어, **같은 채팅에서만** `Not connected`가 남을 수 있다(에이전트 규칙 `notebooklm-mcp-session-bridge.mdc`와 동일).

### Vault 동기화 — 로컬 부재 Skip (정상, 2026-04)

아래 경로는 스크립트의 복사 목록에 있으나 **최소 클론·본 저장소 트리에 없을 수 있다**. 부재 시 동기화는 건너뛰며(스크립트는 해당 7개를 **optional**로 처리해 WARNING 대신 회색 한 줄만 출력), **오류가 아니다**.

| 경로 | 비고 |
|------|------|
| `projects/bitcoin-trading/ops/v2/memory/decision_ledger.py` | 현재 원격 인덱스에 없음 — VPS/별도 배포 트리에 있을 수 있음 |
| `projects/bitcoin-trading/ops/v2/memory/fact_lock_snapshot.py` | 동일 |
| `projects/bitcoin-trading/ops/windows-rehearsal/WAITING_QUEUE_DUAL_BTC_RUNBOOK.md` | 동일 |
| `projects/bitcoin-trading/ops/windows-rehearsal/DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md` | 동일 |
| `backtest_results/LOGOS_RESONANCE_BTC_BULL_FULL.json` | `backtest_results/`는 `.gitignore` — 로컬 생성·역수입 시에만 존재 |
| `backtest_results/LOGOS_RESONANCE_BTC_BEAR_FULL.json` | 동일 |
| `backtest_results/LOGOS_RESONANCE_BTC_SIDEWAYS_FULL.json` | 동일 |

**권장**: 일상 운영은 부재를 **무시**해도 됨(`copied`만으로 미러 성공 판단). 목록에서 경로를 **삭제(Prune)** 하지 않는 한, 나중에 파일이 생기면 **같은 스크립트가 자동으로 포함**한다.

### Unified-Intelligence — 메인 지휘 (2026-03-29)

- **통합 전황판 (A1 16-State + Logos Phase 1 + Git 슬롯)**: `docs/final/UNIFIED_INTELLIGENCE_BATTLEBOARD_2026-03-29.md`
- **합류 방식**: 병렬 창은 **경로·커밋 해시·exit code**로만 보고 → 메인에서 매니페스트·전황판 갱신. **매니페스트 직접 편집은 메인 창만.**

### Gemini ↔ NotebookLM — 작전 브리핑 앵커 (2026-04)

**목적**: 지휘관 환경에서 **Gemini(앱/스튜디오 등)가 NotebookLM 노트북을 컨텍스트로 묶는** 흐름을 쓸 때, 레포 쪽 **동일 앵커 URL**을 SSOT로 고정한다.

- **역할**: 브리핑·질의·소스 아카이브 레이어. **구현 여부·수치·경로의 단일 진실**은 여전히 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·호출 가능 스크립트·JSON 산출물(`AGENTS.md` 동일).
- **작전 지휘 참조 노트북 (NotebookLM URL)**  
  - `작전지휘부 Ops20260318` (`347e5cbe-0ade-4615-9aac-8747d4fa644e`) — https://notebooklm.google.com/notebook/347e5cbe-0ade-4615-9aac-8747d4fa644e — **NL·MCP 표시명:** `00_MASTER_TRACKC_BOARD_2026Q2` (동일 UUID; MCP 라이브러리 id `ops-command-anchor-fact-lock`).  
  - `Fusion Insight Hub - Bible x Myeongri x Sasang (2026-04-01)` (`71f55a03-09d0-411f-b365-0ce2a2064c24`) — https://notebooklm.google.com/notebook/71f55a03-09d0-411f-b365-0ce2a2064c24  
- **압축·복원·예언 통합 (FACT 중심, 작전/성경/명리 제외)** — 브리핑·RAG 보조 전용; SSOT는 여전히 레포·`CONSTITUTION`·`artifacts`.  
  - `aba1f8b1-be62-4367-ac7f-b1a997bb77d4` — https://notebooklm.google.com/notebook/aba1f8b1-be62-4367-ac7f-b1a997bb77d4 — 제목: **MKM_CORE_INTELLIGENCE_V1** (MCP `notebook_create` + `source_add`; `.json` 단일 파일 업로드는 도구 제한 시 텍스트 요약·포인터로 대체)
- **Gemini 실사용 표준 세트 (지휘 기본 3종, 2026Q2)** — 최근 UI 명칭 기준으로 아래 3개를 기본으로 선택한다.
  - `00_MASTER_TRACKC_BOARD_2026Q2` — Track C 전황 보드(마스터 컨텍스트)
  - `10_OPS_MKM_CORE_INTELLIGENCE_2026Q2` — Ops/Core intelligence 중심 지휘
  - `03_P3P4_명리_성경_해설형_허브_2026Q2` — 멀티렌즈 해설 허브(P3/P4)
  - **UUID 정렬:** `00_MASTER_TRACKC_BOARD_2026Q2` 는 위 **작전 지휘 참조** URL `347e5cbe-0ade-4615-9aac-8747d4fa644e` 와 **동일 노트**(NL에서 노트북 제목만 변경한 경우). 별도 UUID가 아니다.
- **명명 규칙 (혼선 방지)** — 새 노트북을 만들 때는 숫자만 앞세우지 말고, `영역_우선순위_역할_분기` 순서를 권장한다.
  - 권장 예: `OPS_00_MASTER_TRACKC_BOARD_2026Q2`, `OPS_01_MKM_CORE_INTELLIGENCE_2026Q2`, `FUSION_02_P3P4_MYEONGNI_LOGOS_HUB_2026Q2`
  - 운영 원칙: 브리핑·지휘는 **역할명(OPS/FUSION + 역할)**으로 고르고, 숫자 접두(`00/03/10`)는 보조 정렬키로만 쓴다.
- **LOG_METABOLISM JSONL 정제 전용** — 원시 로그·엄격 프롬프트 산출 JSONL만 적재; `discover_nl_metabolism_source.py`가 `notebooklm_pull_manifest_v1.json`의 `discover_priority_notebook_ids`로 **최우선 스캔**.  
  - `e457f7ae-24b6-49fa-8f3f-1881e5ae027a` — https://notebooklm.google.com/notebook/e457f7ae-24b6-49fa-8f3f-1881e5ae027a — 제목: **MKM_LOG_METABOLISM_REFINERY_V1**
- **CORE ↔ Refinery 교차 질의 보강 (포인터 1파일)** — `docs/final/NOTEBOOKLM_LOG_METABOLISM_CORE_BRIDGE_POINTER_V1.md` 를 **MKM_CORE_INTELLIGENCE_V1** 노트에만 소스 추가 권장(Refinery 노트는 동 문서·CONSTITUTION 이미 보유로 중복 최소화). MCP `cross_notebook_query` 시 CORE 쪽이 LOG_METABOLISM 격벽을 근거로 답하도록 한다.
- **보조 노트북 (지휘관 지정 · B 궤적 / 브리핑·역사 소스)** — 위 메인 앵커를 **대체하지 않음**. 구현·게이트 팩트는 `CONSTITUTION`·`artifacts`·`.py`만.  
  - `978ab6ca-d069-4a78-8916-30c7844c4fa6` — https://notebooklm.google.com/notebook/978ab6ca-d069-4a78-8916-30c7844c4fa6  
  - `d193d8d4-5678-4cc7-8eb6-7046a9a3b16d` — https://notebooklm.google.com/notebook/d193d8d4-5678-4cc7-8eb6-7046a9a3b16d  
  - **로컬 대응(참고):** `H:\workspace\docs\` — 레포 `docs\final` SSOT와 **경로·동일성 보장 없음**; 필요 시 해당 MD를 `@` 첨부.  
- **Vault**: `sync_notebooklm_sources_to_mkm_data_vault.ps1`가 레포 SSOT를 `notebooklm_sources/`로 미러할 때, 에페메럴 핸드오프 `docs/final/CURRENT_OPS_SNAPSHOT.md`와 스크립트 `$SourceFiles`에 적힌 **분리 아카이브**(예: `docs/final/artifacts/ops_snapshot_body_archive_2026-05-15.md`, `docs/final/artifacts/research_history_notebooklm_snapshot_2026-04-12.md`)도 함께 복사되어 **Hub B / 오프라인 RAG**와 날짜를 맞추기 쉽다.

---

## A 궤적 — **팩트** 소스 (Hard-Fact)

| 우선순위 | 경로 (워크스페이스 기준) | 비고 |
|----------|--------------------------|------|
| P0 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` | 헌법 추론 구현 SSOT (**§14 Prism Index** 포함) |
| P1 | `docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json` | Prism 논리 색인(Grand Indexing 2.0); 경로·역할·`agent_access`; 코드 4D 축과 혼동 금지 |
| P0 | `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` | 압축-해석 파이프라인 Fact-Lock SSOT |
| P1 | `docs/final/COMPRESSION_EVALUATE_REPORT_DATA_FLOW_V1.md` | `evaluate_report`·4D 브리지·스윕 CLI 관계(벤치 혼동 방지); 수치는 artifacts 우선 |
| P1 | `docs/final/MKM_LESSONS_LEARNED_V1.md` | 반복 NO_GO 교훈 인덱스(비-SSOT); 구현 팩트는 CONSTITUTION·artifacts |
| P1 | `docs/final/NOTEBOOKLM_LOG_METABOLISM_CORE_BRIDGE_POINTER_V1.md` | NotebookLM **MKM_CORE_INTELLIGENCE_V1** 전용: LOG_METABOLISM·압축 축 격벽 경로 포인터; 구현 SSOT는 CONSTITUTION |
| P1 | `docs/final/INTERNAL_COMPRESSION_MAX_LANE_FOUNDATION_V1.md` | 내부 전용 압축/복원 개발 원점(정경 원어 코어 vs 번역기 레일·조건부 압축·비합선 원칙) |
| P1 | `docs/final/artifacts/MANSE_SAJU_STAGE_LAW_CONTRACT_V0.json` | 만세력·사주 단계 법칙 수학화 계약(v0, 연구 전용·검증 통과분만 freeze) |
| P1 | `docs/final/artifacts/manse_saju_stage_law_spike_latest.json` | 만세력·사주 단계 예측 스파이크 산출(v0, research_only) |
| P1 | `docs/final/COMPRESSION_RESTORATION_EVOLUTION_INDEX_V1.md` | 압축·복원 축 연대기·읽기 순서·`H:\workspace` 병행 근거(비-Git); 수치·GO는 artifacts·스크립트 우선 |
| P1 | `docs/final/MKM_CORE_THEORY_V1.md` | L0/L1/L2 팩트체크에서 **[FACT]만** 추린 압축·복원·예언 축 번들; CONSTITUTION·artifacts 우선 |
| P0 | `docs/final/COMPRESSION_SLA_POLICY_V1.md` | 투트랙 압축 SLA(범용·리터럴)·산출·헬스·웹훅 범위; NotebookLM이 이 수치를 대체하지 않음 |
| P1 | `docs/final/artifacts/business_registration_plan_v1.md` | 사업자등록 주종목·KSIC·R&D 신청 정합 SSOT |
| P1 | `docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_overview_v1.md` | 중기부 AI+ OpenData **제2026-327** 과제① 사업계획 개요·접수·K-Startup+나라장터 병행 |
| P1 | `docs/final/artifacts/ai_opendata_challenge_2026_327_market_expansion_summary_v1.md` | 동 공모 시장·확장(3-2) 요약·30초 피치 |
| P1 | `docs/final/artifacts/moksori_mega_commercialization_roadmap_from_repo_ssot_v1.md` | 레포 기반 메가 로드맵(공모→문서 OS→a-codeai→mkmlife 등) |
| P1 | `docs/final/MKM12_L0_L1_L2_CLAIMS_TAGGED_FACTCHECK_2026-04-09.md` | L0/L1/L2 클레임 태그·역추론/사이드 채널 SSOT 인용·외부 문헌 앵커(§I); 운영 통합 여부는 CONSTITUTION·`.py`로만 판정 |
| P1 | `docs/final/openapi_token_compression_stub_v1.yaml` | 토큰 압축 API 스텁 OpenAPI 3 계약 |
| P0 | `docs/final/STATE16_INTERFACE_INSERTION_CONTRACT_2026-03-31.md` | 16상 인터페이스 삽입 계약(비강제·단계 게이트) |
| P0 | `docs/final/MASTER_Linguistic_Contract_2026.md` | 어휘·코퍼스 FACT-LOCK(레일·v2·스테이징) SSOT |
| P0 | `docs/final/master_codebook_dual_track.template.json` | 듀얼 트랙 코드북 템플릿 |
| P0 | `scripts/experimental/codebook_runtime_pack/README.md` | 코드북 런타임 팩 **공식 명칭 SSOT** (`codebook_runtime_pack`), legacy `codepack_recovery`와 구분 |
| P1 | `docs/final/artifacts/codebook_factsafe_bundle_latest.json` | 코드북 팩트세이프 번들 최신 결과(옵션: recovered readiness 포함) |
| P1 | `docs/final/artifacts/recovered_codebook_operational_readiness_latest.json` | 코드북 런타임 팩 운영 준비도 PASS/FAIL 산출 |
| P1 | `projects/bitcoin-trading/ops/.hermes.md` | 외부 부관(Hermes 등) **얇은 프로필**: SSOT 포인터·금지·스킬 앵커; 본문 복제 금지 |
| P1 | `data/regimes/regime_fusion_policy.json` | 레짐 퓨전 정책 |
| P1 | `data/regimes/regime_map.json` | 1차 레짐 맵 |
| P1 | `projects/bitcoin-trading/src/integration/dual_regime_api.py` | dual-regime API |
| P2 | `projects/bitcoin-trading/ops/v2/memory/decision_ledger.py` | 의사결정 ledger |
| P2 | `projects/bitcoin-trading/ops/v2/memory/fact_lock_snapshot.py` | 팩트 스냅샷 |
| P1 | `data/myeongni/myeongni_16_state_experiment_20260329.jsonl` | 명리 16-State 실험 **정본** JSONL (2026-03-29; `state_id` 1–16) |
| P1 | `data/myeongni/16_STATE_MASTER_PROBE_v1.json` | **Master Probe v1** 집계 SSOT (16/16 coverage; NotebookLM/RAG·격벽) |

### Gemini 개발 순서 앵커 (A, 2026-04-30)

Gemini/NotebookLM이 "지금 개발이 어디까지 왔는지"를 빠르게 파악하도록, 아래 6개를 **순서대로** 우선 인용한다.

| 순서 | 경로 | 역할 |
|------|------|------|
| 1 | `docs/final/CURRENT_OPS_SNAPSHOT.md` | 최신 작업 흐름·핸드오프 요약 |
| 2 | `docs/final/P0_COMMERCIALIZATION_TRACKER.md` | 상용화 단계/게이트 SSOT |
| 3 | `docs/final/artifacts/mkm_submission_packet_v1.md` | 제출 패킷 메인(초록/방법/한계/FAQ + 승격 매트릭스) |
| 4 | `docs/final/artifacts/mkm_submission_preflight_10min_checklist_v1.md` | 제출 직전 10분 점검 루틴 |
| 5 | `docs/final/artifacts/two_track_submission_camera_ready_latest.json` | 카메라레디 제출 JSON(최종 문구 잠금) |
| 6 | `docs/final/artifacts/two_track_kdd_submission_template_latest.json` | KDD 제출 템플릿(최종 문구 잠금) |
| 7 | `docs/final/artifacts/two_track_submission_evidence_bundle_latest.json` | 필수 증거 번들 충족 여부 |
| 8 | `docs/final/artifacts/external_message_claim_guard_latest.json` | 대외 문구 가드 상태(`status=pass` 확인) |

보조 점검(선택): `docs/final/artifacts/global_atom_sota_baseline_readiness_latest.json`  
(placeholder baseline 여부를 확인해 과장 주장 방지)

**확인**: Vault·로컬 경로 정합은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §7 참조.

### 명리 16-State Master Probe (2026-03-29 정본)

| 항목 | 경로 | 비고 |
|------|------|------|
| 정본 JSONL | `data/myeongni/myeongni_16_state_experiment_20260329.jsonl` | 16줄; 날짜 접미사로 **다른 실험 파일과 혼선 방지** |
| Master Probe 집계 | `data/myeongni/16_STATE_MASTER_PROBE_v1.json` | `coverage_summary.states_with_audit === 16`일 때만 “완전 커버리지”로 서술 |
| 생성기 | `scripts/myeongni_summary_gen.py` | 예: `py scripts/myeongni_summary_gen.py --audit-path data/myeongni/myeongni_16_state_experiment_20260329.jsonl --output data/myeongni/16_STATE_MASTER_PROBE_v1.json` |

**레거시**: `MASTER_PROBE_v1_ACTUAL.json` 등 구버전 이름이 남아 있어도 **SSOT·NotebookLM 인용은 `16_STATE_MASTER_PROBE_v1.json`만** 사용한다.

**격벽**: NotebookLM·RAG 요약·인용 전용. **실매매 트리거·본선 OOF와 자동 합선 금지** (Logos-first·레짐 규칙과 동일하게 “추론 레이어”만).

**NotebookLM — Master Probe 권위 검증 질의 (예시)**

1. 이 워크스페이스에서 **16개 에너지 격자(state 1–16)** 감사·집계의 단일 진실 공급원 파일명과 경로는 무엇인가? (`16_STATE_MASTER_PROBE_v1.json` 우선 인용)
2. `state_id`가 7인 항목의 요약·감사 필드(있다면)를 JSON에서 그대로 인용하라.
3. `myeongni_16_state_experiment_20260329.jsonl`이 아닌 **다른 날짜·다른 접미사**의 실험 파일과 본 정본을 구분하는 한 줄 규칙을 말하라.
4. 작전지휘부 노트북 등 **대량 소스** 없이, `16_STATE_MASTER_PROBE_v1.json`만으로 16-State 지형(커버리지·상태 ID 목록)을 설명할 수 있는가?
5. (코드 리뷰용) JSONL **물리적 줄 번호**가 `state_id`와 같다고 가정하지 말 것 — 근거는 `state_id` 필드와 Master Probe의 `state_ids_present`뿐이라고 요약하라.

---

## B 궤적 — **통찰** 소스 (Insight / Hypothesis)

| 항목 | 경로 (또는 TBD) | 비고 |
|------|------------------|------|
| Track C IP 사업계획 (v2, §3.11 GTM) | `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` | B2B/IP 수익화·§3.11 플랫폼 GTM 냉정 정렬; 비투자자문·Track A/B/C 경계·Fact-Lock 수치 |
| DSS / Qumran | `docs/final/DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md` | Creative-Lock; frontline closeout SSOT |
| 명리·융합 의사결정 | `docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` | SSOT; B 노트북에는 동명 텍스트 소스로 반영(`MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json`). A와 역할 분리 |
| AI·명리·만세 외부 참조 | `docs/final/AI_MYEONGNI_MANSE_EXTERNAL_REFERENCE_LANDSCAPE_2026-03-29.md` | 타 서비스·RAG·LLM 패턴 정리(참고만); 본선 OOF·A와 무단 합선 금지 |
| AI-Logos 외부 연구 (arXiv·Kaggle) | `docs/external_research/AI-Logos_Research_Bibliography_2026.md` | B-only; **Confirmed URL** 서지·TBD 분리; 작전 **LeWorld-Enlightenment**; A·본선 자동 합선 금지 |
| Logos 교집합 랭킹 SSOT | `docs/final/LOGOS_INTERSECTION_RANKING_SSOT_2026-03-29.md` | `mean`/`min` 지표·경로; λ(편향)와 기호 분리; 본선·실매매 자동 합선 금지 |
| 한의 원전·프록시 | `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` · `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md` · `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §9 | 코퍼스 B 분리·승격 경계; 정책 SSOT는 handoff MD |
| 일반예언 — VPS Git + 미래학 딥리서치 융합 번들 | `docs/final/NOTEBOOKLM_GENERAL_PROPHECY_VPS_GIT_FORESIGHT_BUNDLE_2026-04-11.md` | B-only; Git·서지·§7.4 웹 딥리서치·격벽; **예언 전용 노트** `07_PROPHECY_BTRACK_2026Q2` · UUID `3e95ca50-66f8-4b54-b0ef-81821c199518` (레거시 `9de651e6-…` 대체) |
| 일반 미래 예측 데이터 계약(초안) | `docs/final/GENERAL_PROPHECY_SCHEMA_V1.json` | B-only; `CONSTITUTION` Prophecy 절 포인터; Phase 2–4 스크립트 미구현 |
| BTC 금융 Hub B — A/B 교차검증 브리프 | `docs/final/NOTEBOOKLM_HUB_B_BTC_AB_TRACK_CROSSCHECK_BRIEF_2026-04-04.md` | NotebookLM 소스 ID `bd996cd5-cb6e-444c-8110-eb2ce6a4c745` · 노트북 `b79929a2-8742-42a8-a4d7-06523e12935d` (2026-04-04 적재). OHLCV·온톨로지=B 연구 가설 vs A 본선 팩트 구분·Promotion Loop·Fact-Lock |
| Swarm 심리 메트릭 (B-track 데이터 계약) | `docs/final/SWARM_SENTIMENT_METRIC_SCHEMA_DRAFT.json` · `docs/final/dummy_swarm_score.jsonl` · `[HYPO]` 샘플 `docs/final/hypo_test_sentiment.jsonl` · 듀얼렌즈 1호 `[HYPO]` `docs/final/corr_report_001_hypo.jsonl` + 좌측 참고 `docs/final/corr_report_001_left_lens.json` | MiroFish류 군집 출력→이산 수치 JSON 계약(draft-07); 로컬 검증 `py scripts/validate_swarm_sentiment_dummy.py` 및 `--jsonl …`; 일괄: `scripts/Validate-SwarmSentimentBTrack.ps1`; CI: `swarm-sentiment-schema-validate.yml`; A-track 트리거·실매매 합선 금지 |
| Swarm 메트릭 Hub B 번들 (RAG) | `docs/final/SWARM_SENTIMENT_METRIC_NOTEBOOKLM_BUNDLE_2026-04-04.md` | NotebookLM 금융 Hub B 소스 ID `582bfa0b-ac4d-4715-9073-b170bd7a8719` — JSON 직접 업로드 불가 시 MD 번들로 동일 내용 인제스트 |
| MKMLIFE 뉴스 토픽 · 질문 스타터 | `docs/final/NOTEBOOKLM_MKMLIFE_NEWS_QUESTION_STARTER_BUNDLE_2026-04-12.md` | B-only; 토픽→질문 아이디어만·A/실매매·압축과 격벽; Vault 동기·NotebookLM 인제스트 후 mkmlife UI는 선택 |

### B-Track Major Reference (4D 융합·위성 코퍼스, OBSERVATION_ONLY)

작전지휘부·RAG가 **비교 배경(Comparative Background)** 으로 우선 인용할 B-Track 앵커 묶음. **A-Track·실매매 엔진 기본 로딩·자동 트리거 합선 금지** (`CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §4.5·격벽). `[HYPO]` 서술·승격은 인벤토리 스키마의 `promotion_status` enum(`draft`·`bench_only`·`superseded`·`retired`)만 사용.

| 우선순위 | 경로 | 비고 |
|----------|------|------|
| P0 | `docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json` | 정경 16-state↔verse 코사인 스냅샷; CROSS_REF의 `canonical_ref` 조인 기준 |
| P0 | `docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json` | DSS/외경·위성↔state v2; ENTRY_07·08·16은 line/witness 대기·`note`에 검증 조건 명시 |
| P0 | `docs/final/artifacts/B_TRACK_HYPOTHESIS_INVENTORY_V1.json` | B 가설 인벤토리; `CROSS_REF_DSS_TO_STATES_DRAFT`·`ENTRY_*` 교차 링크 |
| P1 | `projects/dss-4d-ingest/outputs/unified_frontline_cycle_report_command_center_followup_20260327_f.json` | **디스크에 존재하는** frontline 사이클 JSON. 종료 문서가 인용하는 `…_r_ext3` 가 레포에 없을 때 **본 파일을 SSOT**로 삼음 |
| P1 | `docs/final/NOTEBOOKLM_DSS_APOCRYPHA_BUNDLE_NOTE_command_center_followup_20260327_f.md` | DSS/외경 번들 노트(규칙·인사이트 우선순위) |
| P2 | `docs/final/DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md` | Frontline closeout 브리핑(위 표 JSON·`_r_ext3` 명명과 불일치 시 **실파일·위 표 우선**) |
| P2 | `docs/final/artifacts/original_corpus_regime_singularity_balanced_report_v1.json` | 레짐별 할당 특이점 B-track(코사인); A·실매매 합선 금지 |
| P2 | `docs/final/artifacts/original_corpus_regime_singularity_report_with_canon_v1.json` | DSS+외경+정경(`verse_decoded_v2`) 레짐 공명 스캔; `top_canon_singularities`=정경 레인만 상위 N |
| P2 | `docs/final/artifacts/original_corpus_regime_singularity_balanced_report_with_canon_v1.json` | 동일 입력에 균형 할당(per-regime quota)·`canon_jsonl` 포함 시 counts.canon_rows |
| P2 | `docs/final/artifacts/original_corpus_regime_singularity_canon_only_v1.json` | 정경 전용(`--canon-only`) 레짐 공명 스캔; DSS/외경 로딩 없이 canon lane만 계산 |
| P2 | `docs/final/artifacts/original_corpus_regime_singularity_canon_lane_summary_v1.json` | 정경 lane 가독 요약(top/global + regime별 상위); 특이점 원본 리포트의 파생 산출물 |
| P2 | `docs/final/artifacts/original_corpus_regime_singularity_balanced_canon_only_v1.json` | 정경 전용(`--canon-only`) 균형 할당(per-regime quota) 결과 |
| P2 | `docs/final/artifacts/original_singularity_gloss_report_v3.json` | 동일 유니온 행 글로스(v3·코드북 브리지·선택 오버라이드); 번역 확정 아님·[HYPO] 보조 |
| P2 | `docs/final/artifacts/original_singularity_gloss_report_v4.json` | v3 스택 + 검증 접두 탈형 체인(표면 길이 우선 첫 매핑); 공격적 정규화 금지·[HYPO] 보조 |
| P2 | `docs/final/artifacts/hebrew_singularity_gloss_overrides_v1.json` | 분석자 오버라이드(단편/DSS 형태 등); [HYPO] |
| P2 | `docs/final/artifacts/master_codebook_lexicon_v1_export_pointer_latest.json` | 최신 `master_codebook_lexicon_v1_*_rows_latest.json` 포인터(행 수·atoms 입력 SHA); 대용량 lexicon 본체는 `reports/constitution/btrack_pilot/` |

### B 보조 — Obsidian Context (Creative-Lock, 로컬 볼트)

**목적**: 레포·`docs/final`에 없는 **지휘관 의도·초안·런북 맥락**을 NotebookLM/Vault 미러에 올릴 때 사용. **A(Fact-Lock)를 대체하지 않음.** 민감·미완료·내부 은어는 선별·비식별 후 반영.

**로컬 SSOT 경로**: `memory/obsidian_vault/` (주 볼트; `AGENTS.md` 동일)

| 카테고리 (v4.7 매핑) | 실제 워크스페이스 경로 (디렉터리는 `*.md`만 Vault로 미러) | 비고 |
|----------------------|----------------------------------------------------------|------|
| 코어·대시보드 | `memory/obsidian_vault/00_Project_Core/` | S-L-K-M·12 도메인 대시보드 등 |
| 전략·연구 초안 | `memory/obsidian_vault/raw_research/` | 로드맵·NotebookLM·Kaggle·마케팅 메모 다수 |
| OPS·엔지니어링 | `memory/obsidian_vault/OPS/`, `memory/obsidian_vault/CODING/` | 런북 성격 |
| Theology / Logos 에세이 | `memory/obsidian_vault/SPIRIT/` | 일지·성찰 계열( B 궤적 ) |
| 시장·트레이딩 | `memory/obsidian_vault/TRADING/`, `memory/obsidian_vault/RESEARCH/` | 일지·리서치 |
| NotebookLM 인덱스 | `memory/obsidian_vault/NotebookLM*.md` (볼트 루트, 파일명 패턴) | 스크립트가 동적 매칭 |

**제외(동기화 스크립트)**: `.obsidian/`, `_cursor_session_staging/` (설정·스테이징 노이즈)

**Vault 미러 출력**: `G:\공유 드라이브\MKM_DATA_VAULT\vault\obsidian_context\` (또는 `MKM_VAULT_ROOT\obsidian_context\`) — `sync_notebooklm_sources_to_mkm_data_vault.ps1 -IncludeObsidianContext`

**소스 경로 오버라이드**: 실제 볼트가 레포 밖이면 환경 변수 `MKM_OBSIDIAN_VAULT_ROOT` 또는 같은 스크립트의 `-ObsidianVaultRoot`로 볼트 루트를 지정한다. 미지정 시 기본은 `<workspace>/memory/obsidian_vault`(`.gitignore`로 클론에 없을 수 있음); 첫 동기 시 해당 경로에 매니페스트 하위 폴더 스텁이 만들어진다.

---

## 이제마_B_Track (분리 원칙)

**원칙**: 라벨 코호트 **A**와 원전·프록시 코퍼스 **B**를 분리. **B를 본선 OOF에 자동 합선하지 않음.**

**인벤토리 기준일**: 2026-03-29 (`data/corpus/ijeoma/_inventory` 등).

### B 핵심 파일 (NotebookLM file 소스 7) — Vault 동기화 + NotebookLM `source_add` 권장

워크스페이스에 존재. **Source-Boost (2026-03-29)** + **AI-Logos 서지 (2026-03-29)** + **Deep Past Kaggle URL (2026-03-29)**: `notebook_get` 기준 B = **파일 소스 7** + **arXiv URL 3** + **Kaggle URL 3** + **Wikipedia URL 8** = **총 21**.

| # | 경로 | NotebookLM `source_id` (ingested) | 비고 |
|---|------|-----------------------------------|------|
| 1 | `data/corpus/ijeoma/originals/jeokcheonsu_core_logic_chunk.md` | `1b40f632-3a46-4fc2-9570-64f8c585817e` | 《적천수》맥락·일간 강약 스캐폴드(B-only; A·OOF 자동 합선 금지) |
| 2 | `data/corpus/ijeoma/schemas/myeongni_fusion_schema_v2_draft.md` | `cab11051-b771-4698-8ef3-70fb556a19d0` | JSON 스키마 v2 초안 MD(B 노트북에 업로드한 경로; SSOT) |
| 3 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md` | `24123e98-0a14-4a4c-9a4f-fbe7a53c198c` | B 전용 추론 경계 |
| 4 | `docs/final/myeongni_fusion_schema_v2_draft.md` | — | (2)와 동일 초안의 **문서 미러**; NotebookLM에는 **(2)만** 올려 중복 방지 |
| 5 | `docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` | (기존 B 등록) | 명리 융합 의사결정 JSON; B에 동명 파일 소스로 기존 반영 |
| 6 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` | — | §9 A/B 분리·구현 팩트; A 노트와 역할 구분 유지 |

### B 보조·인벤토리 (NotebookLM·Vault 동기화 시)

| 경로 | 비고 |
|------|------|
| `data/corpus/ijeoma/_inventory/IJEOMA_NOTEBOOKLM_QUERY_SET_2026-03-29.md` | 쿼리 세트 |
| `data/corpus/ijeoma/_inventory/IJEOMA_INSIGHT_UNITS_XINGMING_SAMPLE_2026-03-29.json` | 통찰 단위 샘플(JSON) |
| `data/corpus/ijeoma/_inventory/IJEOMA_INSIGHT_UNITS_SASANG_FOUR_SAMPLE_2026-03-29.json` | 사상 사본 샘플(JSON) |
| `data/corpus/ijeoma/_inventory/IJEOMA_CODEBOOK_INDEX_DRAFT_2026-03-29.json` | 코드북 인덱스 초안 |
| `data/corpus/ijeoma/e_drive_mirror/donguisusebowon_mastery_report.md` | 동의보감 마스터리 보고서(NotebookLM 소스) |

### 마스터·청크·인벤토리 (대용량·선택)

| 경로 | 비고 |
|------|------|
| `data/corpus/ijeoma/_inventory/IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json` | 마스터 매니페스트 초안 |
| `data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl` | 청크 테이블 |
| `data/corpus/ijeoma/_inventory/IJEOMA_CORPUS_INVENTORY_2026-03-28.json` | 코퍼스 인벤토리 |
| `data/corpus/ijeoma/_inventory/hwp_com_export_report.json` | HWP/COM보내기 리포트 |

### 통찰→팩트 후보 (승격 전 확인)

| 통찰→팩트 후보 | 제안 경로 또는 조건 | 비고 |
|----------------|---------------------|------|
| DSS Apocrypha proxy handoff 등 | `docs/final/DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md` | 본선 편입 전 A SSOT 갱신·검토 |

---

## Logos_MKM / Logos-Insight

**메타 가이드**: `docs/final/LOGOS_NOTEBOOK_META_GUIDE.md`

**용어 (L2 브리핑)**: “Logos Lens / Ruleset” 표기는 구현·산출물 **로고스 독립 렌즈**와 동일 계열로 본다 — `logos_independent_lens` → `docs/final/artifacts/logos_independent_lens_latest.json`, `scripts/run_lens_logos.py`, `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 표.

| 우선순위 | 경로 (워크스페이스 기준) | 비고 |
|----------|--------------------------|------|
| P0 | `docs/final/LOGOS_NOTEBOOK_META_GUIDE.md` | Logos-Insight 경계(금융/레짐 비혼선) |
| P0 | `docs/final/LOGOS_RISK_BRIDGE_v1.md` | Logos–시장 심리·레짐 **메타** 브리지(가설·v1; verse 파이프와 분리) |
| P0 | `data/logos/verse_4pipeline_full_31102.json` | 4D verse 풀(31102절) |
| P0 | `data/logos/bible_original_hebrew_greek.jsonl` | 원어 라인 |
| P1 | `data/logos/manuscripts/dss_parsed.jsonl` | 사해사본 파싱 JSONL (Logos GPU·벤치 `--include-dss-apocrypha`) |
| P1 | `data/logos/manuscripts/apocrypha_std.jsonl` | 외경 표준 JSONL (동일) |
| P1 | `data/logos/bible_original_verses.jsonl` | 원문 절 라인 |
| P1 | `data/logos/bible_original_for_decode.jsonl` | 복호·해석용 |
| P1 | `data/logos/aruljohn_kjv/` | KJV per-book JSON |
| P2 | `data/logos/reports/ensemble_core_v1_1.csv` | Core 앙상블 CSV(기술 서술 시 **311** 구절) |
| P2 | `data/logos/reports/logos_core_verses_20260315.md` | Core 구절 MD |
| P2 | `data/logos/reports/logos_wide_20_for_notebooklm.json` | Wide 20 권보내기(JSON) |
| P2 | `data/logos/reports/logos_wide_20_for_notebooklm.csv` | Wide 20 권보내기(CSV) |
| P2 | `data/regimes/btc_regime_map.json` | BTC 레짐 맵(`scripts/logos_vector_resonance_probe.py` `--rank-by-regime` FULL 시 입력) |
| P2 | `backtest_results/LOGOS_RESONANCE_BTC_BULL_FULL.json` | canon-only FULL 공명(BULL); `verses_scanned` 31102; 스키마 `logos_resonance_probe_v2` |
| P2 | `backtest_results/LOGOS_RESONANCE_BTC_BEAR_FULL.json` | canon-only FULL 공명(BEAR); 동일 |
| P2 | `backtest_results/LOGOS_RESONANCE_BTC_SIDEWAYS_FULL.json` | canon-only FULL 공명(SIDEWAYS); 동일 |
| — | `.cursor/rules/logos-first-pipeline.mdc` | 근원(Logos)과 확장 레이어 분리 |

**확장 후보(용량·라이선스 검토 후)**

- `data/logos/bibles/hebrew_bhs_sanitized.jsonl`
- `data/logos/bibles/greek_septuagint_public.md`
- `data/logos/bibles/kjv_public_domain.txt`
- `data/logos/manuscripts/dead_sea_scrolls_summary.md` — 요약·가이드; **본선 JSONL SSOT는** `dss_parsed.jsonl`
- `data/logos/manuscripts/apocrypha_guide.md` — 요약·가이드; **본선 JSONL SSOT는** `apocrypha_std.jsonl`
- **보류(미작성)**: `docs/final/LOGOS_PIPELINE_SPEC_V1.md`, `docs/final/GEMATRIA_CODEBOOK_CONCEPT.md` — 현재 워크스페이스에 **파일 없음**. 대체 SSOT: `docs/final/LOGOS_NOTEBOOK_META_GUIDE.md`, `docs/final/LOGOS_RISK_BRIDGE_v1.md`, `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`. 독립 스펙이 생기면 본 표에 경로만 추가(중복 MD 남발 금지).

---

## 통찰 승격 (Promotion Loop)

1. B에서 가설·통찰 산출.  
2. 검증·편집 후 팩트/코드북/레짐 정책에 반영.  
3. `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`에 **구현·경로** 갱신 시 A 궤적·Cursor 규칙과 정합 유지.

---

## 작전지휘부(Ops) NotebookLM 메모 (2026-04-03)

- **2026-04-03 L2 Logos KOSPI Shadow 동기화**: Vault 미러에 다음이 포함됨 — `docs/final/NOTEBOOKLM_OPS_COMMAND_BRIEF_LOGOS_SHADOW_2026-04-03.md`(상황·NotebookLM 질의 세트), `docs/final/artifacts/LOGOS_SHADOW_202003_INSIGHT_BRIEF_V1.md`, `docs/final/artifacts/logos_kospi_shadow_evaluation_bundle_v23_notebooklm.md`(v23 번들 JSON의 Markdown 래퍼; NotebookLM 파일 업로드는 `.json` 미지원 사례 대비). SSOT 수치는 여전히 `reports/research/logos_shadow_v1/logos_kospi_shadow_evaluation_bundle_v23_latest.json`. 작전지휘부 노트북에는 MCP `source_add`(동일 제목 구버전 있으면 `source_delete`로 정리 후) 권장.
- **2026-04-03 (브리지 정정)**: `NOTEBOOKLM_OPS_COMMAND_BRIEF_LOGOS_SHADOW_2026-04-03.md`에 **`--bare` vs `DEFAULT_SHADOW_EXTRA`(latest)** 이중 스냅샷과 SSOT 주의문을 반영함. 문서만 보고 “전 구간 미통과”로 단정하지 말 것.
- **2026-04-03 (v23 MD 래퍼)**: `docs/final/artifacts/logos_kospi_shadow_evaluation_bundle_v23_notebooklm.md`는 `v23_latest.json`과 불일치 시 `py scripts/regen_logos_kospi_shadow_v23_notebooklm_md.py`로 재생성. 일괄: `pwsh -File scripts/Invoke-LogosKospiShadowNotebooklmBundle.ps1` (옵션 `-SyncVault`). Ablation 요약은 `reports/.../logos_kospi_shadow_ablation_v23_round1_summary.json`(Vault 동기화 목록에 포함).
- **NotebookLM**: 노트북명 `작전지휘부 Ops20260318`, ID `347e5cbe-0ade-4615-9aac-8747d4fa644e`, 소스 **13**개 (`notebook_list` 2026-04-02 재확인). 과거 중복 제거 이력(230→151)은 보존하되, 운영 판단 시에는 **현재 MCP 조회값**을 우선한다.
- **전체 wipe**: **기본 금지**. 소스 대량 삭제는 사용자가 **명시적으로 재구축·전체 재업로드**를 요청한 경우에만 수행.
- **`OPS_ONEPAGE_STATUS_LATEST.md`**: 워크스페이스 `docs/final/OPS_ONEPAGE_STATUS_LATEST.md`는 **미존재**할 수 있음. NotebookLM에는 소스 **제목**으로만 존재할 수 있음. 새 MD 남발 대신 `docs/final/` 기존 SITREP·본 매니페스트에 **Gap 한 줄** 기록.

## Internal 95+ briefing bridge (2026-05)

- NotebookLM은 브리핑 근거 확장용으로 사용하되, 응답 생성은 항상 내부 표준화 계약(`intent/scope/constraints/output/evidence/uncertainty`)을 거친다.
- 권장 출력 고정 순서: `Field(Regime) -> Lens(사상/명리/성경) -> Conflict Resolver -> Final Action -> Evidence Index`.
- NotebookLM에서 가져온 내용은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 `docs/final/artifacts/*_latest.json`과 교차 검증 후만 승격한다.
- **로컬 브리지 문서**: `docs/작전지휘부/` 등 경로는 **Vault·다른 머신에만** 있을 수 있음. `source_add` 전 **파일 존재 확인** 필수.

### 파일 기반 장기기억(.mkm-memory) — 멀티렌즈 압축·4D 동기화 (A, 2026-04)

- **역할**: NotebookLM 질의 시 **본 절 + 아래 경로**를 `source_add`하면 작전지휘부 노트에서 **B/High·B/Ultra·A/Extreme 파일럿·재색인 절차**를 근거로 답할 수 있음(측정값은 레포 JSON이 SSOT).
- **파일럿 실행**: `scripts/pilot_compress_mkm_memory_queue.py` — `reports/memory/mkm_memory_priority_queue_latest.json` 기준; P1 헤드 스윕 산출 예: `mkm_memory_pilot_sweep_ultra_latest.json`, `mkm_memory_pilot_conservative_p1head_latest.json`.
- **비교 매트릭스**: `reports/memory/mkm_memory_pilot_sweep_matrix_latest.json`.
- **`content` 변경 후 `vector_4d`**: 동기화 필수 — `tools/tools/core/file_based_memory.py`(`hybrid_vectorize`) 및 `reports/memory/mkm_memory_vector_4d_reindex_paths_v1.json` 참조. `scripts/normalize_mkm_memory_vector_4d.py`는 **중첩 필드 호이스트**용이며 **새 텍스트 재임베딩 대체 아님**.
- **운영 GO/NO_GO**: `reports/memory/mkm_memory_ultra_compression_go_checklist_v1.json` + `reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json` + `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json` **교차** (민감 무결성·카나리·`go_no_go`).
- **격벽**: 파일럿 수치(A)와 NotebookLM 서술(B) 혼동 금지; 본선 `memory/` **인플레이스 쓰기**는 승인·백업·롤백 게이트 후 — `reports/memory/mkm_memory_rollout_gates_v1.json`.

---

## 만세력·사주 NotebookLM (A/B 참조)

**역할**: **A = Fact-Lock(제품·팩트)**, **B = Creative-Lock(연구·통찰)**. 작전지휘부·Logos와 동일하게 **전체 wipe 지양**, 파일 단위 `source_add`만.

| 구분 | NotebookLM 노트북 ID (참고) | 비고 |
|------|-----------------------------|------|
| A (팩트) | `31e6d45a-4a0e-40e6-a010-9c03a6ec1239` | 표 ID와 일치 (`notebook_get` 2026-03-29 검증). **계정·프로필 전환 시** UI 또는 `notebook_get`으로 재확인 |
| B (통찰) | `af639d3e-b455-4f3f-8e25-47f58d962c60` | 동일 |

**MCP 검증 (2026-03-29, 현재 계정)**: `notebook_get` 성공 — A 제목 `만세력·사주_AI_A_제품 (MKM Fact-Lock)`, 소스 **7**개; B 제목 `만세력·사주_AI_B_연구 (MKM Abstract)`, 소스 **21**개(파일 7 + arXiv 3 + Kaggle 3 + Wikipedia 8). **Source-Boost ([A] 경로, 2026-03-29)** + **AI-Logos 번들 URL·서지** + **Deep Past Initiative Kaggle `source_add`** 반영 후 **`notebook_get` 재확인** — B 총 **21**.

**장부 최종 동기화 (`notebook_get` 재실측, 2026-03-29, Operation [B])**: `notebook_id` `af639d3e-b455-4f3f-8e25-47f58d962c60` — `source_count` **21** (Deep Past Kaggle URL 엔트리 추가). 아래 표는 API 반환 **`title`·`id` 원문**으로 SSOT 박제(위키·Kaggle 표시명은 UI와 동일).

**B — AI-Logos 외부 연구 번들 (LeWorld-Enlightenment, 2026-03-29)** — arXiv·Kaggle **URL** + 로컬 서지 MD `source_add` 후 **`notebook_get`으로 소스 수 재확인** (아래는 Confirmed 링크만; “Project Enoch” 등 미검증 주장은 **서지 TBD**).

| 구분 | URL |
|------|-----|
| [PAPER] LeWorldModel | `https://arxiv.org/abs/2603.19312` |
| [PAPER] DSS ink/parchment segmentation | `https://arxiv.org/abs/2411.10668` |
| [PAPER] DSS writer ID (1QIsaa) | `https://arxiv.org/abs/2010.14476` |
| [KAGGLE] Vesuvius ink detection | `https://www.kaggle.com/competitions/vesuvius-challenge-ink-detection` |
| [KAGGLE] CommonLit readability (텍스트 회귀 참고) | `https://www.kaggle.com/competitions/commonlitreadabilityprize` |
| [KAGGLE] Deep Past Initiative (Akkadian→English MT) | `https://www.kaggle.com/competitions/deep-past-initiative-machine-translation` — **NotebookLM URL 소스** `f0cbb85f-b5bf-4ec5-b958-4c690d282a01` (제목: Deep Past Challenge - Translate Akkadian to English \| Kaggle). 서지 `AI-Logos_Research_Bibliography_2026.md`와 병행. |

- **로컬 서지 (file)**: `C:\workspace\docs\external_research\AI-Logos_Research_Bibliography_2026.md` — `source_type: file`, `wait: true`.

**B 노트 전체 소스 (Fact-Locked, `notebook_get` 2026-03-29)** — `source_count` = **21** (API `sources` 순서):

| # | `source_id` | `title` (API) |
|---|-------------|---------------|
| 1 | `c0835f38-3442-4556-8c6d-d482218c5160` | AI-Logos_Research_Bibliography_2026.md |
| 2 | `c8c33f64-1591-4e27-9c79-6ac7f467b28f` | AI_MYEONGNI_MANSE_EXTERNAL_REFERENCE_LANDSCAPE_2026-03-29.md |
| 3 | `24123e98-0a14-4a4c-9a4f-fbe7a53c198c` | CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md |
| 4 | `0936b481-8411-462a-bc84-f31b2e67a0f3` | Chinese calendar - Wikipedia |
| 5 | `8040cf3b-9788-48e3-81c8-585479747f8a` | CommonLit Readability Prize \| Kaggle |
| 6 | `f0cbb85f-b5bf-4ec5-b958-4c690d282a01` | Deep Past Challenge - Translate Akkadian to English \| Kaggle |
| 7 | `7397498f-ae59-42eb-bc13-743cd685bbbb` | Four Pillars of Destiny - Wikipedia |
| 8 | `7d7417ac-0adc-4d9f-9dd9-21e60fb5f91c` | Korean calendar - Wikipedia |
| 9 | `b7af7a11-d243-4f0f-ab7b-15b99a51a1cd` | Lunisolar calendar - Wikipedia |
| 10 | `0c755abd-592d-4347-9306-3226380b5934` | MANSE_SAJU_AI_RESEARCH_SYNTHESIS_2026-03-29.md |
| 11 | `77ae458c-259f-4e92-ad12-ae5e2bd650f8` | MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json |
| 12 | `cc9dd0b9-393b-4f0a-a458-6c48b7ada4f5` | Sexagenary cycle - Wikipedia |
| 13 | `45bc0dac-0b90-4786-9474-58fcfc1708a1` | Vesuvius Challenge - Ink Detection \| Kaggle |
| 14 | `0939abb4-73dc-49e4-aee7-75518fd5e410` | [2010.14476] Artificial intelligence based writer identification generates new evidence for the unknown scribes of the Dead Sea Scrolls exemplified by the Great Isaiah Scroll (1QIsaa) |
| 15 | `f4a61719-9678-46c6-be81-302e003dd99b` | [2411.10668] Segmentation of Ink and Parchment in Dead Sea Scroll Fragments |
| 16 | `794cf83b-4bce-4452-82fc-55b279be31a8` | [2603.19312] LeWorldModel: Stable End-to-End Joint-Embedding Predictive Architecture from Pixels |
| 17 | `1b40f632-3a46-4fc2-9570-64f8c585817e` | jeokcheonsu_core_logic_chunk.md |
| 18 | `cab11051-b771-4698-8ef3-70fb556a19d0` | myeongni_fusion_schema_v2_draft.md |
| 19 | `a60a8dc9-9ec3-4235-ac7d-0a8618f903d6` | 만세력 - 위키백과, 우리 모두의 백과사전 |
| 20 | `f1403d37-9616-408f-aae0-8404a80abc0b` | 사주 - 위키백과, 우리 모두의 백과사전 |
| 21 | `1291ea4c-53a7-43bd-8fb1-892a9e8b143d` | 사주명리학 - 위키백과, 우리 모두의 백과사전 |

**A 노트 소스 제목 (요약, `notebook_get`과 동일)** — 카운트 **7**; 상세 ID 목록은 필요 시 동일 절차로 `notebook_get`(`31e6d45a-4a0e-40e6-a010-9c03a6ec1239`) 실측.

**B — Wikipedia URL SSOT (`source_add` 2026-03-29)** — 통찰·참고 전용; 본선 OOF·A와 무단 합선 금지.

```
https://en.wikipedia.org/wiki/Four_Pillars_of_Destiny
https://en.wikipedia.org/wiki/Korean_calendar
https://en.wikipedia.org/wiki/Sexagenary_cycle
https://en.wikipedia.org/wiki/Lunisolar_calendar
https://en.wikipedia.org/wiki/Chinese_calendar
https://ko.wikipedia.org/wiki/%EC%82%AC%EC%A3%BC
https://ko.wikipedia.org/wiki/%EB%A7%8C%EC%84%B8%EB%A0%A5
https://ko.wikipedia.org/wiki/%EC%82%AC%EC%A3%BC%EB%AA%85%EB%A6%AC%ED%95%99
```

**명리 스키마 B 반영 (2026-03-29)**: SSOT는 `docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json`. 파일 소스 `source_add`가 실패한 경우 **`source_type: text`**로 본문 전체 업로드 가능 — B에 `MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` 제목으로 등록됨(`source_id` `77ae458c-259f-4e92-ad12-ae5e2bd650f8`). 구현·경로 팩트는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §7과 정합 유지.

**소스 경로 SSOT**: 워크스페이스에 `docs/작전지휘부/CURSOR_CHAT_NOTEBOOKLM_COMMAND_BRIDGE_2026-03-28.md`가 **있을 때** 해당 MD의 `[FACT] 만세력·사주 이원 노트` 블록을 우선. **없으면** 본 매니페스트 **A/B 궤적** 표와 사용자가 지정한 경로만 사용. **`scripts/push_manse_saju_notebooklm_from_manifest.ps1`는 존재하지 않음** (벌크 푸시 스크립트 금지).

**갱신 절차**: `notebook_get` → 갱신할 파일 `Test-Path` → MCP `source_add`(`source_type: file`, `file_path`, `wait: true`).

---

## B-Track — 사해(DSS)와 외경 순차 작업 (권장 운영, 2026-03-30)

**목적**: 노트북 한 곳에 DSS·외경을 **처음부터 한꺼번에 융합**하면 출처·인용이 섞여 통찰 품질이 떨어지기 쉬움. **비트코인·16상 매핑 없이** 순수 문헌 통찰만 뽑을 때도 동일 원칙 적용.

| 단계 | 범위 | NotebookLM 조작 |
|------|------|-----------------|
| **1** | **DSS·쿰란만** (1QM, 1QS, 페셔 등) | **별도 노트** 권장(예: 제목에 `DSS-only`). 소스는 아래 DSS Fusion 표의 MD·URL 중 DSS에 해당하는 것만 우선. 질의마다 *「지금은 사해/쿰란 사본만 인용」* 문구 명시. |
| **2** | **외경·유경만** (1에녹, 희년서, 마카베오기 등) | **다른 노트**로 분리(예: `Apocrypha-only`). 1단계 노트와 소스를 섞지 않음. 번역·요약 MD 청크를 `source_add`할 때도 코퍼스별로 나눔. |
| **3 (선택)** | 두 전통 **대조** | 1·2에서 내보낸 **요약·핵심 구절 표**만 세 번째 노트에 모으거나, Cursor 채팅에 투하하여 대조. **기존 DSS Fusion 번들 노트**(`2b2eeff1-…`)는 참고·아카이브용; 순차 1·2와 혼동되면 **새 노트**가 더 안전. |

**금지(권장 수준)**: 1단계 미완에 2단계 소스를 같은 노트에 대량 추가하여 *즉시* “통합 사상” 질의만 하는 방식 — 인용 혼선 유발.

**격벽**: 본 절은 **NotebookLM·연구 워크플로** 안내. 정경 31,102 파이프라인·A-Track 실매매 코드와 **자동 합선 없음** (`CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 멀티 코퍼스 표와 동일).

**MCP 자동 생성 노트 (2026-03-30, `notebook_create` + `source_add`; 이후 보강 반영)**

| 노트 제목 | `notebook_id` | URL | `source_count` / 비고 (2026-03-30 갱신) |
|-----------|---------------|-----|----------------------------------------|
| B-Track DSS-only (Qumran) 2026-03-30 | `3839cf65-d97c-465c-a252-7ca9441af201` | `https://notebooklm.google.com/notebook/3839cf65-d97c-465c-a252-7ca9441af201` | **`notebook_get` 실측 10** (2026-03-30) — 스코프·메타·리스크·DSS 아카이브 URL·arXiv 2건·`btrack_dss_1QM_col1_excerpt.md`·`btrack_dss_1QS_sectarian_context.md`·`btrack_dss_1QS_pure_discipline.md` |
| B-Track Apocrypha-only 2026-03-30 | `17ab44ab-0f62-4714-99ac-12688a469597` | `https://notebooklm.google.com/notebook/17ab44ab-0f62-4714-99ac-12688a469597` | **`notebook_get` 실측 10** (2026-03-30) — 동일; **`btrack_apocrypha_jubilees_calendar_364.md` NL 재동기화**(구 소스 삭제 후 최신 로컬 재`source_add`, 2026-03-30)로 Charlesworth·1에녹 72–82 병치 문단 인덱스 확인 |
| B-Track Phase3 Contrast (exports only) 2026-03-30 | `aced4a3e-6ece-4770-b46d-46e1454da893` | `https://notebooklm.google.com/notebook/aced4a3e-6ece-4770-b46d-46e1454da893` | **`notebook_get` 실측 2** — `Phase3 — 사용법…` + **`btrack_phase3_cross_ref_snapshot.md` 재동기화**(구 `cc37772c…` 삭제 → 신 `4a76d12a…`, ENTRY_01–10·`generated_at_utc` JSON 정합, 2026-03-30) |

---

## DSS Fusion Sources (DSS + 외경)

**역할**: DSS·외경(Apocrypha) 번들·리스크·구현 팩트를 한 노트에 모음. **JSONL**은 NotebookLM 파일 업로드가 실패할 수 있으므로 **`docs/final/*.md`** 위주로 `source_add`.

| 항목 | 값 |
|------|-----|
| **제목** | DSS Fusion Sources 2026-03-26 |
| **notebook_id** | `2b2eeff1-1bac-424c-9128-59d0f0946908` |
| **URL** | `https://notebooklm.google.com/notebook/2b2eeff1-1bac-424c-9128-59d0f0946908` |

**`notebook_get` 검증 (2026-03-29)**: `source_count` **8**.

**[Deduplication-Audit] (2026-03-29)**: 본 노트(`2b2eeff1-1bac-424c-9128-59d0f0946908`) 및 **만세력·사주 B**(`af639d3e-b455-4f3f-8e25-47f58d962c60`, `source_count` 21)에 대해 `notebook_get` 실측 후 **정규화 제목**(앞뒤 공백 제거·연속 공백 통일) 기준 **완전 동일 쌍 없음**. 참고: DSS 노트 URL 2건은 *The Dead Sea Scrolls* vs *The Dead Sea Scrolls - Explore the Archive*로 **문자열이 달라** 엄격 중복 아님(의미상 근접 시 수동 병합은 선택).

| 소스 제목 (표시명) | 비고 |
|-------------------|------|
| `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` | 구현 팩트 SSOT |
| `DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md` | DSS·외경 프론트라인 클로즈아웃 |
| `LOGOS_NOTEBOOK_META_GUIDE.md` | 노트북 메타 가이드 |
| `LOGOS_RISK_BRIDGE_v1.md` | 리스크 브리지 |
| `NOTEBOOKLM_DSS_APOCRYPHA_BUNDLE_NOTE_command_center_followup_20260327_f.md` | 번들 노트 |
| *(URL)* GitHub - ETCBC/dss … | Abegg/TF 참조 |
| *(URL)* The Dead Sea Scrolls | 외부 DSS |
| *(URL)* The Dead Sea Scrolls - Explore the Archive | 아카이브 탐색 |

**`source_add` 로컬 파일 확정 (2026-03-29, `Test-Path` 전부 True)** — NotebookLM MCP `source_type: file` 시 `file_path` 예시:

| # | `file_path` (Windows) |
|---|------------------------|
| 1 | `C:\workspace\docs\final\CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` |
| 2 | `C:\workspace\docs\final\DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md` |
| 3 | `C:\workspace\docs\final\LOGOS_NOTEBOOK_META_GUIDE.md` |
| 4 | `C:\workspace\docs\final\LOGOS_RISK_BRIDGE_v1.md` |
| 5 | `C:\workspace\docs\final\NOTEBOOKLM_DSS_APOCRYPHA_BUNDLE_NOTE_command_center_followup_20260327_f.md` |

위 5개는 **MD·SSOT**로 DSS Fusion 노트와 정합; **JSONL**은 업로드 실패 가능성이 있어 본 노트의 직접 소스로는 권장하지 않음.

**원시 코퍼스** (`data/logos/manuscripts/*.jsonl`)는 노트에 직접 붙이기 어려울 수 있음 → 필요 시 **MD/TXT 청크** 또는 **PDF**로 내보낸 뒤 `source_add file`.

---

## 차기 작업 (Gap)

- **Blind Replay C.1 (2026-04-02)**: ✅ Phase C.1 피처 확장 산출물 반영 완료 — `BLIND_REPLAY_PROXY_PROFILE_D_PARAMS_V1.json`, `BLIND_REPLAY_PROXY_PROFILE_D_ENSEMBLE_SEARCH_V1.json`, `aegis_unified_scoreboard_abcds_latest.json`, `blind_replay_dataset_grid_btc_s80_latest.json`, `blind_replay_dataset_grid_kospi_s80_latest.json`를 NotebookLM 동기화 스크립트 복사 목록에 추가.
- **B — AI-Logos 번들**: ✅ `source_add`(URL 5 + file 서지) 반영·**`notebook_get` B=21** 확인(2026-03-29; Deep Past Kaggle URL 추가). ✅ 서지에 **arXiv 2407.12013(Enoch)**·**deeppast.org** Confirmed 반영(2026-03-29). ✅ Deep Past **Kaggle 대회 URL**: 서지 `AI-Logos_Research_Bibliography_2026.md` + **NotebookLM URL 소스** `f0cbb85f-b5bf-4ec5-b958-4c690d282a01` (`source_add`, 2026-03-29). ✅ **Operation [B] 장부**: 매니페스트에 B 노트 **21개 전체** `source_id`·`title` 실측 표 박제(2026-03-29).
- **B — `notebook_query` (노트 `af639d3e-b455-4f3f-8e25-47f58d962c60`)**: Q1/Q2 Gap 유지. ✅ **후속 적층 질의**(LeWM 초록 ↔ DSS 세그멘테이션·필적 식별 대조, 사실/가설 표·비유 한계) `conversation_id` **`deb0fc0c-5e20-4041-a917-0fe240f0b2bb`**로 실행·응답 수신(2026-03-29); 인용 소스 ID: `794cf83b-…`(LeWM), `f4a61719-…`(2411.10668), `0939abb4-…`(1QIsaa).
- **Logos BTC 공명**: canon-only **BULL/BEAR/SIDEWAYS FULL** 산출물은 본 매니페스트 Logos 표에 등록됨. **Ancient-expanded**(`--ancient-resonance`)는 별도 파일명으로 실행·등록(캐논 FULL 시리즈와 혼선 금지).
- **이제마 B**: Source-Boost·AI-Logos 번들·Deep Past Kaggle URL 반영·`notebook_get` B=21 확인 후 — 통찰 품질·중복 소스 점검, 필요 시 Vault `sync_notebooklm_sources_to_mkm_data_vault.ps1`. `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §9·B 표와 정합 유지.  
- **명리**: SSOT `MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json`는 B에 동기화됨; MD 스키마 초안은 `data/corpus/ijeoma/schemas/myeongni_fusion_schema_v2_draft.md`(B 노트 등록)와 `docs/final/myeongni_fusion_schema_v2_draft.md`(미러). 본선 OOF·실매매 트리거 자동 연동은 **헌법·팩트 문서에서 명시된 구현 경로가 있을 때만** — 스키마만으로 자동 합선하지 않음.
- **명리 승격 게이트 최신 실측 (2026-05-06)**: `docs/final/artifacts/myeongni_promotion_gate_latest.json`에서 `status=PASS`, `decision=MANUAL_PROMOTION_REVIEW_GO`; 단, 정책은 `track_b_to_a_auto_bridge=false`, `live_trigger_auto_enabled=false`, `human_signoff_required=true` 유지(자동 승격/자동 실전 합선 금지).
- **날씨/일반예언 explainability 최신 실측 (2026-05-06)**: `docs/final/artifacts/general_prophecy_explainability_quality_v1_latest.json` 기준 `coverage_rate=1.0`, `conflict_resolution_rate=1.0`, `reproducible_evidence_rate=1.0`, `direct_match_rate=1.0`, `fallback_match_rate=0.0`; holdout 분리/게이트는 `general_prophecy_explainability_holdout_report_v1_latest.json`·`general_prophecy_explainability_holdout_gate_v1_latest.json`에서 `decision=GO_HOLDOUT_STABLE`, `all_pass=true` 확인. 스케줄러는 `Register-GeneralProphecyDailyQueueTask.ps1`로 `\GeneralProphecyDailyQueueV1`를 `-HoldoutGateProfile ops`로 고정 가능하며, holdout 경보는 `alert_general_prophecy_holdout_gate_v1.py`가 WARN에서만 발송하고 결과 JSON에 `failed_check_keys`를 남긴다(`general_prophecy_explainability_holdout_alert_latest.json`). 동일 시점 명리 게이트 재생성(`build_myeongni_promotion_go_nogo_v1.py`) 후 `myeongni_promotion_gate_latest.json` `weather_signal_linked=true` 및 `myeongni_promotion_failure_analysis_latest.json` `warn_count=0` 확인.
- **holdout evolution + 명리 v2 자동 산출 (2026-05-06)**: 일일 체인 `run_general_prophecy_daily_queue_refresh_v1.ps1`에 후보/ablation 단계가 연결되어 `general_prophecy_holdout_evolution_candidates_latest.json`(`proposal_only_no_auto_apply`)·`general_prophecy_holdout_evolution_ablation_latest.json`이 자동 생성된다(현재 추천 `recommended_candidate_id=noop_keep_current_policy`). 주간 운용은 `Register-GeneralProphecyHoldoutEvolutionWeeklyTask.ps1`로 `\GeneralProphecyHoldoutEvolutionWeeklyV1`(SUN 09:00, ops 프로파일) 등록되었고 수동 1회 실행 `LastResult=0` 확인. 동일 체인 말단에서 `build_mkm_myeongni_response_v2.py` + `validate_mkm_myeongni_response_v2.py`를 실행해 `mkm_myeongni_response_v2_latest.json`을 생성/검증하며, 코디네이터는 `direction_override_allowed=false`를 유지한 채 weather를 confidence-only로 반영한다. 캘리브레이션 추천 산출(`mkm_myeongni_response_v2_calibration_latest.json`) 기준 임계값(`hold=0.36`, `reduce_direction=0.45`, `reduce_confidence=0.64`)을 적용한 최신 결과는 `decision=WATCH`.
- **헬스 확장 스위치 (2026-05-06)**: `run_workspace_automation_health.ps1`에 `-IncludeGeneralProphecyEvolutionHealth`(선택 strict: `-StrictGeneralProphecyEvolutionHealth`)가 추가되어 ablation/myeongni v2/주간 태스크 상태를 종합 점검하고 `general_prophecy_evolution_health_latest.json`를 남긴다. 동시에 히스토리 `general_prophecy_evolution_health_history_v1.jsonl`를 누적해 `myeongni_v2_decision_counts`, `ablation_recommended_candidate_id_counts`, `myeongni_v2_watch_streak` 추세를 기록한다.
- **운영 런북 (실패 시 3단계 점검)**: 1) `general_prophecy_explainability_holdout_gate_v1_latest.json`에서 `decision/checks/failed_check_keys` 확인 → 2) `general_prophecy_explainability_holdout_alert_latest.json`에서 `dispatch_result/webhook_dispatched` 확인 → 3) `general_prophecy_daily_queue_failure_summary_latest.json`에서 `failed_step/exit_code/holdout_gate_profile` 확인.
- **Fact-Lock 번들 strict 보강 (2026-05-06)**: `run_fact_lock_bundle.ps1` 말단 헬스가 `-IncludeGeneralProphecyTaskProfileGuard -StrictGeneralProphecyTaskProfileGuard -IncludeGeneralProphecyEvolutionHealth -StrictGeneralProphecyEvolutionHealth`까지 포함하도록 고정되어, `\GeneralProphecyDailyQueueV1`의 `-HoldoutGateProfile ops` 누락 드리프트와 evolution/myeongni v2 상태를 기본 감시한다.
- **축약 Fact-Lock 실패 복구 리허설 (2026-05-06, 최종 갱신)**: `bridge_adjustment` confidence lane 수정 + 누락 매니페스트/컨트랙트/fixture/lexicon 복구 후 전체 번들 재실행 `exit_code=0 (ALL OK)` 달성. 경과는 `29 -> 1 -> 0`으로 수렴했고 최종 분류/근거는 `docs/final/artifacts/fact_lock_failure_classification_latest.json`에 반영됨.
- **Master Probe (2026-03-29)**: ✅ 매니페스트 **A 궤적** 및 **§명리 16-State Master Probe**에 `data/myeongni/16_STATE_MASTER_PROBE_v1.json`·`data/myeongni/myeongni_16_state_experiment_20260329.jsonl` 경로·격벽·검증 질의 SSOT 박제. 차기(선택): 대상 노트북에 `source_add`(file)로 JSON 주입 후 본문 §검증 질의로 권위 응답 확인.
- **Track C Agentic 방향성 (2026-05-05)**: ✅ 사업계획 `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md`에 §12(Agentic Economy Direction Lock) 반영. NotebookLM 브리핑 시 질문 우선순위를 `policy/authority/audit trail/exception queue`로 고정하고, `UI 기능` 중심 질의는 후순위로 둔다.

---

**상태**: A 궤적 · Logos-Insight 표(wide_20 JSON/CSV 포함) · **BTC 레짐 공명 FULL JSON 3종·btc_regime_map** 매니페스트 반영 · 이제마 B 분리 · 작전지휘부 151 소스·wipe 정책 · 만세력·사주 A/B `notebook_get` 검증 완료(표 ID 일치; **B 소스 21개**·파일 7·arXiv 3·Kaggle 3·위키 8·AI-Logos 서지·명리 스키마·외부 참조 랜드스케이프·Deep Past Kaggle URL) · **B `notebook_query`** 소스-바운드 Q1/Q2 Gap 기록(2026-03-29) · **DSS Fusion** 노트(`2b2eeff1-…`) 소스 8개 검증 · OPS_ONEPAGE Gap 기록 정책 · **Master Probe v1 / 16-State 정본(2026-03-29) 매니페스트 SSOT** (2026-03-29)
· **Codebook Runtime Pack 명칭 고정** (`codebook_runtime_pack`, legacy `codepack_recovery` 호환) 및 readiness 아티팩트 A 궤적 반영 (2026-04-09)
