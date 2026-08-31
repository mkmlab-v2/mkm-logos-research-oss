# DPT-R Situated Protocol v0.1 — REVISED SPECIFICATION

**Mission:** `COMMANDER_DPT_R_SITUATED_PROTOCOL_V0_1_SPEC_REVISION_ACK`  
**Prior:** `DPT_R_SITUATED_PROTOCOL_V0_1_DESIGN.md` (unchanged on disk)  
**Red-team input:** `DPT_R_SITUATED_PROTOCOL_V0_1_RED_TEAM.json`  
**Status:** `[HYPO]` · `DESIGN_ONLY` · `B_TRACK_RESEARCH_ONLY` · `NON_GATING`  
**send_gate:** `HOLD`  
**PROTOCOL_EXECUTION:** `NOT_AUTHORIZED`

This revision **narrows** the v0.1 design to address bounded red-team gaps only. It does **not** add BESD theory, implementation, or empirical claims.

**Core rule (R7):**

```
Conflict ≠ DPT-R
```

Not every friction event requires DPT-R intervention.

**Compile skeleton (unchanged):**

```
Situation → Risk → Capture Frame → Telos → Available Agency → Protocol
```

**Forbidden:** “Matthew 5 says do action X.”  
**Required:** Context → constraints → feasible set → normative filters → bounded action class (or explicit non-DPT conclusion).

---

## Locked inputs (no new kernel)

1. Imposed-role detection / role refusal  
2. Dignity invariance  
3. Telos / Truth / Context constrained control  
4. Non-mimetic action  

Action vocabulary (unchanged; `EMERGENCY_RESPONSE` = design alias for immediate safety dispatch: call emergency services / equivalent lawful emergency path — **not** a new operator):

`ABSTAIN` · `DEFER` · `SEEK_INFORMATION` · `SEEK_COUNSEL` · `EXIT` · `SEEK_HELP` · `REPORT` · `PROTECT` · `LEGAL_REMEDY` · `EMERGENCY_RESPONSE` · `DEFEND_WHEN_JUSTIFIED` · `COOPERATE` · `WITHDRAW` · `SILENCE` · `NEGOTIATE` · `NONCOOPERATE` · `EXPOSE_COERCION`

**Walls:** youth physical violence role-play product; FOMO/Agency market; clinical/counseling claims; loader/operator/codebook/BESD core/CEM C2 mutation.

---

## D01_INPUT_STATE_SCHEMA

Record `I_t` as **qualitative state**. No numeric score.

| Field | Meaning | Fail-closed if |
| --- | --- | --- |
| `C_t` | Situation / setting / time-pattern | materially incomplete |
| `observed_coercive_frame` | Hypothesis: what interaction the other party is trying to make *be* | unknown **and** action treats guessed frame as FACT |
| `R_imposed_candidate` | Hypothesis only until D02 support | treated as FACT without support |
| `truth_evidence_state` | known / alleged / reconstructed | material unresolved where action depends on it |
| `uncertainty` | `U(Truth, Context)` material or not | material → D03 / D10 |
| `safety_state` | immediate harm, escape, weapons, surround, medical | cannot be assessed |
| `third_party_risk` | children, bystanders, dependents | not assessable where foreseeable |
| `retaliation_risk` | **(R3)** credible risk if agent reports/exits/exposes | not assessable where reporting/exposure is contemplated |
| `latent_coercion_signals` | **(R2)** economic, reputational, institutional, relational dependency, pattern, information asymmetry | used as coercion FACT without contextual evidence |
| `available_lawful_actions` | actions agent can take without inventing legal strategy | legally material **and** lawful options unknown |
| `telos_candidate` | safety, dignity, scene end, accountability, option-value | telos overrides known evidence |

`R_imposed` **must not** be inferred from pain, illness, aging, or environmental constraint alone (spec §5.1.3).

**Presence of asymmetry alone ≠ coercion** (R2).

---

## D02_IMPOSED_ROLE_DETECTION_RULE

### D02-A — Not coercion (R1)

The following are **not** sufficient for `R_imposed`:

| Label | Meaning |
| --- | --- |
| `PRESSURE` | deadline, urgency, social expectation |
| `DISAGREEMENT` | ordinary dispute, criticism, debate |
| `ACCOUNTABILITY` | lawful demand to answer, apologize, perform duty, repay |
| `LAWFUL_AUTHORITY` | legitimate instruction within lawful remit |

Hierarchy, criticism, or discomfort **≠** coercion by default.

### D02-B — Coercive mechanism evidence (R1, R2)

Candidate `R_imposed` requires **contextual evidence** of at least one relevant mechanism (no numeric threshold):

- meaningful threat (explicit or credibly implied)  
- constrained choice under **exploited** asymmetry (not asymmetry alone)  
- retaliation risk if agent refuses/submits differently  
- dependency exploitation (economic, visa, housing, care, employment, institutional)  
- compelled identity/role internalization (subordinate, retaliator, silent debtor, conscript, …)  
- material penalty linked to submission  
- reputational threat used as leverage  
- repeated pattern increasing capture probability  
- information asymmetry used to foreclose agency  

**Inspect explicitly (R2):** economic dependency · reputational threat · employment/institutional leverage · relational dependency · repeated pattern · retaliation probability · information asymmetry · vulnerable-person dependency.

### D02-C — Decision

**Ask:** “What role is this situation trying to assign me?”

**Detect `R_imposed` only if:** social/agentive assignment **and** D02-B mechanism evidence **and** not adequately explained by D02-A alone.

If classification **materially uncertain** → `ABSTAIN` / `SEEK_INFORMATION` / `SEEK_COUNSEL` (not DPT-R theater).

If support **absent** → see D10 non-DPT outputs (`NO_COERCIVE_ROLE_ESTABLISHED`, etc.); route D04 if safety still requires protection without full role model.

---

## D03_TRUTH_UNCERTAINTY_GATE

If Truth or Context is **materially uncertain**:

```
a ∈ {ABSTAIN, DEFER, SEEK_INFORMATION, SEEK_COUNSEL}
```

Telos and moral/religious certainty **must not** override unresolved evidence.  
Historical reconstruction **must not** be treated as FACT to justify a unique punitive action class.

---

## D04_SAFETY_THIRD_PARTY_GATE

### D04-A — SAFETY_GATE precedence (R3)

**Order:**

```
SAFETY_GATE  precedes  EXPOSE_COERCION / symbolic resistance / role-play aesthetics
```

If **credible** immediate safety risk, vulnerable third-party risk, or escalation risk **dominates**:

**First-output candidates (non-exhaustive):**  
`EXIT` · `WITHDRAW` · `SEEK_HELP` · `REPORT` · `PROTECT` · `LEGAL_REMEDY` · `EMERGENCY_RESPONSE` · `DEFEND_WHEN_JUSTIFIED`

`EXPOSE_COERCION` is **never mandatory**.  
Boundary phrase or visible resistance **must not** delay the above when safety gate fires.

Dignity is preserved under **withdrawal and protection** (not endurance in danger).

### D04-B — Condition table

| Condition | Effect on `A_feasible` |
| --- | --- |
| Immediate danger / cannot leave / weapons / group surround | D04-A first outputs **outrank** EXPOSE/negotiate/witty third way |
| Credible retaliation risk if REPORT/EXIT | D04-A + `SEEK_COUNSEL`; **unsafe public exposure not default** |
| Repeated coercion with physical contact | record + ally + `REPORT` admissible; boundary-only **insufficient** as sole class |
| Foreseeable third-party harm | `PROTECT` / `REPORT` outrank agent symbolic performance |
| Youth physical violence | official protection **before** coaching/role-play (wall) |
| Latent coercion (R2) without immediate physical danger | D02-B + pattern; escalation paths admissible without forcing EXPOSE |

Surface resemblance to opponent force allowed if independently justified (spec §5.2 N3).

---

## D05_FEASIBLE_ACTION_SET

```
a_(t+1) ∈ A_feasible(Truth, Context, Safety, Law, ThirdPartyHarm, Uncertainty)
```

No universal preferred action. `T_DPT` must not force stereotyped creative resistance.

Inclusion/exclusion with reason (D09). Heroic third way not required. D11 may leave only `ABSTAIN`.

---

## D06_ROLE_REFUSAL_CHECK

**Applies only if** D02 establishes supported `R_imposed` (not FACT without support).

- Refuse worth-collapse internalization.  
- Refuse compulsory entry into aggressor’s **closed script**.  
- Role refusal ≠ stay, lecture, win, or refuse **legitimate responsibility** (R6).

`WITHDRAW` / `EXIT` satisfy role refusal.  
Role refusal concerns **illegitimate imposed identity/control**, not lawful accountability.

---

## D07_DIGNITY_INVARIANCE_CHECK

`Dignity(t) = constant` — normative metaphor, not health score.

### D07-A — Pass

Selected class does not encode “I am worth less because I was harmed.”  
`REPORT` / `SEEK_HELP` / `EXIT` are **not** dignity failures.

### D07-B — Dignity ≠ entitlement firewall (R6)

`DIGNITY_INVARIANCE` does **NOT** imply:

- freedom from accountability  
- immunity from criticism  
- exemption from lawful authority  
- entitlement to preferred outcome  
- moral superiority  
- permission for revenge/escalation  

Dignity belongs equally to **agent, opponent, third parties**.

**Fail:** endurance of ongoing assault as dignity; dignity used to block lawful accountability; revenge/ego telos dressed as dignity.

---

## D08_NON_MIMETIC_CONTROL_CHECK

### D08-A — Wrong test (rejected, R4)

Non-mimetic is **not:** “Is this action superficially different from the opponent’s action?”

### D08-B — Independent justification test (R4)

```
NON_MIMETIC_CONTROL =
  action has independent justification
  outside simple opponent mirroring
```

**Counterfactual probe:**

> Would this action still be justifiable from Truth / Context / Safety / Dignity / ThirdPartyHarm **if the opponent had behaved differently**?

- Same outward action **may** be non-mimetic if independently justified.  
- Different outward action **may** still be opponent-controlled if chosen only to mirror/react.

**Fail:** revenge, humiliation-return, “prove strength,” or organizing telos = retaliate because opponent acted.

**Not claimed:** empirical validation of this criterion.

Default surface constraint remains useful as **heuristic only**:

```
a_(t+1) ≠ Mirror(opponent_action_t)   unless D08-B independently justified
```

---

## D09_ACTION_SELECTION_RECORD

### D09-A — Mandatory fields (R5)

Every **non-abstain** DPT-R-compatible record must document:

1. **imposed_role_assessment** — support / absent / uncertain + D02-B mechanisms cited  
2. **truth_context_basis** — what is known vs hypothesis  
3. **safety_third_party_gate** — SAFETY_GATE fired? retaliation? third party?  
4. **dignity_invariant** — pass / fail + D07-B entitlement check  
5. **non_mimetic_independent_justification** — D08-B counterfactual answer  
6. **feasible_set_membership** — why selected action remains in `A_feasible`

### D09-B — DPT-specific contribution (R5)

If items **1, 4, and 5** would make **no difference** to the chosen action vs GENERIC_SAFE_DECISION_POLICY:

```
DPT_SPECIFIC_CONTRIBUTION = NOT_DEMONSTRATED
```

Do **not** force a DPT-R label. Prefer D10 non-DPT outputs.

### D09-C — Record shape

```text
v0_1_revised_selection_record:
  protocol_path: DPT_R | NON_DPT | GENERIC_SAFETY_ONLY
  dpt_specific_contribution: DEMONSTRATED | NOT_DEMONSTRATED | NOT_APPLICABLE
  imposed_role_assessment: { status, mechanisms[], uncertainty }
  truth_context_basis: { known[], alleged[], unresolved[] }
  safety_third_party_gate: { safety_gate_fired, retaliation_risk, third_party_risk }
  dignity_invariant: pass|fail
  dignity_entitlement_check: pass|fail
  non_mimetic_independent_justification: pass|fail|not_applicable
  included: [{ action_class, reason }]
  excluded: [{ action_class, reason }]
  claim_tag: HYPO
```

Safety-fast-path may skip D06 role-refusal theater but **must** still complete D09-A fields 3–6 when any action is recommended.

---

## D10_ABSTAIN_DEFER_AND_NON_DPT_OUTPUTS

### D10-A — Uncertainty / fail-closed

When D03 or D11 fires: `ABSTAIN` · `DEFER` · `SEEK_INFORMATION` · `SEEK_COUNSEL` — **success classes**.

### D10-B — Non-DPT formal outputs (R7)

Permitted **terminal conclusions** (not protocol failure):

| Output | When |
| --- | --- |
| `NO_COERCIVE_ROLE_ESTABLISHED` | D02-A explains situation; D02-B support absent |
| `NO_DPT_R_INTERVENTION_INDICATED` | No coercive capture; generic conflict handling suffices |
| `ABSTAIN_INSUFFICIENT_INFORMATION` | Material uncertainty; no safe unique action |
| `GENERIC_SAFETY_RESPONSE_ONLY` | Safety dominates; DPT-R identity adds nothing (record D09-B) |

**Conflict ≠ DPT-R.** Simple instruction, criticism, or lawful accountability may correctly end here.

### D10-C — Chosen abstention

`ABSTAIN` admissible when telos is to end participation without speech act.

---

## D11_FAIL_CLOSED_CONDITIONS

STOP / ABSTAIN / D10 outputs if:

- truth materially unresolved  
- context materially incomplete  
- immediate safety cannot be assessed  
- third-party harm not assessable where relevant  
- retaliation risk not assessable where REPORT/EXPOSE contemplated  
- lawful options unknown where legally material (**not** a legal-advice engine)  
- `R_imposed` used as FACT without D02 support  
- action requires historical reconstruction as FACT  
- D02 classification materially uncertain and action would pretend certainty  

No numeric threshold invented.

---

## D12_CLAIM_CEILING

**PASS of bounded spec revision establishes only:** specification narrowed to address red-team findings.

**Does not establish:** executable protocol; empirical validity; behavioral efficacy; real-world safety; legal adequacy; clinical/coaching usefulness; novelty; theological consensus; product readiness; compile consistency; D08 criterion empirically validated.

---

## Compile falsifier — EXAMPLE_PROBE_ONLY (R8)

**Label:** `EXAMPLE_PROBE_ONLY` — **not** validation data, empirical evidence, normative gold, or exhaustive use cases. Do not tune spec merely to make probes pass.

Same `I_t` + D02–D11. Different `A_feasible` membership/priority required across probes.

### S1 — Workplace coercion (`EXAMPLE_PROBE_ONLY`)

Imposed frame: “Endure it or quit.” D02-B: constrained choice + institutional leverage.  
**Not** the lawful performance-plan variant (that variant → `NO_COERCIVE_ROLE_ESTABLISHED`).

### S2 — Ongoing harassment, safety-first (`EXAMPLE_PROBE_ONLY`)

Imposed frame: “Fight, submit, or be a snitch.” SAFETY_GATE may fire; EXPOSE not mandatory.

### S3 — Low-risk social pressure (`EXAMPLE_PROBE_ONLY`)

Imposed frame: “Everyone does it.” `COOPERATE` may be best; must not import S2 safety stack.

---

## DECIDE_ONE (this artifact)

`DPT_R_SITUATED_PROTOCOL_V0_1_SPEC_REVISION_PASS`

**STOP_AFTER_RESULT:** `TRUE`  
**Next:** `SPEC_REVISION_REAUDIT` (not implementation).
