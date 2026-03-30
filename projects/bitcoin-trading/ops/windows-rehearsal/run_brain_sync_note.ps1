$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\build_brain_sync_note.py"

if (-not (Test-Path $runner)) {
    throw "Brain sync builder not found: $runner"
}

Set-Location $projectRoot
python "$runner"
if ($LASTEXITCODE -ne 0) {
    throw "Brain sync note build failed with exit code: $LASTEXITCODE"
}
