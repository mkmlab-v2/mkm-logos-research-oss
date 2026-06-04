# Register aux PC watchdog (run ONCE on DESKTOP-AP1DC83 as admin).
param(
    [string]$TaskName = "MKM_NextGen_AuxWatchdog",
    [string]$ShareRoot = "Z:\nextgen_cpu_aux",
    [int]$IntervalMinutes = 2
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$watchdog = Join-Path $ShareRoot "run_nextgen_aux_watchdog_v1.py"
if (-not (Test-Path $watchdog)) {
    Write-Error "Missing $watchdog — run deploy from main first."
}

$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw "Python not found on aux PC" }

$tr = "`"$py`" `"$watchdog`" --share-root `"$ShareRoot`" --once"
$existing = schtasks /Query /TN $TaskName 2>$null
if ($LASTEXITCODE -eq 0) {
    schtasks /Delete /TN $TaskName /F | Out-Null
}

schtasks /Create /TN $TaskName /TR $tr /SC MINUTE /MO $IntervalMinutes /F
Write-Host "Registered: $TaskName every $IntervalMinutes min -> $tr"
schtasks /Query /TN $TaskName /V /FO LIST | Select-String "TaskName|Task To Run|Status|Next Run"
