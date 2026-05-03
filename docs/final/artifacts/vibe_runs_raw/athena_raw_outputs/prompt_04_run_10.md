# prompt_04_run_10.md

Runtime: Gemini JAMS (Athena persona)

Final Action: WATCH
Confidence: 0.70
Risk Flags: [macro_headwinds, geopolitical_uncertainty, elevated_leverage, sentiment_overextension]

Evidence pointers:
- external_inputs_jsonl: docs/final/artifacts/vibe_external_inputs_latest.jsonl

Rationale:
- Crypto-specific sentiment (CRYPTO_FGI) and microstructure (BTC_FUNDING_RATE, BTC_OPEN_INTEREST) indicate strong bullish momentum and increasing leverage.
- Broader market risk sentiment (VIX) is improving, generally supportive of risk assets.
- Macro conditions present headwinds with rising US10Y yields and a strengthening DXY, typically negative for risk assets.
- Geopolitical risk (GEO_RISK_KEYWORD_SCORE) is elevated and increasing, adding external uncertainty.
- The combination of increasing leverage within crypto markets and rising external macro/geopolitical risks creates a fragile environment.
- Conflicting signals necessitate a cautious approach and close monitoring for resolution of these opposing forces.

Notes:
- The resilience of crypto's internal bullish momentum against tightening macro conditions and rising geopolitical risk is uncertain.
- The elevated leverage in BTC derivatives increases vulnerability to potential deleveraging events if sentiment shifts.
{
  "decision": "WATCH",
  "confidence": 0.70,
  "rationale_short": "Conflicting signals with strong internal crypto bullishness and leverage clashing with macro headwinds and rising geopolitical risk, creating a fragile market.",
  "risk_flags": [
    "macro_headwinds",
    "geopolitical_uncertainty",
    "elevated_leverage",
    "sentiment_overextension"
  ]
}
