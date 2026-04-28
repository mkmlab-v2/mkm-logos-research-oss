# B2B Package — HFT Desk v1

## 1) Audience

- Securities HFT desk
- Market data platform engineering
- Low-latency infra owners

## 2) Core Message (Fact-Safe)

Use conditional hybrid routing to reduce repetitive prompt/transport load in eligible lanes, while preserving deterministic fallback when risk signals appear.

## 3) Business KPI Lens

- Primary:
  - infra cost per replay/day
  - routing stability (guard/fallback correctness)
  - decision distribution (`GO/WATCH/HOLD`)
- Secondary:
  - candidate-ok rate
  - unresolved token trend

## 4) HFT-specific Success Criteria

- No production interruption from pointer trials
- Guard drill pass recorded during PoC
- Measured conditional efficiency uplift on agreed repetitive feed lane
- Auto-downgrade traceability retained in artifacts

## 5) Deliverables for HFT Meetings

- One-pager:
  - `docs/final/B2B_PITCH_COPYDECK_HFT_V1.md`
- SLA draft:
  - `docs/final/B2B_POINTER_ROUTER_SLA_DRAFT_V1.md`
- PoC contract skeleton:
  - `docs/final/B2B_POC_CONTRACT_SKELETON_V1.md`
- 4-week execution:
  - `docs/final/B2B_POC_4W_EXECUTION_CHECKLIST_V1.md`
- Evidence appendix:
  - `docs/final/B2B_POINTER_ROUTER_FACT_APPENDIX_V1.md`

## 6) Negotiation Guardrails

- Avoid absolute claims (`always 99%`, `zero latency`)
- Use condition-bound statements with artifact references
- Keep rollback rights explicit in contract language

## 7) Commercial Ask

- Approve 4-6 week PoC
- Lock success criteria and reporting cadence
- Assign technical and business owner for weekly gate review

