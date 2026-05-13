# AGENTS — 워크스페이스 에이전트 SSOT 포인터

**역할**: Cursor/Athena 에이전트가 먼저 읽는 **짧은 진입점**이다. 상세 규칙은 아래 파일이 주도한다.

## 로컬↔VPS 운영 표준 (충돌 방지 SSOT)

- **정책 단일 SSOT:** `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`
- **실행 절차 부록:** `docs/final/FINANCIAL_PROPHECY_VPS_LIVE_TRADING_DIRECTIVE_V1.md`
- **원칙 고정:** 코드/전략 동기화는 상시, 실전 주문 활성화(ON/OFF)는 별도 승인 게이트
- **보수 하드라인(v1):** `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`의 `24h 보수 운영 하드라인 (Fact-Lock v1)`을 실전 기본값으로 적용

## 로컬 PC 전용 경로 (Git에 올리지 않음)

- **템플릿(추적):** `docs/final/LOCAL_MACHINE_POINTER_V1.template.md` — bare·클론·Vault 마운트 등 **한 대 PC만** 쓰는 경로를 적는 절차.
- **실제 파일(비추적):** `docs/final/LOCAL_MACHINE_POINTER_V1.md` — 템플릿을 복사해 채움. `.gitignore`로 **원격에 푸시되지 않음**. `CONSTITUTION`에 절대 경로를 박지 않을 때의 대안.
- **MKM Trinity 인덱스(목차·포인터만):** `docs/final/MKM_TRINITY_INDEX_V1.json` — 렌즈 키 `sasang` / `logos` / `myeongni`(표시 `label_ko`). `_meta.truth_source`는 헌법; FACT 판정은 인덱스가 아니라 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 각 스크립트·테스트.
- **Windows C: 루트 정리 (관리자 PowerShell, 채팅 간 공유용):** `scripts/Invoke-CRootInstallerLeftoversCleanup_v1.ps1`(VS/인스톨러 잔재)·`scripts/Invoke-CRootAmdInstallerCacheCleanup_v1.ps1`(`C:\AMD` 캐시). 삭제 대상은 각 스크립트 본문이 SSOT. **일시 핸드오프·다음 일정 한 줄:** `docs/final/CURRENT_OPS_SNAPSHOT.md` 상단 **Ops slice · Cross-chat SSOT** 표.
- **Ollama 모델/캐시 경로:** 레포 공통으로 고정하지 않음 — 비추적 `docs/final/LOCAL_MACHINE_POINTER_V1.md`(아래 템플릿에서 복사)에 본인 PC의 모델 루트(예: F: 정션)만 적고, 런타임은 루트 `.env`의 `OLLAMA_HOST` / `OLLAMA_MODEL`(`.env.example`·`CLAUDE.md` 참고).

## 로컬 재생성 산출물 (`*_latest` 등) — Git 정책

- **이미 추적되는 파일**은 `scripts/verify_p0_constitution_gate_paths.ps1` 등에 경로가 박혀 있을 수 있다. `.gitignore`만으로 **수정 diff가 사라지지는 않는다** (추적 유지). 타임스탬프만 바뀐 로컬 굴레면 `git restore …`로 되돌리고, **의도한 갱신만** 커밋한다 (`AGENTS.md` 런타임 JSON 절과 같음).
- **아직 추적되지 않은** `docs/final/artifacts/*_latest.json` / `*_latest.md` 및 `reports/bio_sasang_nstates_*.json`은 루트 `.gitignore`로 **기본 비표시**(신규 클론·로컬 실행 잡음 감소). 레포에 **새로** 올릴 때만 `git add -f`(승격·증거 패키지 등)로 예외 처리한다.

## 중앙 메모리 (크로스 채팅 정체성)

- **지속 SSOT:** `docs/final/CENTRAL_AGENT_MEMORY_V1.md` — Athena 정체성·격벽·Fact-Lock·「분기별 한 줄」.
- **자동 주입:** `.cursor/rules/central-agent-memory.mdc` (`alwaysApply`)에 **SSOT 핵심 5줄**이 매 에이전트 턴 컨텍스트에 포함된다. `@` 없이도 원칙 정렬은 가능하다.
- **한계:** 채팅 로그는 세션 간 공유되지 않는다. “지난 작업” 맥락은 **본 파일·커밋**으로 누적한다. 표 전체·깊은 동기화가 필요하면 작업 시작 시 **`@CENTRAL.md`**(루트 바로가기) 또는 `@docs/final/CENTRAL_AGENT_MEMORY_V1.md` 또는 에이전트 `Read`를 쓴다.

### MKM 초간결 운영 프로토콜 (크로스 채팅 최소 부하)

1. **Cursor User Rules (지휘관 PC, 선택):** Settings → Rules for AI에 예: `새 세션에서는 docs/final/CENTRAL_AGENT_MEMORY_V1.md를 읽고 현재 진행 단계·Fact-Lock을 파악한 뒤 짧게 브리핑한다.` — 레포와 자동 동기화되지 않으므로 본 절은 **복붙용 안내**다.
2. **시작:** 말 한 줄만으로도 됨 — **고정 재개 트리거(동등·한쪽만 있어도 동일):** (A) 「**장기기억 맥락이어라**」「**장기기억 맥락 이어**」 (B) 「**장기기억 토대로**」「**장기기억 토대로 진행해**」 — **A와 B는 같은 우선순위**로 취급한다. 추가 동일 프로토콜: 「CENTRAL 기준으로 진행해」「팩트락 기준으로 자동 처리해」「MKM 장기기억」「이어서」「CENTRAL 기준」. 에이전트는 위 **어느 것이든** 받으면 레포 `.cursorrules` **[MKM AI Operating Protocol]** 에 따라 **다른 답변·코딩보다 먼저** `CENTRAL`·`AGENTS`·(필요 시)`CONSTITUTION_*`를 읽고, 운영 체크포인트·분기 한 줄을 근거로 짧게 브리핑한 뒤 작업한다. 또는 `@CENTRAL.md` / `@docs/final/CENTRAL_AGENT_MEMORY_V1.md` + 질문.
3. **종료 1초 체크포인트:** `py scripts/athena_checkpoint.py "완료/다음 한 줄"` — `CENTRAL`의 **운영 체크포인트** 마커와 `last_updated_utc` 갱신. **저위험 MD 편집**이므로 `athena_run_v1.py`로 감쌀 필요 없음(ECC·실거래 경로와 무관). 말로 **「장기기억 저장하라」「장기기억 저장해」「장기기억 저장해줘」「체크포인트」**만 해도 레포 `.cursorrules`에 따라 에이전트가 같은 명령을 실행하도록 고정됨(요약 한 줄은 채팅에 같이 주면 확실).
4. **재개 팩(선택):** `py scripts/build_mkm_chat_resume_pack_v1.py` → `docs/final/artifacts/mkm_chat_resume_pack_latest.md` 등 기존 산출과 병용 가능.
5. **`.cursorrules` 이중 관리:** 일일 `scripts/enforce_cursorrules_slim_ssot.py`는 `docs/final/artifacts/cursorrules_slim_ssot_v1.txt`를 `.cursorrules`에 복사한다. 루트 `.cursorrules`를 손대면 **템플릿도 같이** 맞춘다.

### 채팅 간 동기화 (레포 SSOT vs Cursor User Rules)

- **대화 내용은 복사되지 않는다.** 새 세션에서도 동일한 안내를 쓰려면, 일정·운영·Remote Publication 등 **반복 안내를 레포 파일에 적어 두고 커밋**한다. 같은 워크스페이스의 다른 채팅에서는 파일을 열거나 **`@AGENTS.md`**(필요 시 `@CLAUDE.md`·중앙 메모리)로 한 번 참조하면 갱신된 본문이 보인다.
- **다른 PC/클론**에서는 그쪽에서 **`git pull`** 후 동일하다.
- **중앙 규칙:** 루트 **`.cursorrules`**, **`.cursor/rules/*.mdc`** 도 레포에 있으면 **파일이 최신인 저장소**에서 Cursor가 적용한다.
- **Cursor Settings → User Rules**만으로 팀·본선 기준을 두지 않는다 — 레포와 **자동 동기화되지 않는다**. 본선·팀 합의 문구는 **`AGENTS.md`·`CLAUDE.md`·`CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 등 SSOT**에 둔다(요지는 아래 **「Cursor 3.0 · 규칙 스택」**의 User Rules 한 줄과 동일 선상).

| 반영되는 것 | 설명 |
|-------------|------|
| **AGENTS.md 수정·커밋** | 같은 워크스페이스의 다른 채팅에서 파일을 열거나 `@AGENTS.md`로 참조하면 갱신된 글이 보인다. 다른 PC/클론은 `git pull` 후 동일. |
| **중앙 규칙** | 루트 `.cursorrules`, `.cursor/rules/*.mdc` — 레포 파일이 최신이면 Cursor가 적용한다. |
| **Cursor Settings → User Rules만** | 레포와 **자동 동기화되지 않음**. 팀·본선 기준은 SSOT에 둔다. |
| **정리** | 세션 간 **대화 내용이 복사되는 것은 아니다**. 반복 안내·운영 메모는 레포에 커밋해 두고, 새 세션에서는 `@AGENTS.md`(필요 시 `@CLAUDE.md`·중앙 메모리)로 동일하게 따라간다. |

## 렌즈 역할 계약 (모든 채팅 공통 · 혼동 금지)

- **렌즈 명칭 고정:** `사상`, `명리`, `성경(Logos)` 3개만 사용한다. `Macro/Regime` 같은 운영 레이어명을 렌즈명처럼 혼용하지 않는다.
- **역할 고정:** 성경=`거시/레짐 게이트(허용·감쇠)`, 명리=`중기 방향 코어`, 사상=`단기 심리·강도 조절`.
- **A-track 규칙:** 실전 트리거는 1차 실물 `regime_map`과 운영 게이트가 주도한다. 3렌즈는 보조이며 직접 주문 트리거로 승격하지 않는다.
- **출력 고정 포맷:** `Field(레짐)` → `Lens(사상/명리/성경)` → `Conflict Resolver` → `Final Action(HOLD/REDUCE/WATCH)` 순서를 유지한다.
- **명리 고도화(장기기억):** `docs/final/CENTRAL_AGENT_MEMORY_V1.md` 「명리 렌즈 고도화 v1」— 만세력 Fact-Lock·§3.3 결정론 스택·삼고(입력·엔진·출력); 날씨·일반예언(B 레일)은 **캘리브레이션·게이트 원리만** 차용하고 명리 결정론과 **데이터 자동 합선 금지**.
- **명리 주간 최소 루프(원클릭):** `scripts/Run-MyeongniWeeklyOpsSummary_v1.ps1` → `reports/myeongni_weekly_ops_summary_latest.md`(비권위); KPI는 `independent_lens_shadow_gate_latest.json`(§3.3 표); 선택 `-Include16StateProbe`.
- **시장 단기 × 명리(권장 고정 · 3층):** (1) **시장 축** — 지수·선물·수급·매크로 및 B-track 가설·채점 체인; 단기 방향 단정은 이 축 또는 `[HYPO]` 근거로만. (2) **명리 축** — **한 프로필(출생·IANA TZ) 결정론**: `run_manseryeok_bot_v1` → `MyeongriCompleteFusion` → `run_lens_myeongni` → 산출 JSON·보조 해석(`MYEONGRI_AI_*`); **내일 장 일주로 사주를 자동 치환하는 경로는 없음**(현행 `market_myeongni`는 상류 렌즈 점수에 정책 오버레이만). (3) **Track A** — 실매매·주문은 실물 레짐·운영 게이트·휴먼; 명리·시장 B-track과 **자동 합선 금지**.
- **명리·시장 체인(선택 실행 순서):** `scripts/run_myeongni_lens_chain_from_bot_v1.py`(`--profile-json` 또는 `--demo-smoke`) → `scripts/run_market_myeongni_lens_v1.py --upstream docs/final/artifacts/myeongni_independent_lens_from_chain_latest.json`(또는 동일 세션에서 쓴 상류 렌즈 경로). 계약·표: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §3.3, `docs/final/artifacts/MARKET_MYEONGNI_LENS_V1_CONTRACT.json`.
- **B-track 세션 시각 패널(CSV, 정량):** `scripts/build_btrack_session_instant_myeongni_panel_v1.py` — 날짜 구간·로컬 개장 시각(기본 09:00, `Asia/Seoul`, `--calendar-mode krx_weekdays`)마다 만세력 **四柱** + `mkm_myeongni_math.compute_quant_profile_v0` 오행 질량·불균형 지표를 CSV(+`.meta.json`)로 출력; **擇日/日課 전 학파를 대변하지 않음**(동일 엔진을 세션 벽시계에 적용). **날씨·OHLCV 조인·상관(권장 순서):** (1) 패널 CSV (2) 날짜 맞춘 날씨 피처 CSV (3) 일봉 OHLCV → `scripts/join_btrack_session_panel_weather_ohlcv_v1.py` → (4) `scripts/correlate_btrack_joined_wide_csv_v1.py`(`--x-cols` 또는 `--x-auto-prefixes`) → `reports/btrack_joined_wide_correlation_latest.json`(선택 SciPy p-value). **원클릭:** `scripts/run_btrack_session_panel_weather_corr_chain_v1.py`(동일 순서 서브프로세스) · Windows 래퍼 `scripts/Run-BtrackSessionPanelWeatherCorrChain_v1.ps1`. API 미호출·B-track. 회귀: `tests/test_build_btrack_session_instant_myeongni_panel_v1.py`, `tests/test_join_btrack_session_panel_weather_ohlcv_v1.py`, `tests/test_correlate_btrack_joined_wide_csv_v1.py`, `tests/test_run_btrack_session_panel_weather_corr_chain_v1.py`.
- **금지:** "성경 렌즈가 하락을 예언했다"처럼 결정론적 가격 단정 문구 사용 금지. 성경은 `[NON_GATING]` 보조 해설로만 표기한다.

## MKM AI 아키텍처 명명 계약 (4AI 고정)

- **코어 정의:** MKM AI는 `사상 4AI 코어`(태양/소양/태음/소음 편향 에이전트)로 정의한다.
- **조율 정의:** `Absolute Balance`는 **제5 AI/제5 체질이 아닌 조율 상태(Coordinator Mode)** 다.
- **표준 표기:** 문서/대외 문구는 `MKM = 4AI core + Absolute Balance Coordinator Mode`를 기본으로 사용한다.
- **금지:** `5AI`, `제5 체질`, `추가 체질` 같은 표현으로 구조를 재정의하지 않는다.

## 홍보 프레이밍 계약 (뇌과학 영감 반영)

- **원칙:** 뇌과학 기반 영감(프레이밍/주의 전환/인지 부하 관리)은 **대외 과학 단정 근거가 아니라 커뮤니케이션 설계 원칙**으로만 사용한다.
- **표현:** 외부 카피는 `검증 가능한 아티팩트 + 면책 문구 + 경계(무엇을 하지 않는지)` 3요소를 기본으로 구성한다.
- **금지:** `신경과학적으로 증명됐다`, `뇌 기반으로 성과 보장` 같은 단정 문구를 마케팅·제안서에 사용하지 않는다.

## 발표 설득 모듈 계약 (LG/대외 공통)

- **기본 모듈:** 대외 발표·Q&A 초안은 `docs/final/artifacts/lg_hs_persuasion_module_v1_2026-05-08.md`의 4단 구조(오프닝/본문/Q&A/클로징)를 기본 템플릿으로 사용한다.
- **톤 비율:** `70/20/10` 고정(과제 직결 70, 운영 성숙도 20, 장기 비전 힌트 10). 비전 비율이 과제 본문을 넘지 않게 유지한다.
- **핵심 답변 구조:** `결론 -> 근거(아티팩트) -> 제한사항(로컬 기준선/실측 전환)` 순서를 고정한다.
- **금지:** 경쟁사 비방, 시장 서열 단정(예: "삼성급으로 점프"), 과학 단정형 수사(예: "뇌과학이 보장") 사용 금지.

## Athena 실행 거버넌스 (§28 · 선택 일상 점검)

- **헌법:** `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §28 — `scripts/athena_run_v1.py`(ECC·`--target`/DPAPI·감사 JSONL·선택 `ATHENA_ECC_AUDIT_WEBHOOK_URL`).
- **원클릭 스모크:** `py scripts/check_athena_execution_governance_smoke_v1.py` — 스크립트 존재·doctor·HOLD 차단 경로(exit 2) 확인 (실매매·웹훅 전송 없음).
- **상태 요약:** `py scripts/athena_doctor_v1.py`
- **규칙:** Cursor·에이전트는 `.cursorrules` 「Execution Governance」; 실키·웹훅 URL은 레포가 아니라 `.env`/스토어.
- **CI:** GitHub `dual-regime-integrity` 워크플로가 §28 관련 pytest(`test_athena_run_v1`·`test_athena_doctor_v1`·`test_check_athena_execution_governance_smoke_v1`)를 실행 — 레포 시크릿 `ATHENA_ECC_AUDIT_WEBHOOK_URL`은 선택(현재 스텝은 웹훅 불필요).

## 세션 핸드오프 (선택)

새 채팅에서 직전 작전의 팩트만 이어 붙일 때 `@docs/final/CURRENT_OPS_SNAPSHOT.md`를 첨부한다. **불변 SSOT가 아니며** 필요 시 갱신·비운다. 압축 파이프라인(A/B Track)과 역할을 섞지 않는다.

다단계 임무의 **종료 조건·로컬 체크리스트**만 디스크에 남길 때는 `MISSION_LOG.template.md` → **`MISSION_LOG.md`**(로컬 전용,`.gitignore`). **작전 요약·세션 핸드오프**는 `docs/final/CURRENT_OPS_SNAPSHOT.md`가 우선이며, 동일 SSOT를 스냅샷과 `MISSION_LOG`에 **이중 서술하지 않는다**. 순서·상용 게이트 SSOT는 `P0_COMMERCIALIZATION_TRACKER.md`이다. 자율 의사결정 감사 로그는 `reports/agent_decisions_log.jsonl`에 append-only로 남긴다. **한 파일에 두 형식이 공존할 수 있다:** (1) `scripts/log_agent_decision.py`가 쓰는 일반 결정 한 줄(`timestamp`·`mission_id`·`stage`·`decision`·`evidence_path`·`actor` 등). (2) 메타 인지 봉투 적재 시 `decision=meta_layer_envelope_v1`와 `meta_layer_envelope` 객체(CONSTITUTION §1.3.1). 집계·파서는 `decision`(및 존재 시 `meta_layer_envelope`)으로 분기한다.

## 병렬 작전 권장 (다중 채팅·서브에이전트)

채팅 로그는 세션 간 공유되지 않으므로, **역할이 다르면 채팅을 나누는 것이 권장**이다.

| 갈래 | 내용 | 병렬 시 주의 |
|------|------|----------------|
| **사업·공고** | 평가표·실증 요건·파트너·제출물 — SSOT 수치만으로 당선을 단정하지 않음; 갭 매트릭스 `docs/final/artifacts/defense_rfp_evaluation_gap_matrix_v1.json` · **붙임2 체크리스트** `docs/final/artifacts/defense_pitchday_2026_annex2_proposal_checklist_v1.json` | 레포 대규모 편집과 **동시에 한 사람이** 맡으면 컨텍스트가 섞임 → **별도 채팅** 권장 |
| **B-track 연구** | 예언 스윕·오버레이 AB·명리·로고스 — §1.1·§8·합선 금지 | 본선/국방 제안 서사와 **문장·코드 합선 금지** |
| **레포 본선** | `CONSTITUTION`·`scripts/run_*`·CI·헌법 경로 | **직렬 우선**: 동일 파일을 두 세션에서 동시 편집하지 않음 |

- **동시 편집을 피할 파일(직렬 대상 예시):** 루트 `AGENTS.md`·`CLAUDE.md`, `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`, 동일 `scripts/run_defense_*.py` / `run_prophecy_restoration_spike.py` 등 **한 스트림에서만** 바꾼다.
- **코드 병렬이 필요하면:** 브랜치 분리 또는 `git worktree`(작업 트리 복제)로 나눈 뒤 → 머지 전 충돌 확인.
- **서브에이전트/Task 병렬:** 조사·읽기 위주는 부담 적음; **쓰기**는 디렉터리·브랜치 범위를 명시해 겹치지 않게 한다.

### Git Hygiene 기본 프로토콜 (재부팅/세션 종료 후에도 유지)

- **원칙:** `1작업 = 1브랜치 = 1PR` 고정. 장기 브랜치에 연속 누적 커밋 금지.
- **기본 작업 위치:** 더티 루트 대신 `origin/<base>`에서 시작한 **클린 worktree**를 기본으로 사용한다.
- **푸시 전략:** 대형 푸시가 지연/행(hang)되면 즉시 **초소형 배치(권장: 1커밋)** 로 전환해 `push -> PR -> merge`를 반복한다.
- **정리 규칙:** PR merge 후 원격 브랜치와 임시 worktree를 즉시 정리해 다음 작업의 분기 오염을 방지한다.
- **우선순위 고정:** Git hygiene 규칙이 다른 문서와 상충하면 항상 루트 `.cursorrules`의 "Git Hygiene 고정 (세션 종료 후에도 유지)" 4줄을 우선 적용한다.
- **로컬 개발서버 정리(선택):** 수동은 `scripts/stop_local_dev_servers.ps1` (`-DryRun` / `-IncludeNpxMcp`); 로그오프 시 자동 실행 작업 등록은 `scripts/register_local_dev_server_stop_logoff_task.ps1` (`-IncludeNpxMcp`로 MCP 브리지까지).

### Remote Publication 운영 기본값 (모든 채팅 공통)

- **본선 push:** `internal` 원격(내부/Gitea/로컬 bare)만 기본 사용.
- **GitHub 비사용 기본:** 일반 작업에서는 GitHub를 쓰지 않는다(기본은 internal/gitea only).
- **GitHub push:** 기본 차단(`origin`/`hq` push URL=`no_push`)을 유지하고, 사용자 명시 승인 없이는 해제/우회하지 않는다.
- **권장 명령:** `scripts/Show-RemotePublicationMode.ps1`(상태 점검), `scripts/push-internal.ps1`(기본 push), `scripts/Push-GitHub-Explicit.ps1 -Acknowledge`(예외 공개).
- **대용량/민감 산출물:** GitHub 기본 제외. 특히 `docs/final/artifacts/global_atom_full_canon/*`는 최신 consolidated manifest만 추적한다.
- **GitHub 푸시 거절(GH001 등):** 브랜치 히스토리에 **100MB 초과** Git 객체(예: 위 `global_atom_full_canon` 대용량 JSON/JSONL)가 포함되면 원격이 받지 않는다. 이 경우 **GitHub PR 없이 `internal`/`gitea`에서 머지**하거나, LFS·히스토리 정리 후 예외 푸시(`Push-GitHub-Explicit.ps1`)를 별도 검토한다.

### 일인 개발(solo)일 때만 단순화

- **매일 쓰는 것 하나:** 작업 저장은 **`scripts/push-internal.ps1`** 만 기억하면 됨 → **`gitea`** 또는 **`internal`** 로만 올라감(GitHub 주소를 외울 필요 없음).
- **런타임 산출물:** 스케줄/체인이 갱신하는 `*_latest`류는 **로컬 디스크 SSOT**로 두고 Git에는 올리지 않는다(`.gitignore`로 워킹트리 clean 유지). 다른 PC는 `git pull` 후 필요한 체인을 한 번 돌리면 동일 경로에 재생성된다.
- **stash:** 평소 루틴에 끼우지 말고, **정말 섞일 위험이 있을 때만** 임시 격리용으로 사용한다.
- **브랜치:** 급하면 `main`에서 바로 커밋해도 된다. 여유가 생기면 그때 `1작업=1브랜치`로 정리해도 된다(강제 아님).
- **피처 → 통합 브랜치:** 일상 머지 대상은 **`gitea/main`**(bare가 `E:\Git\repos\mkm-destiny-ai-41e38ec6.git`이면 `internal`과 동일). `main`이 `C:\workspace`가 아니라 **다른 워크트리**에만 열려 있어도 되고, 그때는 **`scripts/SoloDev-MergeFeatureToGiteaMain.ps1`** 로 현재 브랜치를 main에 합친 뒤 `gitea`로 push(먼저 `-DryRun`).
- **GitHub:** 공개 미러·외부에 보여줄 필요가 있을 때만. 평소에 안 써도 레포 규칙과 충돌 없음. 의도적으로 올릴 때는 **`scripts/Push-GitHub-Explicit.ps1 -Acknowledge`** (실수 방지용 게이트).
- **`origin`의 push가 `no_push`인 설정은 유지 권장:** 일반 `git push origin` 으로 GitHub에 안 가게 막는 안전장치.
- **`hq` 등 다른 리모트:** 팀용 이름일 뿐이며, 일인이면 **주 저장소는 `gitea`/`internal` 하나로 통일**하고 나머지는 필요할 때만 의식하면 됨. 헷갈리면 **`scripts/Show-RemotePublicationMode.ps1`** 로 “어디로 열려 있는지”만 확인.
- **PR·worktree 병렬:** 문서의 Git hygiene은 팀 협업용 바람직함이다. **혼자면 브랜치 하나로 길게 가도 되고**, 나중에 정리할 여유가 있을 때만 `1작업=1브랜치`를 적용해도 된다.
- **런타임 JSON 잡음:** 데몬·스케줄이 `projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json` 등만 갱신하면 `git status`에만 뜰 수 있다. **타임스탬프만 바뀐 로컬 굴레**면 커밋에 넣지 말고 `git restore projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json` 로 되돌린다(운영 반영을 의도해 고친 경우만 커밋).

## 필수 우선순위

1. **루트 `.cursorrules`** — 최상단 **TITAN · 자율 기동(Command-by-Negation)**. 예외가 아니면 권장 조치를 질문 없이 수행·사후 보고; 끝맺음은 [A]/[B] 선택 강요 없이 **완료 보고 + 잔여 리스크(있을 때만)**.
   - 실무 해석 고정: 명시적 STOP/승인 필요 예외(파괴적 삭제·실거래·비용 유발·비가역 근본 변경) 외에는 파일 편집/터미널/검증을 자율 연속 수행한다.
   - 모호성 처리 고정: 저위험 모호성은 질문 대신 합리적 기본값으로 구현/검증 후 사후 보고한다.
2. **`.cursor/rules/sovereign-central-command.mdc`** — Vault·NotebookLM·보안·운영(3문장 요약 + **§4 마무리**). §4에서 **폐지**: “Next Action 2가지”, `[A]`/`[B]`·a/b 강요. **대체**: TITAN 마무리 또는 고위험 시 **승인 범위만** 명시(루트 `.cursorrules`와 동일 방향).
3. **구현 팩트(환각 차단)**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` — 기획·NotebookLM만 보고 “이미 구현” 단정 금지. **§1.1.1 [VISION]** — 예언 성능·재현 채점 우선(`prophecy_hit_rate_eval_report_v2`, `scripts/run_prophecy_restoration_spike.py` 등 AB 산출); 대외 도메인 사례(예: 국방 벤치)는 **`research_only`** 격리·본선 주장과 분리. P0·헌법 핵심 경로 존재 여부: `scripts/verify_p0_constitution_gate_paths.ps1`.
4. **Prism 색인 (논리 레이어, 선택)**: 물리 이동 없이 경로·역할만 묶은 **Grand Indexing 2.0** — `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` **§14**, 가독 색인 초안 `docs/final/MKM12_GRAND_INDEX_MAP.md`, 중앙 레지스트리 `docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json`. 코드 4D 벡터 축 `(S,L,K,M)`과 혼동하지 말 것.
5. **정체성 (Multi-Lens):** 단일 TOE·통일장 “완성” 선언 금지 — §1.1. 레짐·로고스·명리·외경은 **격벽·교차 참고** (§2.1·§4).
6. **Cursor Cloud Sandbox · 본선 분리:** Cloud Agent/Sandbox는 검증·병렬 가속 전용; 실매매·프로덕션 쓰기·실키 주입은 로컬/VPS 본선과 분리. 상세 `.cursor/rules/cursor-cloud-sandbox-boundary.mdc`.

## 하네스 정밀 하드닝 (Agent Harness Engineering, 운영 규약)

- **래칫 등급 운영:** 실패 재발 방지는 `임시(관찰)` → `반영 후보` → `영구 규칙(헌법/훅)` 3단계로 승격한다. 단발성 이슈를 즉시 영구 규칙화하지 않는다.
- **생성/평가 독립성:** 장기 작업은 생성 루프와 평가 루프를 분리하고, 평가는 최소 1개 고정 홀드아웃(블라인드 샘플 포함)으로 수행한다.
- **컨텍스트 SLO 고정:** 긴 로그·대형 산출물은 기본 오프로드하고, 요약 주기·토큰 상한·재주입 조건을 명시한 채 운영한다.
- **침묵 성공 + 하트비트:** 성공 시 상세 로그는 루프에 재주입하지 않되, 통과 카운트·소요시간·최근 체크포인트는 경량 하트비트로 남긴다.
- **HaaS 가드:** 프레임워크/HaaS를 사용해도 핵심 게이트는 로컬 재현 가능한 스크립트·아티팩트·exit code로 검증한다(Fact-Lock 우선).

## 로컬 검증 진입점 (개발·PR 전 권장)

### 페르소나 단축 호출 (SSOT · 채팅 트리거 → 고정 스크립트)

Cursor/채팅에서 아래 **구분자**가 나오면, 에이전트는 **추측 요약보다** 아래 **래퍼 한 줄**을 실행하고 **exit code**를 보고한다. 추가 `-Include*` 등은 래퍼가 아니라 **각 하위 `.ps1`에 직접** 넘긴다.

| 구분자(트리거 예) | 한 줄 역할 | 고정 명령 (저장소 루트) |
|-------------------|------------|-------------------------|
| 【아테나 점검】 | Fact-Lock 번들 (`run_fact_lock_bundle.ps1`, CI에 가까운 순서) | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaBundle` |
| 【프리미엄 큐 권장】 | 프리미엄 멀티렌즈 pytest 4종 + `drain --allow-missing-queue` + S1 승격 게이트(번들 4b·헬스 Premium과 동선) | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona PremiumMultilensQueue` |
| 【암행어사 점검】 | 자동화 헬스 기본 실행 (`run_workspace_automation_health.ps1` 기본 스위치) | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AmsaengHealth` |
| 【빠른 헌법 점검】 | P0 필수 경로 존재만 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona P0` |
| 【예언 레일 일단락】 | 예언 본선 클로저(P0·B-track 정렬 pytest·safe ops·GO/NO_GO 갱신). 통과 판정은 `reports/prophecy_lane_closure_bundle_v1_latest.json`의 **`closure_ok: true`** 및 `manual_remainder`(Windows `schtasks` 일반예언·Track A 실매매는 수동 잔여) | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1` |

### Fact-Lock + 프리미엄 멀티렌즈 권장 루틴 (운영 고정)

- **주간·넓게(기본 권장):** 【아테나 점검】→ `Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaBundle` → `run_fact_lock_bundle.ps1`에 **프리미엄 멀티렌즈 pytest(단계 4b)+`drain --allow-missing-queue`**가 포함되며, CI `dual-regime-integrity.yml`과 동일 **3종 pytest + drain**이다.
- **프리미엄·큐만 좁게:** 【프리미엄 큐 권장】→ `Invoke-MkmPersonaHealth_v1.ps1 -Persona PremiumMultilensQueue`(내부적으로 `Invoke-PremiumMultilensQueueRoutine_v1.ps1`).
- **가볍게 프리미엄만:** `pwsh scripts/run_workspace_automation_health.ps1 -PremiumBtrackMultilensReportSmokeOnly` (P0·reconcile·pytest 4종 + drain + S1 gate).
- **파일 큐(v0):** `py scripts/premium_multilens_job_queue_stub_v1.py` — `enqueue` / **`drain`**(`--allow-missing-queue` 권장) / **`export-pending --out-json …`**(대기 목록+렌즈 스크립트 포인터, 비실행). 원클릭: `Invoke-PremiumMultilensQueueRoutine_v1.ps1`(`-ExportPendingJson` 선택; 말단 S1 승격 게이트 기본, `-SkipPromotionGate`로 생략).
- **암행어사 기본:** `AmsaengHealth`는 **프리미엄을 기본 포함하지 않는다**(실행 시간·역할 분리). 전체 헬스에 함께 돌리려면 `run_workspace_automation_health.ps1`에 **`-IncludePremiumBtrackMultilensReportSmoke`**를 별도로 넘긴다.
- **경로 존재만:** 【빠른 헌법 점검】(`Persona P0`) — pytest는 실행하지 않는다.

- **이름 충돌 주의:** `scripts/Invoke-AthenaAutomationRegistryCheck.ps1`의 Athena는 **태스크 스케줄 vs `automation_registry.json`** 전용이며, 위 표의 **AthenaBundle**과 **다르다.**
- **좁은 암행어사 한 바퀴(SafeOps·MCP·비밀·no1kmedi API 등):** `scripts/Invoke-AmsaengEosaGovernanceCycle.ps1` — 범위는 `docs/final/artifacts/amsaeng_eosa_governance_scope_v1.json`.
- **비밀 키 하이브리드 권장(로컬 DPAPI / VPS env):** `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md` 「비밀 키」절 · `scripts/Invoke-MkmSecretsHybridReadiness_v1.ps1`(레포 위생 + Windows DPAPI 스토어 존재·키 개수만) · VPS 템플릿 `scripts/deploy/linux/mkm-monorepo-vps.env.example`.

- **만세력 Phase B 스모크 (Meeus vs Swiss 立春 Reference B + 59-case ganji 코호트 + 충돌 사전 네이티브 검증):** `python scripts/run_manseryeok_validation_smoke_v1.py` (B-2만: `--skip-ephemeris`; 충돌 생략: `--skip-collision-dict`). 단독: `python scripts/validate_collision_dictionary_v1.py`. CI: **`main` 푸시마다** + 경로 맞는 PR + 수동 — `.github/workflows/manseryeok-validation-smoke.yml`. 대조 템플릿·채집 절차: `docs/final/artifacts/manseryeok_collision_dictionary_v1.json` (`collection_howto`, **`ssot_policy`**). **회귀·본선 기준은 `pillars_native`(엔진)**; `pillars_external`은 외부 UI 스냅샷. 엔진 변경 후 네이티브 동기화: `python scripts/collision_dict_refresh_native_v1.py --write`. 코호트 행 추가(네이티브만): `python scripts/sync_collision_dict_cohort_entries_v1.py --case-id <id> --write`.
- **전 세계 사용자 출생 입력 (IANA TZ, DST 안전 권장):** `scripts/saju_birth_resolver_v1.py` — 절대시각 **`birth_instant_utc`(ISO Z) + `iana_tz`** 가 1순위; 로컬 벽시계만 쓸 때는 DST 겉넘김 구간 에러 처리. CLI 예: `python scripts/run_saju_global_birth_v1.py --utc-instant 1992-03-12T17:00:00Z --iana-tz Asia/Seoul`. Pack 0-B(명리 결정론 LoRA 골든 JSONL 한 행): `scripts/prep_myeongri_deterministic_lora_golden_v1.py` — 대량·시드·매니페스트: `scripts/build_myeongri_deterministic_lora_golden_bulk_v1.py` — DoD **`docs/final/LORA_PACK_V0_DOD_V1.md`**. `scripts/saju_dual_verify.py`에도 동일 계약: `--birth-instant-utc` + `--tz` IANA. **mkm-life** `POST /api/v1/saju/verify` 는 `birth_instant_utc` + `tz` 를 그대로 전달(서버 `zoneinfo` 정규화, 기존 y/m/d/h/mi 본문은 계속 지원). **jema-ai.com** (소스만 `projects/no1kmedi`): CDSS `lane_a_profile` 및 `ATHENA_MANSERYEOK_API_URL` 호출 시 동일 키(`birth_instant_utc`, `iana_tz`; 레거시 `birth_datetime` 선택). **엔진 직접 프록시(로컬/동일 배포):** `POST /api/manseryeok/reference` → `run_saju_global_birth_v1.py`(`MKM_WORKSPACE_ROOT`); `npm run smoke:manseryeok-reference` (서버 기동 후). 계약 스키마: `docs/final/artifacts/schemas/saju_global_birth_request_v1.schema.json`.
- **구현 판정**은 (3)의 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`와 호출 가능 스크립트·테스트로만 한다. 브리핑·노트만으로 경로를 확정하지 않는다.
- **번들 한 방**: `scripts/run_fact_lock_bundle.ps1` — 루트에서 실행; 맥락·완료 정의는 `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 하단. 기본에 B-track **§3.8.4** VA→fusion→감사 체인 + `va_tag_boost_v1` 정책 골든 pytest가 포함되며, 생략은 `-SkipVaFusionControlIntegritySmoke`.
- **Bio 논문 SNP 사이드카 조인(§8.1, 선택):** `pwsh scripts/run_workspace_automation_health.ps1 -IncludeBioPaperSnpJoinSmoke` — pytest 스모크만(네트워크 없음; join/apply + sidecar chain CLI + EPMC CLI 3종). 빠른 단축: `-BioSnpOnly`(P0 경로 + reconcile + Bio 스모크). CI: `.github/workflows/bio-paper-snp-sidecar-smoke.yml`. v3→JSON→코호트 일괄: `scripts/Run-BioPaperSnpSidecarExportAndApply.ps1`.
- **Control-Integrity Golden/LoRA 파이프라인(선택, GPU 불필요):** `pwsh scripts/run_workspace_automation_health.ps1 -IncludeMkmControlIntegritySmoke` — aggregate·프로모션 게이트·오라클 추론 타이밍 회귀. 빠른 단축: `-MkmControlIntegritySmokeOnly`. Fact-Lock 표: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.2.1.
- **VA→fusion→control-integrity 체인(선택, B-track §3.8.4):** `pwsh scripts/run_workspace_automation_health.ps1 -IncludeVaFusionControlIntegritySmoke` — `va_trajectory_log`→`cross_lens_fusion_report`→`fusion_control_integrity_audit` 계약 회귀. 빠른 단축: `-VaFusionControlIntegritySmokeOnly`(P0 + reconcile + 체인 스모크). Windows 원클릭 `Run-VaFusionControlIntegrityChain_v1.ps1`는 감사 실패 시 선택 웹훅(`FUSION_CONTROL_INTEGRITY_AUDIT_WEBHOOK_URL` → `OPS_ALARM_WEBHOOK_URL`); 비밀 없는 실행은 `-SkipWebhook`.
- **Premium B-track multi-lens report v1(선택):** `pwsh scripts/run_workspace_automation_health.ps1 -IncludePremiumBtrackMultilensReportSmoke` — 스키마·동기 빌더 subprocess pytest(CI·Fact-Lock 번들 4b와 동일). 빠른 단축: `-PremiumBtrackMultilensReportSmokeOnly`. Fact-Lock: `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` Premium 표 행.
- **AI BGM 게이트 v1 (선택):** `py -m pytest tests/test_audio_bgm_gate_report_v1.py` — 가성비 원클릭 `pwsh -File scripts/Run-AudioBgmEconomyChain_v1.ps1 -SeedJson data/audio/seeds/tension_sasang_01.example.json` (비용 없음; 유료 확장은 `-Live`; Phase A만으로 드라이·게이트). 오프라인 톤: `-ExternalScript scripts/audio/tone_external_generator_v1.py`; 드라이 확장+톤 힌트: `-ExternalScript scripts/audio/expand_tone_external_generator_v1.py`(-DryRun 경로에서 확장도 비과금); ffmpeg 브라운 베드: `-ExternalScript scripts/audio/ffmpeg_bed_external_generator_v1.py`(ffmpeg 없으면 톤 폴백). 엄격 LUFS 전 의존성: `py scripts/audio/check_audio_gate_optional_deps_v1.py` (`--require-all` 시 미충족 exit 1). CI `.github/workflows/audio-bgm-gate-smoke.yml`. 상세 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 헤더 AI BGM 보강.
- **상징→오디오 B-track §3.9 (연구 승격 번들, 선택):** `py scripts/check_lens_music_symbolic_audio_promotion_gate_v1.py` — M0–M5·게이트 체인·**M32 `gematria_seed_trace` 스키마**·**M20/M31 `build_lens_music_prompt_overlay_v1` 회귀**·내부 eval·**M31 hormone webhook dispatch smoke** pytest 번들; **exit 0**는 pytest 통과에 더해 **기본 `--m31-profile strict`일 때 `decision≠HOLD_M31_HORMONE_GUARD`**(soft 프로필은 pytest 통과만으로 exit 0). `B_TRACK_RESEARCH_PROMOTION_READY`는 레포 연구 준비 의미. **Track A 상용 오디오·Track C 1차 GTM 자동 승격 아님**(`track_wall`). SSOT: `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.9.2 · `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 보강.
- **렌즈 뮤직 M32·M20·M31 증거 복기(W1, 비커밋 권장):** `py scripts/run_lens_music_gematria.py --sasang-primary taeeum -o reports/tmp_lens_w1_lens.json` → `py scripts/run_lens_music_gematria_gate_chain_v1.py --lens-json reports/tmp_lens_w1_lens.json --export-chain reports/tmp_lens_w1_chain.json --export-audio-report reports/tmp_lens_w1_audio_gate.json`(WAV는 플레이스홀더 기본)·`py scripts/build_lens_music_prompt_overlay_v1.py --chain-json reports/tmp_lens_w1_chain.json --out reports/tmp_lens_w1_overlay.json`(거버넌스 JSON은 `--governance-json`로 지정; 기본 `docs/final/artifacts/lens_music_audition_governance_status_latest.json`가 있으면 동 경로). 체인의 `gematria_seed_trace`가 오버레이·`hormone_like_state`에 흐르는지 확인. PR 전 `verify_p0_constitution_gate_paths.ps1`·CI `dual-regime-integrity.yml` 경로 포함.
- **렌즈 뮤직 M31 트렌드·웹훅·대시보드(W2 운영):** `build_lens_music_hormone_trend_v1`는 히스토리 JSONL에 `hormone_state` 행이 없으면 `state=NODATA` 및 `operator_hint`(오버레이 실행으로 히스토리 적재 안내). `dispatch_lens_music_hormone_trend_webhook_v1`는 트렌드 **WATCH일 때만** POST(`LENS_MUSIC_HORMONE_WEBHOOK_URL` 미설정 시 skipped). `build_mkm_trackc_ops_dashboard_v1`의 `trackc.lens_music_hormone_state`에 M32 요약(`gematria_trace_present` 등), `trackc.lens_music_hormone_trend.operator_hint`를 노출(소스: `reports/lens_music_hormone_state_latest.json`, `reports/lens_music_prompt_overlay_latest.json`, `docs/final/artifacts/lens_music_hormone_trend_latest.json`).
- **렌즈 뮤직 W3 (M31 게이트 프로필·감사):** `check_lens_music_symbolic_audio_promotion_gate_v1.py`가 `m31_hormone_guard.invocation`에 `profile`(strict|soft)·임계·`hormone_trend_json` 경로를 기록; `--m31-profile` 또는 `--allow-soft-m31`(동치 soft). 산출 JSON에 **`promotion_process`**(W5: `process_exit_code`·`process_pass`·`pytest_pass`와 대시보드 노출). 일일 퓨전은 기본 strict — M31 HOLD 시 **exit 1**로 단계 실패; 콜드스타트만 `Invoke-TrackCMacroDailyFusion_v1.ps1 -LensMusicPromotionGateSoftM31`(등록 스크립트 동명 스위치) 또는 `scripts/Run-LensMusicPromotionGateStagingStrict_v1.ps1`로 명시 strict 재실행.
- **사상→감정 VA 연속축 계약 §3.10 (Draft, 스키마만):** `docs/final/schemas/sasang_emotion_mapping_v1.schema.json` · example · `tests/test_sasang_emotion_mapping_schema_v1.py` — `sasang_music_mapping_v1`와 분리; 상용·실거래·범용 추론 자동 향상 단정 금지.
- **보조**: `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1` (bitcoin-trading 디렉터리에서). CI 정합은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §6.
- **예언 오버레이 AB 스파이크(§1.1.1)**: `py -m pytest tests/test_prophecy_restoration_spike.py` — GitHub `.github/workflows/prophecy-restoration-spike-smoke.yml` (스크립트·테스트 변경 시). 임계값 스윕 산출(로컬 재생성): `docs/final/artifacts/prophecy_prior_threshold_sweep_v1_latest.json`.
- **LLM 검증 티어:** 기본은 **로컬·자체 호스팅 모델**로 게이트·벤치; 상용·대외 품질 확정 전에만 **고급 클라우드 모델 소표본 섀도우**(드리프트 방지). 상세: `docs/final/P0_COMMERCIALIZATION_TRACKER.md` **「LLM 검증 티어」**.
- **MKM-Orchestrator (bounded `todo_queue_v1`):** `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.4 · `docs/final/artifacts/mkm_orchestrator_connection_spec_v1.json` · 로컬 스모크 `scripts/run_mkm_orchestrator_smoke_v1.ps1`(기본 `pip install -q jsonschema`) · 경로 점검 `scripts/verify_mkm_orchestrator_bundle_v1.py` · 큐 생성 `scripts/bootstrap_mkm_orchestrator_queue_v1.ps1`(`-Profile TrackCFromBridge` = 사업계획 브릿지 JSON 적용) · 상태 요약 `scripts/show_mkm_orchestrator_queue_status_v1.py` · 연속 루프(선택) `scripts/run_mkm_continuous_daemon.ps1`/`Register-MkmOrchestratorDaemonTask.ps1`. B→A·실매매 자동 합선 없음.
- **Track C 매크로·Logos 일일(융합 단일 진입점):** `scripts/Invoke-TrackCMacroDailyFusion_v1.ps1` — `Invoke-FragilityMacroRiskDaily` 한 번 후 `run_macro_risk_forward_daily_chain_v1.ps1 -SkipFragilityChain` · `run_logos_4d_state_chain_v1.ps1 -SkipFragilityChain` · Logos 섀도우 일련(스크립트 본문) · **`build_role_router_s1_shadow_advisory_v1.py`**(기본, advisory_only·non-gating; `-SkipRoleRouterShadowAdvisory` 생략) · **렌즈 뮤직 M31** `build_lens_music_hormone_trend_v1.py`·`dispatch_lens_music_hormone_trend_webhook_v1.py`(대시보드 직전·기본; `-SkipLensMusicHormoneTrend`로 생략) · `build_mkm_trackc_ops_dashboard_v1.py`. 스케줄 등록: `scripts/Register-TrackCMacroDailyFusionTask.ps1` (**`-DryRun`**으로 변경 없이 점검; **`-UnregisterLegacyTasks`**로 기본 레거시 작업명 2개 제거 후 등록 권장). 무인 안정화 예: **`-SkipGateAlert -SkipExodusSourceFetch`**. 등록 후 인자 확인: `scripts/Verify-TrackCMacroDailyFusionScheduledTask_v1.ps1`. 헬스: `scripts/run_workspace_automation_health.ps1 -IncludeTrackCMacroFusionSmoke`(전체 헬스 안에서 느림) 또는 **`-TrackCMacroFusionSmokeOnly`**(P0+퓨전만). (기존 Fragility/Forward 각각 등록 태스크와 **동시에 돌리면 Fragility 이중 실행**.) 로컬 웹훅 끄기: `-SkipGateAlert`; Exodus 공개 수집 생략: `-SkipExodusSourceFetch`. **선택 메타 인지 게이트:** `-MetaLayerEnvelopePath`(비면 미실행) — `scripts/mkm_meta_layer_envelope_v1.py`·스키마 `docs/final/artifacts/schemas/mkm_meta_layer_turn_envelope_v1.schema.json`·복붙 예시 `docs/final/artifacts/fixtures/mkm_meta_layer_turn_envelope_v1.example.json`·회귀 `tests/test_mkm_meta_layer_envelope_v1.py`; 상세 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.3.1.

## Cursor 3.0 · 규칙 스택 (2026-04)

- **제품**: Cursor 3 — **Agents Window**(로컬·워크트리·클라우드·SSH 병렬 에이전트), **Design Mode**(브라우저 UI 타겟), **Agent Tabs**(다중 채팅). IDE 명령 팔레트에서 “Agents Window” 등(공식 Changelog 2026-04-02).
- **워크스페이스 규칙(SSOT)**: 루트 `.cursorrules`, `.cursor/rules/*.mdc`, 본 `AGENTS.md`, `CLAUDE.md`, `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` — **Git으로 버전 관리**.
- **User Rules**: Cursor **Settings → Rules**에만 있는 문구는 **레포에 자동 동기화되지 않음**; 팀·본선 기준은 반드시 위 SSOT 파일에 반영한다.

## 로컬 Cursor vs SSH VPS (한 원칙)

- **SSOT**: `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md` — 코드·규칙은 **로컬에서만 편집·푸시**; VPS는 **`git pull` + 런북의 재시작/배포만**; 비밀은 **`.env`를 호스트마다** (Git 비추적). bitcoin-trading 본선 **권장 배치**는 동 문서 **「VPS 배치 (권장)」** — 모노레포 루트를 **PM2 `cwd`**, **`projects/bitcoin-trading/start_live_trading.py`** 진입.
- **bitcoin-trading 운영 5줄:** `projects/bitcoin-trading/AGENTS.md` · `projects/bitcoin-trading/로컬_VPS_운영원칙.txt` — **`pm2 restart <이름>`만**, **`restart all` 금지**(런북 예외만), **VPS 직수정 → 레포로 되돌리기**, `.env` 위치는 팀 규칙 한 곳.

## 압축 파이프라인 투트랙 (Fact-Lock 요약)

- **정책**: `docs/final/COMPRESSION_SLA_POLICY_V1.md` — Track A(범용)·Track B(리터럴), 산출 JSON, 손실 패턴 리포트, 웹훅은 `active_kpi`(Track A) 기준.
- **용어 고정**: 공식 운영 트랙은 **Track A/Track B**. `Track Q`는 본 레포 SSOT의 공식 메인 트랙명으로 고정하지 않는다(세부: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §20).
- **4D/게마트리아 위치**: 보조 특성/가산 채널/연구 스파이크로 사용 가능하되, A/B 승격 규칙·명칭을 대체하지 않는다.
- **수치 판정 원칙**: “A 고압축, B 무손실”은 경향 설명이며, 최종 판정은 해당 시점 아티팩트 JSON 필드값으로 확정한다.
- **하이브리드 포인터 라우팅(연구→상용 PoC 단계)**: `run_genesis_pointer_routing_control_chain_v1.py` 기준으로 `GO/WATCH/HOLD` 라벨 → routing decision → guarded decision → runtime config → shadow report → alert → guard drill 순서의 증거 체인을 유지한다.
- **자동 강등 가드**: alert(`pointer_hash_snapping_router_shadow_alert_latest.json`)가 켜지면 guarded decision에서 `HOLD_POINTER_ROUTE` + `track_a_primary`로 강등한다.
- **주장 톤 고정**: “무조건 99%/100%/지연 0” 금지. 외부/내부 보고는 조건부·아티팩트 근거형 문장만 사용한다.
- **실행**: `scripts/run_ultra_compression_default.py` / `--mode literal` / `--mode ultra-literal`(연구·극정밀); `scripts/run_compression_automation_chain.ps1 -IncludeLiteralTrack` / `-IncludeUltraLiteralTrack`; 헬스: `scripts/run_workspace_automation_health.ps1 -IncludeCompressionKpi [-IncludeLiteralTrack]`(체인은 in-process 호출).
- **압축 거버넌스(현행)**: `scripts/run_compression_automation_chain.ps1` + `scripts/run_workspace_automation_health.ps1 -IncludeCompressionKpi [-IncludeLiteralTrack]`를 기본 운영 진입점으로 사용한다. 판정 기준 산출물은 `docs/final/artifacts/a_track_go_nogo_status_latest.json`, `docs/final/artifacts/trackb_weekly_gate_recheck_latest.json`, `docs/final/artifacts/MULTILENS_P1_AB_FINAL_SELECTION_V1.json`.
- **압축 API 폴백 텔메트리(24h 요약):** 일일 `scripts/Invoke-MkmAiV2DailyReadiness.ps1`가 `build_fallback_trigger_daily_summary_v1.py`를 실행한다(BL-011). 헬스에서는 `-IncludeFallbackTriggerTelemetry` 또는 `-IncludeCompressionKpi`(압축 KPI와 함께 요약 갱신·산출 존재 검증). 임계 프로파일 재생성: `py scripts/build_fallback_trigger_threshold_profile_v1.py` → `docs/final/artifacts/fallback_trigger_threshold_profile_latest.json`. Windows 일일 등록: `scripts/Register-MkmAiV2ReadinessDailyTask.ps1`(태스크명 `MKM_AIV2_DailyReadiness`).
- **Track A 상용화 하네스(시뮬·섀도우·계량·SLA 초안):** `run_track_a_conversational_cost_simulation.py` · `run_track_a_shadow_corpus_eval.py` / `Run-TrackAShadowJsonlSample.ps1` · `compression_token_api_stub.py`의 `POST /v1/metering/log`·`eval_context.meter_log`·`run_track_a_metering_summary.py` (`Run-TrackAMeteringSummary.ps1`)·`run_track_a_metering_weekly_report.py` (`Run-TrackAMeteringWeeklyReport.ps1`)·`check_track_a_metering_band_gate.py`·`build_track_a_signal_light_report.py`·`run_track_a_commercialization_daily_chain.ps1` (`Register-TrackACommercializationDailyTask.ps1`·`Verify-TrackACommercializationDailyScheduledTask_v1.ps1`, 기본 `GateMode=warning`) · `docs/final/TRACK_A_SLA_DRAFT.md` — 상세·경로는 `docs/final/P0_COMMERCIALIZATION_TRACKER.md` 압축·L2 절.
- **해석 파이프라인**: `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` — NotebookLM·브리핑은 **참고**; 구현·KPI는 스크립트·산출물만 SSOT.
- **Multilens P1 A/B**: 본선 갱신 `py scripts/run_multilens_p1_production_chain.py`(또는 `scripts/Run-MultilensP1ProductionChain.ps1`); B-track 샌드박스 `py scripts/run_multilens_p1_btrack_chain.py`(또는 `Run-MultilensP1BTrackSuite.ps1`, `-IncludeBalancedWeightsSweep` 선택). 명령만 확인: `--dry-run`; JSON 실행 계획만 출력: `--json-plan`(서브프로세스 미실행, schema `multilens_p1_chain_plan_v1`).

## 도메인 핸드오프(참고)

- **jema12.com 본선(SSH Cursor)**: `docs/final/SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md` — 원격 워크스페이스에서 `git pull` → `scripts/deploy/linux/apply_jema12_nginx_snippet.sh` · 검증 스크립트 경로. 도메인·스냅샷: `docs/final/JEMA12_PUBLIC_DOMAIN_AND_DEPLOY_HANDOFF_2026-04-07.md`.
- **jema-ai.com (`projects/no1kmedi`)·mkmlife.com 경로·VPS PM2·Hostinger 수동 배포**: `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` — 파일명의 `NO1KMEDI`는 역사적 레이블(jema-ai.com 앱 경로 포함); 로컬 `C:\workspace` 트리와 분리된 `E:\workspace\mkm-life\deploy-to-hostinger.ps1` 등 **실측 경로** 정리; **UI 면책 배지·컴포넌트/폴백 초안**은 동 문서 **§10**(`§10.3` 부록). jema12 런북과 혼용 금지.
- **다도메인 포트폴리오·미확정(jema-ai.com, personadiary.com 등):** `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` — 표·NotebookLM 기준; 전용 포인터 `JEMA_AI_DOMAIN_POINTER_V1.md`, `PERSONADIARY_DOMAIN_POINTER_V1.md`.
- **일반 예언(B 레일)**: 스키마·스크립트·월간 체인은 **저장소 루트**(`GENERAL_PROPHECY_SCHEMA_V1`, `scripts/generate_general_prophecy_v1.py` 등, `run_waiting_queue_monthly_check.ps1`) — **별도 서브트리에 복제본을 두지 않고** 루트 SSOT를 따른다. 실시간 운영 경로는 `eval_prophecy_hit_rate_v1.py`와 `run_prophecy_restoration_spike.py` 중심으로 유지하며, 비활성/미배포 체인은 SSOT 필수 경로로 고정하지 않는다.
- **B-track 가격 예언 체인(사전 점검)**: `py scripts/check_btrack_prophecy_chain_prereqs_v1.py` — 일일 체인에 쓰는 스크립트·KOSPI/BTC 기본 CSV·주요 `*_latest` 존재·`btrack_prophecy_score_latest.json` 기준 instrument 듀얼 레그 요약; `--stdout-only`·`--strict`. 상세·`--force-dual-leg-panel`은 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` Prophecy Hit Rate 절.
- 한의 원전·코호트: `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` (라벨 A vs 원전 B 혼선 금지).
- NotebookLM 소스: `docs/NotebookLM_sources_manifest.md`.
- **NotebookLM MCP (재발방지)**: Settings에서 녹색·N tools여도 **현재 채팅에 도구가 주입되지 않으면** 에이전트는 호출 불가 — UI 연결 ≠ 세션 사용 가능. **내장 브라우저·Chrome 로그인 ≠ MCP 인증**(전용 Chrome 프로필). **동기화 ≠ 한 가지:** Vault 미러(A)·구글 노트북 소스(B)·채팅 MCP(C)는 독립 — 원샷 점검 `scripts/Invoke-NotebookLmSyncTriage_v1.ps1` · 표 `docs/NotebookLM_sources_manifest.md` 「동기화 오해 · 재발 방지」. SSOT: `.cursor/rules/notebooklm-mcp-session-bridge.mdc`(항상 적용), `docs/NotebookLM_sources_manifest.md`(MCP 인증 절), 점검 `scripts/check_notebooklm_mcp_prereqs.ps1`. 스킬 `.cursor/skills/notebooklm-refresh/SKILL.md` §세션 vs UI.
- **NotebookLM 인증 복구 표준 3단계**: 문제가 나면 `scripts/repair_notebooklm_mcp_auth_stuck.ps1` -> MCP `setup_auth` -> MCP `get_health`(`authenticated=true` 확인) 순으로 고정.
- **NotebookLM 세션 시작 게이트**: NotebookLM을 쓰는 턴의 첫 호출은 항상 MCP `get_health`; `authenticated=false`면 질의 전에 복구 3단계를 먼저 수행한다.

## 운영 자동화 vs 연구 레인

- **본선 OPS** (`projects/bitcoin-trading/ops/windows-rehearsal`, `verify_all_green`, `automation_registry.json`): **관측·스케줄·게이트** 전용. 헌법·백서를 LLM이 매 실행마다 해석해 본선을 바꾸는 **자율 전략 엔진**으로 단정하지 않는다. 구현 여부는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 호출 가능 스크립트로만 말한다.
- **Phase 1 통합 리포트 SSOT**: `projects/bitcoin-trading/memory/v2/ops/ops_phase1_chain_report_latest.json` — **exit_code·타임스탬프·산출 경로** 중심. 브리핑 전용 필드(예: `go_no_go`)는 **레포 산출물에 없으면** 근거 없는 수치로 쓰지 않는다.
- **헌법 게이트(옵션)**: `run_ops_phase1_chain.ps1 -IncludeConstitutionGates` → `verify_constitution_gates.ps1` → `projects/bitcoin-trading/memory/v2/ops/constitution_gates_result_latest.json`; allowlist `constitution_gates_v1.json`. 상세 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §13.1.
- **Phase 1 일일 원클릭**: `projects/bitcoin-trading/ops/windows-rehearsal/bootstrap_ops_phase1_daily.ps1` — User 환경 동기화 후 `\Bitcoin-Ops-Phase1-Chain-Daily` 등록(헌법 게이트 기본 켬). 점검·웹훅 스모크: `-IncludeReadiness`, `-IncludeWebhookSmoke`.
- **Pre-News Shadow 일일 체인(운영)**: `scripts/run_daily_prophecy_then_pre_news_v1.ps1 -EnablePreNewsShadow -EnablePreNewsShadowWeeklyReport` — projection/weekly/audit bundle을 한 체인으로 갱신.
- **Pre-News Health/Alert 체인**: `scripts/run_pre_news_shadow_health_chain.ps1` + CI `.github/workflows/pre-news-shadow-health-smoke.yml` — task health/alert/drill 계약 회귀를 고정.
- **Pre-News 월간 거버넌스 드릴**: `scripts/run_pre_news_shadow_monthly_governance_drills_v1.ps1` (lock mismatch + policy alert drill) — 결과는 `pre_news_shadow_monthly_drill_summary_alert_latest.json`으로 확인.
- **MKM Study**(예: `projects/mkm/mkm-study`): **연구·프로토타입·학습** 레인. 실매매·본선 OOF·올그린 게이트와 **자동 합선하지 않는다** (NotebookLM·A/B 격벽과 동일 방향).

## B-track 실행 기본값 (탐색 우선)

- **기본 모드**: B-track은 보수 게이트 우선이 아니라 **성능 탐색 우선**으로 운영한다.
- **원클릭 진입점**: `scripts/run_btrack_full_explore.ps1`를 기본 실행 경로로 사용한다.
- **최소 안전선만 유지**: `B-track 아티팩트 경로`, `재현 seed 기록`, `시간/비용 상한`, `A-track 자동 합선 금지`.
- **전환 규칙**: 유망 uplift가 확인되면(예: short-bucket 개선) 동역학 결합 모델까지 포함해 즉시 비교 벤치를 확장한다.
- **금지**: B-track 실험 결과를 승인 없이 실거래/프로덕션 게이트에 자동 반영하지 않는다.
- **승격 (압축·복원 연구 → 상용/프로덕션 주장):** `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` §9 + `docs/final/P0_COMMERCIALIZATION_TRACKER.md` — `projects/bitcoin-trading/docs/final/STAGING_TO_PRODUCTION_PROMOTION_CHECKLIST_2026-03-25.md`(거래 스테이징)와 **절차·범위 혼동 금지**.
- **Track B 주간 메트릭·게이트(연구 레인, 압축 엔진과 별도)**: `scripts/Run-TrackBWeeklyRefresh.ps1` — 도메인 쌍·semantic(Jaccard/cosine_tokens)·`build_trackb_semantic_eval_by_domain.py`·OOV 스윕·action layer·결정성·선택 상태 시뮬·`trackb_weekly_gate_recheck_latest.json` 등. `-SkipSsmSmoke` / `-SkipCosine` / `-IncludeExtendedStressGrid`(확장 Length/OOV 스트레스, 시간 증가) 선택; 요약 MD 예시 `docs/final/artifacts/trackb_weekly_formula_utility_report_2026-04-08.md`.
- **에이전트·채팅에서 Track B 명시 시:** 가설·멀티렌스·메타포 등 **탐색 서술을 넓힌다**. 답변·산출 끝에 **B-track·`[HYPO]`·Track A·실매매와 자동 합선되지 않음**을 한 줄로 남긴다(대외 주장·운영 트리거로 격상 금지).
- **“무제한”이 아닌 제약:** 가설 JSON은 `py scripts/generate_btrack_hypothesis_prophecy_v1.py` 및 `docs/final/BTRACK_HYPOTHESIS_PROPHECY_V1.schema.json` 기준으로 **`hypothesis_tier=B`·`boundary_ack`·라벨 `[HYPO]`** 등 필드·경계를 지킨다. 클라우드 Gemini·유료 API는 **명시 플래그·환경·비용 상한** 하에서만.
- **가격 적중 채점 체인(팩트 포인터):** 일일 번들 `scripts/run_btrack_daily_hypothesis_chain.ps1`이 (기본) `generate_btrack_hypothesis_prophecy_v1` → `build_btrack_prophecy_score_from_ohlcv.py` → `eval_prophecy_hit_rate_v1.py --run-mode price` 경로를 포함한다(`-SkipHitRate`로 생략 가능). 표·분기·proxy 분기는 **`docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`** 일일 B-Track 번들·Prophecy Hit Rate 절.
- **권장 측정·neutral_bps 자동 스윕(주간 스케줄 가능):** `py scripts/run_prophecy_btrack_recommended_eval_chain_v1.py --auto-sweep-and-apply` 또는 `scripts/Run-BtrackRecommendedEvalAutoSweep_v1.ps1` — 기본 그리드 스윕 후 최적 행을 `reports/*_recommended*_latest*`에 반영; 승격 판정은 `reports/prophecy_promotion_gates_recommended_chain_v1_latest.json`. 로그오프 실행(S4U) 묶음: `scripts/Register-BtrackRecommendedEvalAutoSweepWeeklyTask.ps1 -RunWhenLoggedOff`(관리자 번들 `Register-MkmBtrackProphecyTasksRunWhenLoggedOff_v1.ps1`에 포함). **A-track·실매매 자동 합선 없음.**

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

- **대외 보안·IP·카피(웹·제안서·쇼룸 공통):** `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` — 비밀·내부 경로 비노출, 이론·파이프라인 비노출, 과장·규제 민감 표현 회피; 상용·법무 경계는 `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md`와 정합. 구현 팩트는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`만 SSOT.
- **도메인별 쇼룸·체험 표면(어디에 무엇):** `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` §1.1 — jemaai.cloud(공개 전광판)·mkmlife.com(원퀘스천 리포트)·jema-ai.com(브랜드 허브) 등 역할 분리; **§1.1b** = jema-ai 랜딩→타 도메인 **CTA 라벨 초안**; 표 개정 시 Track C·NO1KMEDI·`JEMA_AI_DOMAIN_POINTER_V1`과 함께 맞출 것.
- **하이브리드 대시보드 스펙(SSOT):** `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md` — 공개(전광판) vs 비공개(조종실), `public-event.v1` 필드·경계선.
- **MVP 게이트웨이:** `public_event_gateway.py` — `GET/POST` 경로·토큰은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 동 디렉터리 nginx 예시 참고.
- **로컬 융합 점검 (비배포):** `scripts/run_jemaai_cloud_completion_chain.ps1` — Fact-Lock·Thin·BTC 앵커·P1(기본)·MVP 파일 존재 확인; `-SkipP1AB`로 P1 생략. VPS/nginx 반영은 본선 일정에서 수동.
- **쇼룸 정적 → VPS (워크스페이스 루트에서):** `pwsh .\scripts\sync_showroom_to_vps.ps1 -RefreshStaging` — 래퍼가 `projects/bitcoin-trading/ops/windows-rehearsal/sync_showroom_to_vps.ps1`로 위임. `sync_showroom_to_vps.ps1`만 입력하면 PATH에 없어 실패할 수 있음. scp 비밀번호 반복 완화: User 환경에 `MKM_VPS_SCP_EXTRA_ARGS`(예: `-i` 키경로); 업로드 후 nginx 자동 reload는 `JEMAAI_VPS_RELOAD_NGINX=1`일 때만(의도 확인 후). 상세 표: `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`(Showroom VPS 전송 행).

## SSH Cursor · VPS 실매매 (전제)

- **Git 재발 방지 점검:** `scripts/Verify-GitWorkspaceSanity.ps1` 또는 `scripts/run_workspace_automation_health.ps1 -IncludeGitSanity`(`-StrictGitSanity`는 exclude/원격 오류 시 exit 1). `.git/info/exclude`에 `tools/`·`scripts/`만 두고 `!` 예외 없이 막으면 추적 파일이 조용히 제외된다(루트 `AGENTS.md` 본 절과 동일 경고).
- **`origin/main` 대비 drift:** Linux·SSH는 `scripts/verify_git_origin_main_sync.sh`(`--strict` 권장 후 `git pull --ff-only origin main`). Windows는 동일 로직을 `Verify-GitWorkspaceSanity.ps1 -CheckOriginMainSync`로 실행; 헬스 체인은 `run_workspace_automation_health.ps1 -IncludeGitOriginMainSync`(`-StrictGitOriginMainSync` 선택).
- **SSH로 연 원격 폴더**를 열면 그쪽 `AGENTS.md` / `.cursor/rules`가 적용된다. 로컬 `C:/workspace`와 동시에 쓰면 **git 동기화**로 규칙을 맞춘다.
- 로컬 트리는 **개발·테스트·문서** 우선. **실매매 런타임**은 VPS 등 별도 배포본일 수 있으므로, 코드·설정이 자동 동일하다고 가정하지 않는다.
- 질문·답변에서 **로컬만**인지 **배포(VPS) 후**인지 구분한다. VPS 경로·PM2 앱 이름 등은 **지휘관이 확정한 값**으로만 서술하고, 미확인이면 “확인 필요”로 표기한다.
- **Ollama (VPS/본선)**: `gemma4:e2b` 등 최신 모델 풀 시 구버전은 레지스트리 **412** 가능 → **Ollama 업그레이드** 후 `ollama pull`. 로컬 `C:\workspace` Cursor 세션은 **VPS 셸이 아님**; 업그레이드·모델 설치는 **서버 셸(또는 SSH Cursor가 연 그 호스트)** 에서 수행. 태그 정렬: **`OLLAMA_MODEL=gemma4:e2b`**(로컬 `.env` 등).
- 로컬 **SITREP → 공유 Vault 보급**(Windows, G: 마운트 시): `scripts/titan-sync.ps1` — **VPS 실매매 배포와는 별 작업**이다.
- **리스크 프로필 소스 고정(n8n 등):** Windows 사용자 환경변수 `RISK_PROFILE_SOURCE_NAME` / `RISK_PROFILE_MODE_NAME`을 설정하면 `projects/bitcoin-trading/ops/windows-rehearsal/ensure_daemon_running.ps1`의 Fact-Safe 동기화가 매 기동 시 동일 라벨을 넘긴다(미설정 시 기존 `memory/v2/risk/risk_profile_fact_safe_latest.json`의 source/mode를 보존).

## 예언 레일 운영 요약 (7줄)

- 클로저 실행: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1`
- 통과 판정: `reports/prophecy_lane_closure_bundle_v1_latest.json`의 `closure_ok: true` + `steps[*].exit_code==0`
- 수동 잔여: `manual_remainder` 기준으로 `schtasks` 자격/로그온 정책과 Track A 승격·실매매 인간 게이트를 분리 유지
- 일반예언 스케줄: `\GeneralProphecyDailyQueueV1`, `\GeneralProphecyHoldoutEvolutionWeeklyV1`를 Task Scheduler에서 `Ready` 확인
- 소프트 인플루언스 갱신(선택): `build_general_prophecy_explainable_v1.py` -> `report_general_prophecy_explainability_quality_v1.py` -> `sync_biblical_lane_hook_to_bitcoin_trading.py`
- 경계선 고정: B-track 산출은 `[HYPO]`/관측 레일이며 Track A 실거래로 자동 합선되지 않음
- 운영 기본: 실패·경고는 아티팩트 JSON과 exit code로 보고하고, 실거래 활성화는 별도 승인 절차를 따른다
