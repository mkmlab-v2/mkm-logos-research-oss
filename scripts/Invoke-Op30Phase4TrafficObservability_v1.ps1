#Requires -Version 5.1
<#
.SYNOPSIS
  O-P30 Phase4 open-beta traffic observability: live probe (append history) + summary JSON.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipProbe,
    [switch]$IncludeSection11
)

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }
$reportPath = Join-Path $WorkspaceRoot "reports\op30_phase4_traffic_observability_latest.json"
$failed = @()

if ($IncludeSection11) {
    Write-Host "==> section11 readiness" -ForegroundColor Cyan
    & $py scripts/check_mkmlife_section11_readiness_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "section11" }
}

if (-not $SkipProbe) {
    Write-Host "==> live probe (history append)" -ForegroundColor Cyan
    & $py scripts/probe_mkmlife_magic_orb_live_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "probe" }
}

Write-Host "==> CF analytics (optional token)" -ForegroundColor Cyan
& $py scripts/probe_mkmlife_cf_traffic_v1.py
if ($LASTEXITCODE -ne 0) { $failed += "cf_traffic_probe" }

Write-Host "==> traffic summary" -ForegroundColor Cyan
& $py scripts/build_magic_orb_open_beta_traffic_summary_v1.py
if ($LASTEXITCODE -ne 0) { $failed += "traffic_summary" }

$summaryPath = Join-Path $WorkspaceRoot "reports\magic_orb_open_beta_traffic_summary_latest.json"
$summary = $null
if (Test-Path $summaryPath) {
    $summary = Get-Content -LiteralPath $summaryPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

[ordered]@{
    schema = "op30_phase4_traffic_observability_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    failed_steps = @($failed)
    history_entries = if ($summary) { $summary.history_entries_total } else { $null }
    last_7d_all_ok_rate = if ($summary) { $summary.windows.last_7d.all_ok_rate } else { $null }
    streak_all_ok = if ($summary) { $summary.streak_all_ok_from_latest } else { $null }
    payment_e2e_deferred = $true
    phase = "O-P30-Phase4-traffic-observability"
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host "Wrote $reportPath failed=$($failed.Count)" -ForegroundColor $(if ($failed.Count -eq 0) { "Green" } else { "Yellow" })
if ($failed.Count -gt 0) { exit 1 }
exit 0
