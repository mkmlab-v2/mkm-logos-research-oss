# Compression / restore bridge — Fact-Lock bundle step.
# Validates general compression benchmark manifest + restore-stress NO_GO hard lock.
# Does not run full compression sweeps (use run_compression_automation_chain.ps1 for that).

param(
    [string]$WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $WorkspaceRoot

$py = Join-Path $WorkspaceRoot 'scripts\validate_general_compression_bundle.py'
if (-not (Test-Path -LiteralPath $py)) {
    throw "Missing: $py"
}

Write-Host '== Agent compression/restore bridge: validate_general_compression_bundle.py ==' -ForegroundColor Cyan
& py $py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host 'OK: compression/restore bridge validation passed.' -ForegroundColor Green
exit 0
