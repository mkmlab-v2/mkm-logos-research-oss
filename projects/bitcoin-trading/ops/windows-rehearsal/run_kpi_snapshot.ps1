$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\collect_kpi_snapshot.py"

if (-not (Test-Path $runner)) {
    throw "KPI runner not found: $runner"
}

Set-Location $projectRoot
python "$runner"
if ($LASTEXITCODE -ne 0) {
    throw "KPI snapshot failed with exit code: $LASTEXITCODE"
}
