# MKM 11-Axis Report Template (Fact-Lock)

Use this template for all 11-axis advanced reports.
Every numbered axis line MUST include one evidence tier tag:
`[FACT]` / `[ESTIMATE]` / `[HYPO]`.

## Header
- report_id: `<id>`
- generated_at_utc: `<ISO8601>`
- scope: `<instrument / period / regime>`
- policy: `Most Conservative Wins`

## Axis 1 — Pathology
- verdict: `[FACT|ESTIMATE|HYPO] <content>`

## Axis 2 — Temperament
- verdict: `[FACT|ESTIMATE|HYPO] <content>`

## Axis 3 — Coupling
- verdict: `[FACT|ESTIMATE|HYPO] <content>`

## Axis 4 — Transition Dynamics
- verdict: `[FACT|ESTIMATE|HYPO] <content>`

## Axis 5 — Mass Sentiment
- verdict: `[FACT|ESTIMATE|HYPO] <content>`

## Axis 6 — Metal-Fire Equilibrium
- verdict: `[FACT|ESTIMATE|HYPO] <content>`

## Axis 7 — Survival Axis (Bomyeong)
- verdict: `[FACT|ESTIMATE|HYPO] <content>`

## Axis 8 — Strategic Pharma Vector
- verdict: `[FACT|ESTIMATE|HYPO] <content>`

## Axis 9 — Execution Friction
- verdict: `[FACT|ESTIMATE|HYPO] <content>`

## Axis 10 — Math Alignment
- verdict: `[FACT|ESTIMATE|HYPO] <content>`

## Axis 11 — Calibration Loop
- verdict: `[FACT|ESTIMATE|HYPO] <content>`

## Hard Prohibitions
- Never assert arbitrary slippage percentages without artifact evidence.
- Never assert transition probabilities without reproducible computation output.
- Never assert price levels without source-bound evidence.
- If Axis 9 or Axis 7 fails as `[FACT]`, final action MUST be `HOLD`.

## Final Decision
- action: `HOLD | WATCH | REDUCE | GO`
- reason: `<brief>`
- evidence_summary:
  - FACT count: `<n>`
  - ESTIMATE count: `<n>`
  - HYPO count: `<n>`
