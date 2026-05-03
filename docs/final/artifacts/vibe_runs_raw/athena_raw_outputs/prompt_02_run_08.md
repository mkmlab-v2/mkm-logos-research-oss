# prompt_02_run_08.md

Runtime: Gemini JAMS (Athena persona)

Final Action: HOLD
Confidence: 0.70
Risk Flags: [Macro Headwinds, Leverage Risk]

Evidence pointers:
- external_inputs_jsonl: docs/final/artifacts/vibe_external_inputs_latest.jsonl

Rationale:
- Crypto-specific sentiment (CRYPTO_FGI: 63, up) and derivatives activity (BTC_FUNDING_RATE: 0.009, up; BTC_OPEN_INTEREST: 15.2B, up) indicate strong internal bullish momentum.
- Broader market risk sentiment shows some improvement (VIX: 17.8, down).
- Significant macro headwinds persist with rising US10Y (4.32, up) and a strengthening DXY (105.4, up).
- Elevated geopolitical risk (GEO_RISK_KEYWORD_SCORE: 0.71, up) adds a layer of uncertainty to overall market stability.
- The combination of rising BTC Open Interest and Funding Rates suggests increasing leverage, which could amplify volatility on any adverse price movement.
- The conflicting signals between strong crypto internals and challenging macro/geopolitical externals warrant a neutral HOLD posture.

Notes:
- Uncertainties include the potential for rapid deleveraging if macro conditions worsen or a geopolitical event escalates.
- The sustainability of current crypto-specific bullish sentiment against persistent macro headwinds is a key unknown.

Flip conditions:
- **To WATCH:** If US10Y or DXY show accelerated upward movement, OR if GEO_RISK_KEYWORD_SCORE increases significantly, OR if CRYPTO_FGI drops below 50, OR if BTC_FUNDING_RATE turns negative.
- **To REDUCE:** If a combination of worsening macro conditions (e.g., US10Y > 4.5%, DXY > 106) and a sharp deterioration in crypto microstructure (e.g., BTC_OPEN_INTEREST declining rapidly alongside price, or sustained negative BTC_FUNDING_RATE) is observed.

Missing evidence:
- BTC spot trading volume trends to confirm conviction behind price movements.
- On-chain flow data (e.g., exchange net flows) to assess supply/demand dynamics.
- Correlation data between BTC and traditional risk assets (e.g., S&P 500) to gauge sensitivity to broader market shifts.
