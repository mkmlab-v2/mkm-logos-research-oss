# MKM Living Evidence Ingest V0 — Design

- `PROJECT=MKM_LIVING_EVIDENCE`
- `DOCUMENT=MKM_LIVING_EVIDENCE_INGEST_V0_DESIGN`
- `STATUS=DESIGN_ONLY`
- `AUTHORITY=WORKING_GUIDANCE_ONLY`
- `IMPLEMENTATION_AUTHORIZATION=NO`
- `MERGE_AUTHORIZATION=NO`
- `DEPLOYMENT_AUTHORIZATION=NO`
- `SEND_GATE=HOLD`
- `AUTO_NEXT=false`
- `AUTHORITATIVE_SSOT=C:\workspace + internal Gitea`
- `GITHUB_ROLE=NON_SSOT_WORKING_MIRROR`
- `EVIDENCE_CEILING=BOUNDED_ARCHITECTURE_DESIGN_ONLY`

## 0. Purpose

This document defines a bounded design for an MKM Living Evidence ingest layer.

The intended role is to turn external literature and other evidence sources into source-preserving, auditable, adjudication-ready inputs for MKM evidence workflows without allowing retrieval, extraction, normalization, model confidence, or worker output to silently become fact or authorization.

The first intended vertical is Korean-medicine / clinical literature. The architecture should remain source- and model-agnostic enough to support other domains later.

This document does **not** authorize implementation, source collection, database access, scraping, model calls, benchmark execution, production ingestion, SSOT promotion, or deployment.

---

## 1. Core Thesis

The proposed pipeline is:

```text
EXTERNAL SOURCE
      |
      v
RAW SOURCE PRESERVATION
      |
      v
DETERMINISTIC EXTRACTION
      |
      v
DETERMINISTIC NORMALIZATION
      |
      +---- unmatched / ambiguous ----+
      |                               |
      v                               v
ACCEPTED MAPPING              LLM NORMALIZATION CANDIDATE
                                      |
                                      v
                               ADJUDICATION
                             ACCEPT / REJECT / UNKNOWN
                                      |
                                      v
                                EVIDENCE DELTA
                                      |
                                      v
                               MKM EVIDENCE GRAPH
                                      |
                                      v
                              LIVING REVIEW QUEUE
```

Primary invariant:

> **A newly discovered source may create a review obligation, but it does not automatically rewrite a protected fact, raise an evidence ceiling, or authorize an action.**

---

## 2. Relationship to Existing MKM Components

This design is intended to sit **above / after** the file-native foundation rather than replace it.

Proposed dependency direction:

```text
file-native retrieval
        |
        v
persistent incremental index
        |
        v
source / claim / receipt ontology
        |
        v
receiver-verifiable Context Packet
        |
        v
----------------------------------- foundation boundary
        |
        v
Living Evidence Ingest V0
        |
        v
Evidence Delta / review queue
        |
        v
future Agent Control & Evidence Runtime dogfood
```

Important boundaries:

- retrieval hit `!=` evidence
- extracted field `!=` fact
- normalized term `!=` clinical truth
- LLM candidate `!=` accepted mapping
- confidence `!=` adjudication
- evidence relation candidate `!=` semantic support
- new source `!=` Fact-Lock rewrite
- research PASS `!=` deployment permission

The Living Evidence lane must not require premature collapse of file-native retrieval, ontology, receipts, Context Packet, or future action-gate logic into one monolithic runtime.

---

## 3. External Reference Position

A published pharmacopuncture living-evidence-map workflow using PubMed retrieval, AI-assisted extraction/classification, spreadsheet storage, visualization, and hybrid terminology standardization is a useful external engineering reference.

Reference:

- PubMed: `https://pubmed.ncbi.nlm.nih.gov/40896349/`
- PMC article: `https://pmc.ncbi.nlm.nih.gov/articles/PMC12395373/`

The reference is used here as design inspiration only.

The following are **not inherited claims** for MKM:

- task accuracy
- extraction accuracy
- time savings
- cross-domain generalization
- Korean-medicine-wide effectiveness
- production readiness

Any MKM benchmark must establish its own task-level evidence.

---

## 4. Canonical V0 Objects

V0 starts with five explicit objects.

### 4.1 `RawSourceEnvelope`

Purpose: preserve source identity and acquisition provenance before semantic transformation.

Minimum candidate fields:

```text
schema_version
source_id
source_system
external_id
canonical_url
retrieved_at
retrieval_method
raw_path
raw_sha256
content_type
language
license_or_access_metadata
source_revision_or_version
acquisition_receipt_ref
```

Rules:

1. `raw_sha256` binds to preserved source bytes, not a later normalized representation.
2. `source_system` may identify PubMed, PMC, OASIS, or a future adapter, but the adapter name is not authority.
3. Missing license/access state remains `UNKNOWN` / `NOT_ESTABLISHED`; it must not be guessed.
4. Source collection must respect the source system's actual access and usage terms.

### 4.2 `ExtractionArtifact`

Purpose: represent machine- or rule-extracted fields while retaining pointers back to source evidence.

Minimum candidate fields:

```text
schema_version
artifact_id
source_id
source_sha256
extractor_id
extractor_version
created_at
extracted_fields[]
  field_name
  raw_value
  normalized_value_optional
  source_pointer
  extraction_state
artifact_sha256
```

`source_pointer` should be reconstructable where the source format permits, for example:

```text
path / section / paragraph / character span
or
structured source field identifier
```

Rules:

- extraction output is an artifact, not truth.
- every semantically important extracted field should remain traceable to the source.
- unsupported fields remain absent or `UNKNOWN`; no completion from model priors.

### 4.3 `NormalizationCandidate`

Purpose: separate canonicalization from source extraction and distinguish deterministic mappings from semantic proposals.

Minimum candidate fields:

```text
schema_version
candidate_id
source_id
artifact_id
field_name
raw_value
candidate_canonical_id
candidate_canonical_label
normalization_method
rule_or_dictionary_version
model_id_optional
model_version_optional
confidence_optional
evidence_pointer
adjudication_state
```

Candidate `normalization_method` values:

```text
EXACT_DICTIONARY
APPROVED_ALIAS
DETERMINISTIC_RULE
LLM_SEMANTIC_CANDIDATE
MANUAL_CANDIDATE
```

Candidate `adjudication_state` values:

```text
ACCEPTED
REJECTED
UNKNOWN
NOT_ADJUDICATED
```

Critical invariant:

```text
confidence != adjudication_state
```

A high-confidence LLM output remains a candidate until the applicable policy says otherwise.

### 4.4 `AdjudicationReceipt`

Purpose: make normalization/evidence decisions reconstructable and prevent silent state promotion.

Minimum candidate fields:

```text
schema_version
receipt_id
target_type
target_id
input_hash
decision
validator_or_actor
validator_type
policy_version
decided_at
reason
supporting_refs[]
previous_receipt_optional
```

Candidate decision values:

```text
ACCEPT
REJECT
HOLD
UNKNOWN
```

Rules:

- receipt existence does not itself prove semantic correctness.
- a receipt records who/what decided under which policy and against which immutable input identity.
- changed input hash invalidates direct reuse unless a policy explicitly permits it.

### 4.5 `EvidenceDelta`

Purpose: represent the effect a new source **might** have on an existing protected claim without directly rewriting that claim.

Minimum candidate fields:

```text
schema_version
delta_id
existing_claim_id
new_source_id
new_source_sha256
relation_candidate
support_direction
freshness_state
conflict_state
evidence_ceiling_change_candidate
adjudication_required
created_at
supporting_refs[]
```

Candidate `support_direction` values:

```text
SUPPORTS_CANDIDATE
CONTRADICTS_CANDIDATE
MIXED
IRRELEVANT
UNKNOWN
```

Candidate `freshness_state` values:

```text
NEW_SOURCE
KNOWN_SOURCE_NEW_VERSION
STALE_SOURCE
DUPLICATE_SOURCE
UNKNOWN
```

Candidate `conflict_state` values:

```text
NO_OBSERVED_CONFLICT
POTENTIAL_FACT_LOCK_CONFLICT
DIRECT_CONFLICT_CANDIDATE
UNKNOWN
```

Critical invariant:

```text
EvidenceDelta != Fact-Lock mutation
```

A delta may create `REVIEW_REQUIRED`; it must not autonomously rewrite a sealed claim.

---

## 5. Terminology Normalization Strategy

V0 uses a deterministic-first hybrid strategy.

```text
raw term
   |
   v
exact canonical dictionary
   |
   +-- match --> ACCEPTED deterministic mapping
   |
   v
approved alias dictionary
   |
   +-- match --> ACCEPTED deterministic mapping
   |
   v
bounded deterministic canonicalization rule
   |
   +-- match --> ACCEPTED deterministic mapping
   |
   v
LLM semantic proposal
   |
   v
NormalizationCandidate
   |
   v
adjudication
```

Example problem class:

```text
황련해독탕
黃連解毒湯
Hwangryunhaedok-tang
Hwangryunhaedok decoction
alternative transliterations
```

The system must preserve the original observed term even after an accepted mapping.

Recommended persistence pattern:

```text
raw_value
canonical_id
canonical_label
mapping_method
mapping_version
adjudication_state
receipt_ref
```

Rejected or unresolved mappings remain queryable rather than being discarded.

---

## 6. Source Adapter Boundary

Core ingest logic should not be coupled directly to one literature provider.

Candidate interface:

```text
SourceAdapter
  discover(query_spec) -> SourceLocator[]
  fetch(locator) -> RawSourceEnvelope candidate
  refresh(locator, prior_identity) -> freshness result
```

Candidate adapters:

```text
PubMedAdapter
PMCFullTextAdapter
OASISAdapter
future CNKIAdapter
```

Status at V0 design time:

```text
PubMedAdapter implementation = NOT_ESTABLISHED
PMCFullTextAdapter implementation = NOT_ESTABLISHED
OASISAdapter implementation = NOT_ESTABLISHED
CNKIAdapter access/legal/technical feasibility = NOT_ESTABLISHED
```

No adapter is authorized by this document.

---

## 7. File-Native Integration Contract

New external material should enter the MKM evidence system through a source-preserving path.

Desired sequence:

```text
1. acquire raw source
2. persist raw source bytes or bounded canonical source artifact
3. compute source SHA256
4. register approved path / manifest entry
5. build file-native locator records
6. produce ExtractionArtifact
7. produce normalization candidates
8. adjudicate candidates
9. construct ontology pointers / evidence relation candidates
10. produce EvidenceDelta against existing claims where applicable
```

The incremental index fast path remains a performance mechanism only.

`size + mtime_ns` reuse must never be interpreted as proof that externally acquired evidence bytes remain cryptographically identical.

Where integrity matters, the applicable full source verification path must be used.

---

## 8. Fact-Lock Change Protocol

Living Evidence must preserve existing protected state until adjudication.

Proposed state transition:

```text
NEW_SOURCE_FOUND
      |
      v
SOURCE_IDENTITY_VERIFIED?
  |              |
 NO             YES
  |              |
 HOLD            v
         RELATED_TO_EXISTING_CLAIM?
             |             |
            NO            YES
             |             |
         INGEST ONLY       v
                      EvidenceDelta
                           |
                           v
                     CONFLICT CANDIDATE?
                       |          |
                      NO         YES
                       |          |
                 REVIEW QUEUE   FACT_LOCK_REOPEN_CANDIDATE
                                      |
                                      v
                                  HUMAN GATE
```

Forbidden automatic transition:

```text
NEW_SOURCE -> modify sealed claim
```

Even an apparently definitive new systematic review creates evidence for adjudication; it does not by itself authorize a protected-state rewrite.

---

## 9. Freshness Rules

### 9.1 Source freshness

A genuinely newly published/retrieved source may constitute new source evidence.

### 9.2 Pipeline rerun freshness

```text
same source set
-> extraction bug discovered
-> parser patched
-> same source set rerun
```

is **not** a new independent fresh corpus.

The rerun may validate the corrected implementation against the same source set, but it must not be promoted to independent fresh external validation merely because the software changed.

### 9.3 Fresh failure

A fresh semantic failure must be preserved as evidence.

Do not automatically:

- retune thresholds
- edit prompts
- change taxonomy
- selectively drop difficult items
- run a second "fresh" set

without a new authorization gate.

---

## 10. Validation Ladder

V0 should use task-level validation rather than a single aggregate accuracy number.

Candidate matrix:

```text
SOURCE_DISCOVERY
SOURCE_IDENTITY
METADATA_EXTRACTION
STUDY_TYPE_CLASSIFICATION
SAMPLE_SIZE_EXTRACTION
INTERVENTION_EXTRACTION
COMPARATOR_EXTRACTION
OUTCOME_EXTRACTION
ADVERSE_EVENT_EXTRACTION
TERM_NORMALIZATION_DETERMINISTIC
TERM_NORMALIZATION_SEMANTIC
SOURCE_POINTER_RECONSTRUCTION
EVIDENCE_DELTA_CLASSIFICATION
FACT_LOCK_CONFLICT_DETECTION
```

Each task should independently report:

```text
PASS
FAIL
NOT_ESTABLISHED
NOT_ADJUDICATED
```

An aggregate metric must not hide a weak safety- or evidence-critical subtask.

Example allowed conclusion:

```text
RCT classification = PASS on frozen suite
adverse-event extraction = NOT_ESTABLISHED
```

Example prohibited conclusion:

```text
overall 94% -> MKM literature pipeline is 94% accurate
```

---

## 11. Failure Modes to Design Against

V0 architecture must explicitly account for:

1. duplicate DOI/PMID under different URLs
2. corrected or retracted articles
3. same title with different source versions
4. abstract/full-text disagreement
5. extraction without reconstructable source pointer
6. terminology over-merging
7. terminology under-merging
8. transliteration ambiguity
9. LLM confidence treated as authority
10. stale dictionary mapping
11. receipt replay against changed input
12. evidence laundering through ontology edges
13. new source silently modifying a protected claim
14. source adapter returning transformed text without preserving acquisition provenance
15. license/access state being assumed rather than established

---

## 12. First Vertical: Korean-Medicine Literature

Candidate source order after implementation authorization:

```text
Phase A: PubMed metadata / abstract
Phase B: PMC legally accessible full text
Phase C: OASIS source adapter feasibility
Phase D: additional sources only after explicit access review
```

Candidate normalization domains:

```text
intervention name
herbal formula name
herb name
acupuncture / pharmacopuncture terminology
condition / diagnosis
Korean-medicine pattern term
outcome measure
adverse event term
```

No claim is made that one normalization policy will work across all domains.

---

## 13. LLM Boundary

The LLM is a replaceable semantic worker, not the pipeline authority.

```text
LLM != pipeline
LLM != validator by default
LLM != authority
LLM output = candidate unless explicitly governed otherwise
```

Model/provider identity should be recorded for semantically generated artifacts where reproducibility or adjudication requires it.

A future implementation may use Claude, GPT, Gemini, local models, or multiple models without changing the core evidence-state contract.

---

## 14. Dogfood Role for Agent Control & Evidence Runtime

Living Evidence is a candidate real-world dogfood application because it naturally exercises:

```text
source identity
source freshness
context reconstruction
semantic candidate generation
claim/evidence separation
receipt lineage
Fact-Lock conflict handling
authority boundaries
human gates
```

However:

```text
Living Evidence design PASS
!= Agent Control Plane implementation PASS
!= agent safety proof
!= production readiness
```

This dogfood role remains a strategic hypothesis until the underlying contracts are implemented and independently validated.

---

## 15. Phase Gates

### Gate 0 — current prerequisite

Current file-native foundation work must reach its separately authorized validation/integration gates.

This design must not be used to bypass unfinished file-native validation.

### Gate 1 — schema design review

Required before implementation authorization:

- five-object schema review
- explicit identity/hash semantics
- normalization state machine review
- EvidenceDelta semantics review
- access/license metadata policy

### Gate 2 — bounded deterministic prototype

Candidate future scope only:

- local fixtures
- no live source polling
- no production database
- deterministic normalization only
- frozen test suite

### Gate 3 — semantic normalization candidate worker

Candidate future scope only:

- unmatched terms only
- candidate output only
- frozen evaluation set
- explicit task-level error matrix

### Gate 4 — one external source adapter

Candidate future scope only after access review.

### Gate 5 — Living Evidence Watch

Candidate future scope only after EvidenceDelta and Fact-Lock conflict semantics are validated.

No gate is authorized by this document.

---

## 16. Current State

### FACT

- MKM already has a file-native retrieval / provenance development lane in progress.
- MKM uses explicit Fact-Lock and evidence-ceiling boundaries as project policy.
- GitHub is a non-SSOT working mirror for this project.
- This document is a new design artifact only.

### SUPPORTED

- deterministic-first terminology normalization plus adjudicated semantic candidates is architecturally compatible with MKM evidence boundaries.
- a source-preserving Living Evidence pipeline is a plausible dogfood workload for provenance, Context Packet, ontology, receipts, and future evidence-control mechanisms.

### NOT_ESTABLISHED

- implementation correctness
- extraction effectiveness
- normalization effectiveness
- OASIS automated-access feasibility
- CNKI access/usage feasibility
- full-text extraction accuracy
- clinical evidence synthesis correctness
- cross-domain generalization
- production readiness
- deployment authorization

### HOLD

- implementation
- live source collection
- model/API integration
- benchmark execution
- internal Gitea promotion
- main merge
- deployment

---

## 17. Proposed Next After Foundation Gate

When the file-native foundation has passed its separately authorized gates, the recommended next Commander decision is:

```text
MISSION=MKM_LIVING_EVIDENCE_INGEST_V0_SCHEMA_REVIEW
```

Bounded review targets:

1. `RawSourceEnvelope`
2. `ExtractionArtifact`
3. `NormalizationCandidate`
4. `AdjudicationReceipt`
5. `EvidenceDelta`

That review should decide whether a deterministic fixture-only prototype is authorized.

Until then:

```text
IMPLEMENTATION_AUTHORIZATION=NO
AUTO_NEXT=false
STOP
```
