# MKM Cursor Session Ops

## Purpose

Run the **minimum validation baseline** for a Cursor chat session: separate in-chat rules from executable gates, wire long-term memory inject, and close with checkpoint + MISSION_LOG lane update.

**SSOT:** `docs/final/CURSOR_SESSION_VALIDATION_BASELINE_V1.md`

## Triggers

Use when the user:

- Starts a large session or says 「장기기억 맥락 이어」「CENTRAL 기준」「미션로그 이어서」
- Logos advanced: 「장기기억 맥락이어 고급해석」→ `-Lane oracle -ResumeMode AdvancedLogos`
- Asks whether Cursor auto-validates theory / AI-to-AI memory
- Ends a meaningful work block (checkpoint, handoff)
- Works a **lane**: MS · Oracle · Infra · web_ops · Design/Showroom

## Session start (execute in order; skip rows marked optional)

1. **Read** `docs/final/CENTRAL_AGENT_MEMORY_V1.md` checkpoint block + `MISSION_LOG.md` relevant lane block (if resume trigger).
2. **Solo ops** (if `reports/mkm_solo_background_ops_state.json` `last_ok` ≠ today local date):
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmSoloBackgroundOps_v1.ps1
   ```
3. **Resume pack** (when lane known):
   ```powershell
   py scripts/build_mkm_chat_resume_pack_v1.py --lane oracle
   ```
   Logos advanced: `powershell -File scripts\Invoke-MkmCursorSessionUpgrade_v1.ps1 -Lane oracle -ResumeMode AdvancedLogos`
   Lanes: `oracle` | `ms` | `infra` | `web_ops` (omit `--lane` for default 3-node pins).
4. **P0** (before implementation claims):
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona P0
   ```

Report one line: `solo_ops: ok|fail · date` · resume pack exit · P0 exit.

## Session mid (match task)

| Task | Command |
|------|---------|
| Showroom / lens media hub | `py scripts/check_lens_media_hub_live_qa_v1.py --offline` |
| Track C health | `powershell -File scripts\Invoke-ShowroomTrackCHealth_v1.ps1` |
| Ops memory index | `powershell -File scripts\Invoke-MkmOpsMemoryIndexRoutine_v1.ps1` |
| Full regression (weekly) | `powershell -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaBundle` |

## Session end

1. ```powershell
   py scripts/athena_checkpoint.py "<완료/다음 한 줄>"
   ```
2. Update **only** the active lane block in `MISSION_LOG.md` — **next 1 action**.
3. Handoff to snapshot **only** if user message includes 「핸드오프」·「옵스 스냅샷」 → `CURRENT_OPS_SNAPSHOT.md` only (not MISSION_LOG duplicate essay).

## AI↔AI memory (not auto every chat)

- **Not a new language** — structured anchors + `must_keep_tags` + JSON resume pack.
- **B-track `[HYPO]`** — no Track A / live trading auto-merge.
- Full chain: `MKM_OPS_MEMORY_AI_TO_AI_DEV_ONE_PAGER_V1.md`

## Fact-Lock footer (baseline / resume answers only)

Use on **resume·헌법 점검·구현 판정** 답변. 일반 코딩·연구 Q&A에는 **루틴 live-trading 면책 생략** (`commander_chat_tone_prefs_v1_latest.json`).

When used, end with:

1. **Layer:** A (rules only) / B (disk+inject) / C (schedule/CI) — which applied this turn.
2. **Evidence:** script paths + exit codes actually run (or 「미실행」).
3. **Boundary:** only if trading·SEND·live deploy was in scope — otherwise omit.
