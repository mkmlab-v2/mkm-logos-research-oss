#Requires -Version 5.1
<#
.SYNOPSIS
  O-P30 weekly: multilens tier-matrix + preview smoke on live mkmlife (probe payment path).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-Op30MagicOrbWeeklyTierMatrix_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipDeployAssets
)

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $WorkspaceRoot
$reportPath = Join-Path $WorkspaceRoot "reports\op30_magic_orb_tier_matrix_weekly_latest.json"
$failed = @()

$phase2Args = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $WorkspaceRoot "scripts\Invoke-Op30Phase2Daily_v1.ps1"),
    "-IncludeTierMatrixSmoke",
    "-IncludeOraclePreviewSmoke",
    "-SkipLivePatrol"
)
if (-not $SkipDeployAssets) { $phase2Args += "-DeployAssets" }

Write-Host "==> O-P30 weekly tier-matrix chain" -ForegroundColor Cyan
powershell @phase2Args
$phase2Ok = ($LASTEXITCODE -eq 0)
if (-not $phase2Ok) { $failed += "phase2_tier_matrix" }

$phase2Report = Join-Path $WorkspaceRoot "reports\op30_phase2_daily_latest.json"
$tierOk = $null
$previewOk = $null
if (Test-Path -LiteralPath $phase2Report) {
    $p2 = Get-Content -LiteralPath $phase2Report -Raw -Encoding UTF8 | ConvertFrom-Json
    $tierOk = $p2.tier_matrix_smoke_ok
    $previewOk = $p2.oracle_preview_smoke_ok
    if ($tierOk -ne $true) { $failed += "tier_matrix_not_true" }
    if ($previewOk -ne $true) { $failed += "preview_smoke_not_true" }
} else {
    $failed += "phase2_report_missing"
}

[ordered]@{
    schema = "op30_magic_orb_tier_matrix_weekly_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    failed_steps = @($failed)
    phase2_ok = $phase2Ok
    tier_matrix_smoke_ok = $tierOk
    oracle_preview_smoke_ok = $previewOk
    deploy_assets = -not $SkipDeployAssets.IsPresent
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host "Wrote $reportPath failed=$($failed.Count)" -ForegroundColor $(if ($failed.Count -eq 0) { "Green" } else { "Yellow" })
if ($failed.Count -gt 0) { exit 1 }
exit 0
