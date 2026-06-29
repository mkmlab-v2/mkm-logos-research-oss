<#
.SYNOPSIS
  Weekly deep research bench: offline pytest + online DR mini harness (P2-G).

.DESCRIPTION
  1) py -m pytest tests/test_mkm_deep_research_bench_mini_v1.py -q  (offline smoke)
  2) py scripts/run_mkm_deep_research_bench_mini_v1.py --include-router --require-entry-level  (online FACT-lite strict)
  3) py scripts/build_mkm_deep_research_bench_ops_paste_v1.py  (commander ops paste md/json)

  Track B · research_only · send_gate HOLD

.PARAMETER OfflineOnly
  Skip online arXiv verification (pytest only).

.PARAMETER AllowFallback
  Allow summary fallback for difficulty pass metrics (default: strict entry-level required).

.PARAMETER WorkspaceRoot
  Repo root (default: MKM_WORKSPACE_ROOT or parent of scripts/).
#>
param(
    [switch]$OfflineOnly,
    [switch]$AllowFallback,
    [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = "Stop"

$resolvedRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
}
elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
}
else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

Set-Location -LiteralPath $resolvedRoot

Write-Host "dr_bench_weekly: step 1/3 pytest offline smoke"
py -m pytest tests/test_mkm_deep_research_bench_mini_v1.py -q
if ($LASTEXITCODE -ne 0) {
    throw "pytest dr bench mini failed exit=$LASTEXITCODE"
}

if ($OfflineOnly) {
    Write-Host "dr_bench_weekly: step 2/3 offline DR bench mini"
    $offlineArgs = @("scripts/run_mkm_deep_research_bench_mini_v1.py", "--offline", "--include-router", "--require-entry-level")
    py @offlineArgs
    if ($LASTEXITCODE -ne 0) {
        throw "offline dr bench mini failed exit=$LASTEXITCODE"
    }
    Write-Host "dr_bench_weekly: step 3/3 ops paste"
    py scripts/build_mkm_deep_research_bench_ops_paste_v1.py
    if ($LASTEXITCODE -ne 0) {
        throw "ops paste build failed exit=$LASTEXITCODE"
    }
    Write-Host "dr_bench_weekly: offline-only OK artifact=reports/mkm_deep_research_bench_ops_paste_v1_latest.md"
    exit 0
}

Write-Host "dr_bench_weekly: step 2/3 online DR bench mini"
$benchArgs = @("scripts/run_mkm_deep_research_bench_mini_v1.py", "--include-router")
if (-not $AllowFallback) {
    $benchArgs += "--require-entry-level"
}
py @benchArgs
if ($LASTEXITCODE -ne 0) {
    throw "online dr bench mini failed exit=$LASTEXITCODE"
}

Write-Host "dr_bench_weekly: step 3/3 ops paste"
py scripts/build_mkm_deep_research_bench_ops_paste_v1.py
if ($LASTEXITCODE -ne 0) {
    throw "ops paste build failed exit=$LASTEXITCODE"
}

Write-Host "dr_bench_weekly: OK artifacts=reports/mkm_deep_research_bench_mini_v1_latest.json reports/mkm_deep_research_bench_ops_paste_v1_latest.md"
exit 0
