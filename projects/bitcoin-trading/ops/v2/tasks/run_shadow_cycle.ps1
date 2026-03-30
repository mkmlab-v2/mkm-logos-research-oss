$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\v2\graph\runner.py"

if (-not (Test-Path $runner)) {
    throw "runner.py not found: $runner"
}

Set-Location $projectRoot
python "$runner" --mode shadow
if ($LASTEXITCODE -ne 0) {
    throw "v2 shadow cycle failed with exit code: $LASTEXITCODE"
}
