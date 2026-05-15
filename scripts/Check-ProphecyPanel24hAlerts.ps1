#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot 24h alert check for panel promotion candidate.

.DESCRIPTION
  Checks three alert rules against latest artifacts:
  1) price_directional_hit_rate >= 0.60
  2) panel strict_passed && auto_promote_ready == true
  3) shared safety gates passed (btc_csv/model/non-neutral-cap)

  Gate resolution: rows are matched in tracks.shared.gates then root gates[]. If a gate_id is
  absent (e.g. btc_only_crossassist emits only score_btc_csv in the shared slice) but
  shared_all_gates_passed is true, that gate is treated as passed via aggregate (not missing=false).

  Exit code:
    0 = all pass
    1 = one or more alerts failed

  Webhook (failure only): PROPHECY_PANEL_24H_ALERT_WEBHOOK_URL, else OPS_ALARM_WEBHOOK_URL.
  Default routing: POST only when ALERT_1 (hit rate) or ALERT_3 (structural shared gates) fails —
  ALERT_2-only failure (strict_passed / auto_promote_ready) does not POST (reduces noise; exit code still 1).
  Use -IncludeAlert2InWebhook to restore legacy "webhook on any alert failure".
  Use -SkipWebhook to suppress POST (e.g. CI without secrets).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [double]$MinHitRate = 0.60,
    [string]$OutJson = "",
    [switch]$AppendLog,
    [switch]$SkipWebhook,
    [switch]$IncludeAlert2InWebhook
)

$ErrorActionPreference = "Stop"

function Read-JsonFile {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing required file: $Path"
    }
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

$hitPath = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_hit_rate_eval_latest.json"
$panelPath = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_promotion_gates_v1_panel_calibrated_latest.json"

$hit = Read-JsonFile -Path $hitPath
$panel = Read-JsonFile -Path $panelPath

if (-not $hit.metrics) {
    throw "prophecy_hit_rate_eval_latest.json missing metrics (required for ALERT_1)"
}
if ($null -eq $hit.metrics.price_directional_hit_rate) {
    throw "prophecy_hit_rate_eval_latest.json missing metrics.price_directional_hit_rate"
}
$hitRate = [double]($hit.metrics.price_directional_hit_rate)
$a1Pass = $hitRate -ge $MinHitRate

$strictPassed = [bool]$panel.strict_passed
$autoReady = [bool]$panel.auto_promote_ready
$a2Pass = $strictPassed -and $autoReady

$sharedGatesList = @()
if ($panel.tracks -and $panel.tracks.shared -and $panel.tracks.shared.gates) {
    $sharedGatesList = @($panel.tracks.shared.gates)
}
$rootGatesList = @()
if (($panel.PSObject.Properties.Name -contains 'gates') -and $panel.gates) {
    $rootGatesList = @($panel.gates)
}
$mergedGates = [System.Collections.Generic.List[object]]::new()
foreach ($g in $sharedGatesList) { [void]$mergedGates.Add($g) }
foreach ($g in $rootGatesList) { [void]$mergedGates.Add($g) }

$sharedAllPassed = $false
if ($null -ne $panel.shared_all_gates_passed) {
    $sharedAllPassed = [bool]$panel.shared_all_gates_passed
}
$trackSharedAllPassed = $false
if ($panel.tracks -and $panel.tracks.shared -and ($null -ne $panel.tracks.shared.all_gates_passed)) {
    $trackSharedAllPassed = [bool]$panel.tracks.shared.all_gates_passed
}

function Resolve-StructuralGate {
    param([Parameter(Mandatory = $true)][string]$GateId)
    foreach ($x in $mergedGates) {
        if ("$($x.gate_id)" -ne $GateId) { continue }
        return @{
            passed = [bool]$x.passed
            mode   = "row"
        }
    }
    if ($sharedAllPassed -and $trackSharedAllPassed) {
        return @{ passed = $true; mode = "aggregate_tracks_shared" }
    }
    if ($sharedAllPassed) {
        return @{ passed = $true; mode = "aggregate_shared_all" }
    }
    return @{ passed = $false; mode = "missing" }
}

$rNeutral = Resolve-StructuralGate "score_neutral_ratio_cap"
$rModel = Resolve-StructuralGate "hypothesis_non_stub_model"
$rBtcCsv = Resolve-StructuralGate "score_btc_csv_input_present"
$a3Pass = $rNeutral.passed -and $rModel.passed -and $rBtcCsv.passed

$allPass = $a1Pass -and $a2Pass -and $a3Pass

$result = [ordered]@{
    schema = "prophecy_panel_24h_alert_check_v1"
    checked_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    inputs = [ordered]@{
        hit_rate_path = $hitPath
        panel_gate_path = $panelPath
        min_hit_rate = $MinHitRate
        webhook_routing = [ordered]@{
            mode = $(if ($IncludeAlert2InWebhook) { "all_alerts" } else { "performance_and_structural_only" })
            posts_when = $(if ($IncludeAlert2InWebhook) { "any_alert_failed" } else { "alert1_or_alert3_failed" })
        }
    }
    alerts = [ordered]@{
        ALERT_1_PERFORMANCE = [ordered]@{
            passed = $a1Pass
            observed_price_directional_hit_rate = [math]::Round($hitRate, 6)
            threshold_min = $MinHitRate
        }
        ALERT_2_GATE_REGRESSION = [ordered]@{
            passed = $a2Pass
            strict_passed = $strictPassed
            auto_promote_ready = $autoReady
        }
        ALERT_3_STRUCTURAL_RISK = [ordered]@{
            passed = $a3Pass
            score_neutral_ratio_cap_passed = $rNeutral.passed
            score_neutral_ratio_cap_resolution = $rNeutral.mode
            hypothesis_non_stub_model_passed = $rModel.passed
            hypothesis_non_stub_model_resolution = $rModel.mode
            score_btc_csv_input_present_passed = $rBtcCsv.passed
            score_btc_csv_input_present_resolution = $rBtcCsv.mode
        }
    }
    overall_passed = $allPass
}

$resultJson = $result | ConvertTo-Json -Depth 8
Write-Output $resultJson

$outPath = $OutJson.Trim()
if (-not [string]::IsNullOrWhiteSpace($outPath)) {
    $dir = Split-Path -Parent $outPath
    if (-not [string]::IsNullOrWhiteSpace($dir) -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $resultJson | Set-Content -LiteralPath $outPath -Encoding utf8
    Write-Host "WROTE: $outPath" -ForegroundColor Green
}

if ($AppendLog) {
    $logDir = Join-Path $WorkspaceRoot "reports"
    if (-not (Test-Path -LiteralPath $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    $logPath = Join-Path $logDir "prophecy_panel_24h_alerts_log.jsonl"
    $line = ($resultJson -replace "`r?`n", " ").Trim()
    Add-Content -LiteralPath $logPath -Value $line -Encoding utf8
    Write-Host "APPENDED: $logPath" -ForegroundColor DarkGray
}

if ($allPass) {
    exit 0
}

if (-not $SkipWebhook) {
    $webhookPost = $false
    if ($IncludeAlert2InWebhook) {
        $webhookPost = $true
    }
    else {
        $webhookPost = (-not $a1Pass) -or (-not $a3Pass)
    }

    $webhook = $env:PROPHECY_PANEL_24H_ALERT_WEBHOOK_URL
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:OPS_ALARM_WEBHOOK_URL
    }
    if (-not [string]::IsNullOrWhiteSpace($webhook)) {
        if ($webhookPost) {
            $payload = [ordered]@{
                event = "prophecy_panel_24h_alert_check_failed"
                ts_utc = (Get-Date).ToUniversalTime().ToString("o")
                workspace = $WorkspaceRoot
                overall_passed = $false
                check = ($result | ConvertTo-Json -Depth 10 | ConvertFrom-Json)
            }
            $body = $payload | ConvertTo-Json -Depth 12 -Compress
            try {
                $null = Invoke-RestMethod -Uri $webhook -Method Post -Body $body -ContentType "application/json; charset=utf-8" -TimeoutSec 30
                Write-Host "Webhook alert sent: prophecy_panel_24h_alert_check_failed" -ForegroundColor Yellow
            }
            catch {
                Write-Warning "Webhook alert failed: $($_.Exception.Message)"
            }
        }
        else {
            Write-Host "Webhook alert skipped: only ALERT_2 failed (strict_passed / auto_promote_ready). Exit code remains 1. Use -IncludeAlert2InWebhook to POST." -ForegroundColor DarkCyan
        }
    }
    else {
        Write-Host "Webhook alert skipped: no PROPHECY_PANEL_24H_ALERT_WEBHOOK_URL or OPS_ALARM_WEBHOOK_URL" -ForegroundColor DarkGray
    }
}

exit 1
