# CPU-only Logos gold query eval — no GPU, no WSL Nemotron.
param(
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$args = @("-3", "scripts/build_logos_gold_query_eval_report_v1.py")
if ($Strict) { $args += "--strict" }

& py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[OK] reports/logos_gold_query_eval_v1_latest.json (CPU-only, no Nemotron)" -ForegroundColor Green
