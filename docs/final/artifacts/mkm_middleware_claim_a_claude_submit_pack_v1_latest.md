# Claude submit pack — Claim-A L0 · honesty rev 1.7 · PASTE_READY

## Security / scope guard
- No secrets · no FULL blind kit · no corpus dump · repo-relative paths only
- Scope: L0 research critique only · not Track A · not live trading · not market GO

## Paste-ready verdict
- status: **PASTE_READY**
- send_gate (scoped): `OPEN`
- independent_blind: `False` (**true only if third_party_human**)
- commander_full_kit_blind / self_reviewed_full_kit: `True` / `True`
- self_accepted_proxy_blind: `False`
- residual warnings:
  - Azure unique-C attrition 6/20; api_error_count=18 is arm-calls (≈6×3), not 90% task fail
  - Gemini plain-arm gate residual weak (~0.20)
  - VALUE-PROP TENSION: unblinded prefer plain_full 14 > id_only 10 (n=24) — legacy 'send pointers' usefulness NOT endorsed; rev 1.7 Hero is egress/security frame only

## Metric definitions (read before numbers)
- **gate_ok**: Syntactic egress contract only: min_locked_citations + no_outside_pack_refs + hold_mentioned + no_forbidden_substrings + non_empty (+ adversarial refusal when applicable). NOT semantic answer quality.
- **api_error_count**: arm-call failures (A/B/C × tasks). Unique adversarial C attrition = `n_adversarial − n_scored_C` (here 6/20). Arm-call total 18 ≈ that unique count × 3 — **not** 18/20=90% task failure.

## Hero / claim frame (rev 1.7 · egress · do not bury)
> Keep the corpus local. What leaves your boundary: pointers, locked citations, and a hard HOLD — never the corpus itself.

**Claim frame:** egress / security boundary only. Do **not** sell pointer-only answers as usefulness-proven.

**Blind usefulness tension (commander Blind unblinded, n=24):** prefer **plain_full 14** > **id_only 10** (plain share ≈ 0.5833). Chars-save / syntactic gate ≠ human prefer for pointer arm. **Not** market GO; Hero reframes product narrative as egress, not usefulness SLA.

### Legacy headline (research ledger only — paste with Counter-signal)
> Keep the corpus local. Send pointers. Enforce citation scope and a hard HOLD line before anything leaves your boundary.

- A/B label tally {'B': 9, 'A': 15} vs unblinded {'id_only': 10, 'plain_full': 14, 'tie': 0}: A/B are randomized sides per item — prefer A count must NOT equal prefer id_only or plain_full. 15/9 vs 10/14 is expected under shuffle, not a 1-row ledger bug. Key A_arm dist={'id_only': 17, 'plain_full': 7}.

## Measured (research · per-signal n · do not merge)
- Fair external AB · n=30 · max_tokens=1024 · chars save≈{'azure': 0.7012, 'gemini': 0.7012}
- Fair gates (syntactic): {'azure': {'plain': 0.5333, 'id_only': 1.0}, 'gemini': {'plain': 0.2, 'id_only': 1.0}}
  - id_only=1.0 on Azure+Gemini can be expected under syntactic gate; it is **not** semantic accuracy.
- Gemini HOLD-first · n=12 · model=`gemini-2.5-flash` · hold 0.25→1.0 · gate 0.25→1.0 · run `2026-07-11T14:50:47Z`
  - Round delta: Prior onepager/rereview cited hold 0.33→1.00 / gate→0.92 while live_hold_first_smoke was null (unreproducible citation / ledger lie). This file is a NEW live remasure (generated_at_utc=2026-07-11T14:50:47Z) with hold 0.25→1.0 and gate 0.25→1.0. Values differ because prior numbers were not backed by this smoke block; do not silently replace 0.33 with 0.25 as if same run.

### Adversarial C — report separately (different n / attrition)
- **Ollama** · n_adv=30 scored_C=30 · true_block=0.8667 · miss=0.0 · refused_ok=0.1333
- **Azure** · n_adv=20 scored_C=14 · unique_C_api_error=6 · api_error_arm_calls=18 · true_block=1.0 (denom=scored_C) · miss=0.0 · model=`gpt-4o-mini`
  - Do **not** read Azure true_block=1.0 as stronger than Ollama 0.87 without footnotes.

- Blind detail · n=24 · scorer=`commander_human` · independent_blind=False · commander_full_kit=True (prefer tallies: see Hero / Blind tension above — not buried here only)

## Closed in 1.5–1.6 · lighted in 1.7
1–5. Labels / api_error / HOLD-first delta / gate_ok / adv footnotes — closed in 1.5.
6. **Selective emphasis:** plain_full Blind prefer lighted beside headline (1.6).
7. **A/B vs arm tallies:** explained via per-item side randomization (not a 1-row bug).
8. **Egress Hero reframe:** external paste uses boundary/HOLD frame; legacy 'Send pointers' usefulness claim withdrawn from Hero (1.7).

## Ask Claude
Re-critique honesty rev **1.7** egress Hero reframe + retained Blind usefulness tension. **Do not** certify market GO / Track A / product SLA / L2-lens=compression success.

## Artifact index
- `docs/final/artifacts/mkm_middleware_claim_a_claude_submit_pack_v1_latest.md`
- `docs/final/artifacts/mkm_middleware_anti_self_grade_checklist_v1_latest.json`
- `docs/final/artifacts/mkm_middleware_gemini_hold_gap_diag_v1_latest.json`
- `docs/final/artifacts/mkm_middleware_claim_a_three_arm_ab_azure_v1_latest.json`
- `docs/final/artifacts/mkm_middleware_l0_send_ready_onepager_v1_latest.md`
- `docs/final/artifacts/mkm_middleware_headline_reuse_checklist_v1_latest.json`

generated_at_utc: 2026-07-11T16:25:57Z
schema: mkm_middleware_claim_a_claude_submit_pack_v1
