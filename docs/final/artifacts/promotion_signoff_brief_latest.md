# Promotion Sign-off Brief (Latest)

## Scope
- Date (UTC): 2026-04-21
- Tracks: Prophecy (B->A readiness), Compression (A-track gate alignment)
- Evidence policy: Artifact-backed facts only, no auto-wiring to live routes

## Key Artifacts
- `docs/final/artifacts/prophecy_promotion_gates_v1_latest.json`
- `docs/final/artifacts/prophecy_hit_rate_eval_latest.json`
- `docs/final/artifacts/fast_promotion_gate_v1_latest.json`
- `docs/final/artifacts/fast_promotion_live_candidate_latest.json`
- `docs/final/artifacts/a_track_go_nogo_status_latest.json`
- `docs/final/artifacts/dual_promotion_prep_pack_latest.json`

## Current Decisions
- Prophecy promotion gates: PASS (`combined_all_passed=true`, `strict_passed=true`)
- Prophecy hit-rate gate: PASS (`price_directional_hit_rate=0.6`, `n_evaluated=60`)
- Fast promotion gate: `live_candidate` (`live_ready=true`)
- A-track global status: HOLD (`overall_go_no_go=HOLD`, `recommended_stage=S1_SHADOW`)

## Operational Interpretation
- Prophecy lane is promotion-ready at the fast gate level.
- Compression/A-track lane remains shadow-stage constrained by global HOLD.
- No direct live deployment is authorized without explicit human sign-off.

## Remaining Constraints
- Human sign-off is mandatory before any B->A or live route switch.
- A-track HOLD policy takes precedence over fast candidate outputs.
- Keep route separation (research vs production) until governance release.

## Hold Root Cause (Verified)
- Source: `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json`
- Current lock fields:
  - `high_reliability_decision: HOLD`
  - `price_output_locked: true`
  - `gate_reason: monthly_check_gate|core_forced_hold`
- Effect in `a_track_go_nogo_status_latest.json`:
  - `high_reliability_decision_not_hold: false`
  - `price_output_unlocked: false`
  - therefore `recommended_stage: S1_SHADOW`

## Required Policy Decision
- Technical fast-gate conditions are satisfied (`live_candidate=true`), but global A-track policy remains HOLD.
- Promotion to S2+ cannot be unlocked by reruns alone; it requires explicit governance decision to release `core_forced_hold` logic.

## Sign-off Checklist
- [ ] Confirm promotion scope (which routes are allowed to move from B to A)
- [ ] Confirm deployment stage (`S1_SHADOW` only vs broader rollout)
- [ ] Confirm rollback trigger conditions and owner on-call
- [ ] Confirm no auto-wiring to live trading path
- [ ] Approve artifact timestamp set as decision baseline

## Commander Decision
- Decision: APPROVE (Limited Live Deployment)
- Approved scope: Fast Gate `live_candidate` 결과에 한해 제한적 라이브 허용. 단, A-track 글로벌 게이트가 `HOLD/S1_SHADOW`인 동안은 풀 스케일 승격 금지.
- Effective time (UTC): 즉시 발효 (2026-04-21T15:40:00Z)
- Conditions:
  - `fast_promotion_gate_v1_latest.json`의 `live_ready=true` 상태 유지
  - `price_output_locked` 정책 해제 전까지는 제한된 라우트/용량에서만 운용
  - 롤백 트리거: 게이트 FAIL, 무결성 경고, 운영 책임자 중지 명령
- Sign-off owner: Commander (Human in the Loop)
