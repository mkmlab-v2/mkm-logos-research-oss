# MKM Rebuttal Template (v1)

## Rebuttal Positioning (Use in opening paragraph)

We appreciate the reviewers' concerns and agree that bounded claims, reproducibility, and lane separation are essential. Our revision clarifies that all reported metrics are as-of artifact snapshots, distinguishes A-track operational evidence from B-track exploratory evidence, and strengthens falsification boundary disclosure.

## R1: "Claims appear stronger than evidence."

**Response Template:**  
Thank you. We have narrowed claim scope to tested conditions only and removed absolute wording. We now cite explicit artifact paths for each quantitative statement and include snapshot qualifiers in text and captions. We also added a disallowed-claims block to prevent guarantee-style interpretation.

**Evidence Slots:**  
- Artifact path(s): `<path>`
- Updated section(s): `<section>`

## R2: "Research-only outputs are mixed with operational claims."

**Response Template:**  
We agree this distinction must be explicit. The revised manuscript enforces lane separation: A-track is presented as operational governance evidence, while B-track is presented as exploratory analysis unless promoted via explicit gates. No automatic promotion is assumed or implied.

**Evidence Slots:**  
- Lane-separation section: `<section>`
- Gate evidence path(s): `<path>`

## R3: "Insufficient statistical rigor."

**Response Template:**  
We expanded the evaluation protocol to include baseline comparison, raw OOS readiness checks, bootstrap/permutation significance testing, and falsification suite outcomes with boundary disclosure. We now provide first non-pass thresholds to expose failure conditions.

**Evidence Slots:**  
- Significance artifact: `<path>`
- Falsification artifact(s): `<path>`

## R4: "Potential over-interpretation for financial direction."

**Response Template:**  
We explicitly state that the system is for risk-control governance and observability, not directional investment advice or guaranteed returns. We have inserted this notice in abstract-adjacent text, limitations, and caption policy.

**Evidence Slots:**  
- Compliance section: `<section>`
- Disclosure statement location: `<section>`

## R5: "System architecture claims are ambiguous (e.g., shard/runtime)."

**Response Template:**  
We clarified runtime transparency: current active runtime is documented as 8 shards, while 12AI is presented as roadmap intent. We removed wording that could be interpreted as fully active 12-shard production deployment.

**Evidence Slots:**  
- Runtime clarification section: `<section>`
- Supporting artifact/doc path: `<path>`

## Closing Paragraph Template

In summary, the revised manuscript narrows claims to validated scope, strengthens reproducibility traceability, and separates exploratory and operational evidence by design. We believe these revisions address the reviewers' concerns while preserving the technical contribution: a safety-gated, artifact-anchored framework for risk-control decision support under high-complexity input conditions.

