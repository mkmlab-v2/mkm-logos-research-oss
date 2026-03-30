# SSH/VPS 24H Independent Operation Prep

This guide prepares independent 24/7 operation on SSH/VPS for:

- Bitcoin Auto-Ops v2 (`shadow`, `execute_guarded`, `ops_digest`)
- Bible insight batch (`bible_insight_hourly`)

## 1) Preconditions

- Linux VPS with `git`, `python3`, `node/npm`
- SSH Cursor connected to VPS
- Repo path target: `/opt/bitcoin-trading`
- Optional scripture source repo path: `/opt/workspace` (for `scripts/final_prophecy_apocalypse_2026.py`)

## 2) Bootstrap VPS

```bash
cd /opt
git clone <YOUR_REPO_URL> bitcoin-trading
cd /opt/bitcoin-trading
bash ops/v2/ssh/bootstrap_vps.sh /opt/bitcoin-trading
```

## 3) Configure runtime environment

Required for execute approval guard:

```bash
export EXECUTE_APPROVAL_HMAC_KEY="<strong-secret>"
```

Optional (external memory):

```bash
export EXTERNAL_MEMORY_ENABLED=true
export EXTERNAL_MEMORY_BACKEND=mkm_local
# or: mem0 / zep
```

Optional (replace scripture insight command):

```bash
export BIBLE_INSIGHT_COMMAND="/opt/bitcoin-trading/.venv/bin/python /opt/workspace/scripts/final_prophecy_apocalypse_2026.py"
```

## 4) Start PM2 stack

```bash
cd /opt/bitcoin-trading
pm2 start ops/v2/ssh/ecosystem.ssh.config.cjs
pm2 save
pm2 startup
```

## 5) Verify health

```bash
cd /opt/bitcoin-trading
/opt/bitcoin-trading/.venv/bin/python ops/v2/reports/check_ops_health.py
cat memory/v2/ops/task_health_latest.json
pm2 status
```

## 6) Process map

- `bitcoin-v2-shadow-15min` -> every 15 min, runs `runner.py --mode shadow`
- `bitcoin-v2-execute-guarded-15min` -> every 15 min, guardrail+approval gate then execute
- `bitcoin-v2-opsdigest-30min` -> every 30 min, read-only + brief + digest + health
- `bitcoin-v2-bible-insight-hourly` -> every 60 min, scripture insight batch command
- `bitcoin-v2-logos-core-hourly` -> every 60 min, domain-neutral logos core + adapters (finance/health/life)

## 7) Operational notes

- Keep SSH/VPS runtime independent from local Cursor. Local is control-plane; VPS is execution-plane.
- Execute path is always protected by:
  - `risk_mode_guardrail`
  - optional HMAC approval token gate (`execute_approval.json`)
- For stop-all:

```bash
pm2 stop all
```

