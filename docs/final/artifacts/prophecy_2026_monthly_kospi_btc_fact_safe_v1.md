# 2026 Monthly KOSPI/BTC Fact-Safe Prophecy V1

## 3문장 요약
1) 본 문서는 확정 예언이 아닌 월별 확률 시나리오다.
2) 현재 신뢰도 배지/게이트는 MID / HOLD다.
3) HOLD 모드에서는 방어 가중치가 자동 적용된다.

## 메타 고정
- generated_at_utc: 2026-04-01T16:58:17Z
- engine_id: V2_Precision_MCP
- engine_scope: monthly_prophecy_generation_only
- boundary_rule: observatory_ephemeris_v1
- myeongri_verification_engine: project-0-workspace-athena-manseryeok.verify_saju_date
- calendar_source_type: external_standard_required
- calendar_source_name: standard_rabbinic_calendar
- reliability_badge: MID
- high_reliability_decision: HOLD
- gate_reason: monthly_check_gate|core_forced_hold
- price_output_locked: True
- lock_reason: low_or_hold_mode_price_output_forbidden
- btc_backtest_best_period: 2026-01-01..2026-12-31
- k_shield_candidate_name: k_shield_h1_soft
- k_shield_candidate_net_return_pct: -6.383742
- k_shield_candidate_max_drawdown_pct: 8.285629
- core_score: 0.25
- core_decision: HOLD
- core_reason: score_inside_locked_band
- hypothesis_target_condition: return_pct <= -0.8
- hypothesis_falsification_condition: return_pct >= +1.5
- observed_lever_priority: ['overnight_global_risk', 'usdkrw_fx', 'rates_front_end', 'semiconductor_news', 'foreign_institutional_flow']

## 채점 규칙 (HIT/FAIL/NEUTRAL_DRAW)
- target_metric: KOSPI_D1_RETURN_PCT
- HIT: return_pct <= -0.8
- FAIL: return_pct >= 1.5
- NEUTRAL_DRAW: HIT/FAIL 사이 구간(승패 미반영)

## Risk Profile (Trinity Governor)
- mode: LOCKED_MODE
- logos_regime_score: 0.56
- myeongri_timing_score: 0.72
- sasang_response_score: 0.68
- fused_risk_pressure: 0.632
- position_scale_cap: 0.2
- daily_loss_cap_pct: 1.0416

## 월별 시나리오
- 1월 (기준선/탐색) | KOSPI: 방어하방 (상/중/하=30/36/34) | BTC: 방어하방 (상/중/하=29/36/35)
- 2월 (기준선/탐색) | KOSPI: 방어하방 (상/중/하=30/36/34) | BTC: 방어하방 (상/중/하=29/36/35)
- 3월 (기준선/탐색) | KOSPI: 방어하방 (상/중/하=30/36/34) | BTC: 방어하방 (상/중/하=29/36/35)
- 4월 (압박/방어) | KOSPI: 방어하방 (상/중/하=20/34/46) | BTC: 방어하방 (상/중/하=19/34/47)
- 5월 (압박/방어) | KOSPI: 방어하방 (상/중/하=20/34/46) | BTC: 방어하방 (상/중/하=19/34/47)
- 6월 (압박/방어) | KOSPI: 방어하방 (상/중/하=20/34/46) | BTC: 방어하방 (상/중/하=19/34/47)
- 7월 (재정비/경쟁) | KOSPI: 방어하방 (상/중/하=29/35/36) | BTC: 방어하방 (상/중/하=28/35/37)
- 8월 (재정비/경쟁) | KOSPI: 방어하방 (상/중/하=29/35/36) | BTC: 방어하방 (상/중/하=28/35/37)
- 9월 (재정비/경쟁) | KOSPI: 방어하방 (상/중/하=29/35/36) | BTC: 방어하방 (상/중/하=28/35/37)
- 10월 (성과 회수/정리) | KOSPI: 완만상방 (상/중/하=34/34/32) | BTC: 중립 (상/중/하=33/34/33)
- 11월 (성과 회수/정리) | KOSPI: 완만상방 (상/중/하=34/34/32) | BTC: 중립 (상/중/하=33/34/33)
- 12월 (성과 회수/정리) | KOSPI: 완만상방 (상/중/하=34/34/32) | BTC: 중립 (상/중/하=33/34/33)

## 면책
- 본 문서는 투자/법률/의료의 확정 판단 근거가 아니며, Fact-Safe 계약에 따른 확률형 보조 자료다.
