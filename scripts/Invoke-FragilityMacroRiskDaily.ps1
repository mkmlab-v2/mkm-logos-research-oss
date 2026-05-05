[CmdletBinding()]
param(
    [switch]$PreferFred,
    [string]$AssetScope = "BTC-USD",
    [ValidateSet("1h", "4h", "24h", "7d")]
    [string]$Horizon = "24h",
    [string]$OutputPath = "",
    [string]$FailureLogPath = "",
    [string]$FailureWebhookUrl = "",
    [string]$GateAlertWebhookUrl = "",
    [string]$RunLogPath = "",
    [switch]$SkipFailureAlert,
    [switch]$SkipGateAlert
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Import-FragilityDailyEnvFromDotEnv {
    param([string]$Root)
    $dot = Join-Path $Root ".env"
    if (-not (Test-Path -LiteralPath $dot)) { return }
    $keysWanted = @("MKM_DAILY_CHECK_FAILURE_WEBHOOK_URL", "MKM_FRAGILITY_GATE_ALERT_WEBHOOK_URL", "OPS_ALARM_WEBHOOK_URL")
    foreach ($raw in Get-Content -LiteralPath $dot -Encoding utf8) {
        $line = $raw.Trim()
        if (-not $line -or $line.StartsWith("#")) { continue }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { continue }
        $key = $line.Substring(0, $eq).Trim()
        if ($key -notin $keysWanted) { continue }
        $val = $line.Substring($eq + 1).Trim()
        if ($val.Length -ge 2 -and (
                ($val.StartsWith([char]34) -and $val.EndsWith([char]34)) -or
                ($val.StartsWith([char]39) -and $val.EndsWith([char]39)))) {
            $val = $val.Substring(1, $val.Length - 2)
        }
        if ([string]::IsNullOrWhiteSpace($val)) { continue }
        if (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($key, "Process"))) { continue }
        [Environment]::SetEnvironmentVariable($key, $val, "Process")
    }
}

Import-FragilityDailyEnvFromDotEnv -Root $repoRoot

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot "reports/fragility_macro_risk_daily_latest.json"
}
if ([string]::IsNullOrWhiteSpace($FailureLogPath)) {
    $FailureLogPath = Join-Path $repoRoot "reports/fragility_macro_risk_daily_failures.jsonl"
}
if ([string]::IsNullOrWhiteSpace($RunLogPath)) {
    $RunLogPath = Join-Path $repoRoot "reports/fragility_macro_risk_daily_run_log.jsonl"
}
if ([string]::IsNullOrWhiteSpace($FailureWebhookUrl)) {
    $FailureWebhookUrl = [Environment]::GetEnvironmentVariable("MKM_DAILY_CHECK_FAILURE_WEBHOOK_URL", "Process")
    if ([string]::IsNullOrWhiteSpace($FailureWebhookUrl)) {
        $FailureWebhookUrl = [Environment]::GetEnvironmentVariable("OPS_ALARM_WEBHOOK_URL", "Process")
    }
    if ([string]::IsNullOrWhiteSpace($FailureWebhookUrl)) {
        $FailureWebhookUrl = [Environment]::GetEnvironmentVariable("MKM_DAILY_CHECK_FAILURE_WEBHOOK_URL", "User")
    }
    if ([string]::IsNullOrWhiteSpace($FailureWebhookUrl)) {
        $FailureWebhookUrl = [Environment]::GetEnvironmentVariable("MKM_DAILY_CHECK_FAILURE_WEBHOOK_URL", "Machine")
    }
    if ([string]::IsNullOrWhiteSpace($FailureWebhookUrl)) {
        $FailureWebhookUrl = [Environment]::GetEnvironmentVariable("OPS_ALARM_WEBHOOK_URL", "User")
    }
    if ([string]::IsNullOrWhiteSpace($FailureWebhookUrl)) {
        $FailureWebhookUrl = [Environment]::GetEnvironmentVariable("OPS_ALARM_WEBHOOK_URL", "Machine")
    }
}

if ([string]::IsNullOrWhiteSpace($GateAlertWebhookUrl)) {
    $GateAlertWebhookUrl = [Environment]::GetEnvironmentVariable("MKM_FRAGILITY_GATE_ALERT_WEBHOOK_URL", "Process")
    if ([string]::IsNullOrWhiteSpace($GateAlertWebhookUrl)) {
        $GateAlertWebhookUrl = [Environment]::GetEnvironmentVariable("OPS_ALARM_WEBHOOK_URL", "Process")
    }
    if ([string]::IsNullOrWhiteSpace($GateAlertWebhookUrl)) {
        $GateAlertWebhookUrl = [Environment]::GetEnvironmentVariable("MKM_FRAGILITY_GATE_ALERT_WEBHOOK_URL", "User")
    }
    if ([string]::IsNullOrWhiteSpace($GateAlertWebhookUrl)) {
        $GateAlertWebhookUrl = [Environment]::GetEnvironmentVariable("MKM_FRAGILITY_GATE_ALERT_WEBHOOK_URL", "Machine")
    }
    if ([string]::IsNullOrWhiteSpace($GateAlertWebhookUrl)) {
        $GateAlertWebhookUrl = [Environment]::GetEnvironmentVariable("OPS_ALARM_WEBHOOK_URL", "User")
    }
    if ([string]::IsNullOrWhiteSpace($GateAlertWebhookUrl)) {
        $GateAlertWebhookUrl = [Environment]::GetEnvironmentVariable("OPS_ALARM_WEBHOOK_URL", "Machine")
    }
}

$chainScript = Join-Path $PSScriptRoot "run_fragility_macro_risk_chain_v1.ps1"
$weeklyReportScript = Join-Path $PSScriptRoot "build_fragility_macro_risk_weekly_report_v1.py"
if (-not (Test-Path -LiteralPath $chainScript)) {
    throw "Required script not found: $chainScript"
}
if (-not (Test-Path -LiteralPath $weeklyReportScript)) {
    throw "Required script not found: $weeklyReportScript"
}

$result = [ordered]@{
    schema = "fragility_macro_risk_daily_run_v1"
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    status = "unknown"
    chain = [ordered]@{
        script = $chainScript
        prefer_fred = [bool]$PreferFred
        asset_scope = $AssetScope
        horizon = $Horizon
    }
    artifacts = [ordered]@{
        inputs = "docs/final/artifacts/macro_fragility_inputs_latest.json"
        fragility = "docs/final/artifacts/fragility_composite_v1_latest.json"
        response = "docs/final/artifacts/macro_risk_warning_api_smoke_latest.json"
        policy_binding = "docs/final/artifacts/macro_risk_warning_policy_binding_latest.json"
    }
    error = $null
    runtime = [ordered]@{
        gate = $null
        decision_state = $null
        risk_warning_level = $null
        source_mode = $null
        quaternion_signal = $null
    }
}

try {
    $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $chainScript, "-AssetScope", $AssetScope, "-Horizon", $Horizon)
    if ($PreferFred) { $args += "-PreferFred" }
    $chainOut = & powershell @args 2>&1
    $result.chain_output_preview = ($chainOut | Select-Object -Last 20) -join "`n"
    $result.status = "pass"
}
catch {
    $result.status = "fail"
    $result.error = $_.Exception.Message
}

$outDir = Split-Path -Parent $OutputPath
if (-not [string]::IsNullOrWhiteSpace($outDir) -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$prevGate = $null
if (Test-Path -LiteralPath $RunLogPath) {
    try {
        $lastLine = Get-Content -LiteralPath $RunLogPath -Tail 1 -ErrorAction Stop
        if (-not [string]::IsNullOrWhiteSpace($lastLine)) {
            $prevObj = $lastLine | ConvertFrom-Json
            if ($null -ne $prevObj.gate) { $prevGate = [string]$prevObj.gate }
        }
    }
    catch {
        $prevGate = $null
    }
}

$inputsArtifactPath = Join-Path $repoRoot "docs\final\artifacts\macro_fragility_inputs_latest.json"
$respArtifactPath = Join-Path $repoRoot "docs\final\artifacts\macro_risk_warning_api_smoke_latest.json"
try {
    if (Test-Path -LiteralPath $inputsArtifactPath) {
        $inputDoc = Get-Content -LiteralPath $inputsArtifactPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($null -ne $inputDoc.source_mode) { $result.runtime.source_mode = [string]$inputDoc.source_mode }
    }
    if (Test-Path -LiteralPath $respArtifactPath) {
        $respDoc = Get-Content -LiteralPath $respArtifactPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($null -ne $respDoc.fragility_composite -and $null -ne $respDoc.fragility_composite.gate) {
            $result.runtime.gate = [string]$respDoc.fragility_composite.gate
        }
        if ($null -ne $respDoc.decision_state) { $result.runtime.decision_state = [string]$respDoc.decision_state }
        if ($null -ne $respDoc.risk_warning_level) { $result.runtime.risk_warning_level = [string]$respDoc.risk_warning_level }
        if ($null -ne $respDoc.non_gating_narrative -and $null -ne $respDoc.non_gating_narrative.quaternion_signal) {
            $result.runtime.quaternion_signal = [string]$respDoc.non_gating_narrative.quaternion_signal
        }
    }
}
catch {
    # Keep runtime enrichment best-effort only.
}

$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

$runEntry = @{
    ts_utc = $result.ts_utc
    status = $result.status
    gate = $result.runtime.gate
    decision_state = $result.runtime.decision_state
    risk_warning_level = $result.runtime.risk_warning_level
    quaternion_signal = $result.runtime.quaternion_signal
    source_mode = $result.runtime.source_mode
    output_path = $OutputPath
    host = $env:COMPUTERNAME
} | ConvertTo-Json -Depth 8 -Compress

$runDir = Split-Path -Parent $RunLogPath
if (-not [string]::IsNullOrWhiteSpace($runDir) -and -not (Test-Path -LiteralPath $runDir)) {
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
}
Add-Content -LiteralPath $RunLogPath -Value $runEntry -Encoding UTF8
Write-Output ("run_log_path={0}" -f $RunLogPath)

try {
    py $weeklyReportScript | Out-Null
}
catch {
    Write-Output ("weekly_report_refresh: FAIL - " + $_.Exception.Message)
}

if ($result.status -eq "pass" -and -not $SkipGateAlert -and -not [string]::IsNullOrWhiteSpace($GateAlertWebhookUrl)) {
    $g = $result.runtime.gate
    if ($g -in @("RED", "AMBER")) {
        $shouldSend = $false
        $alertReason = ""
        if ($g -eq "RED") {
            $shouldSend = $true
            $alertReason = "red_each_pass"
        }
        elseif ($g -eq "AMBER" -and $prevGate -ne "AMBER") {
            $shouldSend = $true
            $alertReason = "amber_on_transition_or_first"
        }
        if ($shouldSend) {
            try {
                $gatePayload = @{
                    schema = "fragility_macro_risk_gate_alert_v1"
                    ts_utc = $result.ts_utc
                    gate = $g
                    alert_reason = $alertReason
                    previous_gate = $prevGate
                    decision_state = $result.runtime.decision_state
                    risk_warning_level = $result.runtime.risk_warning_level
                    quaternion_signal = $result.runtime.quaternion_signal
                    source_mode = $result.runtime.source_mode
                    asset_scope = $AssetScope
                    host = $env:COMPUTERNAME
                    artifacts = $result.artifacts
                } | ConvertTo-Json -Depth 8
                Invoke-RestMethod -Method Post -Uri $GateAlertWebhookUrl -ContentType "application/json; charset=utf-8" -Body $gatePayload -TimeoutSec 15 | Out-Null
                Write-Output "gate_alert_webhook: SENT"
            }
            catch {
                Write-Output ("gate_alert_webhook: FAIL - " + $_.Exception.Message)
            }
        }
        else {
            Write-Output "gate_alert_webhook: SKIPPED (amber steady-state; no transition)"
        }
    }
}
elseif ($result.status -eq "pass" -and -not $SkipGateAlert) {
    Write-Output "gate_alert_webhook: SKIPPED (set MKM_FRAGILITY_GATE_ALERT_WEBHOOK_URL or OPS_ALARM_WEBHOOK_URL)"
}

Write-Output ("fragility_daily_status={0}" -f $result.status)
Write-Output ("output_path={0}" -f $OutputPath)

if ($result.status -ne "pass") {
    $failureEntry = @{
        ts_utc = $result.ts_utc
        event = "fragility_macro_risk_daily_fail"
        status = $result.status
        error = $result.error
        output_path = $OutputPath
        host = $env:COMPUTERNAME
    } | ConvertTo-Json -Depth 8 -Compress

    $failDir = Split-Path -Parent $FailureLogPath
    if (-not [string]::IsNullOrWhiteSpace($failDir) -and -not (Test-Path -LiteralPath $failDir)) {
        New-Item -ItemType Directory -Path $failDir -Force | Out-Null
    }
    Add-Content -LiteralPath $FailureLogPath -Value $failureEntry -Encoding UTF8
    Write-Output ("failure_log_path={0}" -f $FailureLogPath)

    if (-not $SkipFailureAlert -and -not [string]::IsNullOrWhiteSpace($FailureWebhookUrl)) {
        try {
            $payload = @{
                schema = "fragility_macro_risk_daily_alert_v1"
                ts_utc = $result.ts_utc
                status = $result.status
                error = $result.error
                output_path = $OutputPath
                host = $env:COMPUTERNAME
            } | ConvertTo-Json -Depth 8
            Invoke-RestMethod -Method Post -Uri $FailureWebhookUrl -ContentType "application/json; charset=utf-8" -Body $payload -TimeoutSec 15 | Out-Null
            Write-Output "failure_alert_webhook: SENT"
        }
        catch {
            Write-Output ("failure_alert_webhook: FAIL - " + $_.Exception.Message)
        }
    }
    elseif (-not $SkipFailureAlert) {
        Write-Output "failure_alert_webhook: SKIPPED (set MKM_DAILY_CHECK_FAILURE_WEBHOOK_URL or OPS_ALARM_WEBHOOK_URL)"
    }

    exit 1
}
