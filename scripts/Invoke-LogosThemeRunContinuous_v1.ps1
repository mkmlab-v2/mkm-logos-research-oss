#Requires -Version 5.1
<#
.SYNOPSIS
  LOGOS-THEME-RUN continuous loop: optional backlog expand + integrate chain (Track B, NON_GATING).

.DESCRIPTION
  1) run_logos_theme_backlog_expand_v1.py (default 1 theme per run if backlog pending)
  2) run_logos_theme_integrate_chain_v1.py (validate, cards, slice, appendix, pytest, deploy if changed)

  Stop: create docs/research/logos_metaphor_db_v1/LOGOS_THEME_RUN.stop
  State: reports/logos_theme_run_state_v1_latest.json
  Logs: reports/logos_theme_integrate_log.jsonl, reports/logos_theme_expand_log.jsonl

.PARAMETER SkipExpand
  Integrate only (no new theme JSON from backlog).

.PARAMETER UseGeminiExpand
  Pass --use-gemini to expand script when GEMINI_API_KEY is set.

.PARAMETER ExpandMaxPerRun
  Max new themes per invocation (default 1).

.PARAMETER SkipDeploy
  Skip showroom deploy/VPS sync even when theme count changes.

.PARAMETER ForceDeploy
  Always deploy after integrate.
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [switch]$SkipExpand,
    [switch]$UseGeminiExpand,
    [int]$ExpandMaxPerRun = 5,
    [switch]$AutoRefillSeed = $true,
    [int]$SeedRefillBatch = 10,
    [switch]$SkipPytest,
    [switch]$SkipDeploy,
    [switch]$ForceDeploy,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}

$stopFile = Join-Path $repoRoot "docs\research\logos_metaphor_db_v1\LOGOS_THEME_RUN.stop"
if (Test-Path -LiteralPath $stopFile) {
    Write-Host "[logos-theme-run] STOP file present — exit 0 ($stopFile)" -ForegroundColor Yellow
    exit 0
}

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$expand = Join-Path $repoRoot "scripts\run_logos_theme_backlog_expand_v1.py"
$integrate = Join-Path $repoRoot "scripts\run_logos_theme_integrate_chain_v1.py"
$backlog = Join-Path $repoRoot "docs\research\logos_metaphor_db_v1\theme_backlog_v1.jsonl"
$statePath = Join-Path $repoRoot "reports\logos_theme_run_state_v1_latest.json"

$expandedThisRun = $false

if (-not $SkipExpand) {
    if (-not (Test-Path -LiteralPath $expand)) {
        throw "Missing: $expand"
    }
    $expandArgs = @(
        $expand, "--max-per-run", "$ExpandMaxPerRun",
        "--auto-refill-seed", "--seed-refill-batch", "$SeedRefillBatch"
    )
    if ($UseGeminiExpand) { $expandArgs += "--use-gemini" }
    if ($DryRun) { $expandArgs += "--dry-run" }
    Write-Host "[logos-theme-run] expand (max=$ExpandMaxPerRun)" -ForegroundColor Cyan
    if ($DryRun) {
        Write-Host "  $py $($expandArgs -join ' ')"
    } else {
        $themeDir = Join-Path $repoRoot "docs\research\logos_metaphor_db_v1"
        $themeCountBefore = @(Get-ChildItem -LiteralPath $themeDir -Filter "theme_*.json" -File -ErrorAction SilentlyContinue).Count
        & $py @expandArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        $themeCountAfter = @(Get-ChildItem -LiteralPath $themeDir -Filter "theme_*.json" -File -ErrorAction SilentlyContinue).Count
        if ($themeCountAfter -gt $themeCountBefore) {
            $expandedThisRun = $true
        }
    }
}

$pendingBacklog = 0
if (Test-Path -LiteralPath $backlog) {
    $pendingBacklog = [int](& $py $expand --print-pending --backlog $backlog 2>$null)
}

if (-not $expandedThisRun -and $pendingBacklog -eq 0 -and -not $ForceDeploy) {
    $prevCount = -1
    if (Test-Path -LiteralPath $statePath) {
        try {
            $stateObj = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
            $prevCount = [int]$stateObj.theme_count
        } catch {
            $prevCount = -1
        }
    }
    $themeDir = Join-Path $repoRoot "docs\research\logos_metaphor_db_v1"
    $currentCount = @(Get-ChildItem -LiteralPath $themeDir -Filter "theme_*.json" -File -ErrorAction SilentlyContinue).Count
    if ($prevCount -ge 0 -and $currentCount -eq $prevCount) {
        Write-Host "[logos-theme-run] tick only (pending=0, theme_count=$currentCount unchanged) — skip heavy integrate" -ForegroundColor DarkGray
        exit 0
    }
}

if (-not (Test-Path -LiteralPath $integrate)) {
    throw "Missing: $integrate"
}

$intArgs = @($integrate, "--skip-if-unchanged")
if ($SkipPytest) { $intArgs += "--skip-pytest" }
if ($SkipDeploy) { $intArgs += "--skip-deploy" }
if ($ForceDeploy) { $intArgs += "--force-deploy" }
if ($DryRun) { $intArgs += "--dry-run" }

Write-Host "[logos-theme-run] integrate chain" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "  $py $($intArgs -join ' ')"
    exit 0
}

& $py @intArgs
exit $LASTEXITCODE
