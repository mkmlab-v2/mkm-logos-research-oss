# B2B Hybrid Pointer Router PoC Contract Skeleton v1

Status: Draft skeleton for deal execution (not legal advice).

## 1. Parties and Purpose

- Provider: [Company Name]
- Customer: [Customer Name]
- Purpose: Validate conditional cost/latency efficiency and safety fallback in customer environment.

## 2. PoC Scope

- Duration: 4-6 weeks
- Environment: Customer-designated non-production or controlled production shadow
- Workloads:
  - Repetitive/structured traffic lane (candidate for pointer route)
  - Baseline lane (Track A primary fallback)
- Exclusions:
  - Unconditional 99% savings guarantee
  - Universal perfect reconstruction for open-vocabulary traffic

## 3. Technical Model

- Routing policy: `GO/WATCH/HOLD`
- Safety controls:
  - Health alert gate
  - Automatic guard downgrade to `HOLD_POINTER_ROUTE`
  - Runtime fallback to `track_a_primary`
- Sync policy:
  - Daily full sync + hourly delta sync
  - Mismatch -> forced fallback

## 4. Success Criteria (SLA-style PoC gates)

- Must pass all:
  - No service interruption caused by pointer route trials
  - Guard drill evidence pass at least once during PoC
  - Measurable conditional efficiency uplift in agreed candidate lane
  - Alert/guard behavior traceable via artifacts
- Suggested KPI fields:
  - pointer candidate-ok rate
  - unresolved token rate
  - route decision distribution (`GO/WATCH/HOLD`)
  - fallback frequency

## 5. Evidence and Reporting

- Daily artifact bundle delivered:
  - routing decision / guarded decision
  - runtime config
  - shadow daily report
  - alert snapshot
  - control chain result
- Weekly executive summary:
  - cost implication estimate
  - risk events and mitigations
  - go/no-go recommendation

## 6. Commercial Terms (PoC)

- PoC fee: [Fixed Fee / Milestone]
- Infra responsibility: [Provider/Customer split]
- Data handling: customer policy first, no uncontrolled export
- Change control: material scope change requires written approval

## 7. Conversion Terms

- Conversion trigger:
  - PoC success criteria met and approved by both sides
- Production onboarding:
  - staged enablement with guard active by default
- If unmet:
  - extension with narrowed scope, or closeout with final findings

## 8. Risk and Liability Language (Draft)

- Condition-bound performance only
- No guarantee for traffic outside agreed operating zone
- Immediate rollback rights reserved for either party on safety breach

## 9. Sign-off

- Customer technical owner:
- Customer business owner:
- Provider technical owner:
- Provider commercial owner:
- Date:

