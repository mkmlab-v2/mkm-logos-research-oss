# Stops ad-hoc Chronos-Forward runs (py -c ... ChronosForwardTrainer) so only the
# SSOT CLI remains: scripts/run_chronos_forward_kospi_baseline.py
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\stop_duplicate_chronos_forward_runs.ps1
#   .\stop_duplicate_chronos_forward_runs.ps1 -WhatIf

param([switch]$WhatIf)

$ErrorActionPreference = "Stop"

$targets = Get-CimInstance Win32_Process -Filter "name='python.exe'" |
    Where-Object {
        $cl = $_.CommandLine
        if (-not $cl) { return $false }
        ($cl -match 'ChronosForwardTrainer|chronos_forward_trainer') -and
        ($cl -notmatch 'run_chronos_forward_kospi_baseline')
    }

if (-not $targets) {
    Write-Host "[stop-chronos-dupes] No duplicate Chronos trainer processes found."
    exit 0
}

foreach ($p in $targets) {
    $procId = [int]$p.ProcessId
    $line = $p.CommandLine
    if ($line.Length -gt 140) { $line = $line.Substring(0, 140) + "..." }
    if ($WhatIf) {
        Write-Host "[whatif] Would stop PID=$procId $line"
    } else {
        Write-Host "[stop-chronos-dupes] Stopping PID=$procId"
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}

if (-not $WhatIf) {
    Write-Host "[stop-chronos-dupes] Done."
}
