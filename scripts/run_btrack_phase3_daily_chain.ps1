#Requires -Version 5.1
<#
.SYNOPSIS
  Daily Phase 3 B-track chain (Binance fetch + multilens per-date loop + sidecar).

.NOTES
  research_only — no prod score mutation, no Track A promotion.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipBinanceFetch,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$pyArgs = @(
    "scripts/run_btrack_phase3_leading_sensors_chain_v1.py",
    "--skip-auto-optimal",
    "--join-180",
    "--skip-seed"
)
if (-not $SkipBinanceFetch) {
    $pyArgs += "--fetch-binance"
}
if ($DryRun) {
    $pyArgs += "--dry-run"
}

# Global lens snapshots (free; tail JSONL — feeds logos block in per-date loop)
& py scripts/run_lens_myeongni.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py scripts/run_lens_sasang.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py scripts/run_lens_logos.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py @pyArgs
exit $LASTEXITCODE
