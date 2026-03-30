# MVP Three-Bot Orchestrator

Scope:

- Athena bot: final decision coordinator
- Watchdog bot: runtime risk assessment
- Brain Sync bot: SSOT sync freshness check

## Contract

- `three_bots_contract.json`

## Runtime

- Runner: `run_mvp_three_bots.ps1`
- Main: `mvp_three_bots.py`
- Output:
  - `memory/orchestrator/mvp_three_bots_latest.json`
  - `memory/orchestrator/mvp_three_bots_YYYYMMDD.jsonl`

## Schedule (optional)

```powershell
cd C:\workspace\projects\bitcoin-trading
powershell -ExecutionPolicy Bypass -File .\ops\orchestrator\register_mvp_three_bots_task.ps1
```

Task name:

- `Bitcoin-MVP-ThreeBots-15min`
