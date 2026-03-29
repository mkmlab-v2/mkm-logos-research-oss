#Requires -Version 5.1
<#
.SYNOPSIS
  Robocopy C:\workspace (or repo root) to an external path. Optional: only if nightly_ops passed.

.DESCRIPTION
  - Default: incremental copy (/E), does NOT delete extra files on destination (no /MIR).
  - -Mirror: full mirror (/MIR) — DELETES files on dest that are not in source. Use with care.
  - -RequireNightlyPass: requires logs/nightly_ops_last_run.json with ok=true (from run_nightly_ops.ps1).
  - Excludes heavy/ephemeral dirs (node_modules, .venv, .git optional).

  Example:
    .\scripts\backup_workspace_mirror.ps1 -DestinationRoot 'F:\Backup\workspace' -RequireNightlyPass
    .\scripts\backup_workspace_mirror.ps1 -DestinationRoot 'E:\mirror\workspace' -IncludeGit -Mirror

.NOTES
  F:/E: paths are examples — set -DestinationRoot to your disk. No cloud upload here.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$DestinationRoot,

    [switch]$RequireNightlyPass,

    [int]$MaxNightlyAgeHours = 26,

    [switch]$Mirror,

    [switch]$IncludeGit,

    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$markerPath = Join-Path $RepoRoot 'logs\nightly_ops_last_run.json'

if ($RequireNightlyPass) {
    if (-not (Test-Path -LiteralPath $markerPath)) {
        Write-Error "Nightly marker missing: $markerPath. Run scripts\run_nightly_ops.ps1 successfully first."
        exit 2
    }
    $raw = Get-Content -LiteralPath $markerPath -Raw -Encoding utf8 | ConvertFrom-Json
    if (-not $raw.ok) {
        Write-Error "Last nightly_ops was not ok (ok=false in marker)."
        exit 2
    }
    $finished = [datetime]::Parse($raw.finished_at_utc).ToUniversalTime()
    $age = (Get-Date).ToUniversalTime() - $finished
    if ($age.TotalHours -gt $MaxNightlyAgeHours) {
        Write-Error "Nightly marker too old ($([math]::Round($age.TotalHours,1))h > ${MaxNightlyAgeHours}h). Re-run run_nightly_ops.ps1."
        exit 2
    }
    Write-Host "Nightly pass check OK (marker age $([math]::Round($age.TotalHours,2))h)" -ForegroundColor Green
}

if (-not (Test-Path -LiteralPath (Split-Path -Parent $DestinationRoot))) {
    Write-Error "Parent of destination does not exist: $DestinationRoot (create drive/folder first)."
    exit 1
}

$xd = @(
    'node_modules'
    '.venv'
    '__pycache__'
    '.pytest_cache'
    '.next'
    'dist'
    'backtest_results'
    'logs'
)
if (-not $IncludeGit) {
    $xd += '.git'
}

# /XD takes multiple directory names as separate tokens after /XD
$robArgs = @(
    $RepoRoot
    $DestinationRoot
    '/E'
    '/COPY:DAT'
    '/R:2'
    '/W:5'
    '/MT:8'
    '/NFL'
    '/NDL'
    '/NP'
    '/XD'
) + $xd

if ($Mirror) {
    $robArgs += '/MIR'
    Write-Warning 'Mirror mode: extra files under destination will be DELETED to match source.'
}

if ($WhatIf) {
    Write-Host '[WhatIf] robocopy would run:' -ForegroundColor Yellow
    Write-Host ('robocopy ' + ($robArgs -join ' '))
    exit 0
}

Write-Host "Robocopy: $RepoRoot -> $DestinationRoot" -ForegroundColor Cyan
& robocopy @robArgs
$rc = $LASTEXITCODE
# robocopy: 0-7 = success with various meanings; >=8 = error
if ($rc -ge 8) {
    Write-Error "robocopy failed with exit code $rc"
    exit $rc
}
Write-Host "robocopy finished (exit $rc)" -ForegroundColor Green
exit 0
