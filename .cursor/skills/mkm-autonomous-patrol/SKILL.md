---
name: mkm-autonomous-patrol
description: >-
  MKM 자율점검 — solo_ops + Daily/Weekly patrol + Git/CI snapshot + manual_queue.
  Use when user says 자율점검, 【자율점검】, autonomous patrol, or asks for daily
  self-management / ops patrol one-shot.
---
# MKM Autonomous Patrol (자율점검)

## Triggers

- `자율점검` / `【자율점검】` / `autonomous patrol` / `자율 경영`
- User wants one-shot daily ops + Cursor comfort + scheduler hygiene

## ALWAYS (agent)

1. Run from repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmAutonomousPatrol_v1.ps1 -ContinueOnFail
```

Equivalent:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AutonomousPatrol
```

2. Read `reports/mkm_autonomous_patrol_latest.json` — report `overall`, `paste_line`, failed steps.
3. Print **`manual_queue`** items only — do **not** auto-run Tier-3 (GitHub push, ApplySafe, NL login, live, merge main).
4. Fact-Lock: pass/fail = exit code + JSON fields only.

## Cadence (orchestrator logic)

| When | Package |
|------|---------|
| Mon–Sat | `DailyOpsPatrol` after stale `solo_ops` |
| Sunday | `WeeklyOpsPatrol` + lifecycle audit (dry) |

Override: `-ForceWeekly` on orchestrator script.

## NEVER

- Replace `AthenaBundle` / `run_fact_lock_bundle` with 자율점검 (too heavy for daily).
- Auto `Push-GitHub-Explicit`, `SoloDev-MergeFeatureToGiteaMain`, `-ApplySafe` lifecycle.
- Claim Track A / CI green from chat without artifacts.

## Manual Tier-3 SSOT

`docs/final/artifacts/mkm_autonomous_patrol_manual_tasks_v1.json`

## Optional register (commander once)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-MkmAutonomousPatrolDailyTask.ps1
```

Task: `MKM_AutonomousPatrol_Daily` (default 07:30 local).
