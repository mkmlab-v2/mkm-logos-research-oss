# MKM Design Manifesto v1 — Warm Insight in Cold Data

**Status:** Draft-for-operations (design SSOT pointer)  
**Created:** 2026-05-07  
**Scope:** `jema-ai.com` / `no1kmedi.com` / `mkmlife.com` / `a-codeai.com` / `jemaai.cloud`

---

## 1) Design Identity

MKM UI is not a generic dashboard.  
Our visual language is **Warm Insight in Cold Data**:

- **Calm authority:** clear, quiet, and trustworthy
- **Readable intelligence:** data first, ornament second
- **Human guidance:** users find the next action instinctively
- **Safety visible:** limits and disclaimers are explicit, not hidden

---

## 2) Four Principles

### 2.1 Silent Majesty

- Use restrained surfaces and strong spacing rhythm.
- Prefer dark-neutral canvas with controlled contrast.
- Avoid noisy gradients, excessive badges, and decorative clutter.

### 2.2 Living Organism

- Interfaces may feel alive, but motion must serve comprehension.
- Use subtle pulse/flow only for status or attention, never as distraction.
- Motion defaults to smooth, low-amplitude transitions.

### 2.3 Tactile Credibility

- Layer depth should increase confidence (surface hierarchy), not spectacle.
- Glass-like surfaces are allowed only when text contrast remains high.
- Data cards must remain readable under all states.

### 2.4 Instinctive Path

- One primary action per view must be obvious.
- Accent color is scarce and intentional.
- Decision-critical signals are highlighted; everything else is quiet.

---

## 3) Operational Ranges (v1)

Authoritative values live in `docs/final/artifacts/mkm_design_tokens_v1.json`.

- **Background range:** `#050505` to `#0B1117`
- **Surface alpha range:** `0.08` to `0.22`
- **Accent usage budget:** target <= `10%` of visible UI area per screen
- **Motion easing default:** `cubic-bezier(0.4, 0, 0.2, 1)`

These are ranges, not absolutes. Any exception requires design review note.

---

## 4) Five-Surface Application Contract

- **`jema-ai.com` (hub):** orientation and trust; no feature overload
- **`no1kmedi.com` (clinician console):** authority, focus, workflow speed
- **`mkmlife.com` (consumer):** conversion clarity and safe guidance
- **`a-codeai.com` (B2B API):** technical clarity and quick onboarding
- **`jemaai.cloud` (showroom):** demonstrative insight, non-trading posture

All five surfaces share one token system and one motion language.

---

## 5) Hard Don'ts

- No guaranteed outcome visual rhetoric (profit certainty, deterministic claims).
- No hidden safety/legal boundaries in fine print only.
- No conflicting tone between static mirror and primary app routes.
- No shipping UI that breaks OPSEC/public vocabulary policy.

---

## 6) Governance

- **Design philosophy charter (Decide layer):** `docs/final/MKM_DESIGN_PHILOSOPHY_CONSTITUTION_V1.md`
- **Sasang primitive kernel (machine params):** `docs/final/artifacts/sasang_design_primitive_kernel_v1_latest.json` · gate: `scripts/check_sasang_design_primitive_kernel_v1.py`
- Strategy anchor: `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md`
- Public copy/security anchor: `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`
- Domain-role anchor: `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md`
- Host token source: `docs/final/artifacts/mkm_domain_design_tokens_v1.json`

Violation of this manifesto is treated as a **design review blocker** for public surfaces.
