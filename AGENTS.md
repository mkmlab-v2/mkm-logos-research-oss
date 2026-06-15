# AGENTS — 워크스페이스 에이전트 SSOT (주입층 · slim)

**역할**: Cursor **매 턴 주입**용 짧은 진입점. 페르소나 전체 표·도메인·압축·B-track 상세 → **`docs/final/AGENTS_REFERENCE_V1.md`** (`@` 또는 Read).

## 우선순위 (충돌 시 위가 이김)

1. 루트 `.cursorrules` (TITAN · Ask Gate)
2. `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` + 호출 가능 `.py`/스크립트·exit code·아티팩트
3. `.cursor/rules/*.mdc` 코어 `alwaysApply` (감사: `py scripts/check_cursor_rules_context_diet_v1.py --strict`)
4. 본 파일 · 확장 `docs/final/AGENTS_REFERENCE_V1.md`

## Fact-Lock · 격벽 (한 화면)

- 구현·통과 주장 = CONSTITUTION + 스크립트·pytest만. NL·채팅 요약 단독 근거 금지.
- Track A(운영) vs B(연구/`[HYPO]`) — **B→A·실매매 자동 합선 금지**.
- 렌즈: `사상` / `명리` / `성경(Logos)` — Final Action = 1차 `regime_map` + 운영 게이트.
- MKM = **4AI core + Absolute Balance Coordinator Mode** (제5 AI/체질 아님).

## 재개 · 종료 (SSOT: `.cursor/rules/central-agent-memory.mdc`)

| 트리거 | 동작 |
|--------|------|
| 장기기억 맥락이어 · 미션로그 이어서 · CENTRAL 기준 (동등) | `powershell -File scripts\Invoke-MkmCursorSessionUpgrade_v1.ps1` (`-Lane` 있으면) → Read `docs/final/artifacts/mkm_chat_resume_pack_latest.md` — **MISSION_LOG 통째 금지** |
| 장기기억 저장 · 체크포인트 | `py scripts/athena_checkpoint.py "<한 줄>"` (exit 0) |
| 의미 있는 진행 후 | `MISSION_LOG.md` **해당 레인** 다음 Action **1줄**만 (`mission-log-combat-ssot.mdc`) |

- **solo_ops:** 재개 시 `reports/mkm_solo_background_ops_state.json` 오늘 `last_ok` 아니면 `Invoke-MkmSoloBackgroundOps_v1.ps1` (`mkm-solo-background-ops-auto.mdc`).
- **WSE-3 스타터:** `@.cursor/rules/mkm-wse3-commander-starters.mdc`

## 페르소나 트리거 (요약 — 전체 표는 REFERENCE)

| 구분자 | 명령 (루트 `C:\workspace`) |
|--------|------------------------------|
| 【아테나 점검】 | `powershell -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaBundle` |
| 【빠른 헌법 점검】 | `… -Persona P0` |
| 【암행어사 점검】 | `… -Persona AmsaengHealth` |
| 【커서 세션 업그레이드】 | `… -Persona CursorSessionUpgrade` |
| 【고차원 자율진화】 | `… -Persona HdAutonomousEvolution` (env `MKM_HD_AE_MISSION`·`MKM_HD_AE_LANE`; SSOT `docs/final/artifacts/mkm_high_dimensional_autonomous_evolution_v1_latest.json`) |
| 【Bounded lane shadow】 | `… -Persona BoundedLaneLoopShadow` |
| 【에이전트 micro-loop】 | `… -Persona MkmAgentLoops` → `docs/final/artifacts/mkm_agent_loops_v1_latest.md` |
| 【프리미엄 큐 권장】 | `… -Persona PremiumMultilensQueue` |
| 【Design 레인】 | `… -Persona DesignLane` |

→ 나머지 40+ 행: **`AGENTS_REFERENCE_V1.md` 「페르소나 단축 호출」**

## 핵심 SSOT 포인터

| 주제 | 경로 |
|------|------|
| 정체성·분기 | `docs/final/CENTRAL_AGENT_MEMORY_V1.md` |
| 작전 보드 | `MISSION_LOG.md` (로컬) |
| 로컬↔VPS | `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md` |
| Fact-Lock 번들 | `scripts/run_fact_lock_bundle.ps1` |
| Cursor 세션 baseline | `docs/final/CURSOR_SESSION_VALIDATION_BASELINE_V1.md` |
| 인프라·GPU·PC 경로 | `docs/final/LOCAL_MACHINE_POINTER_V1.md` (비추적) |

## Git · 원격 (한 줄)

- 기본 push: `scripts/push-internal.ps1` → **gitea/internal** only. GitHub: `Push-GitHub-Explicit.ps1 -Acknowledge` 예외만.
- `1작업=1브랜치=1PR` 권장 · 솔로는 `SoloDev-MergeFeatureToGiteaMain.ps1` 참고.

## User Rules (Cursor Settings · 레포 밖)

- **권장(컨텍스트 다이어트):** `docs/final/artifacts/cursor_user_rules_minimal_v1.txt` → User 탭에 **그대로 복붙** (5줄·충돌 시 레포 규칙 우선).
- 장문 합본(핸드오프·일기 분기 포함): **`AGENTS_REFERENCE_V1.md` 「Recommended Cursor User Rules」** — User Rules에 **이중 주입 금지**(slim + 합본 동시 X).

## MCP · 도구 카탈로그 (컨텍스트)

- **워크스페이스 SSOT:** `.cursor/mcp.json` (MKM lean 7). `openchrome`·`hostinger-website-manager`는 **요청 시**만 추가.
- **Cursor 플러그인 MCP**(Figma·Datadog·Slack·Postman 등): 채팅 시작 시 도구 목록에 합류 — **안 쓰면 Settings에서 OFF**.
- NL: `@notebooklm-mcp-session-bridge` · 자율 웹검색: `@autonomous-web-search-v1` · 점검: `scripts/check_notebooklm_mcp_prereqs.ps1` · `scripts/Invoke-McpHygieneProbe.ps1`

## `.cursorrules` (TITAN · Slim v2)

- SSOT 템플릿: `docs/final/artifacts/cursorrules_slim_ssot_v1.txt` — 루트 `.cursorrules`와 **동기 유지** (`py scripts/enforce_cursorrules_slim_ssot.py` · drift: `check_cursorrules_template_drift_v1.py` · diet `--strict`에 포함).

## 확장 읽기 (레인별)

압축·B-track·쇼룸·예언·Gemini·도메인 핸드오프·병렬 작전 → **`docs/final/AGENTS_REFERENCE_V1.md`** 해당 절. `CLAUDE.md` = 개발 진입 요약(중복 최소화).
