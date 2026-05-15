# MKM Gut–Brain Metaphor — Track C / B2B Comms Skill

## Purpose

Draft or review **public-facing** copy that uses the gut–brain / fermentation pedagogical frame without violating Fact-Lock, PUBLIC_FACING v1.7, or B→A isolation.

## Trigger

Use when the user asks for:

- Track C one-pager, B2B deck, showroom narrative using 장-뇌 / gut–brain / vagus / fermentation metaphor
- Scrubbing marketing text for over-claim
- Mapping `outcome_class` to **non-literal** operator language

## Required reads (before drafting)

1. `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` (v1.7 §3 metaphor guardrail)
2. `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.5–3.6
3. Latest gates: `docs/final/artifacts/prophecy_promotion_gates_v1_latest.json` (`outcome_class`, `combined_all_passed` — cite as **local research baseline**, not guarantee)

## Output contract

1. **Audience** (B2B operator vs public billboard)
2. **Metaphor block** — 3–5 sentences, labeled *pedagogical isomorphism*
3. **Evidence block** — artifact paths + `research_only` / `[HYPO]` where applicable
4. **Limits block** — what we do **not** claim (neuroscience proof, live trade trigger, 0% AS)
5. **Suggested disclaimer** — one line aligned with PUBLIC_FACING

## Fact-Lock rules

- No implementation or gate pass from chat alone; run or cite `eval_prophecy_promotion_gates_v1.py` output if discussing promotion state.
- `pass_candidate` / `reject` etc. are **internal taxonomy**; do not translate to medical or guaranteed trading outcomes.
- LG / companion AI layer is separate Fact-Safe product narrative — do not conflate with this metaphor fixing broken AI.

## Commands (repro, optional)

```text
py scripts/eval_prophecy_promotion_gates_v1.py
py scripts/build_prophecy_gate_evidence_pack_v1.py
py scripts/build_mkm_trackc_ops_dashboard_v1.py
```

## NEVER

- Insert metaphor definitions into `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`.
- Commit `docs/research/*` or `memory/obsidian_vault/*` without explicit user request (often gitignored).
