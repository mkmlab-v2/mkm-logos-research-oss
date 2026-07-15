# Cursor Session Validation Baseline v1

**Date:** 2026-06-09  
**Track:** 운영 · Fact-Lock · **not** Track A promotion · **not** live-trading auto-GO  
**SSOT human:** `MISSION_LOG.md` · `docs/final/CENTRAL_AGENT_MEMORY_V1.md`  
**Machine inject:** `scripts/build_mkm_chat_resume_pack_v1.py` · `storage/meta/mkm_ops_memory_index_v1.json`  
**Related:** `docs/final/MKM_OPS_MEMORY_AI_TO_AI_DEV_ONE_PAGER_V1.md` · `.cursor/rules/cursor-session-validation-baseline-v1.mdc`

---

## 1) Fact-Lock 한 줄

**Cursor 사용량 ≠ 자동 검증.** 매 턴은 **규칙(소프트 가드)**만; **실행 검증**은 아래 표의 **트리거·리듬·명령**으로만 판정한다.

---

## 2) 세 층 (혼동 금지)

| 층 | 무엇 | 자동? | 판정 |
|----|------|-------|------|
| **A · In-chat governance** | `.cursor/rules` `alwaysApply`, `.cursorrules` TITAN | 매 Cursor 턴 컨텍스트 주입 | 행동·서술 가이드 (pytest 아님) |
| **B · Disk SSOT + AI↔AI inject** | CENTRAL · MISSION_LOG · ops memory index · resume pack | **재개/체크포인트/루틴** 시 | exit 0 · `must_keep` 게이트 |
| **C · Scheduled / CI** | Task Scheduler · GitHub Actions · PC 예약 | PC/원격 **시간·push** 기준 | exit 0 · `*_latest.json` |

**금지:** A만으로 “이미 검증 통과” 단정 · B-track `[HYPO]`를 Track A·실매매에 자동 합선.

---

## 3) Cursor 세션 — 최소 자동 검증 표 (지휘관·에이전트)

**저장소 루트 `C:\workspace` · Windows `py` / `powershell`**

### 3.1 세션 시작 (새 채팅 · 큰 작업)

| # | When | Action | Pass | Skip when |
|---|------|--------|------|-----------|
| S1 | 재개 트리거(「장기기억 맥락 이어」·`@CENTRAL`·`@MISSION_LOG`) | Read `CENTRAL` + 작전 보드 1블록 | 맥락 1줄 브리핑 | 단순 Q&A 1턴 |
| S2 | 레인 작업(MS/Oracle/Infra/web_ops) | `py scripts/build_mkm_chat_resume_pack_v1.py --lane <lane>` | exit 0 · `mkm_chat_resume_pack_latest.json` | 동일 레인 짧은 후속 1턴 |
| S2b | 재개 트리거 후 (Pillar A LTM) | `Invoke-MkmCursorSessionUpgrade_v1.ps1 -Lane <lane>` → Read pack → envelope → `MISSION_LOG` 다음 1타 | exit 0 · `mkm_cursor_deep_handoff_envelope_v1_latest.json` · `required_ssot_refs` | Oracle graph_slice 채팅 |
| S3 | MISSION_LOG 재개 + 오늘 solo ops 미실행 | `powershell -File scripts\Invoke-MkmSoloBackgroundOps_v1.ps1` | `reports/mkm_solo_background_ops_state.json` `last_ok` 오늘 | 이미 `last_ok` 오늘 |
| S4 | 구현·경로 주장 전 | `verify_p0_constitution_gate_paths.ps1` 또는 【빠른 헌법 점검】 | exit 0 | 문서만 읽기 |

### 3.2 세션 중 (코드·배포·Track C)

| # | When | Action | Pass |
|---|------|--------|------|
| M1 | PR/머지 전 | `Invoke-MkmPersonaHealth_v1.ps1 -Persona P0` | exit 0 |
| M2 | 쇼룸·허브·Track C 표면 | `check_lens_media_hub_live_qa_v1.py --offline` (+ 배포 후 live) | exit 0 · pairs=12 |
| M3 | Track C 번들/게이트 | `Invoke-ShowroomTrackCHealth_v1.ps1` (또는 페르소나 ShowroomTrackCHealth) | exit 0 |
| M4 | Ops Memory inject 변경 | `Invoke-MkmOpsMemoryIndexRoutine_v1.ps1` | source+inject gate OK |

### 3.3 세션 종료 (의미 있는 진행 후)

**지휘관 트리거:** `마무리` · `마무리해줘` (레거시: `장기기억 저장` · `체크포인트`) — SSOT `mkm_commander_resume_triggers_v1.json` `session_end_modes` · 시작과 짝: `장기기억 맥락이어`.

| # | When | Action | Pass |
|---|------|--------|------|
| E1 | 정책·분기 1줄 | `py scripts/athena_checkpoint.py --continuity-id <id> "<한 줄>"` | exit 0 · CENTRAL checkpoint |
| E1b | 턴 메타 (Infra LTM) | `py scripts/append_mkm_cursor_turn_meta_v1.py --continuity-id <id> ...` 또는 `run_mkm_cursor_session_end_v1.py` | `mkm_cursor_turn_meta_log.jsonl` · `self_audit` |
| E1c | 턴 메타 감사 (주기) | `py scripts/check_mkm_cursor_turn_meta_audit_v1.py` | `mkm_cursor_turn_meta_audit_v1_latest.json` · sparse=WARN |
| H1 | Pillar A 회귀 (헬스) | `run_workspace_automation_health.ps1 -PillarACursorContinuitySmokeOnly` | `run_mkm_pillar_a_cursor_health_smoke_v1.py` exit 0 |
| E2 | 레인 다음 1타 | `MISSION_LOG.md` **해당 블록만** 갱신 | 1 action line |
| E3 | (선택) 크로스 채팅 핸드오프 | `@CURRENT_OPS_SNAPSHOT` Ops slice 3줄 | 지휘관이 「핸드오프」 요청 시만 |

### 3.4 PC 리듬 (Cursor와 무관 · 백그라운드)

| 리듬 | 명령 | Evidence |
|------|------|----------|
| **일간** | `Invoke-MkmPersonaHealth_v1.ps1 -Persona AmsaengHealth` | exit 0 |
| **주간** | `Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaBundle` | exit 0 |
| **주간 hygiene** | `Invoke-MissionLogCentralHygiene_v1.ps1` | `overall_ok=true` |
| **쇼룸 public** | GitHub `showroom-public-smoke` (cron) | live hub QA |

---

## 4) AI↔AI · 장기기억 (별도 프로토콜)

- **새 자연어가 아님** — `node_id` · anchor slice · `must_keep_tags` · resume pack JSON.
- **Human SSOT:** Markdown (`MISSION_LOG` · `CENTRAL`) → **derived:** `mkm_ops_memory_index_v1.json`.
- **게이트:** `check_mkm_ops_memory_must_keep_gate_v1.py` (`source` / `inject`).
- **Track:** B · `[HYPO]` · inter-agent wire 본선 승격 **HOLD** (`MKM_OPS_MEMORY_AI_TO_AI_DEV_ONE_PAGER_V1.md` §NEVER).

**NotebookLM:** 참고 원천 — MCP `get_health.authenticated` ≠ 웹 로그인. 체화는 CENTRAL/Git만.

**athena-core MCP (`MKM12_LTM_DB_TYPE=file`):** 보조 — 모든 채팅 필수 아님.

---

## 5) 페르소나 트리거 (복붙)

| 구분자 | 명령 |
|--------|------|
| 【빠른 헌법 점검】 | `Invoke-MkmPersonaHealth_v1.ps1 -Persona P0` |
| 【암행어사 점검】 | `-Persona AmsaengHealth` |
| 【아테나 점검】 | `-Persona AthenaBundle` |
| 【쇼룸 헬스】 | `-Persona ShowroomTrackCHealth` |

전체 표: `docs/final/AGENTS_REFERENCE_V1.md` 「페르소나 단축 호출」(slim `AGENTS.md`는 hot 5만).

---

## 6) NEVER (Fact-Lock)

- Cursor 턴 수·채팅량으로 Track A·예언 품질·실매매 GO 단정.
- `alwaysApply` 규칙만으로 pytest·P0 통과 주장.
- Ops memory index JSON을 human SSOT로 승격.
- repair_v2만으로 Track A promotion (`tracka-raw-gate-guard-v1`).

---

## 7) 승격·변경

본 baseline 변경 시 동기화 대상:

- `.cursor/rules/cursor-session-validation-baseline-v1.mdc`
- `.cursor/skills/mkm-cursor-session-ops/SKILL.md`
- `AGENTS.md` (짧은 포인터)
- `MISSION_LOG.template.md` §Cursor Session Validation
- `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §6 표 1행
- (선택) `TRACK_C_IP_BUSINESS_PLAN` §2 운영 절
