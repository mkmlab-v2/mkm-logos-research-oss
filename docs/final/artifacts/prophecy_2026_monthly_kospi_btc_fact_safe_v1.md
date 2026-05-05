# 2026 Monthly KOSPI/BTC Fact-Safe Prophecy V1

## 3문장 요약
1) 본 문서는 확정 예언이 아닌 월별 확률 시나리오다.
2) 현재 신뢰도 배지/게이트는 MID / PASS다.
3) HOLD 모드에서는 방어 가중치가 자동 적용된다.

## 메타 고정
- generated_at_utc: 2026-05-03T00:15:11Z
- engine_id: V2_Precision_MCP
- engine_scope: monthly_prophecy_generation_only
- boundary_rule: observatory_ephemeris_v1
- myeongri_verification_engine: project-0-workspace-athena-manseryeok.verify_saju_date
- calendar_source_type: external_standard_required
- calendar_source_name: standard_rabbinic_calendar
- reliability_badge: MID
- high_reliability_decision: PASS
- gate_reason: monthly_check_gate|base_and_core_pass
- price_output_locked: False
- lock_reason: price_output_allowed
- btc_backtest_best_period: 2026-01-01..2026-12-31
- k_shield_candidate_name: k_shield_h1_soft
- k_shield_candidate_net_return_pct: -6.383742
- k_shield_candidate_max_drawdown_pct: 8.285629
- core_score: 0.25
- core_decision: PASS_LONG
- core_reason: score_above_long_threshold
- hypothesis_target_condition: return_pct <= -0.8
- hypothesis_falsification_condition: return_pct >= +1.5
- observed_lever_priority: ['overnight_global_risk', 'usdkrw_fx', 'rates_front_end', 'semiconductor_news', 'foreign_institutional_flow']

## 채점 규칙 (HIT/FAIL/NEUTRAL_DRAW)
- target_metric: KOSPI_D1_RETURN_PCT
- HIT: return_pct <= -0.8
- FAIL: return_pct >= 1.5
- NEUTRAL_DRAW: HIT/FAIL 사이 구간(승패 미반영)

## Risk Profile (Trinity Governor)
- mode: ACTIVE_MODE
- logos_regime_score: 0.56
- myeongri_timing_score: 0.72
- sasang_response_score: 0.68
- fused_risk_pressure: 0.632
- position_scale_cap: 0.4944
- daily_loss_cap_pct: 1.0416

## 월별 시나리오
- 1월 (기준선/탐색) | KOSPI: 완만상방 (상/중/하=47/36/17) | BTC: 완만상방 (상/중/하=50/36/14)
- 2월 (기준선/탐색) | KOSPI: 완만상방 (상/중/하=33/40/27) | BTC: 완만상방 (상/중/하=36/40/24)
- 3월 (기준선/탐색) | KOSPI: 완만상방 (상/중/하=33/40/27) | BTC: 완만상방 (상/중/하=36/40/24)
- 4월 (압박/방어) | KOSPI: 방어하방 (상/중/하=28/40/32) | BTC: 완만상방 (상/중/하=31/40/29)
- 5월 (압박/방어) | KOSPI: 방어하방 (상/중/하=21/40/39) | BTC: 방어하방 (상/중/하=24/40/36)
- 6월 (압박/방어) | KOSPI: 방어하방 (상/중/하=14/40/46) | BTC: 방어하방 (상/중/하=17/40/43)
- 7월 (재정비/경쟁) | KOSPI: 방어하방 (상/중/하=26/40/34) | BTC: 방어하방 (상/중/하=29/40/31)
- 8월 (재정비/경쟁) | KOSPI: 완만상방 (상/중/하=33/35/32) | BTC: 완만상방 (상/중/하=36/35/29)
- 9월 (재정비/경쟁) | KOSPI: 완만상방 (상/중/하=43/35/22) | BTC: 완만상방 (상/중/하=46/35/19)
- 10월 (성과 회수/정리) | KOSPI: 완만상방 (상/중/하=49/34/17) | BTC: 완만상방 (상/중/하=52/34/14)
- 11월 (성과 회수/정리) | KOSPI: 완만상방 (상/중/하=49/34/17) | BTC: 완만상방 (상/중/하=52/34/14)
- 12월 (성과 회수/정리) | KOSPI: 완만상방 (상/중/하=49/34/17) | BTC: 완만상방 (상/중/하=52/34/14)

## 면책
- 본 문서는 투자/법률/의료의 확정 판단 근거가 아니며, Fact-Safe 계약에 따른 확률형 보조 자료다.
