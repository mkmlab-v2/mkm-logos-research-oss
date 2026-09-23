# MKM Orchestrator / Evidence Gate V0

Bounded internal control-plane and AI Change-Control candidate for heterogeneous coding workers.

This is intentionally **not another coding agent**. Cursor/Codex/Claude/Ollama-style workers may build, but MKM decides what evidence exists, how fresh it is, which source is authoritative, and whether a change may advance.

## Core rules

- Worker claim != evidence
- Builder != independent validator
- implementation PASS != effectiveness
- patched rerun != independent fresh validation
- candidate != authorization
- HOLD != PASS
- missing stays UNKNOWN
- fresh independent FAIL remains sealed
- no claim above the evidence ceiling

## Implemented V0 components

### Task / workspace binding

- explicit `AuthorityContract`
- explicit `TaskContract`
- deterministic `1 task -> 1 Git worktree`
- exact base revision
- mutation authority gate
- changed-path contract
- task/workspace mismatch denial

V0 intentionally has no destructive worktree cleanup operation.

### Append-only event ledger

`EventLedger` uses SQLite with:

- event-level SHA-256
- hash chaining
- SQL UPDATE denial trigger
- SQL DELETE denial trigger

Current state is replayed from events.

### Evidence freshness

Classes:

- `BUILDER_SELF_REPORT`
- `INDEPENDENT_FRESH`
- `PATCH_CONFIRMATION`
- `REPEAT_OBSERVATION`
- `NOT_ESTABLISHED`

A fresh validator FAIL remains a gate FAIL even if the same suite later passes after a patch. That later result is `PATCH_CONFIRMATION`.

### Independent Validator Contract

The validator adapter is separate from execution. It accepts a bounded validator artifact only after checking:

- validator identity differs from last builder identity
- suite digest shape
- current workspace subject digest
- base revision ancestry
- changed files remain within task contract
- return code
- stdout/stderr digests
- duration metadata

The contract derives PASS/FAIL from the return code rather than trusting a worker PASS string.

### Evidence Receipt V0

`EvidenceReceiptBuilder` produces a normalized re-checkable receipt containing:

- task id/objective
- authority
- exact base revision
- workspace binding
- actual observed HEAD
- actual changed files
- diff SHA-256
- current subject digest
- worker claim
- worker backend
- worker-claim vs observed-state consistency
- evidence records and freshness classes
- evidence ceiling
- merge/deploy/SEND authorization
- covered ledger sequence/head hash
- receipt SHA-256

Worker claims and actual workspace observations are separate fields.

### Authority Resolver V0

Source classes:

- `AUTHORITATIVE`
- `WORKING_MIRROR`
- `TASK_WORKTREE`
- `VALIDATION_CLONE`
- `ARCHIVE`
- `BACKUP`
- `CONFLICT`
- `UNKNOWN`

Important fail-closed behavior:

- exact declared repository path may be AUTHORITATIVE or WORKING_MIRROR
- exact bound linked worktree may be TASK_WORKTREE
- linked but unbound worktree -> UNKNOWN
- same remote separate clone without explicit role marker -> UNKNOWN
- conflicting role marker -> CONFLICT
- validation clone requires explicit matching role marker and declared base presence
- GitHub/mirror recency never promotes authority automatically

### Derived Status Board

`StatusBoard` is a derived view only:

- `authoritative_source=APPEND_ONLY_EVENT_LEDGER`
- `derived_view=true`

It cannot change ledger facts.

#### Retained fresh failure

The first Status Board validation observed:

`12 passed, 1 failed in 15.19s`

Failure:

`KeyError: 'authority'`

The generic ledger accepted a minimal TASK_CREATED payload and the Status Board assumed the full task-contract shape.

Adjudication:

- EventLedger remains generic append-only storage
- Orchestrator semantic APIs own semantic event schema correctness
- StatusBoard must tolerate incomplete/legacy events
- missing fields remain `UNKNOWN`

The bounded patch changed missing authority to:

`UNKNOWN / MISSING_TASK_CREATED_AUTHORITY`

The same suite then observed:

`13 passed in 15.47s`

This is recorded as **PATCH_CONFIRMATION**, not independent fresh validation. The original fresh FAIL remains retained.

## New fresh validation

### Evidence Receipt + Authority Resolver

Fresh dedicated suite:

`11 passed in 30.51s`

Validated:

- exact authority classification
- working mirror preservation
- exact task worktree classification
- unbound linked worktree -> UNKNOWN
- same-remote separate clone -> UNKNOWN
- explicit validation-clone marker
- conflicting marker -> CONFLICT
- receipt re-observes actual workspace
- receipt detects worker-claim drift
- candidate still has merge/deploy NO and SEND HOLD
- receipt issuance covers the previous ledger head and appends metadata only

### Independent Validator + Dogfood Measurement

Fresh dedicated suite:

`9 passed in 19.37s`

Validated:

- builder/validator identity collision rejection
- subject drift rejection
- scope violation rejection
- validator PASS -> INDEPENDENT_FRESH
- nonzero validator return code -> fresh FAIL
- repeat validation -> REPEAT_OBSERVATION
- negative measurement rejection
- <50 tasks -> effectiveness NOT_ESTABLISHED
- balanced 50 tasks -> READY_FOR_HUMAN_EFFECTIVENESS_ADJUDICATION only

Even at 50 measured tasks, the system does **not** automatically claim effectiveness, willingness-to-pay, PMF, or superiority.

## Dogfood Measurement V0

Per-task fields include:

- wrong repo/worktree incidents
- duplicate worker work
- scope violations caught
- false PASS caught
- fresh FAIL caught
- review minutes
- human interventions
- rollback count
- task -> validated candidate time
- worker cost
- builder PASS -> validator FAIL
- UNKNOWN -> human resolution
- human-gate rejection
- evidence reconstruction time

Cohorts:

- `BASELINE`
- `EVIDENCE_GATE`

Readiness requires at least 50 measurements and at least 25 per cohort before human effectiveness adjudication.

## Integration smoke

A synthetic Git repo was run end-to-end:

task -> deterministic worktree -> synthetic builder change -> actual pytest -> validator artifact -> gate -> Evidence Receipt -> Status Board -> Authority Resolver.

Observed after harness correction:

- pytest return code: 0
- validator outcome: PASS
- validator freshness: INDEPENDENT_FRESH
- gate state: CANDIDATE
- gate decision: HUMAN_GATE
- merge authorization: NO
- deployment authorization: NO
- SEND: HOLD
- worker claim consistency: MATCH
- declared source: AUTHORITATIVE
- bound worktree: TASK_WORKTREE
- ledger hash chain: valid
- changed file: app.py

The first integration invocation failed before product logic because PowerShell->Python input retained U+FEFF. This is retained as `HARNESS_FAIL`; rerun after BOM stripping is harness-correction confirmation, not independent fresh evidence.

## Evidence ceiling

`BOUNDED_MKM_EVIDENCE_GATE_V0_CANDIDATE_STATUS_BOARD_PATCH_CONFIRMED_NOT_INDEPENDENT_FRESH`

## Current boundaries

- MERGE_AUTHORIZATION=NO
- DEPLOYMENT_AUTHORIZATION=NO
- SEND=HOLD
- no push
- no deploy
- no destructive worktree cleanup
- no autonomous next-task production progression
- no general cross-model superiority claim
- no external willingness-to-pay claim
- PMF NOT_ESTABLISHED
- production readiness NOT_ESTABLISHED


## V0.1 Dogfood Runner + Shared CURRENT_STATUS

### Dogfood Runner

`DogfoodRunner` now provides a bounded internal lifecycle:

```text
task contract
  -> deterministic worktree
  -> external worker/evidence activity
  -> latest-evidence gate recomputation
  -> dogfood measurement
  -> Evidence Receipt
  -> DOGFOOD_TASK_FINALIZED
  -> sealed shared CURRENT_STATUS publication
```

The worker execution itself remains outside this Evidence lane.

Important closure rule:

`finalize()` **always recomputes the gate from the latest append-only evidence**.

It does not trust a previously cached CANDIDATE. Therefore a fresh FAIL arriving after an earlier candidate evaluation cannot be hidden by that older gate.

Possible runner next actions are bounded to:

- `HOLD`
- `HUMAN_GATE`
- `HUMAN_ADJUDICATION_REQUIRED`

The runner does not create an automatic next task.

Global boundaries remain:

- automatic next task = NO
- merge = NO
- deploy = NO
- SEND = HOLD

### Shared CURRENT_STATUS contract

`SharedStatusPublisher` publishes two atomic files:

- `CURRENT_STATUS.json`
- `CURRENT_STATUS.sha256.json`

The JSON is explicitly a derived view. The append-only ledger remains authoritative.

Verification states:

- `CURRENT` — status SHA and current ledger head both match
- `STALE` — status SHA is valid but the ledger has advanced
- `INVALID` — tampering/unreadable status/ledger-chain problem
- `NOT_ESTABLISHED` — status or seal missing

A stale snapshot is not silently treated as current and is not treated as a tamper event.

The shared view includes:

- Status Board
- dogfood measurement summary
- latest receipt metadata per task
- finalized-task state
- global authorization boundaries

### CLI read surface

The V0 CLI now exposes:

```text
shared-publish
shared-verify
dogfood-summary
```

This gives separate Commander / Validator / Infrastructure chats or local processes a common read surface without treating chat memory as SSOT.

## V0.1 validation

### Dedicated Evidence Gate CI — final current head

GitHub Actions workflow:

`MKM Evidence Gate V0`

Environment:

- Ubuntu 24.04
- Python 3.11
- package compile step: PASS

Final current-head test command covered:

- `test_mkm_evidence_gate_v0.py`
- `test_mkm_validator_measurement_v0.py`
- `test_mkm_dogfood_shared_status_v0.py`
- `test_mkm_shared_status_cli_v0.py`

Observed:

`34 passed in 3.43s`

Workflow job conclusion:

`success`

This is fresh CI evidence for the Evidence Gate / Dogfood / shared-status surface on Ubuntu.

### Earlier dedicated CI run

An earlier run observed:

`30 passed`

but workflow inspection showed the CLI test file had not actually been included in the pytest command. That result is retained but is **not** used as CLI validation evidence.

### Windows validation state for V0.1 additions

The authorized Windows PC was offline when V0.1 fresh validation was attempted.

Therefore:

`DOGFOOD_SHARED_STATUS_WINDOWS_FRESH_VALIDATION = NOT_ESTABLISHED`

Earlier Evidence Gate components retain their prior Windows evidence, but it is not expanded to claim Windows validation of the new Dogfood Runner/SharedStatus surface.

### Legacy MKM Orchestrator Smoke

The existing `MKM Orchestrator Smoke` workflow remains FAIL before its test step.

Observed bundle-path verifier missing:

- `docs/final/artifacts/todo_queue_example_v1.json`
- `docs/final/artifacts/todo_queue_smoke_first_v1.json`
- `docs/final/artifacts/todo_queue_smoke_first_python_v1.json`
- `docs/final/artifacts/mkm_orchestrator_connection_spec_v1.json`

Its `Orchestrator tests` step is skipped.

These artifacts belong to an older/broader bundle contract and were **not fabricated or patched** by this Evidence lane merely to make CI green.

So current CI evidence is deliberately separated:

- dedicated Evidence Gate CI = PASS
- legacy Orchestrator bundle verifier = FAIL / blocker retained

## V0.1 evidence ceiling

`BOUNDED_MKM_EVIDENCE_GATE_V0_1_CI_FRESH_PASS_WINDOWS_DOGFOOD_NOT_ESTABLISHED`

This does not establish:

- Windows reliability of V0.1 Dogfood/SharedStatus
- 50-task effectiveness
- general superiority
- external willingness-to-pay
- PMF
- production readiness
- merge/deploy authorization
