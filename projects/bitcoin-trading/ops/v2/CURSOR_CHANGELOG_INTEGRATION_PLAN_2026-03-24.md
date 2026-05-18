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

---

## 3.3 Integration (2026-05-07) — PR · Plan · Context

**Product source:** Cursor Changelog 3.3 (PR review UI, parallel plan build, split-to-PR, skill quick actions, context usage breakdown).

| Changelog feature | MKM use | Do not |
| --- | --- | --- |
| **PR review (Reviews/Commits/Changes)** | Human review before merge to `gitea/main`; link to `scripts/push-internal.ps1` hygiene | Treat Bugbot/PR comments as CONSTITUTION implementation proof |
| **Parallel plan build** | Independent ops/report tasks in separate chats or Cloud agents; same-file edits stay **serial** per `AGENTS.md` 병렬 작전 | Parallel-edit `CONSTITUTION_*` or live `start_live_trading.py` without branch split |
| **Split changes to PRs** | Align with `1작업=1브랜치=1PR`; use when chat scope mixed research + ops | Auto-split across Track A live config without human gate |
| **Pin skills to quick actions** | Team pins: Fact-Lock bundle persona, VIP pipeline skill, NotebookLM refresh skill | Pin skills that trigger live trade or secret export |
| **Context usage breakdown** | Trim `alwaysApply` rules; audit MCP count per `notebooklm-mcp-session-bridge.mdc` | Assume high context % = bad model — fix rules/MCP first |

### 3.3 Fast checklist
- [ ] Large PRs use in-IDE review tabs before `push-internal.ps1`
- [ ] Multi-file plans use parallel build only for **non-overlapping paths**
- [ ] Context panel reviewed after adding MCP or `alwaysApply` rules
- [ ] Split PR plan approved before pushing mixed B-track + ops commits

---

## 3.4 Integration (2026-05-13) — Cloud Agent dev environment

**Product source:** Cursor Changelog 3.4 (agent dev environments, multi-repo, Dockerfile IaC, build secrets, governance, Teams, Bugbot inference).

| Changelog feature | MKM use | Do not |
| --- | --- | --- |
| **Multi-repo environment** | One Cloud env clones monorepo root; add paths only per `AGENTS.md` domain handoff | Put separate clones with divergent `.env` for “same” strategy |
| **Dockerfile / environment IaC** | Dashboard + optional `.cursor/environment/README.md`; `pip install` + `verify_p0_constitution_gate_paths.ps1` smoke | Commit secrets or production `.env` into Dockerfile |
| **Build secrets** | Private package feeds at image build only | Expect build secrets in agent runtime for trading APIs |
| **Env version / rollback / audit** | Team admin policy; document env id in PR description when Cloud agent ran tests | Roll back env without noting Fact-Lock artifact timestamps |
| **Egress + per-env secrets** | Research/B-track Cloud jobs; zero trading keys | Share one env secret across prod + research |
| **Teams @Cursor** | Optional: incident thread → Cloud agent → PR link in `memory/v2/incidents/*` flow | Teams bot triggers live execute without `run_execute_cycle_guarded.ps1` |
| **Bugbot inference (default/high/custom)** | Dashboard cost/quality tradeoff for GitHub PRs | Bugbot pass replaces `run_fact_lock_bundle.ps1` |

**Boundary SSOT:** `.cursor/rules/cursor-cloud-sandbox-boundary.mdc` (repo-wide `alwaysApply`).

### 3.4 Fast checklist
- [ ] Cloud environment defined in Cursor Dashboard (clone + install + smoke command)
- [ ] `verify_p0_constitution_gate_paths.ps1` exit 0 in Cloud env after bootstrap
- [ ] No `BINANCE_*` / live `ATHENA_ECC_*` / VPS SSH keys in Cloud env secrets
- [ ] Multi-repo list matches actual task (usually **single monorepo root** only)
- [ ] Teams/Bugbot toggles documented in team runbook if enabled (not in CONSTITUTION body)

### 3.4 Suggested Cloud smoke command (monorepo root)

**Committed IaC:** `.cursor/environment.json` runs on every Cloud VM boot:

```bash
bash .cursor/environment/install.sh
# or
python3 scripts/verify_p0_constitution_gate_paths_cloud_v1.py
```

**Windows local (same path list, PS1):**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_p0_constitution_gate_paths.ps1
```

Optional wider smoke (local Windows only): `scripts/Invoke-MkmPersonaHealth_v1.ps1 -Persona P0` or `-Persona AthenaBundle`.
