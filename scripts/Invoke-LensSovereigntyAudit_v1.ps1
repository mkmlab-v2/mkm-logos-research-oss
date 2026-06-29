#Requires -Version 5.1
<#
.SYNOPSIS
  Lens Sovereignty Audit v1 / v1.1 — KOSPI WF + optional role-contract eval (CPU).

.PARAMETER V11
  Use v1.1 blueprint: run three_lens_horizon_empirical_eval_v2 on full window.
#>
param(
    [string]$DateFrom = "1996-12-11",
    [string]$DateTo = "2026-06-05",
    [string]$WorkspaceRoot = (Split-Path $PSScriptRoot -Parent),
    [switch]$SkipFetch,
    [switch]$SkipAblation,
    [switch]$SkipRoleEval,
    [switch]$ReportOnly,
    [switch]$V11,
    [switch]$V12
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$log = Join-Path $WorkspaceRoot "reports\lens_sovereignty_audit_v1.log"
function Write-Log([string]$msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')] $msg"
    Add-Content -Path $log -Value $line -Encoding utf8
    Write-Host $line
}

$useV12 = [bool]$V12
$useV11 = [bool]$V11 -or $useV12
$blueprintRel = if ($useV12) {
    "docs\final\artifacts\lens_sovereignty_blueprint_v1_2.json"
} elseif ($useV11) {
    "docs\final\artifacts\lens_sovereignty_blueprint_v1_1.json"
} else {
    "docs\final\artifacts\lens_sovereignty_blueprint_v1.json"
}

Write-Log "=== Lens Sovereignty Audit START v12=$useV12 v11=$useV11 report_only=$ReportOnly ==="

if (-not $ReportOnly) {
    if (-not $SkipFetch) {
        Write-Log "fetch KOSPI OHLCV (--start $DateFrom)"
        py scripts/fetch_kospi_yfinance_csv.py --start $DateFrom
        if ($LASTEXITCODE -ne 0) { throw "fetch_kospi exit $LASTEXITCODE" }
    }
    else {
        Write-Log "SKIP fetch"
    }

    if (-not $SkipAblation) {
        Write-Log "Invoke-KospiLensAblationWalkforward (SkipJsonlBuild)"
        & powershell -NoProfile -ExecutionPolicy Bypass -File `
            (Join-Path $WorkspaceRoot "scripts\Invoke-KospiLensAblationWalkforward_v1.ps1") `
            -DateFrom $DateFrom `
            -DateTo $DateTo `
            -SkipJsonlBuild `
            -BuildSnapshotVsWalkforwardSummary
        if ($LASTEXITCODE -ne 0) { throw "ablation chain exit $LASTEXITCODE" }
    }
    else {
        Write-Log "SKIP ablation"
    }

    if ($useV11 -and -not $SkipRoleEval) {
        Write-Log "run_three_lens_horizon_empirical_eval_v2 ($DateFrom .. $DateTo)"
        py scripts/run_three_lens_horizon_empirical_eval_v2.py `
            --instrument kospi `
            --date-from $DateFrom `
            --date-to $DateTo
        if ($LASTEXITCODE -ne 0) { throw "horizon eval v2 exit $LASTEXITCODE" }
    }
    elseif ($useV11) {
        Write-Log "SKIP role eval (SkipRoleEval)"
    }

    if ($useV12) {
        Write-Log "build_lens_sovereignty_supplementary_rails_v1_2"
        py scripts/build_lens_sovereignty_supplementary_rails_v1_2.py
        if ($LASTEXITCODE -ne 0) { throw "supplementary rails exit $LASTEXITCODE" }
    }
}

Write-Log "build_lens_sovereignty_report_v1 blueprint=$blueprintRel"
py scripts/build_lens_sovereignty_report_v1.py --blueprint $blueprintRel
if ($LASTEXITCODE -ne 0) { throw "report build exit $LASTEXITCODE" }

Write-Log "=== DONE exit=0 ==="
exit 0
