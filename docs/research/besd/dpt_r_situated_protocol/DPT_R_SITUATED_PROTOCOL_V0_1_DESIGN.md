# DPT-R Situated Protocol v0.1 — DESIGN ONLY

**Mission:** `COMMANDER_DPT_R_SITUATED_PROTOCOL_V0_1_DESIGN_ACK`  
**Status:** `[HYPO]` · `B_TRACK_RESEARCH_ONLY` · `NON_GATING`  
**send_gate:** `HOLD`  
**DESIGN_ONLY:** `TRUE`  
**PROTOCOL_EXECUTION:** `NOT_AUTHORIZED`

This document **does not add theory**. It compiles already-locked DPT-R v2 constraints (`BESD_V0_2_SPEC_DRAFT.md` §5.2, §6, §6.1) into a **situated decision structure**: which action classes are first admissible, which are excluded, and under which fail-closed conditions the protocol must stop.

**Compile skeleton (shared; not a domain script):**

```
Situation → Risk → Capture Frame → Telos → Available Agency → Protocol
```

**Forbidden design move:** “Matthew 5 says do action X.”  
**Required design move:** Context → constraints → feasible set → normative filters → bounded action class.

No implementation script is authorized by this mission.

---

## Locked inputs (no new kernel)

1. Imposed-role detection / role refusal  
2. Dignity invariance  
3. Telos / Truth / Context constrained control  
4. Non-mimetic action  

Safety paths already established (valid outputs, **not** DPT-R failure):

`ABSTAIN` · `DEFER` · `SEEK_INFORMATION` · `SEEK_COUNSEL` · `EXIT` · `SEEK_HELP` · `REPORT` · `PROTECT` · `LEGAL_REMEDY` · `DEFEND_WHEN_JUSTIFIED` (alias: `PHYSICAL_SELF_PROTECTION_WHEN_JUSTIFIED`) · `COOPERATE` · `WITHDRAW` · `SILENCE` · `NEGOTIATE` · `NONCOOPERATE` · `EXPOSE_COERCION`

**Invariant:** Dignity ≠ remaining in danger. Agency Sovereignty ≠ solving alone.

**Walls (this design must not cross):** youth physical violence as AI role-play product; investment/FOMO as Agency-market or live-trade coach; couple/clinical counseling claims; BESD M/R/N/G mutation; CEM C2 mutation; loader/operator mutation.

---

## D01_INPUT_STATE_SCHEMA

Record `I_t` as a **qualitative state**. No numeric score is defined.

| Field | Meaning | Fail-closed if |
| --- | --- | --- |
| `C_t` | Situation / setting / time-pattern (one-off vs repeated) | materially incomplete |
| `observed_coercive_frame` | What the other party is trying to make the interaction *be* | unknown **and** action would treat a guessed frame as FACT |
| `R_imposed_candidate` | Candidate assigned role (subordinate, retaliator, silent debtor, conscript, …) | inference treated as FACT below qualitative support (see D02, D11) |
| `truth_evidence_state` | What is known vs alleged vs reconstructed | material unresolved where the action depends on it |
| `uncertainty` | `U(Truth, Context)` material or not | material → D03 / D10 only |
| `safety_state` | Immediate harm, escape, weapons, group surround, medical | cannot be assessed |
| `third_party_risk` | Children, bystanders, dependents, other targets | not assessable where foreseeable |
| `available_lawful_actions` | Actions the agent can actually take without inventing legal strategy | legally material **and** lawful options unknown |
| `telos_candidate` | Stated aim (safety, dignity, end the scene, accountability, relationship option-value) | telos used to override known evidence |

`R_imposed` **must not** be inferred from pain, illness, aging, or environmental constraint alone (spec §5.1.3).

---

## D02_IMPOSED_ROLE_DETECTION_RULE

**Ask (plain language):** “What role is this situation trying to assign me?”

**Detect `R_imposed` only if** there is a **social/agentive assignment** (demand, humiliation script, forced binary: fight/submit/snitch-as-shame, etc.), not merely a hard constraint.

**Qualitative support (no invented threshold):**

- At least one **observable move** that assigns a role or a closed choice-set; **and**
- The candidate role is named as **hypothesis**, not FACT, until D06.

If support is missing → do **not** run creative-resistance steps. Route to D10 (`ABSTAIN` / `DEFER` / `SEEK_INFORMATION`) or D04 if safety still requires EXIT/SEEK_HELP without a full role model.

---

## D03_TRUTH_UNCERTAINTY_GATE

If Truth or Context is **materially uncertain**:

```
a ∈ {ABSTAIN, DEFER, SEEK_INFORMATION, SEEK_COUNSEL}
```

Telos and moral certainty **must not** override unresolved evidence.  
Historical reconstruction (what “really happened” in an unobserved past) **must not** be treated as FACT to justify a unique action class.

---

## D04_SAFETY_THIRD_PARTY_GATE

Evaluate **before** role-play aesthetics or non-mirror self-image.

| Condition | Effect on `A_feasible` |
| --- | --- |
| Immediate personal danger / cannot leave / weapons / group surround | `EXIT`, `SEEK_HELP`, `PROTECT`, `DEFEND_WHEN_JUSTIFIED` **outrank** exposure/negotiate/witty third way |
| Repeated coercion with physical contact | Record + ally + `REPORT` become **admissible and often required as candidates**; “boundary phrase only” is **not** sufficient as the sole remaining class |
| Foreseeable third-party harm | `PROTECT` / `REPORT` outrank the agent’s non-mimetic performance |
| Youth physical violence | Official protection path **before** coaching/role-play (design wall) |

Surface resemblance to the opponent’s force is **allowed** if independently justified by safety, proportionality, law, and context (spec §5.2 N3). That is **not** mimetic capture by default.

---

## D05_FEASIBLE_ACTION_SET

```
a_(t+1) ∈ A_feasible(Truth, Context, Safety, Law, ThirdPartyHarm, Uncertainty)
```

**No action class is universally preferred.** `T_DPT` must not force stereotyped creative resistance.

Membership is **inclusion with reason** and **exclusion with reason** (D09). Empty of “heroic third way” is allowed. Empty of **all** classes except fail-closed `ABSTAIN` is required when D11 fires.

---

## D06_ROLE_REFUSAL_CHECK

If `R_imposed` is supported:

- Refuse internalization (worth collapsed by the insult/harm).  
- Refuse compulsory entry into the aggressor’s **closed script** (fight / submit / perform).  
- Role refusal is **not** a requirement to stay, lecture, or win.

If the only way to refuse the role is to **leave the chosen battlefield**, `WITHDRAW` / `EXIT` **satisfy** role refusal.

---

## D07_DIGNITY_INVARIANCE_CHECK

`Dignity(t) = constant` is a **normative metaphor**, not a health score.

**Pass:** the selected class does not encode “I am worth less because I was harmed.”  
**Fail (design error):** treating endurance of ongoing assault as dignity, or treating `REPORT`/`SEEK_HELP` as dignity failure.

---

## D08_NON_MIMETIC_CONTROL_CHECK

Default constraint:

```
a_(t+1) ≠ Mirror(opponent_action_t)
```

**Exception (not a loophole for revenge):** independently justified protective/legal/report action may **resemble** opponent force at the surface without being under the opponent’s script.

**Fail:** revenge, humiliation-return, or “prove strength” as the organizing telos.

---

## D09_ACTION_SELECTION_RECORD

Required record shape (design; not a runtime schema freeze):

```text
v0_1_selection_record:
  included: [{ action_class, reason }]
  excluded: [{ action_class, reason }]
  abstain_or_defer: { fired: bool, reason }
  dignity_invariant: pass|fail|not_run
  non_mimetic_control: pass|fail|exception_justified|not_run
  role_refusal: pass|fail|not_applicable
  claim_tag: HYPO
```

Do **not** overwrite a locked v1 fixture label with a v2 class in this document. Dual-label preservation remains a **future bounded consumer** concern; this design does not authorize loader work.

---

## D10_ABSTAIN_DEFER_PATH

Always admissible when D03 or D11 fires.  
Also admissible as a **chosen** class when the agent’s telos is to end participation without a speech act.

`ABSTAIN` / `DEFER` / `SEEK_INFORMATION` / `SEEK_COUNSEL` are **success classes** of the protocol, not operator failure.

---

## D11_FAIL_CLOSED_CONDITIONS

Protocol **STOP / ABSTAIN** (no invented numeric cut) if:

- truth is materially unresolved  
- context is materially incomplete  
- immediate safety cannot be assessed  
- third-party harm is not assessable where relevant  
- lawful options are unknown **where legally material** (this is **not** a legal-advice engine)  
- imposed-role inference is used as FACT without qualitative support (D02)  
- the action requires historical reconstruction treated as FACT  

---

## D12_CLAIM_CEILING

**PASS of this mission establishes only:** a bounded **protocol design** exists that is structurally consistent with current DPT-R v2 constraints.

**PASS does not establish:** biblical truth; novelty; theological consensus; empirical efficacy; legal sufficiency; clinical safety/effectiveness; financial usefulness; real-world deployment; AI-coach competitiveness; CBT/DBT/ACT superiority; compile consistency across domains; behavior change under pressure.

---

## Compile falsifier (design, 3 situations)

Same `I_t` fields and D02–D11 checks. **Different** `A_feasible` membership/priority is required.  
**Falsify compile** if all three collapse to one stereotyped class, or if each row is a disconnected advice script that does not share D01–D11.

### S1 — Workplace coercion (illustrative)

Imposed frame: “Endure it or quit.”  
Telos: dignity + occupational safety + accountability option.  
**Include (candidates):** `DOCUMENT` as `SEEK_INFORMATION`/`REPORT` prep, `ALLY`, `NEGOTIATE` (bounded), `REPORT` (formal channel), `WITHDRAW` from unsafe 1:1.  
**Exclude as sole answer:** mimetic blow-up; “just be professional and absorb.”  
**Escalate:** repeated pattern → `REPORT` / `LEGAL_REMEDY` candidates **without** calling that DPT-R failure.

### S2 — Ongoing harassment, safety-first (illustrative)

Imposed frame: “Fight, submit, or be a snitch.”  
Telos: safety + dignity + scene termination.  
**Include:** short boundary (`NONCOOPERATE` speech), `EXIT`/move to witnesses, record, `SEEK_HELP`/`REPORT`.  
**Exclude as sole answer:** stay and “hold dignity”; AI Level-4/5 role-play as the primary intervention when physical risk is rising.  
**Youth physical harm:** official protection **outranks** coaching.

### S3 — Low-risk social pressure (illustrative)

Imposed frame: “Everyone does it, so you must.”  
Telos: judgment independence; no imminent harm.  
**Include:** `ABSTAIN`, `NONCOOPERATE`, `WITHDRAW`, `NEGOTIATE` (decline).  
**Exclude:** `DEFEND_WHEN_JUSTIFIED` / emergency `REPORT` as default (would be **unnecessary escalation**).  
**Falsifier vs S2:** same operator must **not** copy S2’s safety stack into S3.

---

## Gaps (why `PASS_WITH_GAPS`)

- S1–S3 are **illustrative compile probes**, not verified compile consistency.  
- Fail-closed is qualitative; no threshold was invented (intentional).  
- No red-team of this protocol yet.  
- No runtime / no script.  
- `DOCUMENT` / `ALLY` are **situation labels** mapped onto `SEEK_INFORMATION` / `REPORT` / `SEEK_HELP` — not new kernel operators.

---

## DECIDE_ONE

`DPT_R_SITUATED_PROTOCOL_V0_1_DESIGN_PASS_WITH_GAPS`

**STOP_AFTER_RESULT:** `TRUE`  
**Next (not this mission):** wait for a separate ACK to run **situated protocol red-team**. Implementation remains unauthorized.
