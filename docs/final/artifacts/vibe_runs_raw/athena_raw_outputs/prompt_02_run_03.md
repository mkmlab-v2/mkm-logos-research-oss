# prompt_02_run_03.md

Runtime: Gemini JAMS (Athena persona)

Final Action: HOLD
Confidence: 0.65
Risk Flags: [macro_headwinds, leverage_risk, geopolitical_uncertainty]

Evidence pointers:
- external_inputs_jsonl: docs/final/artifacts/vibe_external_inputs_latest.jsonl

Rationale:
- Crypto sentiment (CRYPTO_FGI: 63, up) indicates strong internal bullish momentum.
- Derivatives microstructure (BTC_FUNDING_RATE: 0.009, up; BTC_OPEN_INTEREST: 15.2B, up) suggests increasing demand and leverage for BTC longs.
- Traditional market risk sentiment (VIX: 17.8, down) is improving, generally supportive of risk assets.
- Macro headwinds persist with rising US10Y (4.32, up) and DXY (105.4, up), indicating tightening liquidity.
- Elevated geopolitical risk (GEO_RISK_KEYWORD_SCORE: 0.71, up) introduces external uncertainty.
- Conflicting signals warrant caution, but internal crypto strength supports maintaining current exposure.

Notes:
- **Uncertainties:** Potential for rapid deleveraging given high funding rates and OI; impact of sustained macro tightening on crypto; specific nature and escalation of geopolitical events.
- **Flip to WATCH:** Significant weakening of crypto microstructure (e.g., FGI reversal, funding rate decline) or acceleration of macro headwinds (e.g., DXY > 106, US10Y > 4.5%).
- **Flip to REDUCE:** A combination of sustained bearish crypto microstructure (e.g., negative funding, sharp OI drop) *and* worsening macro/geopolitical conditions.
- **Missing Evidence:** BTC spot price action/volume; comprehensive on-chain data (exchange flows, stablecoin movements); broader altcoin market performance.
