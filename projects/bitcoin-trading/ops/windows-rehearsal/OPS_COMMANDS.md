# Operator Commands (Direct Watchdog)

## P1 — MASTER_SITREP → Vault + 로컬 이중화 (워크스페이스 루트)

`docs/final`에 새 `MASTER_SITREP_*.md`를 반영한 직후 **한 번** 실행한다.

```powershell
cd C:\workspace
powershell -ExecutionPolicy Bypass -File .\scripts\titan-sync.ps1
```

- **우선순위**: P1 (High). 실행은 **지시 하달 시 즉시(On-demand)**; **주간** 무결성 점검을 권장한다.
- **동작**: 최신 SITREP → `G:\공유 드라이브\MKM_DATA_VAULT\vault\sitrep\` 및 **로컬 이중화** `F:\BACKUP\sitrep\` (F: 미연결·권한 오류 시 경고만; Vault 성공은 유지).
- **옵션**: Vault만 필요하면 `-SkipLocalBackup`. 백업 경로 변경: `-LocalBackupDir "D:\BACKUP\sitrep"`.

## On-demand V2 graph (single run)

```powershell
cd C:\workspace\projects\bitcoin-trading
py .\ops\v2\graph\runner.py --mode shadow
```

## Bootstrap

```powershell
cd C:\workspace\projects\bitcoin-trading
powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\register_direct_watchdog_task.ps1
powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\ensure_daemon_running.ps1
powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\register_kpi_snapshot_task.ps1
powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\register_brain_sync_task.ps1
```

## 30-Second Health Check

```powershell
cd C:\workspace\projects\bitcoin-trading
schtasks /Query /TN "Bitcoin-Direct-Watchdog-5min"
schtasks /Query /TN "Bitcoin-KPI-Snapshot-30min"
schtasks /Query /TN "Bitcoin-BrainSync-Daily-0805"
schtasks /Query /TN "Bitcoin-V2-Orchestrator-15min"
powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\ensure_daemon_running.ps1 -NoStart
python .\ops\windows-rehearsal\collect_kpi_snapshot.py
python .\ops\windows-rehearsal\build_brain_sync_note.py
python .\ops\v2\graph\runner.py
Get-Content .\memory\watchdog_direct.log -Tail 20
Get-Content .\memory\trading_daemon_heartbeat.txt
```

## Emergency Stop

```powershell
cd C:\workspace\projects\bitcoin-trading
ni .\memory\STOP.txt -ItemType File -Force
```

## Resume

```powershell
cd C:\workspace\projects\bitcoin-trading
del .\memory\STOP.txt
powershell -ExecutionPolicy Bypass -File .\ops\windows-rehearsal\ensure_daemon_running.ps1
```
