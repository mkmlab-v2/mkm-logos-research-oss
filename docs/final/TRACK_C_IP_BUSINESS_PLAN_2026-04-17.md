# Track C IP Business Plan (v1)

Date: 2026-04-17  
Owner: MKM core team  
Scope: Separate `Track C (IP licensing and insight products)` from `Track B (direct trading)` while reusing the same governed engine outputs.

## 1) Current Fact-Locked Starting Point

- Governance status: `docs/final/artifacts/integrated_governance_v1_latest.json` shows `final_regime=ATTACK`, `is_fallback=false`, `final_score=0.693774`.
- Engine readiness snapshot:
  - Biblical: `precommercial_ready=true`, `stability_go=false`, `current_ready_streak=2/3` (`kospi_biblical_single_lane_commercial_gate_v1_latest.json`).
  - Myeongri: `standalone_commercial_ready=true` with low drift (`abs_train_test_acc_gap=0.001801`) (`kospi_myeongri_standalone_commercial_gate_v1_latest.json`).
  - Sasang: `commercial_ready=true` (`kospi_sasang_single_lane_commercial_gate_v1_latest.json`).
- Trading bridge status: Integrated governance already constrains runtime risk caps via `scripts/sync_fact_safe_risk_profile.py` and live trader leverage clamp.

## 2) Track C Product Definition (Non-Advisory by Design)

### Product A: Enterprise Macro Risk Warning Brief

- Buyer: CFO/Treasury/Risk team at import-export and crypto-exposed firms.
- Deliverable: Weekly risk brief + event alert stream.
- Promise: Earlier regime-shift warning and reduced decision latency, not buy/sell advice.
- Contract form: 90-day paid pilot, then annual license expansion.

### Product B: Narrative Quant Intelligence Feed

- Buyer: HNW desks, macro research teams, premium newsletter subscribers.
- Deliverable: Structured narrative reports mapping regime pressure transitions to market risk posture.
- Format: API JSON + human-readable report bundle.

### Product C: Engine Licensing (OEM/API)

- Buyer: Existing astrology/fortune or alternative-research platforms.
- Deliverable: `risk posture` / `regime pressure` features under license.
- Constraint: No direct order signal output; only bounded risk-state semantics.

## 3) Pricing and Packaging (Pilot First)

- Pilot window: 90 days.
- Base package:
  - Weekly brief x4/month
  - Event alert channel (rate-limited)
  - Monthly transparency report (hits/misses/false alarms)
- Commercial options:
  - `Starter`: single desk, weekly only
  - `Pro`: weekly + event alert + monthly review
  - `Enterprise`: multi-desk + API + SLA + audit package

## 4) KPI Contract (What Must Be Measured)

- Lead KPI:
  - Qualified leads per month
  - Pilot conversion rate
  - Pilot to annual conversion rate
- Product KPI:
  - Warning lead time against agreed event list
  - On-time delivery rate
  - Alert miss rate and false alarm rate (both disclosed)
- Trust KPI:
  - Artifact-backed reproducibility (path + hash + run log)
  - Monthly full transparency scorecard published to customer

## 5) Legal and Brand Guardrails (Hard Requirements)

- No investment-advisory wording or implied guarantee.
- No direct buy/sell execution suggestions in Track C outputs.
- Public-facing materials must use "risk warning / scenario posture" language only.
- Keep A/B/C boundaries explicit:
  - Track A/B runtime output is operational.
  - Track C is insight/licensing productization with legal wrappers.

### Public Compliance Copy (required literal lines)

- risk warning
- Not investment advice; final decisions remain with client operators.

## 6) 30-60-90 Execution Plan

### Day 0-30: Offer Readiness

- Finalize one-page deck and pilot proposal template.
- Build `Track C evidence pack` from existing artifacts (governance + gates + reliability logs).
- Launch B2B landing page with lead capture (no trading claim copy).

### Day 31-60: Pilot Acquisition

- Secure 3-5 design-partner calls.
- Close first 1-2 paid pilots with fixed KPI appendix.
- Start monthly transparency report cadence.

### Day 61-90: Conversion and Expansion

- Run pilot outcome review with benchmark deltas.
- Propose annual plan and desk expansion.
- Package API licensing option for OEM channel.

## 7) Immediate Next Actions

1. Keep Biblical streak policy-based closeout (`24h spacing`, target `3/3`) in parallel.
2. Publish Track C landing copy with legal-safe value framing.
3. Add Track C section to P0 tracker as a first-class lane with explicit gates.

