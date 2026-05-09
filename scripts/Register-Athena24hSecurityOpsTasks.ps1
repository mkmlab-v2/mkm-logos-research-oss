[CmdletBinding()]
param(
    [switch]$Remove,
    [switch]$StartNow,
    [string]$SecurityTaskName = "MKM-Security-Integrity-Check-5min",
    [string]$OpsTaskName = "MKM-Athena-Ops-Monitor-5min",
    [int]$IntervalMinutes = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$securityScript = Join-Path $PSScriptRoot "security_integrity_monitor_v1.py"
$opsScript = Join-Path $PSScriptRoot "athena_ops_monitor_v1.py"
$securityTaskRunner = Join-Path $PSScriptRoot "Run-SecurityIntegrityCheckTask.ps1"
$opsTaskRunner = Join-Path $PSScriptRoot "Run-AthenaOpsMonitorTask.ps1"
$metricsPath = Join-Path $repoRoot "reports\athena_ops_metrics_latest.json"
$securityManifestPath = Join-Path $repoRoot "reports\security_integrity_manifest_v1.json"
$securityStatusPath = Join-Path $repoRoot "reports\security_integrity_status_latest.json"
$opsStatusPath = Join-Path $repoRoot "reports\athena_ops_status_latest.json"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $SecurityTaskName -Confirm:$false -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $OpsTaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($SecurityTaskName)"
    Write-Output "scheduled_task: REMOVED ($OpsTaskName)"
    exit 0
}

if (-not (Test-Path -LiteralPath $securityScript)) {
    throw "Missing script: $securityScript"
}
if (-not (Test-Path -LiteralPath $opsScript)) {
    throw "Missing script: $opsScript"
}
if (-not (Test-Path -LiteralPath $securityTaskRunner)) {
    throw "Missing runner script: $securityTaskRunner"
}
if (-not (Test-Path -LiteralPath $opsTaskRunner)) {
    throw "Missing runner script: $opsTaskRunner"
}

$reportsDir = Split-Path -Parent $metricsPath
if (-not (Test-Path -LiteralPath $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}

if (-not (Test-Path -LiteralPath $securityManifestPath)) {
    & py $securityScript --mode snapshot --manifest-path $securityManifestPath | Out-Null
}

if (-not (Test-Path -LiteralPath $metricsPath)) {
    $defaultMetrics = @{
        schema = "athena_ops_metrics_v1"
        ts_utc = (Get-Date).ToUniversalTime().ToString("o")
        source = "bootstrap_default"
        api_latency_ms = 250.0
        daily_loss_pct = 0.0
        position_usage_pct = 10.0
        exchange_connected = $true
    } | ConvertTo-Json -Depth 6
    Set-Content -LiteralPath $metricsPath -Value $defaultMetrics -Encoding UTF8
}

$secRun = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$securityTaskRunner`""
$opsRun = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$opsTaskRunner`""

schtasks /Create /TN $SecurityTaskName /TR $secRun /SC MINUTE /MO $IntervalMinutes /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register task: $SecurityTaskName"
}
schtasks /Create /TN $OpsTaskName /TR $opsRun /SC MINUTE /MO $IntervalMinutes /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register task: $OpsTaskName"
}

Write-Output "scheduled_task: REGISTERED ($SecurityTaskName)"
Write-Output "scheduled_task: REGISTERED ($OpsTaskName)"
Write-Output "metrics_path=$metricsPath"
Write-Output "security_manifest_path=$securityManifestPath"

if ($StartNow) {
    Start-ScheduledTask -TaskName $SecurityTaskName
    Start-ScheduledTask -TaskName $OpsTaskName
    Write-Output "scheduled_task: STARTED ($SecurityTaskName)"
    Write-Output "scheduled_task: STARTED ($OpsTaskName)"
}
