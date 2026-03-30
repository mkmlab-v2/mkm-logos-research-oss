param(
    [string]$PythonExe = "py"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = "C:\workspace\scripts\run_btrack_gate_and_lock.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing runner script: $scriptPath"
}

Write-Host "[btrack] Running one-shot gate+lock workflow..."

# Prefer Windows launcher (py -3), fallback to direct python when unavailable.
if ($PythonExe -eq "py") {
    & py -3 $scriptPath
    if ($LASTEXITCODE -eq 2) {
        & python $scriptPath
    }
} else {
    & $PythonExe $scriptPath
}

if ($LASTEXITCODE -ne 0) {
    throw "B-Track one-shot runner failed with exit code $LASTEXITCODE"
}

Write-Host "[btrack] Completed successfully."
