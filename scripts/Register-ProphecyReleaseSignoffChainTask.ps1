param(
    [string]$TaskName = "MKM-Prophecy-Release-Signoff-Chain-Hourly",
    [int]$IntervalHours = 1
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $repoRoot "scripts\run_prophecy_release_signoff_chain_v1.ps1"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner script not found: $runner"
}

$startAt = (Get-Date).AddMinutes(2).ToString("HH:mm")
$taskRun = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`" -SkipConstitutionGate"
schtasks /Create /F /SC HOURLY /MO $IntervalHours /TN $TaskName /TR $taskRun /ST $startAt | Out-Null
Write-Host "REGISTERED: $TaskName every ${IntervalHours}h (start $startAt)"
