# prompt_04_run_05.md

Runtime: Gemini JAMS (Athena persona)

Final Action: REDUCE
Confidence: 0.70
Risk Flags: [macro_headwinds, geopolitical_tension, elevated_leverage, divergent_sentiment]

Evidence pointers:
- external_inputs_jsonl: docs/final/artifacts/vibe_external_inputs_latest.jsonl

Rationale:
- Rising US10Y and DXY indicate tightening macro liquidity and USD strength, typically negative for risk assets.
- Elevated and increasing geopolitical risk adds uncertainty to the global market outlook.
- Crypto-specific sentiment (FGI) is in "Greed" territory, while BTC funding rates and open interest are rising, indicating strong speculative long positioning and increased leverage.
- The combination of high leverage in crypto and external macro/geopolitical headwinds creates vulnerability to a sharp correction.
- Falling VIX suggests reduced fear in traditional markets, but this is outweighed by other macro and geopolitical concerns.

Notes:
- The market exhibits a divergence between strong internal crypto bullishness (driven by sentiment and leverage) and increasing external macro and geopolitical risks. This setup, particularly with elevated leverage, suggests increased fragility and potential for volatility.
{
  "decision": "REDUCE",
  "confidence": 0.70,
  "rationale_short": "Rising macro/geopolitical risks combined with elevated crypto leverage suggest vulnerability despite current bullish sentiment.",
  "risk_flags": [
    "macro_headwinds",
    "geopolitical_tension",
    "elevated_leverage",
    "divergent_sentiment"
  ]
}
