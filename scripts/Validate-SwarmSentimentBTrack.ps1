<#
.SYNOPSIS
  Run B-track Swarm sentiment JSONL validation: dummy wiring + optional [HYPO] sample.

.DESCRIPTION
  Fact-Lock: B-track only; no trading. Exits non-zero if either validation fails.

.NOTES
  From repo root:  .\scripts\Validate-SwarmSentimentBTrack.ps1
#>
param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$py = "scripts\validate_swarm_sentiment_dummy.py"
$hypo = "docs\final\hypo_test_sentiment.jsonl"

Write-Host "[B-track Swarm] validate dummy JSONL (wiring)..." -ForegroundColor Cyan
& py $py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path -LiteralPath (Join-Path $root $hypo))) {
    Write-Warning "Skip [HYPO] sample: missing $hypo"
    exit 0
}

Write-Host "[B-track Swarm] validate [HYPO] sample: $hypo ..." -ForegroundColor Cyan
& py $py --jsonl $hypo
exit $LASTEXITCODE
