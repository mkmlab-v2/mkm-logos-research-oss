#Requires -Version 5.1
<#
.SYNOPSIS
  Background loop: LOGOS-THEME-RUN until STOP file (no chat prompts).

.PARAMETER IntervalMinutes
  Sleep between cycles (default 4). Scheduled task can run in parallel; this is optional extra throughput.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosThemeUnattendedLoop_v1.ps1
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [int]$IntervalMinutes = 4,
    [int]$ExpandMaxPerRun = 5,
    [int]$SeedRefillBatch = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}

$runner = Join-Path $repoRoot "scripts\Invoke-LogosThemeRunContinuous_v1.ps1"
$stopFile = Join-Path $repoRoot "docs\research\logos_metaphor_db_v1\LOGOS_THEME_RUN.stop"
$logPath = Join-Path $repoRoot "reports\logos_theme_unattended_loop_log.jsonl"

function Write-LoopLog([string]$Decision, [string]$Note = "") {
    $row = @{
        timestamp_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        decision      = $Decision
        note          = $Note
    } | ConvertTo-Json -Compress
    Add-Content -LiteralPath $logPath -Value $row -Encoding UTF8
}

Write-Host "[logos-unattended] loop start interval=${IntervalMinutes}m expand=$ExpandMaxPerRun" -ForegroundColor Cyan
Write-LoopLog "loop_start" "interval_min=$IntervalMinutes expand=$ExpandMaxPerRun"

while ($true) {
    if (Test-Path -LiteralPath $stopFile) {
        Write-Host "[logos-unattended] STOP file — exit 0" -ForegroundColor Yellow
        Write-LoopLog "stop_file" $stopFile
        exit 0
    }
    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $runner `
            -WorkspaceRoot $repoRoot `
            -ExpandMaxPerRun $ExpandMaxPerRun `
            -AutoRefillSeed `
            -SeedRefillBatch $SeedRefillBatch
        $code = $LASTEXITCODE
        Write-LoopLog "cycle" "exit_code=$code"
        if ($code -ne 0) {
            Write-Host "[logos-unattended] cycle exit $code" -ForegroundColor Red
        }
    } catch {
        Write-LoopLog "cycle_error" $_.Exception.Message
        Write-Host "[logos-unattended] error: $_" -ForegroundColor Red
    }
    Start-Sleep -Seconds ([Math]::Max(60, $IntervalMinutes * 60))
}
