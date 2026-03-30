# Windows 7-Day Autonomous Rehearsal Runbook

Date: 2026-03-24  
Scope: `projects/bitcoin-trading` single Windows machine rehearsal

## Objective

Validate 24/7 supervised autonomy with four controls:

1. process survival (direct watchdog + scheduled task)
2. stale-process recovery (`watchdog + heartbeat`)
3. operator emergency stop (`STOP.txt`)
4. observable run status (`memory/*.json`)

## Stack Components

- Daemon entrypoint: `scripts/start_24h_daemon.py`
- Direct watchdog: `ops/windows-rehearsal/ensure_daemon_running.ps1`
- Direct watchdog register: `ops/windows-rehearsal/register_direct_watchdog_task.ps1`
- Daemon heartbeat file: `memory/trading_daemon_heartbeat.txt`
- Kill switch file: `memory/STOP.txt`

## Direct Mode (Primary Path)

Use direct watchdog mode as the default operating path in this environment:

```powershell
cd C:\workspace\projects\bitcoin-trading
powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\register_direct_watchdog_task.ps1
```

Direct watchdog components:

- `ops/windows-rehearsal/ensure_daemon_running.ps1`
- `ops/windows-rehearsal/register_direct_watchdog_task.ps1`
- `ops/windows-rehearsal/collect_kpi_snapshot.py`
- `ops/windows-rehearsal/register_kpi_snapshot_task.ps1`
- `ops/windows-rehearsal/build_brain_sync_note.py`
- `ops/windows-rehearsal/register_brain_sync_task.ps1`

Behavior:

- Every 5 minutes, ensures daemon process is running.
- If heartbeat is stale, it restarts daemon process.
- If `memory/STOP.txt` exists, it force-stops daemon and does not restart.

## Day 0 Bootstrap

```powershell
cd C:\workspace\projects\bitcoin-trading
powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\register_direct_watchdog_task.ps1
powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\ensure_daemon_running.ps1
powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\register_kpi_snapshot_task.ps1
powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\register_brain_sync_task.ps1
```

## Operational Checks (Daily)

```powershell
schtasks /Query /TN "Bitcoin-Direct-Watchdog-5min"
schtasks /Query /TN "Bitcoin-KPI-Snapshot-30min"
schtasks /Query /TN "Bitcoin-BrainSync-Daily-0805"
powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\ensure_daemon_running.ps1 -NoStart
python .\ops\windows-rehearsal\collect_kpi_snapshot.py
python .\ops\windows-rehearsal\build_brain_sync_note.py
Get-Content .\memory\watchdog_direct.log -Tail 30
```

Expected:

- heartbeat timestamp keeps moving
- `memory/trading_daemon_status.json` updates
- watchdog prints `Healthy`

## Kill Switch Drill

```powershell
ni .\memory\STOP.txt -ItemType File -Force
```

Expected:

- daemon exits safely
- watchdog refuses restart while STOP exists

Recovery:

```powershell
del .\memory\STOP.txt
powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\ensure_daemon_running.ps1
```

## Incident Playbook

### Symptom: Process alive but no heartbeat update

1. Run watchdog once manually (non-dry):
   `powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\ensure_daemon_running.ps1`
2. Check `memory/watchdog_direct.log` for restart reason.
3. If repeated, raise stale threshold temporarily and inspect exchange/API latency.

### Symptom: Restart loop

1. `Get-Content .\memory\watchdog_direct.log -Tail 200`
2. Disable trading mode in env if risk detected.
3. Create `STOP.txt` and hold until root cause is resolved.

## Success Criteria for 7-Day Rehearsal

- uptime >= 99%
- no orphan process accumulation
- watchdog restart events <= 3/day
- kill switch drill success 100%
- zero uncontrolled live-trading action during STOP state

## NotebookLM Sync (Minimum Loop)

Daily brain sync markdown is generated automatically at:

- `memory/brain_sync/latest.md`
- `memory/brain_sync/brain_sync_YYYYMMDD.md`

Use this file as the daily source when updating NotebookLM SSOT notes.
