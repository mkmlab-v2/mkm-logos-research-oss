---
module: prophecy_sandbox_btrack
date: 2026-05-19
problem_type: workflow_issue
component: testing_framework
severity: medium
tags:
  - prophecy_sandbox
  - fact-lock
  - automation_health
  - b-track
---

# Prophecy Sandbox health: loose vs strict

## Problem

`check_prophecy_sandbox_health_v1.py` returns **exit 0** in default mode when artifacts exist, even if `max_n_calendar_days` is only **2** (`watchlist_ready: false`). Automation health and daily chain used **non-strict** health only, so **“헬스 통과”와 “watchlist 준비”가 어긋날** 수 있었다.

## Resolution

| 용도 | 명령 | strict |
|------|------|--------|
| 일상·암행어사 스모크 | `py scripts/check_prophecy_sandbox_health_v1.py` | off |
| 주간 Phase3·승격 전 | `… --strict` 또는 체인 `--strict-health` | on (`max_n_calendar_days>=3`) |
| 헬스 체인(선택) | `run_workspace_automation_health.ps1 -IncludeProphecySandboxSmoke -ProphecySandboxHealthStrict` | on |
| 페르소나 | `Invoke-MkmPersonaHealth_v1.ps1 -Persona ProphecySandboxStrict` | on |

**주간 기본:** `run_prophecy_sandbox_weekly_phase3_v1.py` → daily chain에 `--strict-health` 전달 (opt-out: `--no-strict-health`).

**격벽:** `hypothesis_tier: SANDBOX`, `research_only: true` — Track A·실매매 자동 합선 없음.

## Verify

```powershell
py scripts/check_prophecy_sandbox_health_v1.py
py scripts/check_prophecy_sandbox_health_v1.py --strict
py -m pytest tests/test_check_prophecy_sandbox_health_v1.py -q
```

## Related

- `scripts/check_prophecy_sandbox_health_v1.py`
- `scripts/run_prophecy_sandbox_daily_chain_v1.py` (`--strict-health`)
- `scripts/run_workspace_automation_health.ps1` (`-ProphecySandboxHealthStrict`)
