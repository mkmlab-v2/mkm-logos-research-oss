# Official External Briefing v1 (Latest)

## Purpose
Externally safe summary grounded in current Fact-Lock artifacts, with explicit scope boundaries and governance guardrails.

## Status Badges
- `track`: `B_TRACK`
- `mode`: `research_only`
- `decision_role`: `non_gating`
- `promotion_gate`: `human_signoff_required`

## As-Of Anchor
- `as_of_utc`: `2026-05-06T23:16:25Z`
- `artifact_scope`: `docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json`
- `scope_note`: "Results are valid for the observed v1 horizon only; long-horizon generalization requires separate validation."

## External 5-Line Core Statement
1. **[Strategy Strength]** In the latest validated artifact scope, `myeongni+sasang` is ranked top (`best_strategy_id`) with `cagr=4.568246`, `sharpe=5.838073`, and `mdd=-0.036296`.
2. **[Risk Governance]** The Logos lens is operated as a risk/context layer, not a standalone execution trigger; within the same artifact horizon, standalone Logos shows `mdd=-0.151538`.
3. **[Decision Policy]** Operationally, primary lanes are prioritized in global coordination, while Sasang veto guardrails can activate conservative protections in designated conditions.
4. **[Validation Boundary]** These statements are tied to versioned artifacts and bounded evaluation windows; promotion to production follows the formal Promotion Loop (`B -> Commander approval -> A`).
5. **[Operating Posture]** The system remains under conservative guardrails until unresolved items are cleared with evidence-backed updates.

## Policy Clarifier (Avoid Misinterpretation)
| Policy Surface | Active Rule | Source |
|---|---|---|
| Global coordinator conflict policy | `primary lanes win; logos remains non-gating` | `reports/mkm_global_coordinator_v1_latest.json` |
| Sasang veto hard guardrail | `most_conservative_wins=true` | `docs/final/artifacts/sasang_veto_only_active_config_latest.json` |

## Evidence Block (1:1 Mapping)
- Canonical claim mapping: `reports/lens_claims_evidence_mapping_v1_latest.json`
- Strategy ranking/mdd source: `docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json`
- Sasang promotion gates: `reports/agct_sasang_stage2_promotion_gate_v1_latest.json`
- Sasang fasttrack gate: `reports/agct_sasang_stage2_fasttrack_gate_v1_latest.json`
- Sasang D+7 checkpoint: `reports/agct_sasang_stage2_d7_checkpoint_v1_latest.json`
- Track wall/autobind lock: `docs/final/artifacts/sasang12_promotion_candidate_gate_latest.json`

## Required Footer for External Use
- No claim in this briefing should be interpreted as guaranteed future performance.
- Any production promotion requires explicit human sign-off and governance gate passage.
- If an expected artifact is missing, the corresponding claim is treated as `NOT_PROVEN`.
