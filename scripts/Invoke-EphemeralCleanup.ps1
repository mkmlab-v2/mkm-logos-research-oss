<#
.SYNOPSIS
  Run ephemeral workspace cleanup in dry-run (default) or apply mode.
#>
param(
    [int]$RetentionDays = 3,
    [switch]$Apply,
    [int]$MaxDeleteCount = 0,
    [switch]$IncludeTmp
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$scriptPath = Join-Path $workspaceRoot "scripts\cleanup_ephemeral_files_v1.py"
$alertCheck = Join-Path $workspaceRoot "scripts\check_ephemeral_cleanup_alert_v1.py"
$alertJsonPath = Join-Path $workspaceRoot "docs\final\artifacts\ephemeral_cleanup_alert_latest.json"

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Cleanup script not found: $scriptPath"
}
if (-not (Test-Path -LiteralPath $alertCheck)) {
    throw "Alert checker not found: $alertCheck"
}

$args = @(
    $scriptPath,
    "--retention-days", "$RetentionDays",
    "--allowed-roots", "out", "logs", "staging"
)

if ($IncludeTmp) {
    $args += "tmp"
}

if ($Apply) {
    $args += "--apply"
}
if ($MaxDeleteCount -gt 0) {
    $args += @("--max-delete-count", "$MaxDeleteCount")
}

Write-Host "Running cleanup (apply=$Apply, retention_days=$RetentionDays, max_delete_count=$MaxDeleteCount, include_tmp=$IncludeTmp)"
& py @args
if ($LASTEXITCODE -ne 0) {
    throw "cleanup_ephemeral_files_v1.py failed with exit code $LASTEXITCODE"
}

& py $alertCheck
if ($LASTEXITCODE -ne 0) {
    throw "check_ephemeral_cleanup_alert_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "Done. Summary: docs/final/artifacts/ephemeral_cleanup_summary_latest.json"
Write-Host "Alert: docs/final/artifacts/ephemeral_cleanup_alert_latest.json"

# Optional alert webhook: only send when status is ALERT and URL is configured.
# Priority: EPHEMERAL_CLEANUP_ALERT_WEBHOOK_URL > OPS_ALARM_WEBHOOK_URL
$webhookUrl = $env:EPHEMERAL_CLEANUP_ALERT_WEBHOOK_URL
if ([string]::IsNullOrWhiteSpace($webhookUrl)) {
    $webhookUrl = $env:OPS_ALARM_WEBHOOK_URL
}
if (Test-Path -LiteralPath $alertJsonPath) {
    try {
        $alertObj = Get-Content -LiteralPath $alertJsonPath -Raw | ConvertFrom-Json
        $status = [string]$alertObj.status
        if ($status -eq "ALERT") {
            if ([string]::IsNullOrWhiteSpace($webhookUrl)) {
                Write-Host "ALERT detected, but no webhook URL is set (EPHEMERAL_CLEANUP_ALERT_WEBHOOK_URL/OPS_ALARM_WEBHOOK_URL). Skipping webhook."
            } else {
                $body = @{
                    source = "ephemeral_cleanup"
                    generated_at_utc = [string]$alertObj.generated_at_utc
                    status = $status
                    reasons = $alertObj.reasons
                    deleted_count = $alertObj.deleted_count
                    deleted_bytes = $alertObj.deleted_bytes
                    error_count = $alertObj.error_count
                } | ConvertTo-Json -Depth 5
                Invoke-RestMethod -Method Post -Uri $webhookUrl -ContentType "application/json" -Body $body | Out-Null
                Write-Host "ALERT webhook sent."
            }
        }
    } catch {
        Write-Warning "Failed to process/send cleanup alert webhook: $($_.Exception.Message)"
    }
}
