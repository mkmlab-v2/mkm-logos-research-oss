# PersonaDiary commercial readiness — local gate (preview_only)
param(
    [string]$BaseUrl = "http://127.0.0.1:3010",
    [switch]$SkipSmoke,
    [switch]$IncludeLiveOpsSmoke
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$argsList = @("scripts/run_personadiary_commercial_readiness_v1.py", "--base-url", $BaseUrl)
if ($SkipSmoke) { $argsList += "--skip-smoke" }

& py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($IncludeLiveOpsSmoke) {
    & py scripts/run_personadiary_live_ops_smoke_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "OK: personadiary commercial readiness -> docs/final/artifacts/personadiary_commercial_readiness_v1_latest.json"
