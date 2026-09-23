# MKM Orchestrator V0

Bounded internal control-plane candidate for coordinating heterogeneous AI coding workers.

This directory is intentionally **not another coding agent**. It sits above Cursor/Codex/Claude/Ollama-style workers and manages:

- authority contracts
- one task -> one isolated Git worktree binding
- worker contracts
- append-only evidence
- freshness classification
- independent validation gates
- derived current-status views

## Core rules implemented

### Worker claim is not evidence

A worker can return `status=PASS`, but the ledger records that result as:

`WORKER_CLAIM_ONLY`

It does not make the task a merge candidate.

### One task -> one deterministic worktree

A task contract binds:

- repository id/path
- exact base revision
- deterministic task branch
- deterministic isolated worktree path

V0 can create worktrees but intentionally has no destructive remove operation.

Workspace creation is denied when:

`mutation_authorized=false`

### Changed-path contract

If a worker reports modified paths outside the task's `allowed_paths`, the orchestrator records:

`POLICY_VIOLATION`

and the gate remains HOLD pending adjudication.

### Evidence freshness

Evidence is classified as:

- `BUILDER_SELF_REPORT`
- `INDEPENDENT_FRESH`
- `PATCH_CONFIRMATION`
- `REPEAT_OBSERVATION`
- `NOT_ESTABLISHED`

A fresh independent FAIL is sealed.

If the subject is patched and the same failed suite is rerun, a PASS is:

`PATCH_CONFIRMATION`

not independent fresh evidence, and it cannot erase the sealed FAIL.

### Candidate is not authorization

Builder PASS + independent fresh validator PASS may produce:

`CANDIDATE / HUMAN_GATE`

but:

- MERGE_AUTHORIZATION=NO
- DEPLOYMENT_AUTHORIZATION=NO
- SEND=HOLD

remain unchanged.

## Append-only ledger

`EventLedger` uses SQLite with:

- hash-chained events
- event-level SHA-256
- SQL triggers blocking UPDATE
- SQL triggers blocking DELETE

Current state is reconstructed from the event log.

## Derived Status Board

`StatusBoard` generates a current view for Commander/Validator/Infrastructure chats.

The status JSON is explicitly:

`derived_view=true`

and identifies:

`authoritative_source=APPEND_ONLY_EVENT_LEDGER`

The generated file is not itself authoritative.

## Validation state

### Initial Orchestrator core

Observed on Windows synthetic Git repos:

`11 passed in 13.12s`

This covered:

- append-only ledger
- hash-chain integrity
- actual Git worktree creation
- duplicate task rejection
- mutation authority gate
- worker claim != evidence
- changed-path policy
- builder PASS insufficient
- independent fresh PASS -> candidate/HUMAN_GATE only
- fresh FAIL sealing
- patch-confirmation classification
- workspace/task mismatch rejection

### Status Board extension — fresh failure retained

After adding the derived Status Board, targeted validation observed:

`12 passed, 1 failed in 15.19s`

Failure:

`test_status_export_does_not_mutate_ledger`

Observed exception:

`KeyError: 'authority'`

The test inserted a minimal `TASK_CREATED` payload directly through the generic ledger API. `StatusBoard` assumed every TASK_CREATED payload contained the full task-contract shape.

Current adjudication:

- failure observed: FACT
- whether generic ledger should permit incomplete TASK_CREATED schema: NOT_ADJUDICATED
- whether StatusBoard should tolerate legacy/incomplete events: NOT_ADJUDICATED
- no automatic patch performed
- no rerun performed after the failure

## Evidence ceiling

`BOUNDED_MKM_ORCHESTRATOR_V0_CANDIDATE_WITH_STATUS_BOARD_FRESH_FAIL`

## Current boundaries

- no merge
- no deploy
- no push
- no destructive worktree cleanup
- no autonomous next-task creation
- no production worker adapter yet
- no claim of cross-model superiority
- no claim of production readiness
