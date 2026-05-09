[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $PSScriptRoot "athena_ops_monitor_v1.py"
$metricsPath = Join-Path $repoRoot "reports\athena_ops_metrics_latest.json"
$statusPath = Join-Path $repoRoot "reports\athena_ops_status_latest.json"

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

& py $scriptPath --metrics-path $metricsPath --output-path $statusPath
