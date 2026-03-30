# Requires -Version 5.1
<#
.SYNOPSIS
  Run state execution packet logger once (live mode).

.DESCRIPTION
  Wrapper around scripts/run_state_execution_packet.py for Task Scheduler.
  Appends one run into backtest_results JSONL.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$PacketPath = "backtest_results\LOGOS_RESONANCE_BTC_EXT_K6866_RELAXED_N2_C0_STATE_EXECUTION_APPROVAL_PACKET_TOP5.json",
    [switch]$Simulate
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\run_state_execution_packet.py"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

Set-Location $WorkspaceRoot

# 30-minute bucket idempotency key (UTC): prevents duplicate appends per cycle window.
$utc = (Get-Date).ToUniversalTime()
$bucketMinute = if ($utc.Minute -lt 30) { "00" } else { "30" }
$packetAbsPath = if ([System.IO.Path]::IsPathRooted($PacketPath)) { $PacketPath } else { Join-Path $WorkspaceRoot $PacketPath }
if (-not (Test-Path -LiteralPath $packetAbsPath)) {
    throw "Packet not found: $packetAbsPath"
}
$packetHash = (Get-FileHash -LiteralPath $packetAbsPath -Algorithm SHA256).Hash.Substring(0, 12).ToLowerInvariant()
$idempotencyKey = "state_packet_30m_{0}{1}{2}{3}_{4}_{5}" -f $utc.Year, $utc.Month.ToString("00"), $utc.Day.ToString("00"), $utc.Hour.ToString("00"), $bucketMinute, $packetHash

$args = @($runner, "--packet", $PacketPath, "--idempotency-key", $idempotencyKey)
if ($Simulate) {
    $args += "--simulate"
}

& py @args
if ($LASTEXITCODE -ne 0) {
    throw "run_state_execution_packet.py failed with exit code $LASTEXITCODE"
}

Write-Host "State execution packet cycle completed."
