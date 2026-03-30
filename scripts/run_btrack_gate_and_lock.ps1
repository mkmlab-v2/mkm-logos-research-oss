param(
    [string]$PythonExe = "py -3"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = "C:\workspace\scripts\run_btrack_gate_and_lock.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing runner script: $scriptPath"
}

Write-Host "[btrack] Running one-shot gate+lock workflow..."

# Support either "py -3" (default) or full python executable path.
if ($PythonExe -eq "py -3") {
    py -3 $scriptPath
} else {
    & $PythonExe $scriptPath
}

if ($LASTEXITCODE -ne 0) {
    throw "B-Track one-shot runner failed with exit code $LASTEXITCODE"
}

Write-Host "[btrack] Completed successfully."
