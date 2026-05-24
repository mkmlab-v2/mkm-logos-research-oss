#Requires -Version 5.1
<#
.SYNOPSIS
  Drain completion catalog: append all pending seeds, then expand+integrate in batches until done.
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [string]$CatalogPath = "scripts/data/logos_theme_completion_catalog_v1.json",
    [int]$BatchSize = 20,
    [int]$MaxRounds = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$append = Join-Path $repoRoot "scripts\append_logos_theme_seed_completion_v1.py"
$continuous = Join-Path $repoRoot "scripts\Invoke-LogosThemeRunContinuous_v1.ps1"
$statePath = Join-Path $repoRoot "reports\logos_theme_run_state_v1_latest.json"

Write-Host "[logos-completion] append catalog (--all) $CatalogPath" -ForegroundColor Cyan
& $py $append --all --catalog $CatalogPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$round = 0
while ($round -lt $MaxRounds) {
    $round++
    $before = 0
    if (Test-Path -LiteralPath $statePath) {
        $before = [int](Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json).theme_count
    }
    Write-Host "[logos-completion] round $round expand+integrate (max=$BatchSize)" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $continuous `
        -WorkspaceRoot $repoRoot -ExpandMaxPerRun $BatchSize -SeedRefillBatch $BatchSize
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $after = [int](Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json).theme_count
    $delta = $after - $before
    Write-Host "[logos-completion] theme_count $before -> $after (delta $delta)" -ForegroundColor Green
    if ($delta -le 0) {
        Write-Host "[logos-completion] no new themes — done" -ForegroundColor Yellow
        break
    }
}

$pending = & $py (Join-Path $repoRoot "scripts\run_logos_theme_backlog_expand_v1.py") --print-pending 2>&1
Write-Host "[logos-completion] backlog pending: $pending"
Write-Host "[logos-completion] burst finished" -ForegroundColor Green
