# One-Page Proposal — Conditional Hybrid Pointer Router

## What We Deliver

A safety-first routing layer that selects the best path per traffic condition:
- `GO`: pointer-centric route in eligible zones
- `WATCH`: shadow/controlled mode
- `HOLD`: automatic fallback to Track A primary

## Why It Matters

- Reduce transport/inference cost in repetitive structured traffic
- Keep reliability via automatic downgrade and fallback
- Preserve auditability with artifact-backed control plane

## What Makes It Different

- Not a single static compressor
- Not unconditional claim marketing
- Conditioned operation with explicit guardrails and rollback logic

## Proven Control Loop (Current State)

- Decision artifacts -> runtime config -> shadow router -> daily report -> alert -> guard
- Guard drill validated for forced downgrade path
- All claims tied to generated artifacts, not narrative-only benchmarks

## Engagement Model (4-6 Week PoC)

1. Week 1: Workload mapping + success gate lock
2. Week 2: Shadow deployment + baseline collection
3. Week 3: Controlled zone activation + guard drills
4. Week 4+: KPI review + conversion decision

## Commercially Safe Promise

We commit conditional performance in agreed operating zones and automatic safety fallback outside them.

## What We Need From Customer

- Candidate traffic sample (or replay stream)
- Security/network constraints and data policy
- Owner assignment for weekly go/no-go review

## Decision Ask

Approve PoC start with:
- Scope
- Success criteria
- Reporting cadence
- Conversion terms

