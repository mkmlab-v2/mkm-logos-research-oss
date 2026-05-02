[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$QuickScriptPath = "",

    [Parameter(Mandatory = $false)]
    [string]$AuditLogPath = "",

    [Parameter(Mandatory = $false)]
    [string]$OutputPath = "",

    [Parameter(Mandatory = $false)]
    [string]$FailureWebhookUrl = "",

    [Parameter(Mandatory = $false)]
    [string]$FailureLogPath = "",

    [switch]$SkipFailureAlert
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Import-MacroRiskDailyCheckEnvFromDotEnv {
    param([string]$Root)
    $dot = Join-Path $Root ".env"
    if (-not (Test-Path -LiteralPath $dot)) { return }
    $keysWanted = @("MKM_DAILY_CHECK_FAILURE_WEBHOOK_URL", "OPS_ALARM_WEBHOOK_URL")
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

Import-MacroRiskDailyCheckEnvFromDotEnv -Root $repoRoot

if ([string]::IsNullOrWhiteSpace($QuickScriptPath)) {
    $QuickScriptPath = Join-Path $PSScriptRoot "Run-MacroRiskN8nOpsQuick.ps1"
}
if ([string]::IsNullOrWhiteSpace($AuditLogPath)) {
    $AuditLogPath = Join-Path (Split-Path -Parent $PSScriptRoot) "reports/macro_risk_approval_webhook_audit.jsonl"
}
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path (Split-Path -Parent $PSScriptRoot) "reports/macro_risk_n8n_daily_check_latest.json"
}
if ([string]::IsNullOrWhiteSpace($FailureLogPath)) {
    $FailureLogPath = Join-Path (Split-Path -Parent $PSScriptRoot) "reports/macro_risk_n8n_daily_check_failures.jsonl"
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

if (-not (Test-Path -LiteralPath $QuickScriptPath)) {
    throw "Quick ops script not found: $QuickScriptPath"
}

$result = [ordered]@{
    schema = "macro_risk_n8n_daily_check_v1"
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    checks = [ordered]@{
        n8n_health = "unknown"
        n8n_service_task = "unknown"
        audit_log_exists = "unknown"
        audit_log_last_line_preview = ""
        audit_log_last_line_length = 0
    }
}

try {
    $healthOut = powershell -NoProfile -ExecutionPolicy Bypass -File $QuickScriptPath -Action health 2>&1
    if (($healthOut -join "`n") -match "n8n_health: PASS") {
        $result.checks.n8n_health = "pass"
    }
    else {
        $result.checks.n8n_health = "fail"
    }
}
catch {
    $result.checks.n8n_health = "fail"
}

try {
    $task = Get-ScheduledTask -TaskName "MKM-n8n-Service" -ErrorAction SilentlyContinue
    if ($null -ne $task -and $task.State -in @("Ready", "Running")) {
        $result.checks.n8n_service_task = "pass"
    }
    else {
        $result.checks.n8n_service_task = "fail"
    }
}
catch {
    $result.checks.n8n_service_task = "fail"
}

if (Test-Path -LiteralPath $AuditLogPath) {
    $result.checks.audit_log_exists = "pass"
    $lastLine = Get-Content -LiteralPath $AuditLogPath -Tail 1
    if ($null -ne $lastLine) {
        $line = [string]$lastLine
        $result.checks.audit_log_last_line_length = $line.Length
        if ($line.Length -gt 500) {
            $result.checks.audit_log_last_line_preview = $line.Substring(0, 500) + "...<truncated>"
        }
        else {
            $result.checks.audit_log_last_line_preview = $line
        }
    }
}
else {
    $result.checks.audit_log_exists = "fail"
}

$overallPass = @(
    $result.checks.n8n_health,
    $result.checks.n8n_service_task,
    $result.checks.audit_log_exists
) -notcontains "fail"

$result.overall = if ($overallPass) { "pass" } else { "fail" }

$outDir = Split-Path -Parent $OutputPath
if (-not [string]::IsNullOrWhiteSpace($outDir) -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

Write-Output ("daily_check_overall={0}" -f $result.overall)
Write-Output ("output_path={0}" -f $OutputPath)

if (-not $overallPass) {
    $failureEntry = @{
        ts_utc = $result.ts_utc
        event = "macro_risk_n8n_daily_check_fail"
        overall = $result.overall
        checks = $result.checks
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
                schema = "macro_risk_n8n_daily_check_alert_v1"
                ts_utc = $result.ts_utc
                overall = $result.overall
                checks = $result.checks
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
