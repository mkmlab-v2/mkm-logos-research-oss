#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot 24h alert check for panel promotion candidate.

.DESCRIPTION
  Checks three alert rules against latest artifacts:
  1) price_directional_hit_rate >= 0.60
  2) panel strict_passed && auto_promote_ready == true
  3) shared safety gates passed (btc_csv/model/non-neutral-cap)

  Exit code:
    0 = all pass
    1 = one or more alerts failed

  Webhook (failure only): PROPHECY_PANEL_24H_ALERT_WEBHOOK_URL, else OPS_ALARM_WEBHOOK_URL.
  Use -SkipWebhook to suppress POST (e.g. CI without secrets).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [double]$MinHitRate = 0.60,
    [string]$OutJson = "",
    [switch]$AppendLog,
    [switch]$SkipWebhook
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

$hitRate = [double]($hit.metrics.price_directional_hit_rate)
$a1Pass = $hitRate -ge $MinHitRate

$strictPassed = [bool]$panel.strict_passed
$autoReady = [bool]$panel.auto_promote_ready
$a2Pass = $strictPassed -and $autoReady

$sharedGates = @()
if ($panel.tracks -and $panel.tracks.shared -and $panel.tracks.shared.gates) {
    $sharedGates = @($panel.tracks.shared.gates)
}

function Gate-Passed([string]$GateId) {
    $g = $sharedGates | Where-Object { $_.gate_id -eq $GateId } | Select-Object -First 1
    if (-not $g) { return $false }
    return [bool]$g.passed
}

$a3Pass = (Gate-Passed "score_neutral_ratio_cap") -and (Gate-Passed "hypothesis_non_stub_model") -and (Gate-Passed "score_btc_csv_input_present")

$allPass = $a1Pass -and $a2Pass -and $a3Pass

$result = [ordered]@{
    schema = "prophecy_panel_24h_alert_check_v1"
    checked_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    inputs = [ordered]@{
        hit_rate_path = $hitPath
        panel_gate_path = $panelPath
        min_hit_rate = $MinHitRate
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
            score_neutral_ratio_cap_passed = (Gate-Passed "score_neutral_ratio_cap")
            hypothesis_non_stub_model_passed = (Gate-Passed "hypothesis_non_stub_model")
            score_btc_csv_input_present_passed = (Gate-Passed "score_btc_csv_input_present")
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
    $webhook = $env:PROPHECY_PANEL_24H_ALERT_WEBHOOK_URL
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:OPS_ALARM_WEBHOOK_URL
    }
    if (-not [string]::IsNullOrWhiteSpace($webhook)) {
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
        Write-Host "Webhook alert skipped: no PROPHECY_PANEL_24H_ALERT_WEBHOOK_URL or OPS_ALARM_WEBHOOK_URL" -ForegroundColor DarkGray
    }
}

exit 1
