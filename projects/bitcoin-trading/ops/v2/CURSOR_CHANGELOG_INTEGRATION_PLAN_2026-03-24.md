# Cursor Changelog Integration Plan (2026-03-24)

## Objective
Apply recent Cursor capabilities to the current `ops/v2` stack in a way that improves reliability, automation coverage, and team operability.

Current stack anchors:
- `ops/v2/graph/runner.py`
- `ops/v2/tasks/*.ps1`
- `memory/v2/*` observability artifacts

## Feature-to-Stack Mapping

### 1) Automations (highest priority)
Use Cursor Automations for event/schedule-based orchestration around the existing guarded runtime.

Recommended use:
- Trigger maintenance/reporting loops (safe, idempotent)
- Trigger drift checks and summaries
- Keep execute gating in local guard scripts (`run_execute_cycle_guarded.ps1`)

Do not move to Automations:
- Final execute safety gate
- Token signature verification/HITL approval checks

Reason:
- Local guard has deterministic files/policies and immediate STOP behavior.
- Automations should orchestrate, not replace hard safety boundaries.

### 2) Marketplace plugin expansion
Adopt external integrations as output/notification channels, not as safety-critical control plane.

Practical mapping:
- Atlassian/GitLab: ticket/incident sync from `memory/v2/incidents/*`
- Datadog: metrics/log forwarding from `memory/v2/ops/execute_guard.log`, KPI snapshots

### 3) Composer 2
Use for high-complexity coding tasks only:
- multi-file refactor in `ops/v2/graph`, `connectors`, `reports`
- policy evolution with strong type/state consistency checks

Do not overuse on simple script wiring.

### 4) JetBrains ACP support
Operational note:
- Keep repo-level runbooks and task scripts as canonical interface
- JetBrains users can invoke same PowerShell/Python entrypoints

### 5) MCP Apps + team marketplace
Use for shared team utilities and governed tool reuse.
- Promote approved MCP utility patterns into team-distributed app templates
- Keep secret-bearing operations local and policy-gated

## First 3 Automations to Build (Actionable)

### Automation A: Morning Brief + Drift Digest
- Frequency: every 30 minutes (or hourly)
- Command chain:
  1. `powershell -ExecutionPolicy Bypass -File .\\ops\\v2\\reports\\run_ops_digest.ps1`
- Output check:
  - `memory/v2/briefs/latest.md`
  - `memory/v2/briefs/ops_digest_latest.json`
  - `policy_drift.recommended_actions` populated

### Automation B: Guarded Execute Supervisor
- Frequency: every 15 minutes
- Command:
  - `powershell -ExecutionPolicy Bypass -File .\\ops\\v2\\tasks\\run_execute_cycle_guarded.ps1`
- Expected behavior:
  - No valid approval token -> skip execute
  - Signed + valid + in-window token -> execute allowed
  - one-time token consumed automatically when `single_use=true`

### Automation C: Incident to Ops Channel
- Trigger: new `memory/v2/incidents/incident_*.md`
- Action:
  - Publish summary to team system (Jira/GitLab/Datadog event)
- Minimum payload:
  - run_id, severity, reasons, sentinel message, risk score

## Governance Rules (must keep)
- Execute requires local guarded gate and policy validation.
- HMAC key (`EXECUTE_APPROVAL_HMAC_KEY`) stays local secret.
- Approval token use is auditable via:
  - `memory/v2/ops/execute_guard.log`
  - `memory/v2/ops/execute_approval_used_jti.jsonl`

## Fast Start Checklist
1. Register existing local tasks:
   - `register_cycle_task.ps1`
   - `register_shadow_cycle_task.ps1`
   - `register_execute_guarded_task.ps1`
   - `register_morning_brief_task.ps1`
2. Enable Cursor Automations for A/B/C wrappers (or equivalent scheduler events).
3. Keep `risk_policy.yaml` and `risk_scoring_policy.yaml` as SSOT.
4. Verify Morning Brief includes:
   - risk score/mode
   - approval token section
   - last consumed approval metadata

## Done Definition
- Automation A/B/C are scheduled and produce expected artifacts/logs for 24h without manual recovery.
- No execute run occurs without valid signed approval token when policy requires HITL.
- Incident artifacts are externally visible in chosen team channel.
