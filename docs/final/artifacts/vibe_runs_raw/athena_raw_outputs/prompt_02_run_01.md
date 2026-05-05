# prompt_02_run_01.md

Runtime: Gemini JAMS (Athena persona)

Final Action: HOLD
Confidence: 0.65
Risk Flags: [macro_headwinds, elevated_leverage, geopolitical_uncertainty]

Evidence pointers:
- external_inputs_jsonl: docs/final/artifacts/vibe_external_inputs_latest.jsonl

Rationale:
- Macro environment shows headwinds with rising US10Y and DXY, typically negative for risk assets.
- VIX is decreasing, indicating improving general market risk sentiment.
- Crypto Fear & Greed Index (FGI) is in "Greed" territory and rising, signaling strong internal bullish sentiment.
- BTC funding rates and Open Interest are both increasing, suggesting growing leveraged long positions.
- Elevated geopolitical risk adds a layer of external uncertainty.
- Conflicting signals between macro headwinds and strong crypto-specific sentiment/microstructure warrant a conservative HOLD.

Notes:
- Uncertainty exists regarding the sustainability of crypto's internal bullish momentum against deteriorating macro conditions.
- The high and rising leverage in BTC derivatives (funding rates, OI) presents a risk of amplified downside if sentiment shifts.

Flip conditions:
- **To WATCH:** If US10Y or DXY show accelerated upward movement, or if CRYPTO_FGI drops below 50, or if GEO_RISK_KEYWORD_SCORE exceeds 0.8.
- **To REDUCE:** If BTC_FUNDING_RATE turns negative while BTC_OPEN_INTEREST remains high, indicating a potential long squeeze, or if VIX reverses sharply upwards alongside a significant drop in CRYPTO_FGI.

Missing evidence:
- Specific BTC price action and technical analysis.
- On-chain flow data for BTC.
- Liquidation data for BTC derivatives.
