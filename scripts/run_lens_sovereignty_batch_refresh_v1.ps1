#Requires -Version 5.1
<#
.SYNOPSIS
  Lens Sovereignty batch refresh — read SSOT artifacts, rebuild report (no daily re-fetch by default).

.DESCRIPTION
  Wrong ops: manual daily Invoke-LensSovereigntyAudit with -SkipFetch -SkipAblation loops.
  Right ops: weekly/batch chain reads accumulated training/eval artifacts; heavy recompute only on -FullRefresh.

  Default: supplementary rails + report from disk SSOT (~seconds).
  -FullRefresh: KOSPI fetch + WF ablation + horizon role eval + rails + report.
#>
param(
    [string]$DateFrom = "1996-12-11",
    [string]$DateTo = "2026-06-05",
    [string]$WorkspaceRoot = (Split-Path $PSScriptRoot -Parent),
    [switch]$FullRefresh
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$log = Join-Path $WorkspaceRoot "reports\lens_sovereignty_batch_refresh_v1.log"
function Write-Log([string]$msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')] $msg"
    Add-Content -Path $log -Value $line -Encoding utf8
    Write-Host $line
}

Write-Log "=== lens sovereignty batch refresh START full=$FullRefresh ==="

if ($FullRefresh) {
    Write-Log "full refresh: Invoke-LensSovereigntyAudit -V12"
    & powershell -NoProfile -ExecutionPolicy Bypass -File `
        (Join-Path $WorkspaceRoot "scripts\Invoke-LensSovereigntyAudit_v1.ps1") `
        -V12 -DateFrom $DateFrom -DateTo $DateTo
    if ($LASTEXITCODE -ne 0) { throw "full audit exit $LASTEXITCODE" }
}
else {
    Write-Log "batch: supplementary rails (SSOT read) + report only"
    py scripts/build_lens_sovereignty_supplementary_rails_v1_2.py
    if ($LASTEXITCODE -ne 0) { throw "supplementary rails exit $LASTEXITCODE" }
    py scripts/build_lens_sovereignty_report_v1.py `
        --blueprint docs/final/artifacts/lens_sovereignty_blueprint_v1_2.json
    if ($LASTEXITCODE -ne 0) { throw "report build exit $LASTEXITCODE" }
}

Write-Log "=== DONE exit=0 ==="
exit 0
