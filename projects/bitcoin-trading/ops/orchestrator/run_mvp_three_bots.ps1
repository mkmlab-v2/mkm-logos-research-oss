$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\orchestrator\mvp_three_bots.py"

if (-not (Test-Path $runner)) {
    throw "MVP orchestrator not found: $runner"
}

Set-Location $projectRoot
python "$runner"
if ($LASTEXITCODE -ne 0) {
    throw "MVP orchestrator failed with exit code: $LASTEXITCODE"
}
