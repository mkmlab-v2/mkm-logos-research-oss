#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot Hostinger full-exit automation: DNS snapshot → stabilization → rollback template from snapshot → dry-run → registrar readiness → decommission gate.

.DESCRIPTION
  Read-only except: appends stabilization JSONL, writes reports and derived rollback_dns_template_from_snapshot_v1.json.
  Does not cancel Hostinger or transfer registrar.

.PARAMETER SkipCloudflareHealth
  Passes through to stabilization (no CLOUDFLARE_API_TOKEN needed for that leg).

.PARAMETER MinStabilizationCycles
  Passed to Invoke-HostingerDecommissionGate_v1.ps1.

.PARAMETER IncludeDuplicateAudit
  Passed to decommission gate.

.PARAMETER SkipGate
  Skip final decommission gate (snapshot + stabilize + rollback build/dry-run + registrar only).

.PARAMETER RegisterWeeklyTask
  If set, runs Register-HostingerFullExitStabilizationWeeklyTask_v1.ps1 after successful chain (same SkipCloudflareHealth as this run).
#>
param(
    [switch]$SkipCloudflareHealth,
    [int]$MinStabilizationCycles = 0,
    [switch]$IncludeDuplicateAudit,
    [switch]$SkipGate,
    [switch]$RegisterWeeklyTask
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$worst = 0

function Step-Exit {
    param([int]$Code)
    if ($Code -gt $worst) { $script:worst = $Code }
}

$dnsSnap = Join-Path $PSScriptRoot "Invoke-HostingerExitDnsSnapshot_v1.ps1"
$stab = Join-Path $PSScriptRoot "Invoke-HostingerFullExitStabilizationCycle_v1.ps1"
$buildRb = Join-Path $PSScriptRoot "Build-HostingerRollbackTemplateFromSnapshot_v1.ps1"
$rbDry = Join-Path $PSScriptRoot "Invoke-HostingerExitRollbackRehearsalDryRun_v1.ps1"
$reg = Join-Path $PSScriptRoot "Invoke-HostingerRegistrarTransferReadiness_v1.ps1"
$gate = Join-Path $PSScriptRoot "Invoke-HostingerDecommissionGate_v1.ps1"
$regTask = Join-Path $PSScriptRoot "Register-HostingerFullExitStabilizationWeeklyTask_v1.ps1"

Write-Host "=== [1/6] DNS snapshot ===" -ForegroundColor Cyan
& $dnsSnap
Step-Exit $LASTEXITCODE

Write-Host "=== [2/6] Stabilization cycle ===" -ForegroundColor Cyan
if ($SkipCloudflareHealth) {
    & $stab -SkipCloudflareHealth
}
else {
    & $stab
}
Step-Exit $LASTEXITCODE

Write-Host "=== [3/6] Build rollback template from snapshot ===" -ForegroundColor Cyan
& $buildRb
Step-Exit $LASTEXITCODE

$derivedRb = Join-Path $PSScriptRoot "data\hostinger_full_exit\rollback_dns_template_from_snapshot_v1.json"
Write-Host "=== [4/6] Rollback rehearsal (derived template) ===" -ForegroundColor Cyan
& $rbDry -TemplateJson $derivedRb
Step-Exit $LASTEXITCODE

Write-Host "=== [5/6] Registrar transfer readiness ===" -ForegroundColor Cyan
& $reg
Step-Exit $LASTEXITCODE

if (-not $SkipGate) {
    Write-Host "=== [6/6] Decommission gate ===" -ForegroundColor Cyan
    if ($IncludeDuplicateAudit) {
        & $gate -MinStabilizationCycles $MinStabilizationCycles -IncludeDuplicateAudit
    }
    else {
        & $gate -MinStabilizationCycles $MinStabilizationCycles
    }
    Step-Exit $LASTEXITCODE
}
else {
    Write-Host "=== [6/6] Decommission gate (skipped) ===" -ForegroundColor Yellow
}

if ($RegisterWeeklyTask -and $worst -eq 0) {
    Write-Host "=== Register weekly stabilization task ===" -ForegroundColor Cyan
    if ($SkipCloudflareHealth) {
        & $regTask -SkipCloudflareHealth
    }
    else {
        & $regTask
    }
    Step-Exit $LASTEXITCODE
}

$sumPath = Join-Path $root "reports\hostinger_full_exit_automation_chain_latest.json"
$sum = [ordered]@{
    schema           = "hostinger_full_exit_automation_chain_v1"
    generated_at_utc = [datetime]::UtcNow.ToString("o")
    worst_exit_code  = $worst
    skip_cloudflare  = [bool]$SkipCloudflareHealth
    skip_gate        = [bool]$SkipGate
    register_weekly  = [bool]$RegisterWeeklyTask
    artifacts        = [ordered]@{
        dns_snapshot      = (Join-Path $root "reports\hostinger_exit_dns_snapshot_latest.json")
        stabilization_log = (Join-Path $root "reports\hostinger_full_exit_stabilization_log.jsonl")
        rollback_derived  = $derivedRb
        rollback_rehearsal = (Join-Path $root "reports\hostinger_exit_rollback_rehearsal_latest.json")
        registrar         = (Join-Path $root "reports\hostinger_registrar_transfer_readiness_latest.json")
        decommission_gate   = if ($SkipGate) { $null } else { (Join-Path $root "reports\hostinger_decommission_gate_latest.json") }
    }
}
$dir = Split-Path -Parent $sumPath
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
($sum | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $sumPath -Encoding UTF8
Write-Host "Wrote $sumPath" -ForegroundColor Green
Write-Host "Chain worst exit code: $worst" -ForegroundColor $(if ($worst -eq 0) { "Green" } else { "Red" })

exit $worst
