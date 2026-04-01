# MKM TOE Gate Policy v1

## Score bands (proposal)
- 0 to <30: DEFENSE mode (risk-off baseline)
- 30 to <60: CAUTION mode (partial exposure)
- 60 to <80: ACTIVE mode (controlled risk-on)
- 80 to 100: HIGH-CONV mode (still requires runtime risk guardrails)

## Non-negotiable runtime guards
- daily_loss_cap must remain enabled.
- slippage and position cap must remain enabled.
- if quality gate is HOLD, force CAUTION or DEFENSE.

## Fact-safe publication rule
- publish as probabilistic support signal only.
- never claim deterministic certainty.

