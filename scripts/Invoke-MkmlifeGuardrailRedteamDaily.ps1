param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipAlert,
    [string]$AlertSeverity = "critical",
    [string]$AlertChannel = "#ops-alerts",
    [string]$AlertMention = "@here"
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$redteamScript = Join-Path $WorkspaceRoot "scripts\run_mkmlife_guardrail_redteam_v1.py"
$gateScript = Join-Path $WorkspaceRoot "scripts\check_mkmlife_guardrail_redteam_gate_v1.py"
$gateOut = Join-Path $WorkspaceRoot "docs\final\artifacts\mkmlife_guardrail_redteam_gate_latest.json"

if (-not (Test-Path -LiteralPath $redteamScript)) { throw "Missing script: $redteamScript" }
if (-not (Test-Path -LiteralPath $gateScript)) { throw "Missing script: $gateScript" }

Write-Host "==> run_mkmlife_guardrail_redteam_v1.py"
py $redteamScript
if ($LASTEXITCODE -ne 0) { throw "Redteam run failed with exit code $LASTEXITCODE" }

Write-Host "==> check_mkmlife_guardrail_redteam_gate_v1.py"
py $gateScript
$gateExit = $LASTEXITCODE
$gateStatus = "UNKNOWN"
if (Test-Path -LiteralPath $gateOut) {
    try {
        $gateDocTmp = Get-Content -LiteralPath $gateOut -Raw | ConvertFrom-Json
        $gateStatus = [string]$gateDocTmp.status
    }
    catch {
        $gateStatus = "UNKNOWN"
    }
}

if ($SkipAlert) {
    if ($gateExit -ne 0) { exit $gateExit }
    exit 0
}

$webhook = $env:MKM_GUARDRAIL_ALERT_WEBHOOK_URL
if ([string]::IsNullOrWhiteSpace($webhook)) {
    $webhook = $env:OPS_ALARM_WEBHOOK_URL
}

if ((Test-Path -LiteralPath $gateOut) -and (-not [string]::IsNullOrWhiteSpace($webhook)) -and ($gateStatus -in @("WARN", "HOLD"))) {
    $doc = Get-Content -LiteralPath $gateOut -Raw | ConvertFrom-Json
    $hardReasons = @($doc.hard_reasons)
    $warnReasons = @($doc.warn_reasons)
    $reasons = if ($hardReasons.Count -gt 0) { $hardReasons } else { $warnReasons }
    $reasonText = if ($reasons.Count -gt 0) { ($reasons -join "; ") } else { "unknown_gate_degradation" }
    $computedSeverity = if ($gateStatus -eq "HOLD") { "critical" } else { "warning" }
    $effectiveSeverity = if ([string]::IsNullOrWhiteSpace($AlertSeverity)) { $computedSeverity } else { $AlertSeverity }
    $summaryText = if ($gateStatus -eq "HOLD") {
        "MKM mkmlife redteam HOLD detected (auto release block)"
    } else {
        "MKM mkmlife redteam WARN detected (degradation alert)"
    }
    $messageText = if ($gateStatus -eq "HOLD") {
        "$AlertMention mkmlife redteam HOLD: $reasonText"
    } else {
        "$AlertMention mkmlife redteam WARN: $reasonText"
    }
        $payload = [ordered]@{
            event = "mkmlife_guardrail_redteam_alarm"
            ts_utc = (Get-Date).ToUniversalTime().ToString("o")
            severity = $effectiveSeverity
            channel = $AlertChannel
            mention = $AlertMention
            summary = $summaryText
            message = $messageText
            status = $doc.status
            reasons = $reasons
            metrics = $doc.metrics
            gate_path = $gateOut
        }
        $json = $payload | ConvertTo-Json -Depth 8 -Compress
    try {
        $null = Invoke-RestMethod -Uri $webhook -Method Post -Body $json -ContentType "application/json; charset=utf-8" -TimeoutSec 30
        Write-Host "[mkmlife-guardrail] ALERT SENT ($gateStatus)" -ForegroundColor Yellow
    }
    catch {
        Write-Host "[mkmlife-guardrail] ALERT FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }
}

if ($gateStatus -eq "HOLD" -or $gateExit -ne 0) {
    throw "mkmlife guardrail gate failed (status=$gateStatus)"
}
if ($gateStatus -eq "WARN") {
    Write-Host "[mkmlife-guardrail] WARN (degraded but non-blocking)" -ForegroundColor Yellow
    exit 0
}

Write-Host "[mkmlife-guardrail] PASS" -ForegroundColor Green
exit 0

