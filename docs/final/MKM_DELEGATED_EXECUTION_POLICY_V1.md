# MKM Delegated Execution Policy v1

**Status:** `ACTIVE_LOCAL` · operational policy (not a competing constitution)  
**Commander ACK:** `MKM_DELEGATED_EXECUTION_GOVERNANCE_V1_ACK`  
**Machine companion:** `docs/final/artifacts/mkm_delegated_execution_policy_v1_latest.json`  
**Parent epistemic pin (do not duplicate):** `docs/final/MKM_LAB_GOVERNANCE_SSOT_PIN_V1.md`  
**Cursor rule:** `.cursor/rules/mkm-delegated-execution-policy-v1.mdc`  
**research_only:** true · **send_gate / LIVE / DEPLOY / TRADE:** HOLD  

## Purpose

Formalize **where Cursor/Codex may auto-chain** vs **where Commander must approve**, without replacing the Lab Governance SSOT pin’s evidence hierarchy, freshness lock, or Builder≠Validator rules.

Success ceiling of this policy file:

- **PASS =** GREEN/YELLOW/RED + STOP_ON + AUTO_NEXT-within-scope are written and wired.
- **PASS ≠** fully autonomous lab · semantic validation complete · production/LIVE authorized.

## Evidence priority (inherits Lab pin)

`CURRENT LOCAL DISK / INTERNAL GITEA` > sealed artifacts/receipts > CENTRAL > GitHub mirror > chat > inference.

`C:\workspace` is a **protected dirty evidence root**. GitHub is mirror only — never invent missing local governance from GitHub.

## GREEN — PREAUTHORIZED (auto-chain inside authorized mission/scope)

- authoritative-state restoration, source/file inspection, forensic (read-only)
- architecture/design, preregistration, implementation planning
- bounded implementation in isolated worktree
- development / synthetic / non-heldout negative tests
- independent validation of **implementation/infrastructure** (not effectiveness promotion)
- receipts, seals, lineage, Fact-Lock hygiene, docs, CENTRAL handoff maintenance
- GitHub mirror **preparation** (not unauthorized public push)
- read-only external research; non-destructive repo inspection

Allowed chain example:

`forensic → design → bounded Builder → dev tests → independent implementation validator → receipt/seal → STOP or next GREEN step in SAME scope`

`AUTO_NEXT` is allowed **only inside this preauthorized chain**. `AUTO_NEXT_BEYOND_GATE=false`.

## YELLOW — COMMANDER GATE (prepare OK; execute STOP)

STOP before executing:

- first real semantic/fresh evaluation; heldout reveal/use; real H2H semantic execution
- large model-call evaluation that becomes evidence; new evaluation generation / domain expansion
- second fresh validation; result-dependent repair+rerun; threshold/case/prompt/comparator change after seeing results
- reclassification that raises epistemic ceiling; G2→G3 / G3→G4 (or analogous)
- production-readiness promotion; claim elevation

## RED — EXPLICIT COMMANDER ONLY

Never auto-execute: `LIVE` · `SEND` · `DEPLOY` · `TRADE` · `PAYMENT` · public release · production mutation · medical/clinical send · banking · destructive ops.

Also blocked without explicit authorization:

- `git reset --hard` / `git clean -fd(x)` on protected evidence root
- destructive rebase/reset; mass checkout over protected dirty state
- deleting sealed artifacts; overwriting historical first result; mutating frozen validation contracts
- replacing FAIL with later PASS; suppressing contradictory evidence

## Mandatory STOP_ON

Immediately STOP and preserve evidence when any is true:

`FIRST_SEMANTIC_OR_FRESH_FAIL` · `FACT_LOCK_CONFLICT` · `HELDOUT_ACCESS_REQUIRED` · `AUTHORITATIVE_SOURCE_MISSING` · `SCOPE_VIOLATION` · `FROZEN_ARTIFACT_MUTATION_REQUIRED` · `EXTERNAL_DEPENDENCY_BLOCKS_VALIDATION` · `DESTRUCTIVE_OPERATION_REQUIRED`

**Forbidden automatic loop:** patch → rerun → call it fresh PASS. A first failure remains a first failure.

## Epistemic rules (pointer; full text in Lab pin)

worker claim ≠ evidence · builder PASS ≠ independent validation · exit 0 ≠ semantic success · implementation PASS ≠ effectiveness · semantic PASS ≠ product DONE · candidate ≠ authorization · HOLD ≠ PASS.

`missing → UNKNOWN` · `unverified → NOT_ESTABLISHED` · `effectiveness unjudged → NOT_ADJUDICATED`. No claim above evidence ceiling.

## Builder / Validator

Where practical: Builder → receipt → independent Validator → seal. Builder must not validate its own effectiveness claim. Builder may run synthetic/dev tests labeled **development evidence** only.

## Freshness

`result → inspect → patch → rerun` does **not** create a new independent fresh result. Historical first result is immutable; later corrected runs need separate generation/lineage + distinct receipt.

## Relation to Ask Gate / existing rules

| Surface | Role |
|---------|------|
| `.cursorrules` Ask Gate | Hard RED subset (destructive / live trade / paid / irreversible) |
| `MKM_LAB_GOVERNANCE_SSOT_PIN_V1.md` | Epistemic constitution pin |
| This policy | Operational GREEN/YELLOW/RED + AUTO_NEXT fence |
| `@mkm-high-delegation-preflight-v1` | M/L host preflight before AUTO |
| `@mkm-task-contract-stop-v1` | Phase STOP / no silent repair |

### Conflict log (this mission)

| OLD_RULE | CONFLICT | RESOLUTION |
|----------|----------|------------|
| Ask Gate “execute without asking except 4 cases” | Broader than RED; under-specifies YELLOW semantic gates | Keep Ask Gate as hard floor; this policy adds YELLOW semantic/fresh gates above it |
| Completion Contract “same failure twice → change strategy” | Could be read as auto repair-rerun | Does **not** authorize treating patch-rerun as fresh evidence; Commander required for result-dependent repair |
| Codex `AUTO_NEXT=false` absolute | Conflicts with GREEN chain efficiency | Amended to `AUTO_NEXT=WITHIN_PREAUTHORIZED_GREEN_ENVELOPE`; beyond-gate false |
| Habitual per-step `AUTO_NEXT=false` / `STOP_FOR_COMMANDER_AFTER_*` in live ops templates | Forces Commander interrupt after every GREEN subtask | Active templates default to GREEN envelope continuation; historical receipts unchanged |
| Sovereign Ignition 10-step / count-based autonomy | **NOT_PRESENT** in current `.cursorrules` slim v2 | No delete; N/A |

## Operational default (activation)

- `AUTO_NEXT=WITHIN_PREAUTHORIZED_GREEN_ENVELOPE`
- `AUTO_NEXT_BEYOND_GATE=false`
- Machine: `docs/final/artifacts/mkm_delegated_execution_policy_v1_latest.json` `DEFAULT`
- Activation receipt: `docs/final/artifacts/mkm_green_envelope_autonomous_continuation_activation_v1_latest.json`

## Revision

| date_utc | change | ack |
|----------|--------|-----|
| 2026-09-07T19:20:00Z | v1.0.0 operational policy formalized | MKM_DELEGATED_EXECUTION_GOVERNANCE_V1_ACK |
| 2026-09-08T01:00:00Z | v1.1.1 GREEN envelope AUTO_NEXT operationalized as default | MKM_GREEN_ENVELOPE_AUTONOMOUS_CONTINUATION_ACTIVATION_V1 |
