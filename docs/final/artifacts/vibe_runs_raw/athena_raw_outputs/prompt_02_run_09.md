# prompt_02_run_09.md

Runtime: Gemini JAMS (Athena persona)

Final Action: HOLD
Confidence: 0.65
Risk Flags: [Leverage Risk, Macro Headwinds, Geopolitical Risk]

Evidence pointers:
- external_inputs_jsonl: docs/final/artifacts/vibe_external_inputs_latest.jsonl

Rationale:
- Macro environment shows headwinds with rising US10Y and DXY, typically negative for risk assets.
- Geopolitical risk is elevated, adding a layer of uncertainty.
- Crypto sentiment (FGI) is in "Greed" territory, while VIX is decreasing, indicating broader risk appetite.
- BTC microstructure shows increasing leverage (rising Funding Rate and Open Interest), which can precede volatility.
- Conflicting signals warrant a cautious stance, acknowledging current sentiment but monitoring underlying risks.
- Current conditions do not yet indicate an immediate need to reduce exposure, but risks are accumulating.

Notes:
- Uncertainty exists regarding the exact trigger point for a potential deleveraging event given high leverage.
- The impact of elevated geopolitical risk on crypto markets is not always direct or immediate.

Flip conditions:
- **To WATCH:** If DXY exceeds 106, US10Y rises above 4.4%, or GEO_RISK_KEYWORD_SCORE surpasses 0.8.
- **To REDUCE:** If BTC_OPEN_INTEREST shows rapid unwinding alongside significant negative funding rates, or if BTC price breaks key support levels indicating a deleveraging cascade.

Missing evidence:
- BTC spot price action and technical analysis.
- Broader equity market performance (e.g., SPX).
- On-chain data (e.g., exchange net flows, stablecoin supply ratio).
