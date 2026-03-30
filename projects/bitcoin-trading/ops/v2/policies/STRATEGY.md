# STRATEGY (v2)

## Mission
Build a resilient autonomous operations core for Bitcoin trading using stateful orchestration and strict safety guardrails.

## Guardrails
- Runtime orders can be automated.
- Strategy/code/risk-limit changes require explicit human approval.
- Kill switch (`memory/STOP.txt`) has highest priority.

## Execution Modes
- `read-only`: observe and decide only
- `shadow`: simulate actions without execution
- `execute`: execution path (requires sentinel + human gate)
