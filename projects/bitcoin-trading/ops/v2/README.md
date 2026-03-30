# Auto-Ops v2 (LangGraph Core)

See also:
- `CURSOR_CHANGELOG_INTEGRATION_PLAN_2026-03-24.md` (Automations/Marketplace/Composer2 integration plan)
- `SSH_VPS_24H_PREP.md` (SSH/VPS independent 24/7 operation for bitcoin + bible insight)

Phase A scope:

- GlobalState and contracts
- Node scaffolding: watchdog, brain_sync, athena, sentinel
- Graph runner with LangGraph and fallback chain
- Minimal scheduled trio (shadow / guarded execute / ops digest)
- Strategy ingest + IDE capability + policy drift + vault sync manifest
- Decision Ledger and Incident Archivist integration
- Policy Drift Bot and Cost Governor Bot integration
- Decision Ledger causal-chain/evidence enrichment
- Incident Archivist RCA template and severity model
- Policy Drift auto-recommended actions and command templates
- Morning Brief delta metrics and Top Risk 3 summary
- Top Risk scoring policy externalized (`risk_scoring_policy.yaml`)
- Morning Brief 48h trend metrics (state journal based)
- Risk score mode guardrail (shadow override / execute block thresholds)

## Run once

```powershell
cd C:\workspace\projects\bitcoin-trading
powershell -ExecutionPolicy Bypass -File .\ops\v2\tasks\run_cycle.ps1
```

## Register scheduler

```powershell
cd C:\workspace\projects\bitcoin-trading
powershell -ExecutionPolicy Bypass -File .\ops\v2\tasks\register_shadow_cycle_task.ps1
powershell -ExecutionPolicy Bypass -File .\ops\v2\tasks\register_execute_guarded_task.ps1
powershell -ExecutionPolicy Bypass -File .\ops\v2\reports\register_ops_digest_task.ps1
```

Operational check:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\v2\reports\check_ops_health.ps1
```

One-shot digest + health check:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\v2\reports\run_ops_digest.ps1 -WithHealth
```

On-demand brain sync note (no always-on schedule required):

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\v2\reports\run_brain_sync_on_demand.ps1
```

## External Memory Runtime (Mem0/Zep)

Enable runtime (User scope; applies to new terminals/scheduled tasks):

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\v2\reports\set_external_memory_runtime.ps1 -Backend mem0 -Endpoint "https://your-mem0-host/store"
```

Local sovereign backend runtime:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\v2\reports\set_external_memory_runtime.ps1 -Backend mkm_local
```

Mem0 SDK runtime (recommended):

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\v2\reports\configure_mem0_runtime.ps1 -ApiKey "m0-..." -UserId "bitcoin-v2-ops"
```

Connectivity probe:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\v2\reports\test_external_memory_endpoint.ps1 -Backend mem0
```

Disable runtime:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\v2\reports\set_external_memory_runtime.ps1 -Disable
```

External memory spool auto-maintenance:

- Runs automatically inside `run_ops_digest.ps1` (no extra scheduler needed).
- Rotates `memory/v2/external_memory/store_spool.jsonl` when line count exceeds threshold.
- Archives old chunks to `memory/v2/external_memory/archive/*.jsonl.gz`.
- Latest maintenance metrics: `memory/v2/external_memory/spool_rotation_latest.json`.
- Optional env tuning:
  - `EXTERNAL_MEMORY_SPOOL_MAX_LINES` (default: `500`)
  - `EXTERNAL_MEMORY_ARCHIVE_KEEP_DAYS` (default: `7`)

High-signal selective memory (default ON):

- `EXTERNAL_MEMORY_ONLY_HIGH_SIGNAL=true` (default)
- `EXTERNAL_MEMORY_HIGH_SIGNAL_MIN_RISK=80` (default)
- Low-signal loop events are kept locally in spool (`status=skipped_low_signal`) and not sent to external memory.
- Optional dynamic thresholds (UTC):
  - `EXTERNAL_MEMORY_HIGH_SIGNAL_MIN_RISK_DAY` (default fallback from `EXTERNAL_MEMORY_HIGH_SIGNAL_MIN_RISK`)
  - `EXTERNAL_MEMORY_HIGH_SIGNAL_MIN_RISK_NIGHT` (default fallback from `EXTERNAL_MEMORY_HIGH_SIGNAL_MIN_RISK`)
  - `EXTERNAL_MEMORY_NIGHT_START_UTC` (default `0`)
  - `EXTERNAL_MEMORY_NIGHT_END_UTC` (default `7`)

Quick profile preset:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\v2\reports\set_external_memory_signal_profile.ps1 -Profile balanced
```

## Execute Approval (TTL)

```powershell
cd C:\workspace\projects\bitcoin-trading
# one-time (PowerShell):
#   setx EXECUTE_APPROVAL_HMAC_KEY "replace-with-strong-secret"
# new terminal required after setx
powershell -ExecutionPolicy Bypass -File .\ops\v2\tasks\grant_execute_approval.ps1 -Minutes 30 -Reason "manual execute window"
# token is one-time: consumed and deleted after successful execute
powershell -ExecutionPolicy Bypass -File .\ops\v2\tasks\grant_execute_approval.ps1 -Minutes 30 -SingleUse false -Reason "temporary multi-use window"
powershell -ExecutionPolicy Bypass -File .\ops\v2\tasks\revoke_execute_approval.ps1
```

Output:

- `memory/v2/latest_state.json`
- `memory/v2/state_YYYYMMDD.jsonl`
- `memory/v2/ide_capability.json`
- `memory/v2/vault_sync_manifest.json`
- `memory/v2/ledger/decision_ledger_YYYYMMDD.jsonl`
- `memory/v2/incidents/latest_status.json` and `incident_*.md` on alert cases
- `memory/v2/briefs/morning_brief_YYYYMMDD.md`
- `memory/v2/ops/execute_guard.log`
- `memory/v2/ops/execute_approval.json`
- `memory/v2/ops/execute_approval_used_jti.jsonl`
- `memory/v2/briefs/ops_digest_latest.json`
- `memory/v2/briefs/ops_digest_YYYYMMDD.jsonl`
- `memory/v2/external_memory/store_spool.jsonl` (best-effort external sync spool)
- `memory/v2/external_memory/latest_health.json`
