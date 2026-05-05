# Daily lightweight refresh for General Prophecy queue artifacts.
# Restores legacy task entrypoint: \GeneralProphecyDailyQueueV1
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$gen = Join-Path $WorkspaceRoot "scripts\generate_general_prophecy_v1.py"
$brief = Join-Path $WorkspaceRoot "scripts\build_general_prophecy_brief.py"
$brier = Join-Path $WorkspaceRoot "scripts\eval_general_prophecy_brier_score.py"

if (-not (Test-Path -LiteralPath $gen)) { throw "Missing script: $gen" }
if (-not (Test-Path -LiteralPath $brief)) { throw "Missing script: $brief" }
if (-not (Test-Path -LiteralPath $brier)) { throw "Missing script: $brier" }

& py -3 $gen --output "docs/final/artifacts/general_prophecy_latest.json" --stub-forecasts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py -3 $brief --input "docs/final/artifacts/general_prophecy_latest.json" --output "docs/final/artifacts/general_prophecy_brief_latest.md"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py -3 $brier --input "docs/final/artifacts/general_prophecy_latest.json" --output "docs/final/artifacts/general_prophecy_brier_eval_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "General prophecy daily queue refresh done."
