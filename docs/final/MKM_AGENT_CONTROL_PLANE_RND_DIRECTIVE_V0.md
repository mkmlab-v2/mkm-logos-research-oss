# MKM Agent Control Plane R&D Directive V0

- `PROJECT=MKM_AGENT_CONTROL_PLANE`
- `DOCUMENT=MKM_AGENT_CONTROL_PLANE_RND_DIRECTIVE_V0`
- `STATUS=STRATEGIC_RND_DIRECTIVE`
- `AUTHORITY=GUIDANCE_ONLY`
- `IMPLEMENTATION_AUTHORIZATION=NO`
- `MERGE_AUTHORIZATION=NO`
- `DEPLOYMENT_AUTHORIZATION=NO`
- `PRODUCT_CLAIM_AUTHORIZATION=NO`
- `SEND_GATE=HOLD`
- `AUTHORITATIVE_SSOT=C:\workspace + internal Gitea`
- `GITHUB_ROLE=NON_SSOT_WORKING_MIRROR`

## 0. Purpose

This document defines a bounded R&D direction for MKM agent reliability and control work.

It does **not** establish that MKM can control AGI, solve alignment, prevent model escape, provide production security, or outperform existing retrieval/security systems.

The purpose is to keep multiple MKM development lanes aligned around one testable technical thesis:

> **No context becomes evidence without source verification, and no agent action becomes authorized merely because a model requested it.**

The near-term target is not model alignment. It is a defense-in-depth runtime layer around agents that can verify context, bind evidence to current sources, enforce authority boundaries, gate actions, and preserve reconstructable receipts.

---

## 1. North Star

Working product/R&D framing:

**MKM Agent Control & Evidence Runtime**

Enterprise-facing shorthand candidate:

**MKM Agent Control Plane**

Current technical substrate:

**MKM Verifiable Agent Context Fabric**

The intended architecture is an external control layer around agents rather than a claim about modifying the model's internal goals or cognition.

```text
MODEL / AGENT
      |
      v
intent / requested action
      |
      v
+----------------------------------+
| MKM AGENT CONTROL PLANE          |
|                                  |
| 1. Context Integrity             |
| 2. Evidence Provenance           |
| 3. Authority Runtime             |
| 4. Action Gate                   |
| 5. Freshness / Revocation        |
| 6. Receipt / Audit               |
+----------------------------------+
      |
      v
AUTHORIZED | HOLD | DENIED | HUMAN_GATE
      |
      v
tool / filesystem / shell / network / API
```

---

## 2. Core Invariants

### 2.1 Locator is not evidence

```text
retrieval hit
  != evidence
```

Required path:

```text
locator
  -> rehydrate current source
  -> verify source hash / revision policy
  -> evidence-eligible context
```

A retrieval score, embedding similarity, sparse match, symbol match, graph edge, or worker statement is never sufficient by itself to establish truth or authority.

### 2.2 Candidate is not authorization

```text
candidate != authorization
receipt != semantic PASS
research PASS != deployment permission
HOLD != PASS
```

An agent request to perform an action never authorizes that action by itself.

### 2.3 Verification must be receiver-side

A packet may carry expected source identity and hashes.

It must not be able to grant itself verification by declaring fields such as `source_verified=true`.

Verification state is computed only after the receiving side reopens the actual source and checks it.

### 2.4 Freshness is explicit

A previously valid source, receipt, locator, or authorization may become stale.

Stale or mismatched source state must not silently remain evidence-eligible.

### 2.5 Unknown remains unknown

Missing or unverified information is not converted into PASS, FALSE, NEGATIVE, DEFAULT, or authorization.

Use bounded epistemic states such as:

```text
FACT
SUPPORTED
INFERENCE
PLAUSIBLE
HYPOTHESIS
UNKNOWN
NOT_ESTABLISHED
NOT_ADJUDICATED
FAIL
```

### 2.6 Builder reports are not acceptance

Builder-side tests and worker reports are evidence inputs, not authoritative product acceptance.

Preferred sequence:

```text
builder
  -> artifact / commit / receipt
  -> independent or bounded external validation
  -> Commander adjudication
  -> optional SSOT acceptance
```

---

## 3. Current MKM Technical Assets

The following are **component directions / bounded implementation candidates**, not a claim that the full Agent Control Plane is implemented.

### 3.1 File-native retrieval

Intended role:

- exact path / filename / symbol locators
- sparse local retrieval
- literal relation expansion
- source SHA256 freshness verification
- `LOCATOR_ONLY` behavior before source verification

### 3.2 Persistent incremental index

Intended role:

- local persistent manifest
- changed/new/removed source updates
- fast reuse path for stat-unchanged sources
- explicit full-rescan integrity path
- atomic manifest persistence

Important boundary:

`size + mtime_ns` reuse is a performance cache, **not cryptographic proof** that source bytes are unchanged.

### 3.3 Context Packet V1

Intended minimum packet:

```text
schema_version
packet_id
repo_id
revision
sources[]
  path
  expected_sha256
  optional symbol
  optional line_start
  optional line_end
verification_policy=VERIFY_BEFORE_EVIDENCE
```

Receiver flow:

```text
packet
  -> reopen source
  -> hash current bytes
  -> compare expected hash
  -> return verified full source/span only on success
```

### 3.4 Source / Claim / Receipt ontology

Intended role:

- SOURCE as default indexed entity
- CLAIM / RECEIPT / ARTIFACT only through explicit declaration
- typed edges
- explicit evidence pointers for semantic edges
- no filename/content inference of authority or truth

### 3.5 Claim Atom Bus / Verifier Ladder

Intended role:

- keep claims separate from receipts and evidence
- append-only lineage
- prevent receipts from silently promoting epistemic state
- track verifier ceilings independently from builder claims
- preserve lower-level failure ceilings

These components may later be connected through pointers. They should not be prematurely collapsed into one runtime until their contracts are stable.

---

## 4. Product Architecture Candidate

The strategic product direction is a six-part control plane.

### 4.1 Context Integrity

Questions:

- Is this the intended source?
- Does the current source still match the expected hash?
- Is the source inside the approved root?
- Can the exact source/span be deterministically reconstructed?

### 4.2 Evidence Provenance

Questions:

- Where did this claim come from?
- Which source/artifact/receipt supports it?
- Is the cited evidence current?
- Is the relationship explicit or inferred?

### 4.3 Authority Runtime

Questions:

- What capability has been granted?
- To which task, target, repository, resource, or time window?
- Has that authority expired or been revoked?

### 4.4 Action Gate

Future bounded primitive candidate:

**Evidence-Bound Action Authorization**

Candidate request envelope:

```text
agent_id
task_id
action_type
target
evidence_refs[]
source_hashes[]
authority_scope
requested_capability
expiry
```

Candidate result enum:

```text
AUTHORIZED
HOLD
DENIED
HUMAN_GATE
```

No action-gate implementation is authorized merely by this document.

### 4.5 Freshness / Revocation

The runtime should be able to reject:

- stale source coordinates
- mismatched hashes
- expired authority
- revoked permissions
- superseded evidence

### 4.6 Receipt / Audit

Every gated action should eventually have a reconstructable record of:

- requested action
- relevant evidence pointers
- source verification result
- policy/authority decision
- final gate result
- resulting action receipt where applicable

This is a future runtime target, not a current production claim.

---

## 5. R&D Execution Order

The order below is strategic guidance. Each phase still requires a separate implementation/validation gate.

### Phase A — Verifiable Context Fabric

```text
file-native retrieval
  + persistent incremental index
  + Context Packet
  + source rehydration/hash verification
```

Goal:

```text
small packet
  -> exact source/span
  -> current hash verification
  -> bounded evidence-eligible context
```

### Phase B — Roo / Coding-Agent Dogfood

Expose the verified context layer to a real coding agent through a narrow tool/MCP bridge.

Candidate minimal tools:

```text
mkm_index_refresh
mkm_context_search
mkm_rehydrate_verify
mkm_index_status
```

The first objective is dogfood and measurement, not replacing all semantic retrieval.

### Phase C — Evidence-Bound Action Gate V0

Only after Context Fabric is sufficiently stable:

```text
agent action request
  -> evidence/freshness/authority checks
  -> AUTHORIZED | HOLD | DENIED | HUMAN_GATE
  -> receipt
```

### Phase D — Frozen Synthetic Action Benchmark

Candidate integrity-critical cases:

- permitted read
- stale source use
- write outside approved root
- unapproved network target
- git push without SEND authorization
- protected artifact deletion
- expired authority
- valid evidence-bound action

Candidate primary metrics:

```text
UNAUTHORIZED_ACTION_ACCEPTANCE
STALE_EVIDENCE_ACCEPTANCE
AUTHORIZED_ACTION_SUCCESS
AUDIT_RECONSTRUCTION_RATE
```

Control-plane overhead is descriptive until a separate superiority benchmark is designed.

### Phase E — Real Agent Validation

Only after bounded synthetic closure:

- coding-agent same-task trials
- external checkout / rehydration trials
- controlled enterprise-agent scenarios
- independent replication where feasible

---

## 6. Retrieval Strategy

MKM should not define itself as a Qdrant replacement.

Preferred layered retrieval direction:

```text
L0 exact/path/hash
  -> L1 sparse/token
  -> L2 structural/relation
  -> verified rehydration
  -> optional L3 semantic fallback on miss
```

Embedding/vector retrieval may remain an optional fallback or plug-in.

Current non-claims:

```text
MKM faster than Qdrant = NOT_ESTABLISHED
MKM semantic recall superiority = NOT_ESTABLISHED
MKM task-success superiority = NOT_ESTABLISHED
```

---

## 7. Multi-Agent Handoff Direction

Long-term candidate:

```text
Agent A
  -> compact source pointer packet
Agent B
  -> rehydrate actual current source
  -> verify hash / revision policy
  -> use verified context
```

The objective is to reduce blind trust amplification across agents.

A2A protocol compatibility is **not established** by this direction.

Do not claim compatibility with any external A2A standard without a dedicated wire-contract validation.

---

## 8. Benchmark Discipline

Benchmark results must not exceed their evidence ceiling.

### Context rehydration

Primary integrity metrics may include:

```text
DETERMINISTIC_REHYDRATION_RATE
STALE_WRONG_SOURCE_ACCEPTANCE_VIOLATIONS
HASH_MISMATCH_DETECTION_RATE
MISSING_SOURCE_DETECTION_RATE
PATH_ESCAPE_REJECTION_RATE
```

Descriptive only until separately adjudicated:

```text
PACKET_BYTES
FULL_SOURCE_BYTES
REHYDRATED_BYTES
CONTEXT_TOKENS
LATENCY
```

A small packet or lower byte count alone does not establish agent superiority or product value.

### Action-gate benchmark

Any unauthorized or stale-evidence action accepted as authorized is an integrity failure.

Fresh first-run failures must be preserved. Do not patch, tune, and rerun the same frozen evidence as if it were an independent fresh validation.

---

## 9. Current Strategic Status

```text
MKM_AGENT_CONTROL_PLANE_RND_DIRECTION
= ADOPTED_AS_STRATEGIC_GUIDANCE_CANDIDATE

MKM_VERIFIABLE_AGENT_CONTEXT_FABRIC
= CURRENT_PREREQUISITE_RND_LANE

EVIDENCE_BOUND_ACTION_GATE
= NEXT_MAJOR_RND_CANDIDATE_AFTER_CONTEXT_FABRIC

AGENT_CONTROL_EFFECTIVENESS
= NOT_ESTABLISHED

PRODUCT_MARKET_FIT
= NOT_ESTABLISHED

SECURITY_SUPERIORITY
= NOT_ESTABLISHED
```

Known working-mirror component candidates at the time of this directive include separate ontology hardening, Context Packet, and persistent incremental-index branches/PRs. Their individual implementation/validation ceilings remain governed by their own receipts and Commander adjudication; this directive does not merge or promote them.

---

## 10. Prohibited Overclaims

The following claims are not authorized by this document:

```text
MKM controls AGI
MKM solves alignment
MKM prevents AI escape
MKM guarantees safe autonomous agents
MKM is production security
MKM is A2A compatible
MKM is superior to Qdrant
MKM reduces tokens/cost in general
MKM improves agent task success in general
MKM has established product-market fit
```

Current states:

```text
AGI_CONTROL=NOT_ESTABLISHED
ALIGNMENT_SOLUTION=NOT_CLAIMED
PREVENTS_AI_ESCAPE=NOT_ESTABLISHED
A2A_COMPATIBILITY=NOT_ESTABLISHED
SECURITY_SUPERIORITY=NOT_ESTABLISHED
PRODUCT_MARKET_FIT=NOT_ESTABLISHED
```

---

## 11. Governance Boundary

This document is a strategic R&D directive only.

It does not authorize:

- merge
- deployment
- production wiring
- SEND
- destructive actions
- network escalation
- credential access
- trading
- live promotion
- benchmark retuning
- reopening frozen facts without new authoritative evidence

GitHub is a non-SSOT working mirror.

Promotion of this directive into authoritative project policy requires explicit acceptance into:

```text
C:\workspace + internal Gitea
```

Until that occurs:

```text
GITHUB_DIRECTIVE_STATUS=WORKING_STRATEGIC_GUIDANCE
AUTHORITATIVE_SSOT_PROMOTION=NOT_ESTABLISHED
```

---

## 12. Commander Decision Rule

Before adding a new feature, ask:

1. Does it strengthen source/context verification?
2. Does it strengthen provenance or evidence boundaries?
3. Does it strengthen explicit authority/action gating?
4. Does it improve reconstructable auditability?
5. Can it be tested under a bounded frozen contract?

If the answer is no to all five, it is probably outside the current Agent Control Plane R&D priority.

The immediate prerequisite remains:

```text
CONTEXT FABRIC CORRECTNESS FIRST
ACTION CONTROL SECOND
PRODUCT CLAIMS LAST
```
