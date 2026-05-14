#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly chain: sweep Aramaic MVP alert thresholds → apply recommended artifact.

.DESCRIPTION
  B-track / research_only promotion path; does not touch trading. SSOT: CONSTITUTION Aramaic MVP table.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $WorkspaceRoot)) {
    throw "WorkspaceRoot not found: $WorkspaceRoot"
}

Push-Location $WorkspaceRoot
try {
    & py "scripts\sweep_aramaic_mvp_alert_thresholds_v1.py"
    if ($LASTEXITCODE -ne 0) { throw "sweep_aramaic_mvp_alert_thresholds_v1.py exited $LASTEXITCODE" }

    $sweepJson = Join-Path $WorkspaceRoot "docs\final\artifacts\aramaic_mvp_alert_threshold_sweep_latest.json"
    & py "scripts\apply_aramaic_mvp_alert_threshold_recommendation_v1.py" --sweep-json $sweepJson
    if ($LASTEXITCODE -ne 0) { throw "apply_aramaic_mvp_alert_threshold_recommendation_v1.py exited $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Write-Host "[DONE] Aramaic MVP threshold weekly chain (sweep -> apply)." -ForegroundColor Green
