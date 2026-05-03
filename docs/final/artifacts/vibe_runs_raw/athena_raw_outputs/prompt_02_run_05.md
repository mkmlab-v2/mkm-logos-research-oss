# prompt_02_run_05.md

Runtime: Gemini JAMS (Athena persona)

Final Action: HOLD
Confidence: 0.65
Risk Flags: [Macro Headwinds, Leverage Risk]

Evidence pointers:
- external_inputs_jsonl: docs/final/artifacts/vibe_external_inputs_latest.jsonl

Rationale:
- Macro indicators (US10Y, DXY) are rising, suggesting tightening liquidity and dollar strength, which are typically headwinds for risk assets.
- Geopolitical risk score is elevated and increasing, adding to market uncertainty.
- Crypto-specific sentiment remains positive, indicated by a decreasing VIX and an increasing Fear & Greed Index (Greed).
- BTC funding rates and Open Interest are both rising, reflecting increasing leverage and bullish positioning in derivatives.
- The confluence of negative macro signals and positive, but potentially overheated, crypto microstructure warrants a neutral HOLD.
- Increasing leverage in derivatives markets introduces a higher risk of volatility or deleveraging events.

Notes:
- Uncertainties exist regarding the persistence of macro headwinds versus crypto-specific bullish sentiment.
- The current level of leverage in BTC derivatives could lead to sharp price movements in either direction.

Flip conditions:
- **To WATCH:** If US10Y exceeds 4.40% or DXY breaks 106, signaling stronger macro headwinds.
- **To REDUCE:** If BTC_FUNDING_RATE turns negative or BTC_OPEN_INTEREST drops by >10% alongside a price decline, indicating deleveraging.
- **To REDUCE:** If CRYPTO_FGI drops below 50 (Neutral) or VIX rises above 20, signaling significant risk-off sentiment.

Missing evidence:
- Current BTCUSDT spot price and recent price action.
- On-chain data (e.g., exchange net flows, whale activity).
- Broader equity market performance (e.g., SPX).
