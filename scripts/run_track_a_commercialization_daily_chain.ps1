#Requires -Version 5.1
<#
.SYNOPSIS
  Track A commercialization daily chain (shadow → metering → weekly → band gate → cost sim → signal light).

.NOTES
  If default metering JSONL is missing, copies tests/fixtures/track_a_metering_log_smoke_v1.jsonl.
#>
param(
    [string]$WorkspaceRoot = "",
    [ValidateSet("warning", "block")]
    [string]$GateMode = "warning"
)

$ErrorActionPreference = "Stop"
if (-not $WorkspaceRoot) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
$root = $WorkspaceRoot
Set-Location $root

$meter = Join-Path $root "reports/constitution/btrack_pilot/track_a_metering_log_v1.jsonl"
$fixture = Join-Path $root "tests/fixtures/track_a_metering_log_smoke_v1.jsonl"
if (-not (Test-Path $meter)) {
    if (-not (Test-Path $fixture)) {
        throw "Missing metering fixture: $fixture"
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $meter) | Out-Null
    Copy-Item -Force $fixture $meter
}

& py (Join-Path $root "scripts/run_track_a_shadow_corpus_eval.py") --workspace-root $root
if ($LASTEXITCODE -ne 0) { throw "shadow corpus eval failed: $LASTEXITCODE" }

& py (Join-Path $root "scripts/run_track_a_metering_summary.py") --workspace-root $root
if ($LASTEXITCODE -ne 0) { throw "metering summary failed: $LASTEXITCODE" }

& py (Join-Path $root "scripts/run_track_a_metering_weekly_report.py") --workspace-root $root
if ($LASTEXITCODE -ne 0) { throw "metering weekly failed: $LASTEXITCODE" }

& py (Join-Path $root "scripts/check_track_a_metering_band_gate.py") --workspace-root $root --mode $GateMode
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 3) { throw "band gate unexpected exit $LASTEXITCODE" }
if ($LASTEXITCODE -eq 3 -and $GateMode -eq "block") { throw "Track A metering band gate blocked" }

& py (Join-Path $root "scripts/run_track_a_conversational_cost_simulation.py") --workspace-root $root
if ($LASTEXITCODE -ne 0) { throw "cost simulation failed: $LASTEXITCODE" }

& py (Join-Path $root "scripts/build_track_a_signal_light_report.py") --workspace-root $root
if ($LASTEXITCODE -ne 0) { throw "signal light report failed: $LASTEXITCODE" }

$log = Join-Path $root "reports/track_a_commercialization_daily_log.jsonl"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$entry = [ordered]@{
    ts_utc    = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    schema    = "track_a_commercialization_daily_log_v1"
    gate_mode = $GateMode
    status    = "ok"
}
Add-Content -Path $log -Value (($entry | ConvertTo-Json -Compress) + "`n") -Encoding utf8
Write-Host "[DONE] Track A commercialization daily chain" -ForegroundColor Green
