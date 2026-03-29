#Requires -Version 5.1
<#
.SYNOPSIS
  Chain local health checks (pytest, manuscript verify, master probes). No live trading.

.DESCRIPTION
  Does NOT run fictional pipelines from narrative (e.g. refine_top_1_percent_logos.py).
  Does NOT git commit. Optional: copy latest SITREP to Vault via titan-sync.ps1.

  Usage (repo root):
    .\scripts\run_nightly_ops.ps1
    .\scripts\run_nightly_ops.ps1 -VaultSync -SkipLocalBackup
    .\scripts\run_nightly_ops.ps1 -VaultWhatIf

.NOTES
  On success, writes logs/nightly_ops_last_run.json (gitignored) for backup_workspace_mirror.ps1 -RequireNightlyPass.
  Schedule via Task Scheduler if desired. Agent sessions may end; this script keeps running on the PC.
#>
param(
    [switch]$VaultSync,
    [switch]$VaultWhatIf,
    [switch]$SkipLocalBackup
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $RepoRoot

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $Name (exit $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

$start = Get-Date

Invoke-Step 'pytest (workspace + bitcoin-trading)' {
    py -m pytest tests projects/bitcoin-trading/tests -q --tb=short
}

Invoke-Step 'verify_logos_manuscripts_integrity' {
    py scripts/verify_logos_manuscripts_integrity.py
}

Invoke-Step 'myeongni sample validate' {
    py scripts/myeongni_16_state_experiment_ledger.py validate-sample --path data/myeongni/myeongni_16_state_experiment_v1.sample.jsonl
}

Invoke-Step 'verify_master_probe_all_states' {
    py scripts/verify_master_probe_all_states.py
}

Invoke-Step 'verify_master_probe_state5' {
    py scripts/verify_master_probe_state5.py
}

if ($VaultSync -or $VaultWhatIf) {
    $tsArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $RepoRoot 'scripts\titan-sync.ps1'))
    if ($VaultWhatIf) { $tsArgs += '-WhatIf' }
    if ($SkipLocalBackup) { $tsArgs += '-SkipLocalBackup' }
    Invoke-Step 'titan-sync (SITREP to Vault)' {
        & powershell @tsArgs
    }
}

$elapsed = (Get-Date) - $start
$sec = [math]::Round($elapsed.TotalSeconds, 2)

# Fact-lock marker for downstream automation (logs/ is gitignored)
$logDir = Join-Path $RepoRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$marker = [ordered]@{
    schema           = 'nightly_ops_last_run_v1'
    ok               = $true
    finished_at_utc  = (Get-Date).ToUniversalTime().ToString('o')
    duration_sec     = $sec
    machine          = $env:COMPUTERNAME
    repo_root        = $RepoRoot
}
($marker | ConvertTo-Json -Depth 3) | Set-Content -Encoding utf8 (Join-Path $logDir 'nightly_ops_last_run.json')

Write-Host ""
Write-Host ">>> nightly_ops OK (${sec}s) | wrote logs/nightly_ops_last_run.json" -ForegroundColor Green
exit 0
