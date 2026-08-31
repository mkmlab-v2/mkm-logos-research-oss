# BESD DPT-R Safety Counterexample Register v0.1

**Mission:** `COMMANDER_BESD_DPT_R_RED_TEAM_V1`  
**Rule:** DPT-R must **NOT require** the unsafe action. Permit protective/legal/exit paths.  
**Claim ceiling:** conceptual compatibility only — not empirical safety validation.  
**SEND_GATE:** HOLD

---

## S1 — Immediate escape is best

| Field | Content |
|-------|---------|
| Scenario | Domestic / street assault escalating; leaving scene minimizes harm |
| Unsafe if DPT-R required | Stay to perform cheek-turn / legitimacy theatre |
| Conceptual model | `Context.safety = ESCAPE_DOMINATES` → action class `EXIT` admissible under T_DPT; Dignity Invariance preserved by refusal of subordinate *interpretation*, not by remaining in kill-zone |
| Fixture pin | Cheek fixture: `safety_constraint: exit_if_escalating_physical_danger`; forbids `unsafe_passivity_required` |
| Stub gap | Operator steps do not enumerate EXIT as first-class step |
| Verdict | **COMPATIBLE** — EXIT allowed; not required to stay |

---

## S2 — Physical defense is justified

| Field | Content |
|-------|---------|
| Scenario | Imminent bodily harm; lawful proportionate self-defense available |
| Unsafe if DPT-R required | Forbid all force; demand non-mirror aesthetics over survival |
| Conceptual model | Mimetic Break forbids **mirror retaliation as imposed script**, not independently justified PROTECT. `π(…, Context)` may select `PHYSICAL_SELF_PROTECTION_WHEN_JUSTIFIED` |
| Firewall | Protective force ≠ revenge TFT; ≠ theology-to-biology claim |
| Stub gap | Stub always selects domain non-mirror class; under-implements Context branch |
| Verdict | **COMPATIBLE** conceptually; stub **implementation LEAK** (protective path not selected) — not FAIL of architecture if ceiling stays conceptual |

---

## S3 — Police / legal / institutional intervention required

| Field | Content |
|-------|---------|
| Scenario | Ongoing coercion where REPORT / restraining order / HR / church discipline is necessary |
| Unsafe if DPT-R required | Private “dignified” silence blocking LEGAL_REMEDY |
| Conceptual model | Coercion Exposure may route to **institutional** exposure; Cost Return without retaliation includes lawful accountability |
| Verdict | **COMPATIBLE** — LEGAL_REMEDY / REPORT admissible |

---

## S4 — Public resistance makes the victim more unsafe

| Field | Content |
|-------|---------|
| Scenario | Public shaming of abuser triggers escalation; quiet exit safer |
| Unsafe if DPT-R required | Mandatory public Coercion Exposure |
| Conceptual model | Step “Expose_Coercion” is **conditional** (fixture results: `Expose_Coercion_Conditional`). When exposure raises victim harm, select EXIT / silence / deferred documentation |
| Verdict | **COMPATIBLE** — exposure not mandatory |

---

## S5 — Third-party protection outranks self nonviolence

| Field | Content |
|-------|---------|
| Scenario | Child / dependent under attack; bystander can intervene with force or alarm |
| Unsafe if DPT-R required | Prioritize agent’s non-mimetic self-image over third-party PROTECT |
| Conceptual model | Priority rule: `third_party_imminent_harm → PROTECT/REPORT outranks self non-mirror aesthetics`. Dignity of victim-other is not traded for agent’s NV performance |
| Stub gap | No explicit third-party harm constraint in operator steps |
| Verdict | **COMPATIBLE** with required **documentation priority rule** (GAP, not anti-safety axiom) |

---

## Aggregate safety judgment

| Metric | Status |
|--------|--------|
| Architecture forces unsafe stay/nonviolence | **FALSE** |
| Architecture forbids EXIT/PROTECT/LEGAL | **FALSE** (conceptually) |
| Stub enumerates all safety paths | **TRUE (documented)** — see `BESD_DPT_R_STUB_SAFETY_PATH_ENUMERATION_RECEIPT_V1.json`; runtime selection **not** wired |
| Triggers `BESD_DPT_R_RED_TEAM_FAIL_UNSAFE_OR_COLLAPSE` | **NO** |

**Register decide:** safety counterexamples **pass conceptual firewall**; stub path enumeration **documented** (`EXIT`/`REPORT`/`LEGAL_REMEDY`/`PROTECT`/`ABSTAIN`); residual = stub runtime `A_feasible` wire or BWH downstream (not novelty/efficacy).
