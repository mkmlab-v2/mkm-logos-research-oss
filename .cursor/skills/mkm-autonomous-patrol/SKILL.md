---
name: mkm-autonomous-patrol
description: >-
  MKM 자율점검/자율루프 — solo_ops + Daily/Weekly patrol + Git/CI snapshot + manual_queue.
  Use when user says 자율루프, 오늘 자율루프, 자율점검, 【자율점검】, autonomous patrol,
  or asks for daily self-management / ops patrol one-shot.
---
# MKM Autonomous Patrol (자율루프 · 자율점검)

**Commander daily contract SSOT:** `docs/final/artifacts/mkm_autonomous_patrol_commander_daily_contract_v1_latest.md`  
**Elementary paste:** `reports/human_paste/mkm_autonomous_loop_daily_elementary_v1.txt`

## Triggers (chat · once/day OK)

- `자율루프` / `오늘 자율루프` / `【자율점검】` / `자율점검` / `자율 경영` / `autonomous patrol`

## ALWAYS (agent)

1. Run from repo root (either is equivalent):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AutonomousPatrol
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmAutonomousPatrol_v1.ps1 -ContinueOnFail
```

2. Pre: stale `solo_ops` is handled **inside** the patrol (do not require separate Doc Sync / 【아테나 점검】).
3. Read `reports/mkm_autonomous_patrol_latest.json` — report `overall`, `paste_line`, failed steps.
4. Also read sticky (if present): `docs/final/artifacts/mkm_autonomous_patrol_sticky_alert_v1_latest.json` — `alert=true` only on hard schedule fail / this-run FAIL. **exit 2 = WARN soft-clear** (not sticky alert).
5. Print **`manual_queue`** items only — do **not** auto-run Tier-3 (GitHub push, ApplySafe, NL login, live, merge main, Polar).
6. Before any 「자동화 완료/경영 자율」 claim: `py scripts/run_mkm_claim_adversarial_reread_v1.py --claim-text "..."` (patrol `metacog_reminder`).
7. Fact-Lock: pass/fail = exit code + JSON fields only. Map SSOT: `docs/final/artifacts/mkm_meta_ops_automation_map_v1_latest.json`.

## Cadence (orchestrator logic)

| When | Package |
|------|---------|
| Mon–Sat | `DailyOpsPatrol` after stale `solo_ops` |
| Sunday | `WeeklyOpsPatrol` + lifecycle audit (dry) |

Override: `-ForceWeekly` on orchestrator script.

## NON-SCOPE (explicit)

- ≠ `AthenaBundle` / `run_fact_lock_bundle` daily (weekly / separate)
- ≠ PR/merge / GitHub Actions green / Polar
- ≠ Track A / live trade / commercial DONE / SEND unlock
- ≠ Expand daily loop into full CI/CD

## NEVER

- Replace `AthenaBundle` / `run_fact_lock_bundle` with 자율루프 (too heavy for daily).
- Auto `Push-GitHub-Explicit`, `SoloDev-MergeFeatureToGiteaMain`, `-ApplySafe` lifecycle.
- Claim Track A / CI green from chat without artifacts.

## Manual Tier-3 SSOT

`docs/final/artifacts/mkm_autonomous_patrol_manual_tasks_v1.json`

## Schedule (durable plumbing)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-MkmAutonomousPatrolDailyTask.ps1
# Ready only if listed in mkm_scheduler_solo_core_stack_v1.json (tier3) — already listed.
```

Task: `MKM_AutonomousPatrol_Daily` (default **07:30** local) · log `reports/mkm_autonomous_patrol_daily.log`  
Membership smoke: `powershell -File scripts\Test-MkmSoloCoreStackTaskMembership_v1.ps1 -TaskName MKM_AutonomousPatrol_Daily`
