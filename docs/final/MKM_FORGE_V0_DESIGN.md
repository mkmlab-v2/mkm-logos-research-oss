# MKM Forge V0 — Design Candidate

- PROJECT=MKM_FORGE
- DOCUMENT=MKM_FORGE_V0_DESIGN
- STATUS=DESIGN_CANDIDATE
- AUTHORITY=WORKING_GUIDANCE_ONLY
- IMPLEMENTATION_AUTHORIZATION=NO
- MERGE_AUTHORIZATION=NO
- DEPLOYMENT_AUTHORIZATION=NO
- SEND_GATE=HOLD
- AUTHORITATIVE_SSOT=C:\\workspace + internal Gitea
- GITHUB_ROLE=NON_SSOT_COLLABORATION_CI_SURFACE
- EVIDENCE_CEILING=BOUNDED_ARCHITECTURE_DESIGN_ONLY
- DATE=2026-09-23

## 0. Purpose

MKM Forge is a candidate local-first development and agent-operations layer that coordinates
task isolation, context/evidence reconstruction, bounded automation, and audit receipts while
using GitHub as a collaboration/CI/event surface rather than as the authoritative project state.

Core thesis:

> GitHub events are signals; verified source + policy + explicit authority determine state.

MKM Forge is not a GitHub replacement. It is a control/evidence layer around local workspaces,
internal Gitea, GitHub, coding agents, and future local desktop-agent tooling.

## 1. V0 Scope

V0 design covers four integration surfaces:

1. GitHub Actions as bounded validator workers.
2. Git worktree isolation for parallel agent tasks.
3. GitHub webhook/API events as state-transition candidates.
4. Evidence-aware pull requests carrying compact source/evidence coordinates and receipts.

Candidate future integrations, explicitly outside V0 implementation authority:

- local Ollama classifier/redactor
- Secret / Identity Broker
- desktop file/shell/browser tools
- remote device pairing
- production action authorization
- clinical/PHI workflows

## 2. Architecture

```text
                     GitHub
             PR / Actions / Reviews
                API / Webhooks
                      |
                 external signals
                      v
+------------------------------------------------+
|                  MKM FORGE                     |
|                                                |
| Task / Worktree Manager                        |
| Thin Coordinate Index                          |
| Context Packet / Source Rehydration            |
| Evidence / Receipt Registry                    |
| Validator Orchestrator                         |
| Policy / State Gate                            |
+-------------------------+----------------------+
                          |
                          v
          C:\workspace + internal Gitea
                AUTHORITATIVE SSOT
```

GitHub must never silently become the authority root.

## 3. Hard Invariants

```text
GitHub Actions green != semantic PASS
PR approved != merge authorization
PR merged != deployment authorization
receipt exists != claim verified
candidate != authorization
HOLD != PASS
worker report != acceptance
retrieval hit != evidence
```

Unknown remains UNKNOWN.

Any GitHub-derived event can create a candidate state or receipt, but cannot autonomously
promote protected SSOT facts or authorization.

## 4. Task / Worktree Contract

Preferred parallel execution primitive:

```text
1 task = 1 task_id + 1 worktree + 1 branch + 1 authority scope
```

Minimum task metadata candidate:

```text
task_id
agent_id
repo_id
base_revision
worktree_path
branch_name
allowed_paths[]
forbidden_paths[]
allowed_capabilities[]
evidence_refs[]
authority_scope
created_at
expires_at_optional
state
```

Candidate task states:

```text
CREATED
READY
RUNNING
VALIDATION_PENDING
REVIEW_PENDING
HOLD
HUMAN_GATE
CLOSED
FAILED
```

No task state itself authorizes SEND, merge, deployment, credential use, or destructive actions.

## 5. Thin Coordinate Layer

V0 candidate coordinate dimensions:

```text
KIND
DOMAIN
TOPIC
STATE
PRIVACY
SOURCE_ID
HASH
RELATIONS
```

Canonical KIND values remain aligned with the existing ontology direction:

```text
SOURCE
CLAIM
RECEIPT
ARTIFACT
```

Candidate PRIVACY values:

```text
PUBLIC
INTERNAL
PERSONAL
PHI
SECRET
```

A thin coordinate is a locator/identity aid, not evidence.

Resolution path:

```text
thin coordinate
 -> locate candidate source
 -> reopen current source
 -> verify hash/revision policy
 -> rehydrate required span
 -> evidence-eligible context
```

A2A wire compatibility is NOT_ESTABLISHED. Coordinates should remain transport-agnostic.

## 6. GitHub Actions Role

GitHub Actions may be used for bounded mechanical checks such as:

- unit tests
- lint/static checks
- schema validation
- manifest verification
- source/hash consistency checks
- secret-pattern scanning
- dependency/security signals
- fixture smoke tests
- receipt generation

Actions may emit a validation receipt.

They may not autonomously establish:

```text
SEMANTIC_PASS
PRODUCT_DONE
SSOT_ACCEPTED
SEND_AUTHORIZED
DEPLOY_AUTHORIZED
SECURITY_SUPERIORITY
```

Candidate result model:

```text
MECHANICAL_PASS
MECHANICAL_FAIL
INCOMPLETE
HUMAN_GATE_REQUIRED
```

## 7. GitHub Event / Webhook Contract

GitHub events are normalized into immutable event receipts.

Candidate examples:

```text
github.pr.opened
github.pr.synchronize
github.pr.review_submitted
github.check.completed
github.pr.closed
github.pr.merged
```

A normalized event may propose a state candidate such as:

```text
CODE_REVIEW_COMPLETED_CANDIDATE
MECHANICAL_VALIDATION_COMPLETED_CANDIDATE
MERGE_OCCURRED_OBSERVED
```

Forbidden direct transitions:

```text
github review approved -> SEMANTIC_PASS
github check green -> SSOT_ACCEPTED
github merge -> DEPLOY_AUTHORIZED
```

## 8. Evidence-Aware Pull Request

Candidate PR-side receipt:

```text
task_id
base_revision
head_revision
changed_paths[]
evidence_refs[]
source_hashes[]
mechanical_checks[]
semantic_state
evidence_ceiling
privacy_state
send_gate
merge_authorization
deployment_authorization
```

Recommended display example:

```text
Task: TASK-2026-0091
Base: abc123
Changed paths: 3
Evidence refs: 2
Source verification: 2/2 VERIFIED
Mechanical tests: 18/18 PASS
Semantic effectiveness: NOT_ADJUDICATED
Evidence ceiling: BOUNDED_IMPLEMENTATION_ONLY
SEND: HOLD
Merge authorization: HUMAN_GATE
```

The receipt is a reconstruction aid and audit artifact, not self-authenticating authority.

## 9. Security Integration Candidate

GitHub security outputs may be ingested as evidence signals:

- dependency alerts
- code scanning findings
- secret scanning findings
- workflow failures

They should remain source-attributed signals with timestamps and current-state verification.

No security feature result should be converted into general claims such as "secure" or
"production-safe" without a separately defined acceptance contract.

## 10. Codespaces Role

Codespaces is a candidate clean-room reproducibility environment only.

Candidate uses:

- OSS contributor onboarding
- reproducible fixture smoke
- CI debugging
- documentation examples

Not the primary runtime for:

- Windows desktop automation
- local Ollama/privacy workflows
- patient/PHI workflows
- OS credential broker
- clinic-specific local filesystem integration

## 11. Integration with Existing MKM Components

Dependency direction candidate:

```text
file-native retrieval
        |
persistent incremental index
        |
Context Packet
        |
Thin Coordinate Index
        |
MKM Forge task/worktree/event receipts
        |
future Evidence-Bound Action Gate
```

Existing component evidence ceilings remain unchanged.

This document does not merge branches, validate interoperability, or promote any component.

## 12. Suggested V0 Implementation Order

Only after separate implementation authorization:

### V0-A — Task / Worktree Manager
- create bounded task metadata
- create worktree + branch
- enforce approved root/path constraints
- close/cleanup with explicit human gate for destructive cleanup

### V0-B — Mechanical Validator Receipt
- run local and/or GitHub mechanical checks
- persist immutable receipt
- preserve exit-code vs semantic-state separation

### V0-C — Evidence-Aware PR Manifest
- generate compact PR receipt
- link thin coordinates to source identities
- never auto-authorize merge/SEND

### V0-D — GitHub Event Adapter
- ingest webhook/API events
- persist event receipts
- output state candidates only

## 13. Non-Goals / Prohibited Overclaims

Not established:

```text
MKM Forge improves developer productivity
MKM Forge reduces tokens/cost in general
MKM Forge is safer than GitHub/Codespaces
MKM Forge is A2A compatible
MKM Forge is production security
MKM Forge replaces Qdrant/vector search
MKM Forge guarantees agent isolation
MKM Forge is ready for clinical/PHI production
```

## 14. Current State

### FACT
- GitHub working mirror already uses an OSS smoke workflow on main.
- Existing working branches contain bounded file-native retrieval, ontology,
  Context Packet, and incremental-index candidates.
- GitHub remains explicitly non-SSOT in current MKM guidance.

### SUPPORTED
- Worktree isolation, bounded validator receipts, GitHub event receipts, and evidence-aware PRs
  are architecturally compatible with the existing MKM evidence/authority model.
- Thin coordinates are compatible with Context Packet style source rehydration.

### NOT_ESTABLISHED
- implementation correctness
- integration correctness across the separate branches
- performance improvement
- token reduction
- A2A interoperability
- security effectiveness
- product-market fit

### HOLD
- implementation
- merge
- SSOT promotion
- deployment
- remote credential use
- destructive action
- clinical/PHI production usage

## 15. Proposed Next Commander Gate

```text
MISSION=MKM_FORGE_V0_A_TASK_WORKTREE_MANAGER
```

Bounded implementation target:

- local-only
- fixture repository first
- no credentials
- no network dependency required
- no destructive cleanup without HUMAN_GATE
- explicit task metadata + worktree + branch + receipt
- frozen tests
- STOP after bounded validation

Until separately authorized:

```text
IMPLEMENTATION_AUTHORIZATION=NO
AUTO_NEXT=false
STOP
```
