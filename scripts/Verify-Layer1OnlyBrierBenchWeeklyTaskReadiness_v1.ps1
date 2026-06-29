<#
.SYNOPSIS
  Readiness check for Layer-1-only Brier bench weekly task + script paths.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-Layer1OnlyBrierBench-Weekly"
)

$ErrorActionPreference = "Stop"
$required = @(
    "scripts\layer1_only_brier_bench_poc_v1.py",
    "scripts\layer1_only_brier_bench_poc_lib_v1.py",
    "scripts\layer1_only_brier_bench_resolver_hooks_v1.py",
    "scripts\probe_layer1_only_brier_bench_resolvers_v1.py",
    "scripts\register_layer1_only_brier_bench_poc_v1.py",
    "scripts\run_layer1_only_brier_bench_chain_v1.py",
    "scripts\Invoke-Layer1OnlyBrierBenchWeekly_v1.ps1",
    "docs\final\artifacts\layer1_only_brier_bench_poc_v1_latest.json",
    "docs\final\artifacts\layer1_only_brier_bench_poc_registry_map_v1.json"
)

$missing = @()
foreach ($rel in $required) {
    $p = Join-Path $WorkspaceRoot $rel
    if (-not (Test-Path -LiteralPath $p)) { $missing += $rel }
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
$fred_api_key_present = [bool]$env:FRED_API_KEY
$envPath = Join-Path $WorkspaceRoot ".env"
if (-not $fred_api_key_present -and (Test-Path -LiteralPath $envPath)) {
    Get-Content -LiteralPath $envPath -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_ -match '^\s*FRED_API_KEY=(.+)$') {
            $fred_api_key_present = ($Matches[1].Trim().Length -gt 0)
        }
    }
}
$report = [ordered]@{
    schema = "layer1_only_brier_bench_weekly_readiness_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    workspace_root = $WorkspaceRoot
    task_name = $TaskName
    task_registered = [bool]$task
    missing_paths = $missing
    fred_api_key_present = $fred_api_key_present
    fred_api_key_source_hint = $(if ($fred_api_key_present) { "env_or_dotenv" } else { "missing" })
    ready = ($missing.Count -eq 0)
}

$out = Join-Path $WorkspaceRoot "reports\layer1_only_brier_bench_weekly_readiness_v1_latest.json"
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $out -Encoding utf8
Write-Host ($report | ConvertTo-Json -Depth 6)

if (-not $report.ready) {
    exit 1
}
exit 0
