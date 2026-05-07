# Sasang Rule-Based Response v1

- generated_at_utc: 2026-05-07T14:27:50Z
- response_mode: dev
- baseline_status: PASS
- winner_sigma: 0.0315

## 1) 4상 관계
- top_axis: TY
- fused_axis: TY=0.283, TE=0.279, SY=0.246, SE=0.192

## 2) 병증약리 전변확률
- calm: 1.000 (HIGH)
- watch: 0.000 (LOW)
- stress: 0.000 (LOW)
- crisis: 0.000 (LOW)

## 3) 금화교역 분해
- panic_fomo_gap: ratio=0.404 (MID)
- sentiment_polarity_gap: ratio=0.387 (MID)
- axis_te_se_spread: ratio=0.145 (LOW)
- axis_ty_sy_spread: ratio=0.063 (LOW)

## 4) 보명지주 분해
- axis_balance_spread_inverse: ratio=0.321 (LOW)
- low_panic_support: ratio=0.237 (LOW)
- low_volatility_support: ratio=0.226 (LOW)
- low_dispersion_support: ratio=0.216 (LOW)

## 5) 결론
- Baseline status=PASS, winner_sigma=0.0315
- Top axis=TY with fused axis [TY=0.283, TE=0.279, SY=0.246, SE=0.192]
- No baseline alerts.

## 6) Mode Output
- mode: DEV (structured whitebox summary; no raw CoT)
- evidence.reasoning_json: C:\workspace\reports\sasang_dna_market_reasoning_v1_latest.json
- evidence.baseline_json: C:\workspace\reports\agct_sigma_locked_baseline_chain_v1_latest.json
- engine.top_next_state: calm
- gate: baseline_status=PASS, winner_sigma=0.0315
- blockers: none
