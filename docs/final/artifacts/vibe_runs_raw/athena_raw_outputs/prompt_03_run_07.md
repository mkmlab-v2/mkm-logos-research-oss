# prompt_03_run_07.md

Runtime: Gemini JAMS (Athena persona)

Final Action: HOLD
Confidence: 0.88
Risk Flags: [Macro Headwinds, Leverage Risk, Sentiment Exuberance, Geopolitical Uncertainty]

Evidence pointers:
- external_inputs_jsonl: docs/final/artifacts/vibe_external_inputs_latest.jsonl

Rationale:
- **Facts**: US10Y and DXY are trending up (0.95 conf), indicating tighter macro liquidity conditions. BTC_FUNDING_RATE (0.8 conf) and BTC_OPEN_INTEREST (0.82 conf) are both rising, suggesting increasing leverage in the crypto derivatives market. CRYPTO_FGI is at 63 and trending up (0.85 conf), signaling 'Greed'. GEO_RISK_KEYWORD_SCORE is also trending up (0.7 conf). VIX is trending down (0.95 conf).
- **Assumptions**: Rising US10Y and DXY are assumed to be headwinds for risk assets like BTC. The combination of high and rising crypto funding rates, open interest, and a 'Greed' FGI suggests an overheated market with elevated liquidation risk. Increasing geopolitical risk is assumed to add systemic uncertainty.
- The decreasing VIX indicates reduced fear in traditional markets, but this general sentiment is outweighed by specific crypto microstructure risks and macro headwinds when applying a risk-first lens.
- Under a Risk-First Lens, the confluence of macro headwinds, elevated crypto leverage, and rising geopolitical risk points to a high-risk environment for BTCUSDT.
- The policy dictates penalizing overfitting and narrative-only signals, and choosing HOLD if assumptions dominate. The interpretation of these facts as significant risks for BTCUSDT constitutes a dominance of assumptions regarding future price action.

Notes:
- Uncertainties exist regarding the precise impact magnitude and timing of macro factors and geopolitical events on BTCUSDT.
- The extent to which traditional market sentiment (VIX down) can offset crypto-specific leverage risks is unclear.
- The confidence in the 'Greed' signal from CRYPTO_FGI is moderate (0.85), and its predictive power for immediate corrections is an assumption.
